# Caching in Log Analyzer Agent

The Log Analyzer Agent includes a built-in caching system to improve performance by avoiding redundant analysis of identical logs.

## Overview

The caching system stores analysis results in memory using an LRU (Least Recently Used) eviction policy. When the agent encounters a log that has been previously analyzed with the same environment configuration, it returns the cached result instead of reprocessing.

## Features

- **In-memory LRU cache**: Automatically evicts least recently used entries when full
- **TTL support**: Entries expire after a configurable time period
- **Environment-aware**: Caches separately based on environment details
- **Statistics tracking**: Monitor cache performance and hit rates
- **CLI management**: Command-line tool for cache operations

## Configuration

Cache settings can be configured through the `Configuration` class:

```python
from src.log_analyzer_agent.configuration import Configuration

config = Configuration(
    enable_cache=True,          # Enable/disable caching
    cache_max_size=100,        # Maximum number of entries (1-1000)
    cache_ttl_seconds=3600     # Time-to-live in seconds (60-86400)
)
```

### Environment Variables

You can also configure cache settings via environment variables:

```bash
export LOG_ANALYZER_CACHE_ENABLED=true
export LOG_ANALYZER_CACHE_MAX_SIZE=200
export LOG_ANALYZER_CACHE_TTL=7200
```

## How It Works

1. **Key Generation**: Cache keys are generated using SHA-256 hash of:
   - Log content
   - Environment details (if provided)

2. **Cache Lookup**: Before analyzing, the agent checks for a cached result
   - If found and not expired: returns cached result
   - If not found or expired: proceeds with analysis

3. **Cache Storage**: After successful analysis, results are stored with:
   - Analysis result
   - Timestamp
   - Hit counter

4. **Eviction**: When cache is full, the least recently used entry is removed

## Cache Management CLI

The cache CLI tool provides various management commands:

### View Statistics

```bash
python -m src.log_analyzer_agent.utils.cache_cli stats
```

Output shows:
- Cache size and capacity
- Hit rate percentage
- Request counts (hits/misses)
- Eviction and expiration counts
- Most accessed entries

### Clear Cache

```bash
# With confirmation prompt
python -m src.log_analyzer_agent.utils.cache_cli clear

# Skip confirmation
python -m src.log_analyzer_agent.utils.cache_cli clear --confirm
```

### Configure Cache

```bash
python -m src.log_analyzer_agent.utils.cache_cli config \
    --max-size 200 \
    --ttl 7200 \
    --no-stats  # Disable statistics tracking
```

### Prune Expired Entries

```bash
python -m src.log_analyzer_agent.utils.cache_cli prune
```

### Export Statistics

```bash
python -m src.log_analyzer_agent.utils.cache_cli export \
    --output cache_stats.json
```

## Performance Considerations

### Benefits

1. **Reduced Processing Time**: Identical logs return instantly from cache
2. **Lower API Costs**: Fewer calls to LLM providers
3. **Consistent Results**: Same logs always return same analysis

### Trade-offs

1. **Memory Usage**: Each cached entry consumes memory
2. **Staleness**: Cached results may not reflect latest model improvements
3. **Cache Misses**: Different environment details create separate cache entries

## Best Practices

1. **Size Configuration**:
   - Development: 50-100 entries
   - Production: 200-500 entries (based on memory availability)

2. **TTL Configuration**:
   - Frequently changing logs: 15-30 minutes
   - Stable log patterns: 1-4 hours
   - Maximum recommended: 24 hours

3. **Monitoring**:
   - Check hit rate regularly (target >70% for stable workloads)
   - Monitor eviction rate (high rate indicates undersized cache)
   - Export statistics periodically for analysis

4. **Cache Warming**:
   - Pre-analyze common log patterns on startup
   - Use representative logs from your environment

## Implementation Details

### Cache Entry Structure

```python
@dataclass
class CacheEntry:
    result: Dict[str, Any]    # Analysis result
    timestamp: float          # Creation time
    hit_count: int = 0       # Access counter
```

### Thread Safety

The current implementation is designed for single-threaded use. For multi-threaded applications, consider adding locks:

```python
from threading import Lock

class ThreadSafeCache(AnalysisCache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock = Lock()
    
    def get(self, *args, **kwargs):
        with self._lock:
            return super().get(*args, **kwargs)
```

## Troubleshooting

### Low Hit Rate

- Check if logs have varying timestamps or IDs
- Ensure environment details are consistent
- Consider increasing cache size

### High Memory Usage

- Reduce cache_max_size
- Decrease cache_ttl_seconds
- Run prune command regularly

### Cache Not Working

- Verify enable_cache=True in configuration
- Check that log content is identical (including whitespace)
- Ensure environment details match exactly

## Future Enhancements

1. **Persistent Cache**: Save cache to disk for restart survival
2. **Distributed Cache**: Redis backend for multi-instance deployments
3. **Smart Invalidation**: Detect model updates and clear relevant entries
4. **Compression**: Store compressed results to increase capacity
5. **Pattern Matching**: Cache based on log patterns, not exact content