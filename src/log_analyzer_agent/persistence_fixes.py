"""Fixes for LangGraph persistence pitfalls.

This module contains patches and utilities to fix common pitfalls
in LangGraph workflows related to persistence and determinism.
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable, TypeVar
from functools import wraps
from datetime import datetime
import hashlib
import json

from .persistence_utils import (
    get_workflow_timestamp,
    generate_deterministic_id,
    log_debug, log_info
)

T = TypeVar('T')


class DeterministicCache:
    """A cache implementation that uses workflow timestamps for deterministic behavior."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
    
    async def get(self, key: str, state: Dict[str, Any]) -> Optional[Any]:
        """Get a value from cache using workflow timestamp."""
        if key in self._cache:
            entry = self._cache[key]
            workflow_time = await get_workflow_timestamp(state)
            
            # Use workflow timestamp for expiry check
            if workflow_time - entry["timestamp"] < self.ttl_seconds:
                await log_debug(f"Cache hit for key: {key[:8]}...")
                return entry["value"]
            else:
                # Expired
                del self._cache[key]
                await log_debug(f"Cache expired for key: {key[:8]}...")
        
        return None
    
    async def set(self, key: str, value: Any, state: Dict[str, Any]) -> None:
        """Set a value in cache using workflow timestamp."""
        workflow_time = await get_workflow_timestamp(state)
        self._cache[key] = {
            "value": value,
            "timestamp": workflow_time
        }
        await log_debug(f"Cached value for key: {key[:8]}...")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()


def capture_decision_time(decision_name: str):
    """Decorator to capture decision time in state for deterministic control flow.
    
    Usage:
        @capture_decision_time("cache_check")
        async def check_cache(state):
            # Decision time is now captured in state["decision_times"]["cache_check"]
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(state: Dict[str, Any], *args, **kwargs):
            # Initialize decision times dict if needed
            if "decision_times" not in state:
                state["decision_times"] = {}
            
            # Capture decision time if not already captured
            if decision_name not in state["decision_times"]:
                state["decision_times"][decision_name] = time.time()
                await log_debug(f"Captured decision time for: {decision_name}")
            
            # Call the original function
            if asyncio.iscoroutinefunction(func):
                return await func(state, *args, **kwargs)
            else:
                return func(state, *args, **kwargs)
        
        return wrapper
    return decorator


def use_captured_time(decision_name: str, default: Optional[float] = None):
    """Get a previously captured decision time from state.
    
    Args:
        decision_name: Name of the decision
        default: Default value if not found (defaults to current time)
        
    Returns:
        The captured timestamp
    """
    def get_time(state: Dict[str, Any]) -> float:
        decision_times = state.get("decision_times", {})
        if decision_name in decision_times:
            return decision_times[decision_name]
        elif default is not None:
            return default
        else:
            # Fallback to current time if not captured
            return time.time()
    
    return get_time


def deterministic_control_flow(decision_name: str):
    """Decorator for functions that make time-based control flow decisions.
    
    This ensures the same decision is made on resume by capturing the
    decision time on first execution.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(state: Dict[str, Any], *args, **kwargs):
            # Ensure decision times dict exists
            if "decision_times" not in state:
                state["decision_times"] = {}
            
            # Capture current time for this decision if not already done
            if decision_name not in state["decision_times"]:
                state["decision_times"][decision_name] = time.time()
            
            # Use the captured time for all decisions in this function
            decision_time = state["decision_times"][decision_name]
            
            # Inject the decision time into kwargs
            kwargs["_decision_time"] = decision_time
            
            # Call the original function
            if asyncio.iscoroutinefunction(func):
                return await func(state, *args, **kwargs)
            else:
                return func(state, *args, **kwargs)
        
        return wrapper
    return decorator


# Patches for existing cache implementations
def patch_cache_entry_is_expired(self, state: Optional[Dict[str, Any]] = None) -> bool:
    """Patched version of CacheEntry.is_expired that uses workflow timestamp."""
    if state and "_workflow_timestamp" in state:
        current_time = state["_workflow_timestamp"]
    else:
        # Fallback to real time if no workflow timestamp
        current_time = time.time()
    
    return current_time - self.created_at > self.ttl_seconds


def patch_cache_entry_access(self, state: Optional[Dict[str, Any]] = None):
    """Patched version of CacheEntry.access that uses workflow timestamp."""
    if state and "_workflow_timestamp" in state:
        self.last_accessed = state["_workflow_timestamp"]
    else:
        self.last_accessed = time.time()
    
    self.access_count += 1


# State immutability helpers
def immutable_update(state: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update state immutably by creating a new dictionary.
    
    This is the preferred pattern for LangGraph state updates.
    """
    return {**state, **updates}


def immutable_append(state: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
    """Append to a list in state immutably."""
    current_list = state.get(key, [])
    return immutable_update(state, {key: current_list + [value]})


def immutable_increment(state: Dict[str, Any], key: str, amount: int = 1) -> Dict[str, Any]:
    """Increment a counter in state immutably."""
    current_value = state.get(key, 0)
    return immutable_update(state, {key: current_value + amount})


# Utility to apply all fixes
async def apply_persistence_fixes():
    """Apply all persistence fixes to the codebase.
    
    This should be called at startup to patch existing implementations.
    """
    try:
        # Import and patch CacheEntry if it exists
        from .cache import CacheEntry
        CacheEntry.is_expired = patch_cache_entry_is_expired
        CacheEntry.access = patch_cache_entry_access
        await log_info("Applied persistence fixes to CacheEntry")
    except ImportError:
        pass
    
    # Additional patches can be added here
    
    await log_info("All persistence fixes applied")


# Export key utilities
__all__ = [
    'DeterministicCache',
    'capture_decision_time',
    'use_captured_time',
    'deterministic_control_flow',
    'immutable_update',
    'immutable_append',
    'immutable_increment',
    'apply_persistence_fixes',
]