"""Centralized circuit breaker and execution control system.

This module provides robust protection against infinite loops, runaway processes,
and resource exhaustion through centralized tracking and circuit breaker patterns.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, Set, Callable, Union
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class ExecutionLimits:
    """Centralized execution limits configuration."""
    max_total_iterations: int = 50
    max_analysis_iterations: int = 10
    max_tool_calls: int = 20
    max_validation_attempts: int = 3
    max_user_interactions: int = 5
    max_execution_time_seconds: int = 300
    max_memory_mb: int = 512
    max_concurrent_operations: int = 10
    
    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 60
    half_open_max_requests: int = 3


@dataclass
class ExecutionMetrics:
    """Tracks execution metrics for circuit breaker decisions."""
    start_time: float = field(default_factory=time.time)
    iteration_counts: Dict[str, int] = field(default_factory=dict)
    total_iterations: int = 0
    tool_call_count: int = 0
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    memory_usage_mb: float = 0.0
    
    def increment_iteration(self, node_name: str) -> None:
        """Increment iteration count for a specific node."""
        self.iteration_counts[node_name] = self.iteration_counts.get(node_name, 0) + 1
        self.total_iterations += 1
    
    def increment_tool_call(self) -> None:
        """Increment tool call count."""
        self.tool_call_count += 1
    
    def record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()
    
    def record_success(self) -> None:
        """Record a success."""
        self.success_count += 1
    
    def get_elapsed_time(self) -> float:
        """Get elapsed execution time."""
        return time.time() - self.start_time
    
    def get_failure_rate(self) -> float:
        """Calculate failure rate."""
        total = self.failure_count + self.success_count
        return self.failure_count / total if total > 0 else 0.0


class CircuitBreaker:
    """Circuit breaker implementation with state management."""
    
    def __init__(self, limits: ExecutionLimits):
        """Initialize circuit breaker.
        
        Args:
            limits: Execution limits configuration
        """
        self.limits = limits
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.half_open_requests = 0
        self._lock = asyncio.Lock()
    
    async def can_proceed(self) -> bool:
        """Check if execution can proceed based on circuit state."""
        async with self._lock:
            now = time.time()
            
            if self.state == CircuitState.CLOSED:
                return True
            
            elif self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if (self.last_failure_time and 
                    now - self.last_failure_time > self.limits.recovery_timeout_seconds):
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_requests = 0
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                    return True
                return False
            
            elif self.state == CircuitState.HALF_OPEN:
                # Allow limited requests to test recovery
                if self.half_open_requests < self.limits.half_open_max_requests:
                    self.half_open_requests += 1
                    return True
                return False
            
            return False
    
    async def record_success(self) -> None:
        """Record successful execution."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                # Successful recovery, close circuit
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker recovered, transitioning to CLOSED")
    
    async def record_failure(self) -> None:
        """Record failed execution."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.limits.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened due to {self.failure_count} failures")
            elif self.state == CircuitState.HALF_OPEN:
                # Failed during recovery, go back to open
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker failed during recovery, returning to OPEN")


class ExecutionController:
    """Centralized execution control with circuit breaker and limits."""
    
    def __init__(self, limits: Optional[ExecutionLimits] = None):
        """Initialize execution controller.
        
        Args:
            limits: Optional custom limits, uses defaults if not provided
        """
        self.limits = limits or ExecutionLimits()
        self.circuit_breaker = CircuitBreaker(self.limits)
        self.metrics = ExecutionMetrics()
        self.active_operations: Set[str] = set()
        self._operation_semaphore = asyncio.Semaphore(self.limits.max_concurrent_operations)
        
    def check_iteration_limits(self, node_name: str) -> bool:
        """Check if iteration limits are exceeded.
        
        Args:
            node_name: Name of the node being executed
            
        Returns:
            True if execution can continue, False if limits exceeded
        """
        # Check total iterations
        if self.metrics.total_iterations >= self.limits.max_total_iterations:
            logger.warning(f"Total iteration limit exceeded: {self.metrics.total_iterations}")
            return False
        
        # Check node-specific limits
        node_count = self.metrics.iteration_counts.get(node_name, 0)
        node_limits = {
            "analyze_logs": self.limits.max_analysis_iterations,
            "validate_analysis": self.limits.max_validation_attempts,
            "handle_user_input": self.limits.max_user_interactions,
        }
        
        max_for_node = node_limits.get(node_name, self.limits.max_total_iterations)
        if node_count >= max_for_node:
            logger.warning(f"Node {node_name} iteration limit exceeded: {node_count}")
            return False
        
        # Check tool call limits
        if self.metrics.tool_call_count >= self.limits.max_tool_calls:
            logger.warning(f"Tool call limit exceeded: {self.metrics.tool_call_count}")
            return False
        
        # Check execution time
        if self.metrics.get_elapsed_time() >= self.limits.max_execution_time_seconds:
            logger.warning(f"Execution time limit exceeded: {self.metrics.get_elapsed_time()}s")
            return False
        
        return True
    
    @asynccontextmanager
    async def execute_operation(self, operation_name: str):
        """Context manager for executing operations with limits and circuit breaker.
        
        Args:
            operation_name: Name of the operation being executed
        """
        # Check circuit breaker
        if not await self.circuit_breaker.can_proceed():
            raise RuntimeError("Circuit breaker is OPEN - operation blocked")
        
        # Acquire semaphore for concurrency control
        async with self._operation_semaphore:
            # Check iteration limits
            if not self.check_iteration_limits(operation_name):
                await self.circuit_breaker.record_failure()
                raise RuntimeError(f"Execution limits exceeded for operation: {operation_name}")
            
            # Track operation
            self.active_operations.add(operation_name)
            self.metrics.increment_iteration(operation_name)
            
            operation_start = time.time()
            
            try:
                yield self.metrics
                
                # Record success
                await self.circuit_breaker.record_success()
                self.metrics.record_success()
                
            except Exception as e:
                # Record failure
                await self.circuit_breaker.record_failure()
                self.metrics.record_failure()
                logger.error(f"Operation {operation_name} failed: {e}")
                raise
                
            finally:
                # Clean up
                self.active_operations.discard(operation_name)
                operation_time = time.time() - operation_start
                logger.debug(f"Operation {operation_name} completed in {operation_time:.2f}s")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current execution status and metrics."""
        return {
            "circuit_state": self.circuit_breaker.state.value,
            "total_iterations": self.metrics.total_iterations,
            "iteration_counts": dict(self.metrics.iteration_counts),
            "tool_calls": self.metrics.tool_call_count,
            "elapsed_time": self.metrics.get_elapsed_time(),
            "failure_rate": self.metrics.get_failure_rate(),
            "active_operations": list(self.active_operations),
            "limits": {
                "max_total_iterations": self.limits.max_total_iterations,
                "max_analysis_iterations": self.limits.max_analysis_iterations,
                "max_tool_calls": self.limits.max_tool_calls,
                "max_execution_time": self.limits.max_execution_time_seconds,
            }
        }
    
    def reset(self) -> None:
        """Reset execution controller to initial state."""
        self.metrics = ExecutionMetrics()
        self.active_operations.clear()
        self.circuit_breaker = CircuitBreaker(self.limits)
        logger.info("Execution controller reset")


# Global instance for easy access
_global_controller: Optional[ExecutionController] = None


def get_execution_controller(limits: Optional[ExecutionLimits] = None) -> ExecutionController:
    """Get or create global execution controller.
    
    Args:
        limits: Optional custom limits for new controller
        
    Returns:
        Global execution controller instance
    """
    global _global_controller
    if _global_controller is None or limits is not None:
        _global_controller = ExecutionController(limits)
    return _global_controller


def reset_execution_controller() -> None:
    """Reset the global execution controller."""
    global _global_controller
    if _global_controller:
        _global_controller.reset() 