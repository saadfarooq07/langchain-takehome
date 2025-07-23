"""Utilities for persistence and reliability in LangGraph workflows.

This module provides task wrappers and utilities to ensure workflows can be
safely resumed without repeating side effects or producing inconsistent results.
"""

import hashlib
import json
import time
import os
from typing import Any, Dict, Optional, TypeVar, Callable, Union
from functools import wraps
from datetime import datetime
from pathlib import Path
import asyncio
import logging

from langgraph.prebuilt import task
from langchain_core.runnables import RunnableConfig

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic functions
T = TypeVar('T')


# Configuration for persistence behavior
class PersistenceConfig:
    """Configuration for persistence and reliability features."""
    def __init__(self):
        # Try to import from main configuration first
        try:
            from .configuration import Configuration
            config = Configuration()
            self.enable_task_wrapping = config.enable_task_wrapping
            self.deterministic_ids = config.deterministic_ids
            self.idempotency_ttl = config.idempotency_ttl
            self.log_side_effects = config.log_side_effects
            self.enable_debug_logging = config.enable_debug_logging
        except ImportError:
            # Fallback to environment variables
            self.enable_task_wrapping = os.getenv("ENABLE_TASK_WRAPPING", "true").lower() == "true"
            self.deterministic_ids = os.getenv("DETERMINISTIC_IDS", "true").lower() == "true"
            self.idempotency_ttl = int(os.getenv("IDEMPOTENCY_TTL", "3600"))
            self.log_side_effects = os.getenv("LOG_SIDE_EFFECTS", "false").lower() == "true"
            self.enable_debug_logging = os.getenv("ENABLE_DEBUG_LOGGING", "false").lower() == "true"


# Global configuration instance
persistence_config = PersistenceConfig()


# Task-wrapped logging functions
@task
async def log_debug(message: str, config: Optional[RunnableConfig] = None) -> None:
    """Task-wrapped debug logging to prevent repetition on resume."""
    if persistence_config.enable_debug_logging:
        print(f"[DEBUG] {message}")
        logger.debug(message)


@task
async def log_info(message: str, config: Optional[RunnableConfig] = None) -> None:
    """Task-wrapped info logging to prevent repetition on resume."""
    if persistence_config.log_side_effects:
        print(f"[INFO] {message}")
        logger.info(message)


@task
async def log_warning(message: str, config: Optional[RunnableConfig] = None) -> None:
    """Task-wrapped warning logging to prevent repetition on resume."""
    print(f"[WARNING] {message}")
    logger.warning(message)


@task
async def log_error(message: str, config: Optional[RunnableConfig] = None) -> None:
    """Task-wrapped error logging to prevent repetition on resume."""
    print(f"[ERROR] {message}")
    logger.error(message)


# Task-wrapped file operations
@task
async def save_to_file(filepath: Union[str, Path], content: str, config: Optional[RunnableConfig] = None) -> None:
    """Task-wrapped file write operation."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Write atomically to avoid partial writes
    temp_path = filepath.with_suffix(filepath.suffix + '.tmp')
    try:
        with open(temp_path, 'w') as f:
            f.write(content)
        temp_path.replace(filepath)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise


@task
async def save_json_to_file(filepath: Union[str, Path], data: Dict[str, Any], config: Optional[RunnableConfig] = None) -> None:
    """Task-wrapped JSON file write operation."""
    content = json.dumps(data, indent=2, sort_keys=True)
    await save_to_file(filepath, content, config)


@task
async def read_from_file(filepath: Union[str, Path], config: Optional[RunnableConfig] = None) -> str:
    """Task-wrapped file read operation."""
    with open(filepath, 'r') as f:
        return f.read()


@task
async def read_json_from_file(filepath: Union[str, Path], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Task-wrapped JSON file read operation."""
    content = await read_from_file(filepath, config)
    return json.loads(content)


# Deterministic ID and timestamp generation
def generate_deterministic_id(content: str, prefix: str = "id") -> str:
    """Generate a deterministic ID based on content hash.
    
    Args:
        content: Content to hash for ID generation
        prefix: Prefix for the ID
        
    Returns:
        Deterministic ID string
    """
    if not persistence_config.deterministic_ids:
        # Fallback to UUID for non-deterministic mode
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:16]}"
    
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return f"{prefix}_{content_hash[:16]}"


def generate_analysis_id(log_content: str, timestamp: Optional[float] = None) -> str:
    """Generate a deterministic analysis ID.
    
    Args:
        log_content: The log content being analyzed
        timestamp: Optional timestamp (will use current time if not provided)
        
    Returns:
        Deterministic analysis ID
    """
    if timestamp is None:
        timestamp = time.time()
    
    # Include timestamp in hash for uniqueness across runs
    content = f"{log_content[:1000]}_{int(timestamp)}"
    return generate_deterministic_id(content, "analysis")


def generate_memory_id(user_id: str, content: str, operation: str = "memory") -> str:
    """Generate a deterministic memory ID.
    
    Args:
        user_id: User identifier
        content: Content to store
        operation: Type of memory operation
        
    Returns:
        Deterministic memory ID
    """
    combined = f"{user_id}_{operation}_{content}"
    return generate_deterministic_id(combined, operation)


@task
async def get_workflow_timestamp(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> float:
    """Get or create a consistent timestamp for the workflow.
    
    This ensures the same timestamp is used throughout a workflow execution,
    even if the workflow is resumed after interruption.
    
    Args:
        state: The workflow state
        config: Optional runnable config
        
    Returns:
        Consistent timestamp for the workflow
    """
    # Check if timestamp already exists in state
    if "_workflow_timestamp" in state:
        return state["_workflow_timestamp"]
    
    # Generate new timestamp and store in state
    timestamp = time.time()
    state["_workflow_timestamp"] = timestamp
    return timestamp


# Idempotency utilities
class IdempotencyCache:
    """Simple in-memory cache for idempotency keys."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                # Expired, remove from cache
                del self._cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache with current timestamp."""
        self._cache[key] = (value, time.time())
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()


# Global idempotency cache
_idempotency_cache = IdempotencyCache(ttl_seconds=persistence_config.idempotency_ttl)


def generate_idempotency_key(operation: str, *args, **kwargs) -> str:
    """Generate an idempotency key for an operation.
    
    Args:
        operation: Name of the operation
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key
        
    Returns:
        Idempotency key string
    """
    # Create a stable string representation
    key_parts = [operation]
    
    # Add positional arguments
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        elif isinstance(arg, dict):
            # Sort dict keys for consistency
            key_parts.append(json.dumps(arg, sort_keys=True))
        else:
            # Use type name for complex objects
            key_parts.append(type(arg).__name__)
    
    # Add keyword arguments (sorted by key)
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}={v}")
        elif isinstance(v, dict):
            key_parts.append(f"{k}={json.dumps(v, sort_keys=True)}")
        else:
            key_parts.append(f"{k}={type(v).__name__}")
    
    # Generate hash of combined key
    combined_key = "|".join(key_parts)
    return hashlib.sha256(combined_key.encode()).hexdigest()


async def idempotent_operation(
    operation_name: str,
    operation_func: Callable[..., T],
    *args,
    cache_result: bool = True,
    **kwargs
) -> T:
    """Execute an operation with idempotency support.
    
    Args:
        operation_name: Name of the operation for key generation
        operation_func: The function to execute
        *args: Arguments to pass to the function
        cache_result: Whether to cache the result
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Result of the operation (from cache or fresh execution)
    """
    # Generate idempotency key
    idempotency_key = generate_idempotency_key(operation_name, *args, **kwargs)
    
    # Check cache
    if cache_result:
        cached_result = _idempotency_cache.get(idempotency_key)
        if cached_result is not None:
            await log_debug(f"Using cached result for {operation_name} (key: {idempotency_key[:8]}...)")
            return cached_result
    
    # Execute operation
    if asyncio.iscoroutinefunction(operation_func):
        result = await operation_func(*args, **kwargs)
    else:
        result = operation_func(*args, **kwargs)
    
    # Cache result
    if cache_result:
        _idempotency_cache.put(idempotency_key, result)
    
    return result


def idempotent(operation_name: Optional[str] = None, cache_result: bool = True):
    """Decorator to make a function idempotent.
    
    Args:
        operation_name: Name for the operation (defaults to function name)
        cache_result: Whether to cache results
        
    Returns:
        Decorated function with idempotency support
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        name = operation_name or func.__name__
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await idempotent_operation(name, func, *args, cache_result=cache_result, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                # Run in event loop if needed
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(
                        idempotent_operation(name, func, *args, cache_result=cache_result, **kwargs)
                    )
                finally:
                    loop.close()
            return sync_wrapper
    
    return decorator


# Utility to clean up expired cache entries
async def cleanup_idempotency_cache() -> None:
    """Clean up expired entries from the idempotency cache."""
    current_time = time.time()
    expired_keys = []
    
    for key, (_, timestamp) in _idempotency_cache._cache.items():
        if current_time - timestamp >= _idempotency_cache.ttl_seconds:
            expired_keys.append(key)
    
    for key in expired_keys:
        del _idempotency_cache._cache[key]
    
    if expired_keys:
        await log_debug(f"Cleaned up {len(expired_keys)} expired idempotency cache entries")


# Export all utilities
__all__ = [
    # Logging functions
    'log_debug',
    'log_info',
    'log_warning',
    'log_error',
    
    # File operations
    'save_to_file',
    'save_json_to_file',
    'read_from_file',
    'read_json_from_file',
    
    # ID generation
    'generate_deterministic_id',
    'generate_analysis_id',
    'generate_memory_id',
    
    # Timestamp utilities
    'get_workflow_timestamp',
    
    # Idempotency utilities
    'generate_idempotency_key',
    'idempotent_operation',
    'idempotent',
    'cleanup_idempotency_cache',
    
    # Configuration
    'PersistenceConfig',
    'persistence_config',
]