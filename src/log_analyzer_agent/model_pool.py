"""Model pool for efficient model instance reuse.

This module provides a pool of language model instances to avoid the overhead
of creating new connections and authenticating on every request. Models are
cached by their configuration and reused across multiple analysis requests.

Key features:
- Thread-safe model instance caching
- Automatic cleanup of stale connections
- Health checking for model instances
- Graceful degradation if pooling fails
"""

import asyncio
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import weakref
from contextlib import asynccontextmanager

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from .configuration import ModelConfig, Configuration
from .utils import init_model_from_config


class ModelInstance:
    """Wrapper for a model instance with health tracking."""
    
    def __init__(self, model: BaseChatModel, config: ModelConfig):
        self.model = model
        self.config = config
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.usage_count = 0
        self.error_count = 0
        self.is_healthy = True
        
    def mark_used(self):
        """Mark the model as used."""
        self.last_used = datetime.now()
        self.usage_count += 1
        
    def mark_error(self):
        """Mark an error occurred with this model."""
        self.error_count += 1
        # Mark unhealthy after 3 consecutive errors
        if self.error_count >= 3:
            self.is_healthy = False
            
    def reset_error_count(self):
        """Reset error count after successful use."""
        self.error_count = 0
        self.is_healthy = True
        
    @property
    def age_seconds(self) -> float:
        """Get age of the model instance in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
        
    @property
    def idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return (datetime.now() - self.last_used).total_seconds()


class ModelPool:
    """Pool for managing model instances efficiently."""
    
    def __init__(
        self,
        max_instances_per_model: int = 5,
        max_idle_seconds: int = 600,  # 10 minutes
        max_lifetime_seconds: int = 3600,  # 1 hour
        health_check_interval: int = 300  # 5 minutes
    ):
        self._pools: Dict[str, list[ModelInstance]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.max_instances_per_model = max_instances_per_model
        self.max_idle_seconds = max_idle_seconds
        self.max_lifetime_seconds = max_lifetime_seconds
        self.health_check_interval = health_check_interval
        
        # Metrics
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "errors": 0,
            "health_checks": 0
        }
        
    async def start(self):
        """Start the cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def stop(self):
        """Stop the cleanup task and close all models."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
                
        # Close all models
        async with self._global_lock:
            for pool in self._pools.values():
                for instance in pool:
                    # Models don't have explicit close, but we can clear references
                    instance.model = None
            self._pools.clear()
            self._locks.clear()
    
    @asynccontextmanager
    async def get_model(self, config: ModelConfig):
        """Get a model from the pool or create a new one.
        
        This is a context manager that ensures the model is properly
        returned to the pool after use.
        
        Args:
            config: Model configuration
            
        Yields:
            Model instance ready for use
        """
        model_instance = await self._acquire_model(config)
        try:
            yield model_instance.model
            # Mark successful use
            model_instance.reset_error_count()
        except Exception as e:
            # Mark error
            model_instance.mark_error()
            raise
        finally:
            # Return to pool
            await self._release_model(model_instance)
    
    async def get_model_direct(self, config: ModelConfig) -> BaseChatModel:
        """Get a model directly (without context manager).
        
        Warning: This doesn't handle returning the model to the pool.
        Use the context manager version when possible.
        """
        instance = await self._acquire_model(config)
        return instance.model
    
    async def _acquire_model(self, config: ModelConfig) -> ModelInstance:
        """Acquire a model instance from the pool."""
        key = self._get_pool_key(config)
        
        # Ensure we have a lock for this model type
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
                self._pools[key] = []
        
        # Try to get from pool
        async with self._locks[key]:
            pool = self._pools[key]
            
            # Find a healthy, not-too-old instance
            for i, instance in enumerate(pool):
                if (instance.is_healthy and 
                    instance.age_seconds < self.max_lifetime_seconds and
                    instance.idle_seconds < self.max_idle_seconds):
                    # Remove from pool
                    pool.pop(i)
                    instance.mark_used()
                    self._metrics["hits"] += 1
                    return instance
            
            # No suitable instance found, create new one
            self._metrics["misses"] += 1
            
        # Create new instance outside the lock
        try:
            model = await init_model_from_config(config)
            instance = ModelInstance(model, config)
            return instance
        except Exception as e:
            self._metrics["errors"] += 1
            raise
    
    async def _release_model(self, instance: ModelInstance):
        """Release a model instance back to the pool."""
        if not instance.is_healthy:
            # Don't return unhealthy instances
            return
            
        key = self._get_pool_key(instance.config)
        
        async with self._locks[key]:
            pool = self._pools[key]
            
            # Only add back if pool isn't full and instance isn't too old
            if (len(pool) < self.max_instances_per_model and
                instance.age_seconds < self.max_lifetime_seconds):
                pool.append(instance)
            else:
                # Instance is evicted
                self._metrics["evictions"] += 1
    
    def _get_pool_key(self, config: ModelConfig) -> str:
        """Get the pool key for a model configuration."""
        return f"{config.provider}:{config.model_name}:{config.temperature}"
    
    async def _cleanup_loop(self):
        """Background task to clean up stale instances."""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._cleanup_stale_instances()
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue
                pass
    
    async def _cleanup_stale_instances(self):
        """Remove stale instances from all pools."""
        async with self._global_lock:
            for key, pool in self._pools.items():
                # Remove old or idle instances
                pool[:] = [
                    instance for instance in pool
                    if (instance.age_seconds < self.max_lifetime_seconds and
                        instance.idle_seconds < self.max_idle_seconds and
                        instance.is_healthy)
                ]
                
                # Track evictions
                evicted = len(pool) - len([i for i in pool if i.is_healthy])
                self._metrics["evictions"] += evicted
    
    async def _perform_health_checks(self):
        """Perform health checks on pooled instances."""
        self._metrics["health_checks"] += 1
        
        # Simple health check - just verify the model can be called
        test_pools = []
        async with self._global_lock:
            for key, pool in self._pools.items():
                if pool:
                    test_pools.append((key, pool[0]))
        
        for key, instance in test_pools:
            try:
                # Simple health check - try to invoke with minimal input
                await instance.model.ainvoke("test")
                instance.is_healthy = True
            except Exception:
                instance.is_healthy = False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics."""
        pool_sizes = {}
        # Note: This is a synchronous method, so we just read the current state
        # without locking. This is safe for metrics reading.
        for key, pool in self._pools.items():
            pool_sizes[key] = {
                "total": len(pool),
                "healthy": len([i for i in pool if i.is_healthy])
            }
        
        return {
            **self._metrics,
            "pools": pool_sizes,
            "hit_rate": (self._metrics["hits"] / 
                        (self._metrics["hits"] + self._metrics["misses"])
                        if self._metrics["hits"] + self._metrics["misses"] > 0 
                        else 0)
        }


# Global model pool instance
_model_pool: Optional[ModelPool] = None
_pool_lock = asyncio.Lock()


async def get_model_pool() -> ModelPool:
    """Get or create the global model pool instance."""
    global _model_pool
    
    async with _pool_lock:
        if _model_pool is None:
            _model_pool = ModelPool()
            await _model_pool.start()
        return _model_pool


async def get_pooled_model(config: ModelConfig) -> BaseChatModel:
    """Get a model from the global pool.
    
    This is a convenience function for backward compatibility.
    Prefer using the context manager for proper resource management.
    """
    pool = await get_model_pool()
    return await pool.get_model_direct(config)


# Context manager for pooled model usage
@asynccontextmanager
async def pooled_model(config: ModelConfig):
    """Context manager for using a pooled model.
    
    Example:
        async with pooled_model(config) as model:
            result = await model.ainvoke("Hello")
    """
    pool = await get_model_pool()
    async with pool.get_model(config) as model:
        yield model


# Cleanup function for graceful shutdown
async def cleanup_model_pool():
    """Clean up the global model pool."""
    global _model_pool
    
    async with _pool_lock:
        if _model_pool:
            await _model_pool.stop()
            _model_pool = None