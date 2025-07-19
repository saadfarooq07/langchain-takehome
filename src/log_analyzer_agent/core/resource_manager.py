"""Resource Management System.

This module provides comprehensive resource management including database connection
pooling, memory monitoring, and resource lifecycle management.
"""

import asyncio
import psutil
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Callable, TypeVar, Generic, AsyncContextManager
from enum import Enum
import logging
import gc
from datetime import datetime, timedelta

try:
    import asyncpg
    from asyncpg import Pool
except ImportError:
    asyncpg = None
    Pool = None

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ResourceType(Enum):
    """Types of managed resources."""
    DATABASE_CONNECTION = "database_connection"
    HTTP_SESSION = "http_session"
    FILE_HANDLE = "file_handle"
    MEMORY_BUFFER = "memory_buffer"
    THREAD_POOL = "thread_pool"


@dataclass
class ResourceLimits:
    """Resource usage limits configuration."""
    # Memory limits
    max_memory_mb: int = 512
    memory_warning_threshold: float = 0.8  # 80% of max memory
    memory_check_interval: int = 30  # seconds
    
    # Database connection limits
    max_db_connections: int = 20
    min_db_connections: int = 5
    db_connection_timeout: int = 30
    db_connection_max_age: int = 3600  # 1 hour
    
    # General resource limits
    max_concurrent_operations: int = 50
    resource_cleanup_interval: int = 300  # 5 minutes
    max_resource_age: int = 1800  # 30 minutes


@dataclass
class ResourceMetrics:
    """Tracks resource usage metrics."""
    # Memory metrics
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    memory_warnings: int = 0
    
    # Connection metrics
    active_connections: int = 0
    peak_connections: int = 0
    connection_errors: int = 0
    
    # General metrics
    resource_count: Dict[ResourceType, int] = field(default_factory=dict)
    cleanup_runs: int = 0
    last_cleanup: Optional[float] = None
    
    def update_memory(self, current_mb: float) -> None:
        """Update memory metrics."""
        self.memory_usage_mb = current_mb
        if current_mb > self.peak_memory_mb:
            self.peak_memory_mb = current_mb
    
    def record_memory_warning(self) -> None:
        """Record a memory warning."""
        self.memory_warnings += 1
    
    def update_connections(self, count: int) -> None:
        """Update connection count."""
        self.active_connections = count
        if count > self.peak_connections:
            self.peak_connections = count
    
    def record_connection_error(self) -> None:
        """Record a connection error."""
        self.connection_errors += 1
    
    def update_resource_count(self, resource_type: ResourceType, count: int) -> None:
        """Update resource count for a type."""
        self.resource_count[resource_type] = count
    
    def record_cleanup(self) -> None:
        """Record a cleanup run."""
        self.cleanup_runs += 1
        self.last_cleanup = time.time()


class ManagedResource:
    """Wrapper for managed resources with lifecycle tracking."""
    
    def __init__(self, resource: Any, resource_type: ResourceType, 
                 cleanup_func: Optional[Callable[[Any], None]] = None):
        """Initialize managed resource.
        
        Args:
            resource: The actual resource
            resource_type: Type of resource
            cleanup_func: Optional cleanup function
        """
        self.resource = resource
        self.resource_type = resource_type
        self.cleanup_func = cleanup_func
        self.created_at = time.time()
        self.last_used = time.time()
        self.use_count = 0
        self.is_closed = False
    
    def use(self) -> Any:
        """Mark resource as used and return it."""
        if self.is_closed:
            raise RuntimeError("Resource has been closed")
        
        self.last_used = time.time()
        self.use_count += 1
        return self.resource
    
    def get_age(self) -> float:
        """Get resource age in seconds."""
        return time.time() - self.created_at
    
    def get_idle_time(self) -> float:
        """Get time since last use in seconds."""
        return time.time() - self.last_used
    
    async def close(self) -> None:
        """Close and cleanup the resource."""
        if self.is_closed:
            return
        
        self.is_closed = True
        
        if self.cleanup_func:
            try:
                if asyncio.iscoroutinefunction(self.cleanup_func):
                    await self.cleanup_func(self.resource)
                else:
                    self.cleanup_func(self.resource)
            except Exception as e:
                logger.error(f"Error during resource cleanup: {e}")


class DatabaseConnectionPool:
    """Async database connection pool with advanced management."""
    
    def __init__(self, connection_string: str, limits: ResourceLimits):
        """Initialize database connection pool.
        
        Args:
            connection_string: Database connection string
            limits: Resource limits configuration
        """
        if asyncpg is None:
            raise ImportError("asyncpg is required for database connection pooling")
        
        self.connection_string = connection_string
        self.limits = limits
        self._pool: Optional["Pool"] = None
        self._pool_lock = asyncio.Lock()
        self._active_connections: Set[str] = set()
        self._connection_metrics = {}
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        async with self._pool_lock:
            if self._pool is not None:
                return
            
            try:
                if asyncpg is None:
                    raise ImportError("asyncpg is required")
                self._pool = await asyncpg.create_pool(
                    self.connection_string,
                    min_size=self.limits.min_db_connections,
                    max_size=self.limits.max_db_connections,
                    command_timeout=self.limits.db_connection_timeout,
                    max_inactive_connection_lifetime=self.limits.db_connection_max_age
                )
                logger.info(f"Database pool initialized with {self.limits.min_db_connections}-{self.limits.max_db_connections} connections")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        if self._pool is None:
            await self.initialize()
        
        connection_id = f"conn_{time.time()}_{id(asyncio.current_task())}"
        
        try:
            async with self._pool.acquire() as connection:
                self._active_connections.add(connection_id)
                self._connection_metrics[connection_id] = {
                    "acquired_at": time.time(),
                    "query_count": 0
                }
                
                # Wrap connection to track usage
                wrapped_connection = ConnectionWrapper(connection, connection_id, self._connection_metrics)
                yield wrapped_connection
                
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            self._active_connections.discard(connection_id)
            self._connection_metrics.pop(connection_id, None)
    
    async def close(self) -> None:
        """Close the connection pool."""
        async with self._pool_lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
                logger.info("Database pool closed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        if self._pool is None:
            return {"status": "not_initialized"}
        
        return {
            "status": "active",
            "size": self._pool.get_size(),
            "available": self._pool.get_idle_size(),
            "active_connections": len(self._active_connections),
            "min_size": self._pool.get_min_size(),
            "max_size": self._pool.get_max_size(),
        }


class ConnectionWrapper:
    """Wrapper for database connections to track usage."""
    
    def __init__(self, connection, connection_id: str, metrics_dict: Dict):
        """Initialize connection wrapper.
        
        Args:
            connection: Database connection
            connection_id: Unique connection identifier
            metrics_dict: Shared metrics dictionary
        """
        self._connection = connection
        self._connection_id = connection_id
        self._metrics = metrics_dict
    
    async def execute(self, query: str, *args, **kwargs):
        """Execute query with metrics tracking."""
        start_time = time.time()
        try:
            result = await self._connection.execute(query, *args, **kwargs)
            self._metrics[self._connection_id]["query_count"] += 1
            return result
        except Exception as e:
            logger.error(f"Query failed on {self._connection_id}: {e}")
            raise
        finally:
            execution_time = time.time() - start_time
            logger.debug(f"Query executed in {execution_time:.3f}s on {self._connection_id}")
    
    async def fetch(self, query: str, *args, **kwargs):
        """Fetch query results with metrics tracking."""
        start_time = time.time()
        try:
            result = await self._connection.fetch(query, *args, **kwargs)
            self._metrics[self._connection_id]["query_count"] += 1
            return result
        except Exception as e:
            logger.error(f"Fetch failed on {self._connection_id}: {e}")
            raise
        finally:
            execution_time = time.time() - start_time
            logger.debug(f"Fetch executed in {execution_time:.3f}s on {self._connection_id}")
    
    async def fetchrow(self, query: str, *args, **kwargs):
        """Fetch single row with metrics tracking."""
        start_time = time.time()
        try:
            result = await self._connection.fetchrow(query, *args, **kwargs)
            self._metrics[self._connection_id]["query_count"] += 1
            return result
        except Exception as e:
            logger.error(f"Fetchrow failed on {self._connection_id}: {e}")
            raise
        finally:
            execution_time = time.time() - start_time
            logger.debug(f"Fetchrow executed in {execution_time:.3f}s on {self._connection_id}")


class MemoryMonitor:
    """System memory monitoring and management."""
    
    def __init__(self, limits: ResourceLimits):
        """Initialize memory monitor.
        
        Args:
            limits: Resource limits configuration
        """
        self.limits = limits
        self.process = psutil.Process()
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable[[float], None]] = []
    
    def add_warning_callback(self, callback: Callable[[float], None]) -> None:
        """Add callback for memory warnings.
        
        Args:
            callback: Function to call when memory exceeds threshold
        """
        self._callbacks.append(callback)
    
    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        memory_info = self.process.memory_info()
        return memory_info.rss / (1024 * 1024)  # Convert bytes to MB
    
    def get_memory_percent(self) -> float:
        """Get memory usage as percentage of limit."""
        current_mb = self.get_memory_usage_mb()
        return current_mb / self.limits.max_memory_mb
    
    def check_memory_threshold(self) -> bool:
        """Check if memory usage exceeds warning threshold."""
        return self.get_memory_percent() > self.limits.memory_warning_threshold
    
    async def start_monitoring(self) -> None:
        """Start memory monitoring task."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Memory monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop memory monitoring task."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Memory monitoring stopped")
    
    async def _monitor_loop(self) -> None:
        """Memory monitoring loop."""
        while self._monitoring:
            try:
                current_mb = self.get_memory_usage_mb()
                
                if self.check_memory_threshold():
                    logger.warning(f"Memory usage high: {current_mb:.1f}MB ({self.get_memory_percent()*100:.1f}%)")
                    
                    # Trigger callbacks
                    for callback in self._callbacks:
                        try:
                            callback(current_mb)
                        except Exception as e:
                            logger.error(f"Memory warning callback failed: {e}")
                    
                    # Force garbage collection
                    gc.collect()
                
                await asyncio.sleep(self.limits.memory_check_interval)
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying


class ResourceManager:
    """Centralized resource management system."""
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        """Initialize resource manager.
        
        Args:
            limits: Optional custom resource limits
        """
        self.limits = limits or ResourceLimits()
        self.metrics = ResourceMetrics()
        
        # Resource tracking
        self._resources: Dict[str, ManagedResource] = {}
        self._resource_lock = asyncio.Lock()
        
        # Database connection pool
        self._db_pool: Optional[DatabaseConnectionPool] = None
        
        # Memory monitoring
        self.memory_monitor = MemoryMonitor(self.limits)
        self.memory_monitor.add_warning_callback(self._handle_memory_warning)
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def initialize(self, database_url: Optional[str] = None) -> None:
        """Initialize resource manager.
        
        Args:
            database_url: Optional database connection string
        """
        self._running = True
        
        # Initialize database pool if URL provided
        if database_url:
            self._db_pool = DatabaseConnectionPool(database_url, self.limits)
            await self._db_pool.initialize()
        
        # Start memory monitoring
        await self.memory_monitor.start_monitoring()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Resource manager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown resource manager and cleanup all resources."""
        self._running = False
        
        # Stop monitoring
        await self.memory_monitor.stop_monitoring()
        
        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close database pool
        if self._db_pool:
            await self._db_pool.close()
        
        # Cleanup all managed resources
        await self._cleanup_all_resources()
        
        logger.info("Resource manager shutdown complete")
    
    @asynccontextmanager
    async def get_database_connection(self):
        """Get database connection with automatic cleanup."""
        if self._db_pool is None:
            raise RuntimeError("Database pool not initialized")
        
        async with self._db_pool.get_connection() as connection:
            self.metrics.update_connections(len(self._db_pool._active_connections))
            yield connection
    
    async def register_resource(self, resource_id: str, resource: T, 
                              resource_type: ResourceType,
                              cleanup_func: Optional[Callable[[T], None]] = None) -> ManagedResource[T]:
        """Register a resource for management.
        
        Args:
            resource_id: Unique identifier for the resource
            resource: The resource to manage
            resource_type: Type of resource
            cleanup_func: Optional cleanup function
            
        Returns:
            Managed resource wrapper
        """
        async with self._resource_lock:
            if resource_id in self._resources:
                raise ValueError(f"Resource {resource_id} already registered")
            
            managed_resource = ManagedResource(resource, resource_type, cleanup_func)
            self._resources[resource_id] = managed_resource
            
            # Update metrics
            current_count = self.metrics.resource_count.get(resource_type, 0)
            self.metrics.update_resource_count(resource_type, current_count + 1)
            
            logger.debug(f"Registered resource {resource_id} of type {resource_type.value}")
            return managed_resource
    
    async def unregister_resource(self, resource_id: str) -> None:
        """Unregister and cleanup a resource.
        
        Args:
            resource_id: Resource identifier
        """
        async with self._resource_lock:
            if resource_id not in self._resources:
                return
            
            resource = self._resources.pop(resource_id)
            await resource.close()
            
            # Update metrics
            current_count = self.metrics.resource_count.get(resource.resource_type, 0)
            self.metrics.update_resource_count(resource.resource_type, max(0, current_count - 1))
            
            logger.debug(f"Unregistered resource {resource_id}")
    
    def _handle_memory_warning(self, memory_mb: float) -> None:
        """Handle memory warning by triggering cleanup."""
        self.metrics.record_memory_warning()
        logger.warning(f"Memory warning triggered at {memory_mb:.1f}MB")
        
        # Schedule immediate cleanup
        asyncio.create_task(self._emergency_cleanup())
    
    async def _emergency_cleanup(self) -> None:
        """Emergency cleanup when memory is high."""
        async with self._resource_lock:
            # Find old or idle resources to clean up
            to_cleanup = []
            current_time = time.time()
            
            for resource_id, resource in self._resources.items():
                if (resource.get_age() > self.limits.max_resource_age or 
                    resource.get_idle_time() > 300):  # 5 minutes idle
                    to_cleanup.append(resource_id)
            
            # Cleanup identified resources
            for resource_id in to_cleanup:
                await self.unregister_resource(resource_id)
            
            if to_cleanup:
                logger.info(f"Emergency cleanup removed {len(to_cleanup)} resources")
        
        # Force garbage collection
        gc.collect()
    
    async def _cleanup_loop(self) -> None:
        """Regular cleanup loop."""
        while self._running:
            try:
                await self._routine_cleanup()
                await asyncio.sleep(self.limits.resource_cleanup_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _routine_cleanup(self) -> None:
        """Routine resource cleanup."""
        async with self._resource_lock:
            current_time = time.time()
            to_cleanup = []
            
            for resource_id, resource in self._resources.items():
                # Cleanup old resources
                if resource.get_age() > self.limits.max_resource_age:
                    to_cleanup.append(resource_id)
                # Cleanup idle resources (more aggressive threshold)
                elif resource.get_idle_time() > 1800:  # 30 minutes idle
                    to_cleanup.append(resource_id)
            
            # Cleanup identified resources
            for resource_id in to_cleanup:
                await self.unregister_resource(resource_id)
            
            self.metrics.record_cleanup()
            
            if to_cleanup:
                logger.debug(f"Routine cleanup removed {len(to_cleanup)} resources")
    
    async def _cleanup_all_resources(self) -> None:
        """Cleanup all managed resources."""
        async with self._resource_lock:
            resource_ids = list(self._resources.keys())
            
            for resource_id in resource_ids:
                await self.unregister_resource(resource_id)
            
            logger.info(f"Cleaned up {len(resource_ids)} resources")
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get comprehensive resource statistics."""
        # Update current memory usage
        current_memory = self.memory_monitor.get_memory_usage_mb()
        self.metrics.update_memory(current_memory)
        
        stats = {
            "memory": {
                "current_mb": round(current_memory, 2),
                "peak_mb": round(self.metrics.peak_memory_mb, 2),
                "limit_mb": self.limits.max_memory_mb,
                "usage_percent": round(self.memory_monitor.get_memory_percent() * 100, 1),
                "warnings": self.metrics.memory_warnings,
            },
            "database": self._db_pool.get_stats() if self._db_pool else {"status": "not_configured"},
            "resources": {
                "total_managed": len(self._resources),
                "by_type": dict(self.metrics.resource_count),
                "cleanup_runs": self.metrics.cleanup_runs,
                "last_cleanup": datetime.fromtimestamp(self.metrics.last_cleanup).isoformat() if self.metrics.last_cleanup else None,
            },
            "limits": {
                "max_memory_mb": self.limits.max_memory_mb,
                "max_db_connections": self.limits.max_db_connections,
                "max_concurrent_operations": self.limits.max_concurrent_operations,
            }
        }
        
        return stats


# Global resource manager instance
_global_resource_manager: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    """Get global resource manager instance."""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = ResourceManager()
    return _global_resource_manager


async def initialize_resources(database_url: Optional[str] = None, 
                             limits: Optional[ResourceLimits] = None) -> None:
    """Initialize global resource manager.
    
    Args:
        database_url: Optional database connection string
        limits: Optional custom resource limits
    """
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = ResourceManager(limits)
    
    await _global_resource_manager.initialize(database_url)


async def shutdown_resources() -> None:
    """Shutdown global resource manager."""
    global _global_resource_manager
    if _global_resource_manager is not None:
        await _global_resource_manager.shutdown()
        _global_resource_manager = None 