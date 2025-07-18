"""Simple caching utility for log analysis results.

This module provides a lightweight in-memory cache for storing
analysis results to avoid reprocessing identical logs.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class CacheEntry:
    """Represents a single cache entry."""
    
    result: Dict[str, Any]
    timestamp: float
    hit_count: int = 0
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if this entry has expired."""
        return (time.time() - self.timestamp) > ttl_seconds


class AnalysisCache:
    """Simple LRU cache for log analysis results.
    
    This cache stores analysis results keyed by a hash of the log content
    and environment details. It includes TTL support and size limits.
    """
    
    def __init__(
        self,
        max_size: int = 100,
        ttl_seconds: int = 3600,  # 1 hour default
        enable_stats: bool = True
    ):
        """Initialize the cache.
        
        Args:
            max_size: Maximum number of entries to store
            ttl_seconds: Time-to-live for cache entries in seconds
            enable_stats: Whether to track cache statistics
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_stats = enable_stats
        
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: list[str] = []  # For LRU eviction
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
    
    def _generate_key(self, log_content: str, environment_details: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key from log content and environment.
        
        Args:
            log_content: The log content to analyze
            environment_details: Optional environment context
            
        Returns:
            A hash key for the cache
        """
        # Create a stable string representation
        key_parts = [log_content]
        
        if environment_details:
            # Sort keys for consistent hashing
            env_str = json.dumps(environment_details, sort_keys=True)
            key_parts.append(env_str)
        
        combined = "|".join(key_parts)
        
        # Use SHA256 for a compact, collision-resistant key
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(
        self,
        log_content: str,
        environment_details: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a cached analysis result.
        
        Args:
            log_content: The log content that was analyzed
            environment_details: Optional environment context
            
        Returns:
            The cached analysis result, or None if not found/expired
        """
        key = self._generate_key(log_content, environment_details)
        
        if key not in self._cache:
            if self.enable_stats:
                self.stats["misses"] += 1
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry.is_expired(self.ttl_seconds):
            del self._cache[key]
            self._access_order.remove(key)
            if self.enable_stats:
                self.stats["expirations"] += 1
                self.stats["misses"] += 1
            return None
        
        # Update access order for LRU
        self._access_order.remove(key)
        self._access_order.append(key)
        
        # Update hit count and stats
        entry.hit_count += 1
        if self.enable_stats:
            self.stats["hits"] += 1
        
        return entry.result
    
    def put(
        self,
        log_content: str,
        analysis_result: Dict[str, Any],
        environment_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store an analysis result in the cache.
        
        Args:
            log_content: The log content that was analyzed
            analysis_result: The analysis result to cache
            environment_details: Optional environment context
        """
        key = self._generate_key(log_content, environment_details)
        
        # Remove existing entry if present
        if key in self._cache:
            self._access_order.remove(key)
        
        # Evict oldest entry if at capacity
        elif len(self._cache) >= self.max_size:
            oldest_key = self._access_order.pop(0)
            del self._cache[oldest_key]
            if self.enable_stats:
                self.stats["evictions"] += 1
        
        # Add new entry
        self._cache[key] = CacheEntry(
            result=analysis_result,
            timestamp=time.time()
        )
        self._access_order.append(key)
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
        self._access_order.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            **self.stats,
            "size": len(self._cache),
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }
    
    def prune_expired(self) -> int:
        """Remove all expired entries from the cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.is_expired(self.ttl_seconds):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            self._access_order.remove(key)
        
        if self.enable_stats:
            self.stats["expirations"] += len(expired_keys)
        
        return len(expired_keys)
    
    def get_most_accessed(self, n: int = 10) -> list[Tuple[str, int]]:
        """Get the most frequently accessed cache entries.
        
        Args:
            n: Number of entries to return
            
        Returns:
            List of (key_prefix, hit_count) tuples
        """
        entries = [
            (key[:8] + "...", entry.hit_count)
            for key, entry in self._cache.items()
        ]
        
        # Sort by hit count descending
        entries.sort(key=lambda x: x[1], reverse=True)
        
        return entries[:n]


# Global cache instance (lazy initialization)
_global_cache: Optional[AnalysisCache] = None


def get_cache() -> AnalysisCache:
    """Get or create the global cache instance.
    
    Returns:
        The global AnalysisCache instance
    """
    global _global_cache
    
    if _global_cache is None:
        _global_cache = AnalysisCache()
    
    return _global_cache


def configure_cache(
    max_size: int = 100,
    ttl_seconds: int = 3600,
    enable_stats: bool = True
) -> AnalysisCache:
    """Configure and return the global cache instance.
    
    Args:
        max_size: Maximum number of entries to store
        ttl_seconds: Time-to-live for cache entries
        enable_stats: Whether to track statistics
        
    Returns:
        The configured cache instance
    """
    global _global_cache
    
    _global_cache = AnalysisCache(
        max_size=max_size,
        ttl_seconds=ttl_seconds,
        enable_stats=enable_stats
    )
    
    return _global_cache