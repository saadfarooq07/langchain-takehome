"""CLI tool for managing the analysis cache."""

import argparse
import json
from typing import Optional

from .cache import get_cache, configure_cache


def display_stats(cache):
    """Display cache statistics."""
    stats = cache.get_stats()
    
    print("\n=== Cache Statistics ===")
    print(f"Size: {stats['size']}/{cache.max_size} entries")
    print(f"Hit Rate: {stats['hit_rate']:.2%}")
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Evictions: {stats['evictions']}")
    print(f"Expirations: {stats['expirations']}")
    print(f"TTL: {cache.ttl_seconds} seconds")
    
    # Show most accessed entries
    most_accessed = cache.get_most_accessed(5)
    if most_accessed:
        print("\n=== Most Accessed Entries ===")
        for i, (key_prefix, hits) in enumerate(most_accessed, 1):
            print(f"{i}. {key_prefix} - {hits} hits")


def clear_cache(cache):
    """Clear all cache entries."""
    size_before = len(cache._cache)
    cache.clear()
    print(f"Cleared {size_before} entries from cache")


def prune_cache(cache):
    """Prune expired entries."""
    pruned = cache.prune_expired()
    print(f"Pruned {pruned} expired entries")


def configure_cache_settings(args):
    """Configure cache settings."""
    cache = configure_cache(
        max_size=args.max_size,
        ttl_seconds=args.ttl,
        enable_stats=not args.no_stats
    )
    print(f"Cache configured:")
    print(f"  Max Size: {cache.max_size}")
    print(f"  TTL: {cache.ttl_seconds} seconds")
    print(f"  Stats: {'Enabled' if cache.enable_stats else 'Disabled'}")
    return cache


def export_stats(cache, filepath: str):
    """Export cache statistics to JSON file."""
    stats = cache.get_stats()
    stats["most_accessed"] = cache.get_most_accessed(10)
    stats["config"] = {
        "max_size": cache.max_size,
        "ttl_seconds": cache.ttl_seconds,
        "enable_stats": cache.enable_stats
    }
    
    with open(filepath, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"Exported cache statistics to: {filepath}")


def main():
    """Main entry point for cache CLI."""
    parser = argparse.ArgumentParser(
        description="Manage the log analyzer cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View cache statistics
  python -m src.log_analyzer_agent.cache_utils.cache_cli stats
  
  # Clear the cache
  python -m src.log_analyzer_agent.cache_utils.cache_cli clear
  
  # Configure cache settings
  python -m src.log_analyzer_agent.cache_utils.cache_cli config --max-size 200 --ttl 7200
  
  # Prune expired entries
  python -m src.log_analyzer_agent.cache_utils.cache_cli prune
  
  # Export statistics
  python -m src.log_analyzer_agent.cache_utils.cache_cli export --output cache_stats.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Display cache statistics')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear all cache entries')
    clear_parser.add_argument(
        '--confirm',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Configure cache settings')
    config_parser.add_argument(
        '--max-size',
        type=int,
        default=100,
        help='Maximum number of cache entries (default: 100)'
    )
    config_parser.add_argument(
        '--ttl',
        type=int,
        default=3600,
        help='Time-to-live in seconds (default: 3600)'
    )
    config_parser.add_argument(
        '--no-stats',
        action='store_true',
        help='Disable statistics tracking'
    )
    
    # Prune command
    prune_parser = subparsers.add_parser('prune', help='Prune expired entries')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export cache statistics')
    export_parser.add_argument(
        '--output',
        '-o',
        default='cache_stats.json',
        help='Output file path (default: cache_stats.json)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Get or configure cache
    if args.command == 'config':
        cache = configure_cache_settings(args)
    else:
        cache = get_cache()
    
    # Execute command
    if args.command == 'stats':
        display_stats(cache)
    
    elif args.command == 'clear':
        if not args.confirm:
            response = input("Are you sure you want to clear the cache? (y/N): ")
            if response.lower() != 'y':
                print("Clear operation cancelled")
                return
        clear_cache(cache)
    
    elif args.command == 'prune':
        prune_cache(cache)
    
    elif args.command == 'export':
        export_stats(cache, args.output)


if __name__ == "__main__":
    main()