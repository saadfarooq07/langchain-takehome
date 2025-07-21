"""Circuit breaker implementation for preventing runaway processes.

This module provides a circuit breaker pattern implementation that prevents
cascading failures and protects the system from runaway processes. It monitors
failures and temporarily disables operations when failure thresholds are exceeded.
"""

import time
import asyncio
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures exceeded threshold, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    failure_reasons: Dict[str, int] = field(default_factory=dict)
    state_changes: List[Dict[str, Any]] = field(default_factory=list)


class CircuitBreaker:
    """Circuit breaker for preventing runaway processes and cascading failures.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected
    - HALF_OPEN: Testing recovery, limited requests allowed
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        half_open_max_calls: Max calls allowed in half-open state
        failure_rate_threshold: Failure rate (0-1) to trigger open state
        monitoring_window: Time window (seconds) for failure rate calculation
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        failure_rate_threshold: float = 0.5,
        monitoring_window: float = 300.0,  # 5 minutes
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.failure_rate_threshold = failure_rate_threshold
        self.monitoring_window = monitoring_window
        self.name = name
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        
        # Statistics
        self._stats = CircuitStats()
        self._call_history: List[tuple[float, bool]] = []  # (timestamp, success)
        
        # State change callbacks
        self._state_change_callbacks: List[Callable[[CircuitState, CircuitState], None]] = []
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for automatic transitions."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state
    
    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._last_failure_time is None:
            return True
        return time.time() - self._last_failure_time >= self.recovery_timeout
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self._stats.state_changes.append({
                "from": old_state,
                "to": new_state,
                "timestamp": time.time(),
                "consecutive_failures": self._consecutive_failures
            })
            
            # Reset half-open counter
            if new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
            
            # Notify callbacks
            for callback in self._state_change_callbacks:
                try:
                    callback(old_state, new_state)
                except Exception as e:
                    logger.error(f"Error in state change callback: {e}")
            
            logger.info(f"Circuit breaker '{self.name}' transitioned from {old_state} to {new_state}")
    
    def _record_success(self) -> None:
        """Record a successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._call_history.append((time.time(), True))
        self._consecutive_failures = 0
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                # Enough successful calls in half-open, close the circuit
                self._transition_to(CircuitState.CLOSED)
    
    def _record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._call_history.append((time.time(), False))
        self._consecutive_failures += 1
        self._last_failure_time = time.time()
        self._stats.last_failure_time = self._last_failure_time
        
        # Track failure reasons
        error_type = type(error).__name__
        self._stats.failure_reasons[error_type] = self._stats.failure_reasons.get(error_type, 0) + 1
        
        # Check if we should open the circuit
        if self._state == CircuitState.CLOSED:
            if self._consecutive_failures >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
            elif self._get_failure_rate() >= self.failure_rate_threshold:
                self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open state reopens the circuit
            self._transition_to(CircuitState.OPEN)
    
    def _get_failure_rate(self) -> float:
        """Calculate recent failure rate."""
        if not self._call_history:
            return 0.0
        
        current_time = time.time()
        window_start = current_time - self.monitoring_window
        
        # Filter calls within the monitoring window
        recent_calls = [(t, s) for t, s in self._call_history if t >= window_start]
        
        if not recent_calls:
            return 0.0
        
        failures = sum(1 for _, success in recent_calls if not success)
        return failures / len(recent_calls)
    
    def _cleanup_history(self) -> None:
        """Remove old entries from call history."""
        current_time = time.time()
        window_start = current_time - self.monitoring_window
        self._call_history = [(t, s) for t, s in self._call_history if t >= window_start]
    
    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Original exception: If function fails
        """
        # Clean up old history periodically
        if len(self._call_history) > 1000:
            self._cleanup_history()
        
        # Check circuit state
        current_state = self.state
        
        if current_state == CircuitState.OPEN:
            self._stats.rejected_calls += 1
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Consecutive failures: {self._consecutive_failures}"
            )
        
        try:
            # Execute the function
            result = func(*args, **kwargs)
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure(e)
            raise
    
    async def call_async(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute an async function through the circuit breaker."""
        # Clean up old history periodically
        if len(self._call_history) > 1000:
            self._cleanup_history()
        
        # Check circuit state
        current_state = self.state
        
        if current_state == CircuitState.OPEN:
            self._stats.rejected_calls += 1
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Consecutive failures: {self._consecutive_failures}"
            )
        
        try:
            # Execute the async function
            result = await func(*args, **kwargs)
            self._record_success()
            return result
            
        except Exception as e:
            self._record_failure(e)
            raise
    
    def decorator(self, func: Callable) -> Callable:
        """Decorator to wrap a function with circuit breaker protection."""
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)
            return sync_wrapper
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state,
            "total_calls": self._stats.total_calls,
            "successful_calls": self._stats.successful_calls,
            "failed_calls": self._stats.failed_calls,
            "rejected_calls": self._stats.rejected_calls,
            "consecutive_failures": self._consecutive_failures,
            "failure_rate": self._get_failure_rate(),
            "last_failure_time": self._stats.last_failure_time,
            "failure_reasons": dict(self._stats.failure_reasons),
            "state_changes": len(self._stats.state_changes)
        }
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._transition_to(CircuitState.CLOSED)
        self._consecutive_failures = 0
        self._half_open_calls = 0
        logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def add_state_change_callback(self, callback: Callable[[CircuitState, CircuitState], None]) -> None:
        """Add a callback for state changes."""
        self._state_change_callbacks.append(callback)


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str = "default",
    **kwargs
) -> CircuitBreaker:
    """Get or create a circuit breaker instance.
    
    Args:
        name: Name of the circuit breaker
        **kwargs: Arguments for CircuitBreaker constructor
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _circuit_breakers[name]


def circuit_breaker(
    name: str = "default",
    **breaker_kwargs
) -> Callable:
    """Decorator factory for circuit breaker protection.
    
    Usage:
        @circuit_breaker(name="api_calls", failure_threshold=3)
        async def call_api():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(name, **breaker_kwargs)
        return breaker.decorator(func)
    return decorator