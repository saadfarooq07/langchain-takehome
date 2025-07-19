"""API Rate Limiting and Quota Management System.

This module provides comprehensive rate limiting, quota tracking, and intelligent
backoff strategies for external API calls (Gemini, Groq, Tavily).
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Awaitable
from contextlib import asynccontextmanager
from functools import wraps
import logging
import json
import os
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

T = TypeVar('T')


class APIProvider(Enum):
    """Supported API providers."""
    GEMINI = "gemini"
    GROQ = "groq" 
    TAVILY = "tavily"
    OPENAI = "openai"


@dataclass
class APILimits:
    """API limits configuration for a provider."""
    # Rate limits (requests per time period)
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    
    # Token/usage limits
    tokens_per_minute: int = 50000
    tokens_per_hour: int = 500000
    tokens_per_day: int = 1000000
    
    # Cost limits (in USD)
    cost_per_hour: float = 5.0
    cost_per_day: float = 50.0
    
    # Concurrent request limits
    max_concurrent_requests: int = 10
    
    # Backoff settings
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    max_retries: int = 3


@dataclass
class APIUsage:
    """Tracks API usage metrics."""
    requests_count: int = 0
    tokens_used: int = 0
    cost_incurred: float = 0.0
    last_request_time: Optional[float] = None
    last_reset_time: float = field(default_factory=time.time)
    
    # Error tracking
    error_count: int = 0
    last_error_time: Optional[float] = None
    consecutive_errors: int = 0
    
    def reset_if_needed(self, window_seconds: int) -> None:
        """Reset counters if the time window has passed."""
        current_time = time.time()
        if current_time - self.last_reset_time >= window_seconds:
            self.requests_count = 0
            self.tokens_used = 0
            if window_seconds >= 3600:  # Only reset cost for hourly+ windows
                self.cost_incurred = 0.0
            self.last_reset_time = current_time
    
    def record_request(self, tokens: int = 0, cost: float = 0.0) -> None:
        """Record a successful API request."""
        self.requests_count += 1
        self.tokens_used += tokens
        self.cost_incurred += cost
        self.last_request_time = time.time()
        self.consecutive_errors = 0  # Reset error streak on success
    
    def record_error(self) -> None:
        """Record an API error."""
        self.error_count += 1
        self.consecutive_errors += 1
        self.last_error_time = time.time()


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        async with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """Wait until enough tokens are available."""
        while not await self.consume(tokens):
            # Calculate wait time
            wait_time = tokens / self.refill_rate
            await asyncio.sleep(min(wait_time, 1.0))  # Cap at 1 second


class BackoffStrategy:
    """Intelligent backoff strategy with jitter."""
    
    def __init__(self, initial_delay: float = 1.0, max_delay: float = 60.0, 
                 multiplier: float = 2.0, jitter: bool = True):
        """Initialize backoff strategy.
        
        Args:
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Delay multiplier for each retry
            jitter: Whether to add random jitter
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.attempt = 0
    
    def get_delay(self) -> float:
        """Get delay for current attempt."""
        delay = self.initial_delay * (self.multiplier ** self.attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add random jitter (±25%)
            import random
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def next_attempt(self) -> float:
        """Move to next attempt and return delay."""
        delay = self.get_delay()
        self.attempt += 1
        return delay
    
    def reset(self) -> None:
        """Reset to initial state."""
        self.attempt = 0


class APIRateLimiter:
    """Comprehensive rate limiter for API providers."""
    
    def __init__(self, provider: APIProvider, limits: Optional[APILimits] = None):
        """Initialize rate limiter for a provider.
        
        Args:
            provider: API provider
            limits: Optional custom limits
        """
        self.provider = provider
        self.limits = limits or self._get_default_limits(provider)
        
        # Token buckets for different time windows
        self.minute_bucket = TokenBucket(
            self.limits.requests_per_minute, 
            self.limits.requests_per_minute / 60.0
        )
        self.hour_bucket = TokenBucket(
            self.limits.requests_per_hour,
            self.limits.requests_per_hour / 3600.0
        )
        
        # Usage tracking
        self.minute_usage = APIUsage()
        self.hour_usage = APIUsage()
        self.daily_usage = APIUsage()
        
        # Concurrency control
        self._concurrent_semaphore = asyncio.Semaphore(self.limits.max_concurrent_requests)
        
        # Backoff management
        self._backoff_strategy = BackoffStrategy(
            self.limits.initial_backoff_seconds,
            self.limits.max_backoff_seconds,
            self.limits.backoff_multiplier
        )
    
    def _get_default_limits(self, provider: APIProvider) -> APILimits:
        """Get default limits based on provider."""
        # These are conservative defaults - adjust based on actual API limits
        if provider == APIProvider.GEMINI:
            return APILimits(
                requests_per_minute=15,  # Conservative for free tier
                requests_per_hour=1000,
                tokens_per_minute=32000,
                cost_per_hour=2.0
            )
        elif provider == APIProvider.GROQ:
            return APILimits(
                requests_per_minute=30,
                requests_per_hour=14400,
                tokens_per_minute=7000,
                cost_per_hour=1.0
            )
        elif provider == APIProvider.TAVILY:
            return APILimits(
                requests_per_minute=20,
                requests_per_hour=1000,
                cost_per_hour=0.5
            )
        else:
            return APILimits()  # Default limits
    
    async def can_make_request(self, estimated_tokens: int = 100) -> bool:
        """Check if a request can be made within limits.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            True if request can be made
        """
        # Update usage windows
        self.minute_usage.reset_if_needed(60)
        self.hour_usage.reset_if_needed(3600)
        self.daily_usage.reset_if_needed(86400)
        
        # Check token buckets
        if not await self.minute_bucket.consume(1):
            return False
        if not await self.hour_bucket.consume(1):
            return False
        
        # Check token limits
        if (self.minute_usage.tokens_used + estimated_tokens > self.limits.tokens_per_minute):
            return False
        if (self.hour_usage.tokens_used + estimated_tokens > self.limits.tokens_per_hour):
            return False
        
        # Check cost limits
        estimated_cost = self._estimate_cost(estimated_tokens)
        if (self.hour_usage.cost_incurred + estimated_cost > self.limits.cost_per_hour):
            return False
        if (self.daily_usage.cost_incurred + estimated_cost > self.limits.cost_per_day):
            return False
        
        return True
    
    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost for token usage based on provider."""
        # Rough cost estimates per 1000 tokens
        cost_per_1k_tokens = {
            APIProvider.GEMINI: 0.00015,  # Flash model pricing
            APIProvider.GROQ: 0.0001,    # Approximate
            APIProvider.TAVILY: 0.001,   # Per search
        }
        
        base_cost = cost_per_1k_tokens.get(self.provider, 0.0001)
        return (tokens / 1000) * base_cost
    
    @asynccontextmanager
    async def make_request(self, estimated_tokens: int = 100):
        """Context manager for making API requests with rate limiting.
        
        Args:
            estimated_tokens: Estimated tokens for the request
        """
        # Wait for rate limit availability
        while not await self.can_make_request(estimated_tokens):
            await asyncio.sleep(0.1)
        
        # Acquire concurrency semaphore
        async with self._concurrent_semaphore:
            request_start = time.time()
            
            try:
                yield
                
                # Record successful request
                actual_cost = self._estimate_cost(estimated_tokens)
                self.minute_usage.record_request(estimated_tokens, actual_cost)
                self.hour_usage.record_request(estimated_tokens, actual_cost)
                self.daily_usage.record_request(estimated_tokens, actual_cost)
                
                # Reset backoff on success
                self._backoff_strategy.reset()
                
            except Exception as e:
                # Record error
                self.minute_usage.record_error()
                self.hour_usage.record_error()
                self.daily_usage.record_error()
                
                # Apply backoff if needed
                if self.minute_usage.consecutive_errors >= 3:
                    backoff_delay = self._backoff_strategy.next_attempt()
                    logger.warning(f"API {self.provider.value} backing off for {backoff_delay:.2f}s after {self.minute_usage.consecutive_errors} errors")
                    await asyncio.sleep(backoff_delay)
                
                raise
            
            finally:
                request_time = time.time() - request_start
                logger.debug(f"API {self.provider.value} request completed in {request_time:.2f}s")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            "provider": self.provider.value,
            "minute_usage": {
                "requests": self.minute_usage.requests_count,
                "tokens": self.minute_usage.tokens_used,
                "cost": round(self.minute_usage.cost_incurred, 4),
                "errors": self.minute_usage.error_count,
            },
            "hour_usage": {
                "requests": self.hour_usage.requests_count,
                "tokens": self.hour_usage.tokens_used,
                "cost": round(self.hour_usage.cost_incurred, 4),
                "errors": self.hour_usage.error_count,
            },
            "daily_usage": {
                "requests": self.daily_usage.requests_count,
                "tokens": self.daily_usage.tokens_used,
                "cost": round(self.daily_usage.cost_incurred, 4),
                "errors": self.daily_usage.error_count,
            },
            "limits": {
                "requests_per_minute": self.limits.requests_per_minute,
                "tokens_per_minute": self.limits.tokens_per_minute,
                "cost_per_hour": self.limits.cost_per_hour,
                "cost_per_day": self.limits.cost_per_day,
            }
        }


class APIManager:
    """Centralized API management with rate limiting and quota tracking."""
    
    def __init__(self):
        """Initialize API manager."""
        self.rate_limiters: Dict[APIProvider, APIRateLimiter] = {}
        self._initialize_default_limiters()
    
    def _initialize_default_limiters(self):
        """Initialize rate limiters for all providers."""
        for provider in APIProvider:
            self.rate_limiters[provider] = APIRateLimiter(provider)
    
    def get_limiter(self, provider: APIProvider) -> APIRateLimiter:
        """Get rate limiter for a provider."""
        if provider not in self.rate_limiters:
            self.rate_limiters[provider] = APIRateLimiter(provider)
        return self.rate_limiters[provider]
    
    async def make_api_call(self, provider: APIProvider, api_function: Callable[[], Awaitable[T]], 
                           estimated_tokens: int = 100) -> T:
        """Make an API call with rate limiting and error handling.
        
        Args:
            provider: API provider
            api_function: Async function that makes the API call
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            Result from the API function
        """
        limiter = self.get_limiter(provider)
        
        async with limiter.make_request(estimated_tokens):
            return await api_function()
    
    def get_all_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all providers."""
        return {
            provider.value: limiter.get_usage_stats()
            for provider, limiter in self.rate_limiters.items()
        }
    
    def export_usage_report(self) -> str:
        """Export detailed usage report as JSON."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "providers": self.get_all_usage_stats(),
            "summary": self._generate_summary()
        }
        return json.dumps(report, indent=2)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate usage summary across all providers."""
        total_requests = sum(
            limiter.hour_usage.requests_count 
            for limiter in self.rate_limiters.values()
        )
        total_cost = sum(
            limiter.daily_usage.cost_incurred 
            for limiter in self.rate_limiters.values()
        )
        total_errors = sum(
            limiter.hour_usage.error_count 
            for limiter in self.rate_limiters.values()
        )
        
        return {
            "total_requests_hour": total_requests,
            "total_cost_day": round(total_cost, 4),
            "total_errors_hour": total_errors,
            "error_rate": round(total_errors / max(total_requests, 1), 4)
        }


# Global API manager instance
_global_api_manager: Optional[APIManager] = None


def get_api_manager() -> APIManager:
    """Get global API manager instance."""
    global _global_api_manager
    if _global_api_manager is None:
        _global_api_manager = APIManager()
    return _global_api_manager


def rate_limited_api_call(provider: APIProvider, estimated_tokens: int = 100):
    """Decorator for rate-limited API calls.
    
    Args:
        provider: API provider
        estimated_tokens: Estimated tokens for the request
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            api_manager = get_api_manager()
            return await api_manager.make_api_call(
                provider, 
                lambda: func(*args, **kwargs),
                estimated_tokens
            )
        return wrapper
    return decorator 