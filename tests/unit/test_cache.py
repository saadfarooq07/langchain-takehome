"""Unit tests for the caching module."""

import pytest
import time
from unittest.mock import patch

from src.log_analyzer_agent.cache import (
    AnalysisCache,
    CacheEntry,
    get_cache,
    configure_cache
)


class TestCacheEntry:
    """Test the CacheEntry class."""
    
    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        result = {"issues": ["test issue"], "severity": "low"}
        entry = CacheEntry(result=result, timestamp=time.time())
        
        assert entry.result == result
        assert entry.hit_count == 0
        assert isinstance(entry.timestamp, float)
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration check."""
        # Create entry with past timestamp
        past_time = time.time() - 100
        entry = CacheEntry(result={}, timestamp=past_time)
        
        # Should be expired with 50 second TTL
        assert entry.is_expired(50) is True
        
        # Should not be expired with 200 second TTL
        assert entry.is_expired(200) is False
    
    def test_cache_entry_not_expired(self):
        """Test non-expired cache entry."""
        entry = CacheEntry(result={}, timestamp=time.time())
        
        # Recent entry should not be expired
        assert entry.is_expired(3600) is False


class TestAnalysisCache:
    """Test the AnalysisCache class."""
    
    def test_cache_initialization(self):
        """Test cache initialization with default values."""
        cache = AnalysisCache()
        
        assert cache.max_size == 100
        assert cache.ttl_seconds == 3600
        assert cache.enable_stats is True
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
    
    def test_cache_custom_initialization(self):
        """Test cache initialization with custom values."""
        cache = AnalysisCache(max_size=50, ttl_seconds=1800, enable_stats=False)
        
        assert cache.max_size == 50
        assert cache.ttl_seconds == 1800
        assert cache.enable_stats is False
    
    def test_key_generation_consistent(self):
        """Test that key generation is consistent."""
        cache = AnalysisCache()
        
        log = "Error in database connection"
        env = {"os": "Linux", "version": "5.0"}
        
        key1 = cache._generate_key(log, env)
        key2 = cache._generate_key(log, env)
        
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex digest length
    
    def test_key_generation_different_inputs(self):
        """Test that different inputs generate different keys."""
        cache = AnalysisCache()
        
        key1 = cache._generate_key("Log 1", {"os": "Linux"})
        key2 = cache._generate_key("Log 2", {"os": "Linux"})
        key3 = cache._generate_key("Log 1", {"os": "Windows"})
        key4 = cache._generate_key("Log 1", None)
        
        # All keys should be different
        keys = [key1, key2, key3, key4]
        assert len(set(keys)) == 4
    
    def test_cache_put_and_get(self):
        """Test basic cache put and get operations."""
        cache = AnalysisCache()
        
        log = "Test log content"
        result = {"issues": ["Issue 1"], "severity": "high"}
        
        # Put into cache
        cache.put(log, result)
        
        # Get from cache
        cached = cache.get(log)
        assert cached == result
        
        # Cache stats should be updated
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 0
    
    def test_cache_miss(self):
        """Test cache miss behavior."""
        cache = AnalysisCache()
        
        # Get non-existent entry
        result = cache.get("Non-existent log")
        assert result is None
        
        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 0
    
    def test_cache_expiration(self):
        """Test cache entry expiration."""
        cache = AnalysisCache(ttl_seconds=1)  # 1 second TTL
        
        log = "Test log"
        result = {"test": "data"}
        
        cache.put(log, result)
        
        # Should retrieve immediately
        assert cache.get(log) == result
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired now
        assert cache.get(log) is None
        assert cache.stats["expirations"] == 1
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = AnalysisCache(max_size=3)
        
        # Fill cache
        cache.put("log1", {"result": 1})
        cache.put("log2", {"result": 2})
        cache.put("log3", {"result": 3})
        
        # Access log1 to make it more recent
        cache.get("log1")
        
        # Add new entry, should evict log2 (least recently used)
        cache.put("log4", {"result": 4})
        
        assert cache.get("log1") is not None  # Still in cache
        assert cache.get("log2") is None      # Evicted
        assert cache.get("log3") is not None  # Still in cache
        assert cache.get("log4") is not None  # Newly added
        
        assert cache.stats["evictions"] == 1
    
    def test_cache_clear(self):
        """Test clearing the cache."""
        cache = AnalysisCache()
        
        # Add some entries
        cache.put("log1", {"result": 1})
        cache.put("log2", {"result": 2})
        
        assert len(cache._cache) == 2
        
        # Clear cache
        cache.clear()
        
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
        assert cache.get("log1") is None
        assert cache.get("log2") is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = AnalysisCache()
        
        # Perform various operations
        cache.put("log1", {"result": 1})
        cache.get("log1")  # Hit
        cache.get("log2")  # Miss
        cache.get("log1")  # Hit
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate"] == 2/3
    
    def test_prune_expired(self):
        """Test pruning expired entries."""
        cache = AnalysisCache(ttl_seconds=1)
        
        # Add entries at different times
        cache.put("log1", {"result": 1})
        time.sleep(0.5)
        cache.put("log2", {"result": 2})
        time.sleep(0.6)  # log1 should be expired, log2 still valid
        
        # Prune expired entries
        pruned = cache.prune_expired()
        
        assert pruned == 1
        assert cache.get("log1") is None
        assert cache.get("log2") is not None
    
    def test_most_accessed(self):
        """Test getting most accessed entries."""
        cache = AnalysisCache()
        
        # Add entries with different access patterns
        cache.put("log1", {"result": 1})
        cache.put("log2", {"result": 2})
        cache.put("log3", {"result": 3})
        
        # Access with different frequencies
        for _ in range(5):
            cache.get("log1")
        for _ in range(3):
            cache.get("log2")
        cache.get("log3")
        
        most_accessed = cache.get_most_accessed(2)
        
        assert len(most_accessed) == 2
        # First should be log1 with 5 hits
        assert most_accessed[0][1] == 5
        # Second should be log2 with 3 hits
        assert most_accessed[1][1] == 3
    
    def test_cache_with_environment_details(self):
        """Test caching with environment details."""
        cache = AnalysisCache()
        
        log = "Test log"
        result1 = {"result": "linux"}
        result2 = {"result": "windows"}
        
        # Same log, different environments
        cache.put(log, result1, {"os": "Linux"})
        cache.put(log, result2, {"os": "Windows"})
        
        # Should get different results based on environment
        assert cache.get(log, {"os": "Linux"})["result"] == "linux"
        assert cache.get(log, {"os": "Windows"})["result"] == "windows"
        assert cache.get(log, {"os": "MacOS"}) is None


class TestGlobalCache:
    """Test global cache functions."""
    
    def test_get_cache_singleton(self):
        """Test that get_cache returns the same instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        
        assert cache1 is cache2
    
    def test_configure_cache(self):
        """Test configuring the global cache."""
        # Configure with custom settings
        cache = configure_cache(
            max_size=50,
            ttl_seconds=1800,
            enable_stats=False
        )
        
        assert cache.max_size == 50
        assert cache.ttl_seconds == 1800
        assert cache.enable_stats is False
        
        # get_cache should return the configured instance
        assert get_cache() is cache
    
    @patch('src.log_analyzer_agent.utils.cache._global_cache', None)
    def test_get_cache_creates_default(self):
        """Test that get_cache creates default cache if none exists."""
        cache = get_cache()
        
        assert cache is not None
        assert cache.max_size == 100
        assert cache.ttl_seconds == 3600
        assert cache.enable_stats is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])