"""Caching and memoization for performance optimization.

This module provides caching mechanisms to improve performance by
avoiding redundant computations and API calls.
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, Any, Optional, Callable, TypeVar, Union
from functools import wraps, lru_cache
from dataclasses import dataclass, asdict
import pickle
from collections import OrderedDict

from .logging import get_logger
from .config import Config


logger = get_logger("log_analyzer.caching")

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Entry in the cache."""
    key: str
    value: Any
    timestamp: float
    ttl: Optional[float]
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl
    
    def access(self):
        """Record an access."""
        self.hit_count += 1


class LRUCache:
    """Least Recently Used cache implementation."""
    
    def __init__(self, max_size: int = 100):
        """Initialize LRU cache.
        
        Args:
            max_size: Maximum cache size
        """
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.logger = get_logger("log_analyzer.lru_cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        
        # Check expiration
        if entry.is_expired():
            self.logger.debug(f"Cache entry expired: {key}")
            del self.cache[key]
            self.misses += 1
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        entry.access()
        self.hits += 1
        
        self.logger.debug(f"Cache hit: {key}", extra={
            "hit_count": entry.hit_count,
            "age_seconds": time.time() - entry.timestamp
        })
        
        return entry.value
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None):
        """Put value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        # Remove oldest if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = next(iter(self.cache))
            self.logger.debug(f"Evicting oldest entry: {oldest_key}")
            del self.cache[oldest_key]
        
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl
        )
        
        self.cache[key] = entry
        self.cache.move_to_end(key)
        
        self.logger.debug(f"Cached: {key}", extra={"ttl": ttl})
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }


class StateCache:
    """Cache for state computations."""
    
    def __init__(self, config: Config):
        """Initialize state cache.
        
        Args:
            config: Configuration
        """
        self.config = config
        self.enabled = config.feature_flags.enable_caching
        self.cache = LRUCache(max_size=50)
        self.logger = get_logger("log_analyzer.state_cache")
    
    def _generate_key(self, prefix: str, data: Union[str, Dict[str, Any]]) -> str:
        """Generate cache key.
        
        Args:
            prefix: Key prefix
            data: Data to hash
            
        Returns:
            Cache key
        """
        if isinstance(data, str):
            content = data
        else:
            content = json.dumps(data, sort_keys=True)
        
        hash_value = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"{prefix}:{hash_value}"
    
    @lru_cache(maxsize=128)
    def get_node_visit_count(self, state_id: str, node_name: str) -> int:
        """Get cached node visit count.
        
        Args:
            state_id: State identifier
            node_name: Node name
            
        Returns:
            Visit count
        """
        # This is memoized at the function level
        return 0  # Default if not in working state
    
    async def get_analysis(
        self,
        log_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached analysis result.
        
        Args:
            log_content: Log content
            metadata: Additional metadata
            
        Returns:
            Cached analysis or None
        """
        if not self.enabled:
            return None
        
        key = self._generate_key("analysis", {
            "content": log_content[:1000],  # First 1000 chars
            "metadata": metadata or {}
        })
        
        return self.cache.get(key)
    
    async def put_analysis(
        self,
        log_content: str,
        analysis: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        ttl: float = 3600  # 1 hour default
    ):
        """Cache analysis result.
        
        Args:
            log_content: Log content
            analysis: Analysis result
            metadata: Additional metadata
            ttl: Time to live
        """
        if not self.enabled:
            return
        
        key = self._generate_key("analysis", {
            "content": log_content[:1000],
            "metadata": metadata or {}
        })
        
        self.cache.put(key, analysis, ttl=ttl)
    
    def get_preprocessed(self, log_content: str) -> Optional[Dict[str, Any]]:
        """Get cached preprocessing result.
        
        Args:
            log_content: Log content
            
        Returns:
            Cached result or None
        """
        if not self.enabled:
            return None
        
        key = self._generate_key("preprocess", log_content[:500])
        return self.cache.get(key)
    
    def put_preprocessed(
        self,
        log_content: str,
        result: Dict[str, Any],
        ttl: float = 1800  # 30 minutes
    ):
        """Cache preprocessing result.
        
        Args:
            log_content: Log content
            result: Preprocessing result
            ttl: Time to live
        """
        if not self.enabled:
            return
        
        key = self._generate_key("preprocess", log_content[:500])
        self.cache.put(key, result, ttl=ttl)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "enabled": self.enabled,
            **self.cache.get_stats()
        }


def memoize_async(
    ttl: Optional[float] = None,
    key_func: Optional[Callable] = None,
    cache_errors: bool = False
):
    """Decorator for memoizing async functions.
    
    Args:
        ttl: Time to live for cache entries
        key_func: Function to generate cache key from arguments
        cache_errors: Whether to cache errors
    """
    cache = LRUCache(max_size=100)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function
            try:
                result = await func(*args, **kwargs)
                cache.put(cache_key, result, ttl=ttl)
                return result
            except Exception as e:
                if cache_errors:
                    cache.put(cache_key, e, ttl=ttl or 60)  # Cache errors for 1 minute
                raise
        
        # Add cache management methods
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear
        wrapper.cache_stats = cache.get_stats
        
        return wrapper
    
    return decorator


class ComputationCache:
    """Cache for expensive computations."""
    
    def __init__(self):
        """Initialize computation cache."""
        self.cache = LRUCache(max_size=200)
        self.logger = get_logger("log_analyzer.computation_cache")
    
    @memoize_async(ttl=300)  # 5 minutes
    async def compute_patterns(self, lines: list[str]) -> list[str]:
        """Compute patterns with caching.
        
        Args:
            lines: Log lines
            
        Returns:
            Detected patterns
        """
        # Expensive pattern detection logic
        patterns = []
        # ... implementation ...
        return patterns
    
    def cached(
        self,
        ttl: Optional[float] = None,
        key_prefix: str = ""
    ):
        """Decorator for caching method results.
        
        Args:
            ttl: Time to live
            key_prefix: Prefix for cache keys
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(self_inner, *args, **kwargs):
                # Generate key
                key_parts = [key_prefix or func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
                
                # Check cache
                cached = self.cache.get(cache_key)
                if cached is not None:
                    self.logger.debug(f"Cache hit for {func.__name__}")
                    return cached
                
                # Compute
                result = await func(self_inner, *args, **kwargs)
                self.cache.put(cache_key, result, ttl=ttl)
                
                return result
            
            @wraps(func)
            def sync_wrapper(self_inner, *args, **kwargs):
                # Generate key
                key_parts = [key_prefix or func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
                
                # Check cache
                cached = self.cache.get(cache_key)
                if cached is not None:
                    self.logger.debug(f"Cache hit for {func.__name__}")
                    return cached
                
                # Compute
                result = func(self_inner, *args, **kwargs)
                self.cache.put(cache_key, result, ttl=ttl)
                
                return result
            
            # Return appropriate wrapper
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        
        return decorator


# Global caches
_state_cache: Optional[StateCache] = None
_computation_cache = ComputationCache()


def get_state_cache(config: Optional[Config] = None) -> StateCache:
    """Get global state cache instance.
    
    Args:
        config: Configuration (uses global if not provided)
        
    Returns:
        State cache instance
    """
    global _state_cache
    
    if _state_cache is None:
        from .config import get_config
        _state_cache = StateCache(config or get_config())
    
    return _state_cache


def get_computation_cache() -> ComputationCache:
    """Get global computation cache instance.
    
    Returns:
        Computation cache instance
    """
    return _computation_cache


def clear_all_caches():
    """Clear all caches."""
    logger.info("Clearing all caches")
    
    if _state_cache:
        _state_cache.cache.clear()
    
    _computation_cache.cache.clear()
    
    # Clear function-level caches
    import gc
    for obj in gc.get_objects():
        if hasattr(obj, 'cache') and hasattr(obj.cache, 'clear'):
            obj.cache.clear()