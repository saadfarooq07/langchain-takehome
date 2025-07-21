"""Rate limiter implementation for API quota protection.

This module provides rate limiting capabilities to prevent exceeding API quotas
and ensure fair resource usage. It supports multiple rate limiting strategies
including token bucket, sliding window, and fixed window algorithms.
"""

import time
import asyncio
from typing import Dict, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from collections import deque
from functools import wraps
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    calls_per_minute: int = 60
    calls_per_hour: Optional[int] = None
    calls_per_day: Optional[int] = None
    burst_size: Optional[int] = None  # For token bucket
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET


@dataclass
class RateLimitStats:
    """Statistics for rate limiter monitoring."""
    total_requests: int = 0
    allowed_requests: int = 0
    rejected_requests: int = 0
    current_tokens: float = 0
    last_refill_time: float = field(default_factory=time.time)
    rejection_reasons: Dict[str, int] = field(default_factory=dict)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimiter:
    """Rate limiter for API quota protection.
    
    Supports multiple rate limiting strategies:
    - Token Bucket: Allows bursts but maintains average rate
    - Sliding Window: Precise rate limiting over time windows
    - Fixed Window: Simple time-based windows
    
    Args:
        config: Rate limit configuration
        name: Name for this rate limiter
    """
    
    def __init__(self, config: RateLimitConfig, name: str = "default"):
        self.config = config
        self.name = name
        self._stats = RateLimitStats()
        
        # Token bucket state
        self._tokens = float(config.burst_size or config.calls_per_minute)
        self._max_tokens = float(config.burst_size or config.calls_per_minute)
        self._refill_rate = config.calls_per_minute / 60.0  # tokens per second
        
        # Sliding window state
        self._request_times: deque[float] = deque()
        
        # Fixed window state
        self._window_start = time.time()
        self._window_count = 0
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        current_time = time.time()
        elapsed = current_time - self._stats.last_refill_time
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self._refill_rate
        self._tokens = min(self._tokens + tokens_to_add, self._max_tokens)
        self._stats.last_refill_time = current_time
        self._stats.current_tokens = self._tokens
    
    async def _check_token_bucket(self, tokens_required: float = 1.0) -> Tuple[bool, Optional[float]]:
        """Check if request is allowed using token bucket algorithm."""
        await self._refill_tokens()
        
        if self._tokens >= tokens_required:
            self._tokens -= tokens_required
            self._stats.current_tokens = self._tokens
            return True, None
        else:
            # Calculate wait time
            tokens_needed = tokens_required - self._tokens
            wait_time = tokens_needed / self._refill_rate
            return False, wait_time
    
    async def _check_sliding_window(self) -> Tuple[bool, Optional[float]]:
        """Check if request is allowed using sliding window algorithm."""
        current_time = time.time()
        
        # Remove old requests outside the window
        window_start = current_time - 60.0  # 1 minute window
        while self._request_times and self._request_times[0] < window_start:
            self._request_times.popleft()
        
        # Check minute limit
        if len(self._request_times) >= self.config.calls_per_minute:
            # Calculate wait time until oldest request expires
            wait_time = self._request_times[0] + 60.0 - current_time
            return False, wait_time
        
        # Check hourly limit if configured
        if self.config.calls_per_hour:
            hour_start = current_time - 3600.0
            hour_requests = sum(1 for t in self._request_times if t >= hour_start)
            if hour_requests >= self.config.calls_per_hour:
                # Find the oldest request in the hour window
                for t in self._request_times:
                    if t >= hour_start:
                        wait_time = t + 3600.0 - current_time
                        return False, wait_time
        
        # Check daily limit if configured
        if self.config.calls_per_day:
            day_start = current_time - 86400.0
            day_requests = sum(1 for t in self._request_times if t >= day_start)
            if day_requests >= self.config.calls_per_day:
                # Find the oldest request in the day window
                for t in self._request_times:
                    if t >= day_start:
                        wait_time = t + 86400.0 - current_time
                        return False, wait_time
        
        # Request allowed
        self._request_times.append(current_time)
        return True, None
    
    async def _check_fixed_window(self) -> Tuple[bool, Optional[float]]:
        """Check if request is allowed using fixed window algorithm."""
        current_time = time.time()
        
        # Check if we need to reset the window
        if current_time - self._window_start >= 60.0:
            self._window_start = current_time
            self._window_count = 0
        
        # Check if under limit
        if self._window_count < self.config.calls_per_minute:
            self._window_count += 1
            return True, None
        else:
            # Calculate wait time until window resets
            wait_time = self._window_start + 60.0 - current_time
            return False, wait_time
    
    async def acquire(self, tokens: float = 1.0) -> None:
        """Acquire permission to make a request.
        
        Args:
            tokens: Number of tokens to consume (for token bucket)
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        async with self._lock:
            self._stats.total_requests += 1
            
            # Check rate limit based on strategy
            if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                allowed, wait_time = await self._check_token_bucket(tokens)
            elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                allowed, wait_time = await self._check_sliding_window()
            else:  # FIXED_WINDOW
                allowed, wait_time = await self._check_fixed_window()
            
            if allowed:
                self._stats.allowed_requests += 1
            else:
                self._stats.rejected_requests += 1
                reason = f"{self.config.strategy}_exceeded"
                self._stats.rejection_reasons[reason] = self._stats.rejection_reasons.get(reason, 0) + 1
                
                raise RateLimitExceeded(
                    f"Rate limit exceeded for '{self.name}'. Retry after {wait_time:.2f} seconds",
                    retry_after=wait_time
                )
    
    async def wait_and_acquire(self, tokens: float = 1.0, max_wait: Optional[float] = None) -> None:
        """Wait if necessary and acquire permission to make a request.
        
        Args:
            tokens: Number of tokens to consume
            max_wait: Maximum time to wait (None for unlimited)
            
        Raises:
            RateLimitExceeded: If wait time exceeds max_wait
        """
        start_time = time.time()
        
        while True:
            try:
                await self.acquire(tokens)
                return
            except RateLimitExceeded as e:
                if e.retry_after is None:
                    raise
                
                # Check if we've waited too long
                if max_wait is not None:
                    elapsed = time.time() - start_time
                    if elapsed + e.retry_after > max_wait:
                        raise RateLimitExceeded(
                            f"Would exceed max wait time of {max_wait}s",
                            retry_after=e.retry_after
                        )
                
                # Wait before retrying
                await asyncio.sleep(e.retry_after)
    
    def decorator(self, tokens: float = 1.0) -> Callable:
        """Decorator to apply rate limiting to a function."""
        def wrapper(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):
                @wraps(func)
                async def async_wrapped(*args, **kwargs):
                    await self.acquire(tokens)
                    return await func(*args, **kwargs)
                return async_wrapped
            else:
                @wraps(func)
                def sync_wrapped(*args, **kwargs):
                    # For sync functions, we need to run acquire in an event loop
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(self.acquire(tokens))
                        return func(*args, **kwargs)
                    finally:
                        loop.close()
                return sync_wrapped
        return wrapper
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        return {
            "name": self.name,
            "strategy": self.config.strategy,
            "total_requests": self._stats.total_requests,
            "allowed_requests": self._stats.allowed_requests,
            "rejected_requests": self._stats.rejected_requests,
            "current_tokens": self._stats.current_tokens if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET else None,
            "rejection_reasons": dict(self._stats.rejection_reasons),
            "config": {
                "calls_per_minute": self.config.calls_per_minute,
                "calls_per_hour": self.config.calls_per_hour,
                "calls_per_day": self.config.calls_per_day,
                "burst_size": self.config.burst_size
            }
        }
    
    def reset(self) -> None:
        """Reset the rate limiter state."""
        self._tokens = self._max_tokens
        self._request_times.clear()
        self._window_start = time.time()
        self._window_count = 0
        self._stats = RateLimitStats()
        logger.info(f"Rate limiter '{self.name}' reset")


# Global rate limiter registry
_rate_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(name: str = "default", config: Optional[RateLimitConfig] = None) -> RateLimiter:
    """Get or create a rate limiter instance.
    
    Args:
        name: Name of the rate limiter
        config: Configuration (required for first creation)
        
    Returns:
        RateLimiter instance
    """
    if name not in _rate_limiters:
        if config is None:
            config = RateLimitConfig()  # Default config
        _rate_limiters[name] = RateLimiter(config, name)
    return _rate_limiters[name]


def rate_limit(
    name: str = "default",
    calls_per_minute: int = 60,
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET,
    tokens: float = 1.0
) -> Callable:
    """Decorator factory for rate limiting.
    
    Usage:
        @rate_limit(name="api", calls_per_minute=30)
        async def call_api():
            ...
    """
    config = RateLimitConfig(
        calls_per_minute=calls_per_minute,
        strategy=strategy
    )
    
    def decorator(func: Callable) -> Callable:
        limiter = get_rate_limiter(name, config)
        return limiter.decorator(tokens)(func)
    
    return decorator


# Predefined rate limiters for common APIs
class APIRateLimiters:
    """Predefined rate limiters for common APIs."""
    
    @staticmethod
    def gemini() -> RateLimiter:
        """Rate limiter for Gemini API (60 requests per minute)."""
        config = RateLimitConfig(
            calls_per_minute=60,
            burst_size=10,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        return get_rate_limiter("gemini", config)
    
    @staticmethod
    def groq() -> RateLimiter:
        """Rate limiter for Groq API (30 requests per minute)."""
        config = RateLimitConfig(
            calls_per_minute=30,
            burst_size=5,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        return get_rate_limiter("groq", config)
    
    @staticmethod
    def tavily() -> RateLimiter:
        """Rate limiter for Tavily API (60 requests per minute)."""
        config = RateLimitConfig(
            calls_per_minute=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        return get_rate_limiter("tavily", config)