"""Bounded LRU cache implementation for analysis results.

This module provides a thread-safe, bounded LRU (Least Recently Used) cache
with TTL (Time To Live) support. It replaces the broken cache implementation
in graph.py with proper size limits, eviction policies, and async support.

Key features:
- Size-bounded with automatic eviction
- TTL support for time-based expiration
- Thread-safe for concurrent access
- Memory-efficient storage
- Comprehensive metrics
"""

import asyncio
import time
import hashlib
import sys
from typing import Dict, Any, Optional, Tuple, List
from collections import OrderedDict
from datetime import datetime, timedelta
import json


class CacheEntry:
    """Represents a single cache entry with metadata."""
    
    def __init__(self, key: str, value: Any, ttl_seconds: int):
        self.key = key
        self.value = value
        self.created_at = time.time()
        self.last_accessed = time.time()
        self.access_count = 0
        self.ttl_seconds = ttl_seconds
        self.size_bytes = self._estimate_size(value)
        
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds
        
    def access(self):
        """Mark this entry as accessed."""
        self.last_accessed = time.time()
        self.access_count += 1
        
    def _estimate_size(self, obj: Any) -> int:
        """Estimate the memory size of an object."""
        try:
            # For dictionaries and lists, serialize to JSON for size estimate
            if isinstance(obj, (dict, list)):
                return len(json.dumps(obj, default=str).encode('utf-8'))
            # For strings
            elif isinstance(obj, str):
                return len(obj.encode('utf-8'))
            # For other objects, use sys.getsizeof
            else:
                return sys.getsizeof(obj)
        except:
            # Fallback to a default size
            return 1024


class BoundedLRUCache:
    """Thread-safe bounded LRU cache with TTL support."""
    
    def __init__(
        self,
        max_size: int = 100,
        max_memory_mb: int = 100,
        default_ttl_seconds: int = 3600,
        eviction_batch_size: int = 10
    ):
        """Initialize the cache.
        
        Args:
            max_size: Maximum number of entries
            max_memory_mb: Maximum memory usage in MB
            default_ttl_seconds: Default TTL for entries
            eviction_batch_size: Number of entries to evict at once
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl_seconds = default_ttl_seconds
        self.eviction_batch_size = eviction_batch_size
        
        # Metrics
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "total_size_bytes": 0,
            "total_entries": 0
        }
        
    async def start(self):
        """Start the cleanup task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def stop(self):
        """Stop the cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
                
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._metrics["misses"] += 1
                return None
                
            # Check expiration
            if entry.is_expired():
                del self._cache[key]
                self._metrics["total_size_bytes"] -= entry.size_bytes
                self._metrics["total_entries"] -= 1
                self._metrics["expirations"] += 1
                self._metrics["misses"] += 1
                return None
                
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.access()
            self._metrics["hits"] += 1
            
            return entry.value
            
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional TTL override
        """
        ttl = ttl_seconds or self.default_ttl_seconds
        entry = CacheEntry(key, value, ttl)
        
        async with self._lock:
            # Remove old entry if exists
            if key in self._cache:
                old_entry = self._cache[key]
                self._metrics["total_size_bytes"] -= old_entry.size_bytes
                del self._cache[key]
            else:
                self._metrics["total_entries"] += 1
                
            # Add new entry
            self._cache[key] = entry
            self._metrics["total_size_bytes"] += entry.size_bytes
            
            # Check size limits and evict if necessary
            await self._evict_if_necessary()
            
    async def delete(self, key: str) -> bool:
        """Delete an entry from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if entry was deleted, False if not found
        """
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                del self._cache[key]
                self._metrics["total_size_bytes"] -= entry.size_bytes
                self._metrics["total_entries"] -= 1
                return True
            return False
            
    async def clear(self) -> None:
        """Clear all entries from the cache."""
        async with self._lock:
            self._cache.clear()
            self._metrics["total_size_bytes"] = 0
            self._metrics["total_entries"] = 0
            
    async def _evict_if_necessary(self) -> None:
        """Evict entries if cache exceeds limits."""
        # Check entry count limit
        entries_to_evict = max(0, len(self._cache) - self.max_size)
        
        # Check memory limit
        if self._metrics["total_size_bytes"] > self.max_memory_bytes:
            # Calculate how many more entries to evict based on average size
            avg_size = self._metrics["total_size_bytes"] / len(self._cache) if self._cache else 1024
            memory_excess = self._metrics["total_size_bytes"] - self.max_memory_bytes
            additional_evictions = int(memory_excess / avg_size) + 1
            entries_to_evict = max(entries_to_evict, additional_evictions)
            
        # Evict in batches
        entries_to_evict = min(entries_to_evict, self.eviction_batch_size)
        
        for _ in range(entries_to_evict):
            if not self._cache:
                break
                
            # Remove least recently used (first item)
            key, entry = self._cache.popitem(last=False)
            self._metrics["total_size_bytes"] -= entry.size_bytes
            self._metrics["total_entries"] -= 1
            self._metrics["evictions"] += 1
            
    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue
                pass
                
    async def _cleanup_expired(self) -> None:
        """Remove all expired entries."""
        async with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                    
            for key in expired_keys:
                entry = self._cache[key]
                del self._cache[key]
                self._metrics["total_size_bytes"] -= entry.size_bytes
                self._metrics["total_entries"] -= 1
                self._metrics["expirations"] += 1
                
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        hit_rate = 0.0
        total_requests = self._metrics["hits"] + self._metrics["misses"]
        if total_requests > 0:
            hit_rate = self._metrics["hits"] / total_requests
            
        return {
            **self._metrics,
            "hit_rate": hit_rate,
            "memory_usage_mb": self._metrics["total_size_bytes"] / (1024 * 1024),
            "avg_entry_size_kb": (
                self._metrics["total_size_bytes"] / self._metrics["total_entries"] / 1024
                if self._metrics["total_entries"] > 0 else 0
            )
        }
        
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        entries_info = []
        for key, entry in self._cache.items():
            entries_info.append({
                "key": key,
                "size_bytes": entry.size_bytes,
                "age_seconds": time.time() - entry.created_at,
                "access_count": entry.access_count,
                "expires_in": max(0, entry.ttl_seconds - (time.time() - entry.created_at))
            })
            
        return {
            "total_entries": len(self._cache),
            "total_size_bytes": self._metrics["total_size_bytes"],
            "max_size": self.max_size,
            "max_memory_bytes": self.max_memory_bytes,
            "entries": entries_info[:10]  # First 10 entries for debugging
        }


# Global cache instance
_analysis_cache: Optional[BoundedLRUCache] = None
_cache_lock = asyncio.Lock()


async def get_analysis_cache() -> BoundedLRUCache:
    """Get or create the global analysis cache instance."""
    global _analysis_cache
    
    async with _cache_lock:
        if _analysis_cache is None:
            _analysis_cache = BoundedLRUCache(
                max_size=int(os.getenv("CACHE_MAX_SIZE", "100")),
                max_memory_mb=int(os.getenv("CACHE_MAX_MEMORY_MB", "100")),
                default_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "3600"))
            )
            await _analysis_cache.start()
        return _analysis_cache


async def cache_analysis_result(
    log_content: str,
    analysis_result: Dict[str, Any],
    ttl_seconds: Optional[int] = None
) -> None:
    """Cache an analysis result.
    
    Args:
        log_content: The log content (used to generate cache key)
        analysis_result: The analysis result to cache
        ttl_seconds: Optional TTL override
    """
    cache = await get_analysis_cache()
    
    # Generate cache key from log content hash
    key = hashlib.sha256(log_content.encode()).hexdigest()
    
    await cache.set(key, analysis_result, ttl_seconds)


async def get_cached_analysis(log_content: str) -> Optional[Dict[str, Any]]:
    """Get a cached analysis result.
    
    Args:
        log_content: The log content (used to generate cache key)
        
    Returns:
        Cached analysis result or None
    """
    cache = await get_analysis_cache()
    
    # Generate cache key from log content hash
    key = hashlib.sha256(log_content.encode()).hexdigest()
    
    return await cache.get(key)


async def cleanup_analysis_cache():
    """Clean up the global analysis cache."""
    global _analysis_cache
    
    async with _cache_lock:
        if _analysis_cache:
            await _analysis_cache.stop()
            _analysis_cache = None


# Decorator for caching function results
def cached_analysis(ttl_seconds: Optional[int] = None):
    """Decorator to cache analysis function results.
    
    Example:
        @cached_analysis(ttl_seconds=1800)
        async def analyze_logs(state):
            # ... expensive analysis ...
            return result
    """
    def decorator(func):
        async def wrapper(state: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
            # Extract log content for cache key
            if hasattr(state, "get"):
                log_content = state.get("log_content", "")
            else:
                log_content = getattr(state, "log_content", "")
                
            # Check cache
            cached_result = await get_cached_analysis(log_content)
            if cached_result is not None:
                return {
                    "analysis_result": cached_result,
                    "messages": [{"content": "Retrieved from cache", "cached": True}]
                }
                
            # Call original function
            result = await func(state)
            
            # Cache successful results
            if result.get("analysis_result"):
                await cache_analysis_result(
                    log_content,
                    result["analysis_result"],
                    ttl_seconds
                )
                
            return result
            
        return wrapper
    return decorator