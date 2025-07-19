"""Enhanced Error Handling and Recovery System.

This module provides comprehensive error handling with specific error types,
recovery strategies, and detailed error context preservation.
"""

import asyncio
import traceback
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Type, Callable, Union, Awaitable
from contextlib import asynccontextmanager
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors."""
    VALIDATION = "validation"
    API_COMMUNICATION = "api_communication"
    AUTHENTICATION = "authentication"
    RATE_LIMITING = "rate_limiting"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATABASE = "database"
    NETWORK = "network"
    PARSING = "parsing"
    CONFIGURATION = "configuration"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types."""
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_IMMEDIATE = "retry_immediate"
    FALLBACK_MODE = "fallback_mode"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    USER_INTERVENTION = "user_intervention"
    CIRCUIT_BREAKER = "circuit_breaker"
    NO_RECOVERY = "no_recovery"


@dataclass
class ErrorContext:
    """Comprehensive error context information."""
    # Basic error info
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    
    # Context information
    operation_name: str
    timestamp: float = field(default_factory=time.time)
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Technical details
    stack_trace: Optional[str] = None
    error_code: Optional[str] = None
    api_response: Optional[Dict[str, Any]] = None
    
    # Recovery information
    recovery_strategy: RecoveryStrategy = RecoveryStrategy.NO_RECOVERY
    retry_count: int = 0
    max_retries: int = 3
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "error_type": self.error_type,
            "error_message": self.error_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "operation_name": self.operation_name,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "user_id": self.user_id,
            "stack_trace": self.stack_trace,
            "error_code": self.error_code,
            "api_response": self.api_response,
            "recovery_strategy": self.recovery_strategy.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata,
        }
    
    def should_retry(self) -> bool:
        """Check if error should be retried."""
        return (self.retry_count < self.max_retries and 
                self.recovery_strategy in [
                    RecoveryStrategy.RETRY_WITH_BACKOFF,
                    RecoveryStrategy.RETRY_IMMEDIATE
                ])


class LogAnalyzerException(Exception):
    """Base exception for log analyzer with enhanced context."""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None):
        """Initialize with message and context.
        
        Args:
            message: Error message
            context: Error context information
        """
        super().__init__(message)
        self.context = context or ErrorContext(
            error_type=self.__class__.__name__,
            error_message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.UNKNOWN,
            operation_name="unknown"
        )


class ValidationError(LogAnalyzerException):
    """Input validation errors."""
    
    def __init__(self, message: str, field_name: Optional[str] = None, 
                 validation_rule: Optional[str] = None):
        context = ErrorContext(
            error_type="ValidationError",
            error_message=message,
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
            operation_name="input_validation",
            recovery_strategy=RecoveryStrategy.USER_INTERVENTION,
            metadata={
                "field_name": field_name,
                "validation_rule": validation_rule
            }
        )
        super().__init__(message, context)


class APIError(LogAnalyzerException):
    """API communication errors."""
    
    def __init__(self, message: str, api_provider: str, status_code: Optional[int] = None,
                 response_data: Optional[Dict[str, Any]] = None):
        
        # Determine recovery strategy based on status code
        recovery_strategy = RecoveryStrategy.RETRY_WITH_BACKOFF
        if status_code:
            if status_code == 429:  # Rate limited
                recovery_strategy = RecoveryStrategy.RETRY_WITH_BACKOFF
            elif status_code in [401, 403]:  # Auth errors
                recovery_strategy = RecoveryStrategy.USER_INTERVENTION
            elif status_code >= 500:  # Server errors
                recovery_strategy = RecoveryStrategy.RETRY_WITH_BACKOFF
            else:
                recovery_strategy = RecoveryStrategy.NO_RECOVERY
        
        context = ErrorContext(
            error_type="APIError",
            error_message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.API_COMMUNICATION,
            operation_name=f"api_call_{api_provider}",
            recovery_strategy=recovery_strategy,
            error_code=str(status_code) if status_code else None,
            api_response=response_data,
            metadata={
                "api_provider": api_provider,
                "status_code": status_code
            }
        )
        super().__init__(message, context)


class DatabaseError(LogAnalyzerException):
    """Database operation errors."""
    
    def __init__(self, message: str, operation: str, 
                 connection_available: bool = True):
        
        recovery_strategy = RecoveryStrategy.RETRY_WITH_BACKOFF
        severity = ErrorSeverity.HIGH
        
        if not connection_available:
            recovery_strategy = RecoveryStrategy.CIRCUIT_BREAKER
            severity = ErrorSeverity.CRITICAL
        
        context = ErrorContext(
            error_type="DatabaseError",
            error_message=message,
            severity=severity,
            category=ErrorCategory.DATABASE,
            operation_name=f"database_{operation}",
            recovery_strategy=recovery_strategy,
            metadata={
                "database_operation": operation,
                "connection_available": connection_available
            }
        )
        super().__init__(message, context)


class ResourceExhaustionError(LogAnalyzerException):
    """Resource exhaustion errors (memory, connections, etc.)."""
    
    def __init__(self, message: str, resource_type: str, 
                 current_usage: Optional[float] = None, limit: Optional[float] = None):
        context = ErrorContext(
            error_type="ResourceExhaustionError",
            error_message=message,
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.RESOURCE_EXHAUSTION,
            operation_name="resource_management",
            recovery_strategy=RecoveryStrategy.GRACEFUL_DEGRADATION,
            metadata={
                "resource_type": resource_type,
                "current_usage": current_usage,
                "limit": limit
            }
        )
        super().__init__(message, context)


class TimeoutError(LogAnalyzerException):
    """Operation timeout errors."""
    
    def __init__(self, message: str, operation: str, timeout_seconds: float):
        context = ErrorContext(
            error_type="TimeoutError",
            error_message=message,
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.TIMEOUT,
            operation_name=operation,
            recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            metadata={
                "timeout_seconds": timeout_seconds
            }
        )
        super().__init__(message, context)


class ConfigurationError(LogAnalyzerException):
    """Configuration-related errors."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        context = ErrorContext(
            error_type="ConfigurationError",
            error_message=message,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.CONFIGURATION,
            operation_name="configuration_validation",
            recovery_strategy=RecoveryStrategy.USER_INTERVENTION,
            metadata={
                "config_key": config_key
            }
        )
        super().__init__(message, context)


class ErrorRecoveryManager:
    """Manages error recovery strategies and tracks error patterns."""
    
    def __init__(self):
        """Initialize error recovery manager."""
        self.error_history: List[ErrorContext] = []
        self.recovery_handlers: Dict[ErrorCategory, Callable] = {}
        self.error_patterns: Dict[str, int] = {}
        self._max_history = 1000
    
    def register_recovery_handler(self, category: ErrorCategory, 
                                handler: Callable[[ErrorContext], Awaitable[bool]]) -> None:
        """Register a recovery handler for an error category.
        
        Args:
            category: Error category
            handler: Async recovery handler function
        """
        self.recovery_handlers[category] = handler
        logger.info(f"Registered recovery handler for {category.value}")
    
    def record_error(self, error_context: ErrorContext) -> None:
        """Record an error for pattern analysis.
        
        Args:
            error_context: Error context to record
        """
        # Add to history
        self.error_history.append(error_context)
        
        # Trim history if too large
        if len(self.error_history) > self._max_history:
            self.error_history = self.error_history[-self._max_history:]
        
        # Track error patterns
        pattern_key = f"{error_context.category.value}:{error_context.error_type}"
        self.error_patterns[pattern_key] = self.error_patterns.get(pattern_key, 0) + 1
        
        # Log error with context
        logger.error(
            f"Error recorded: {error_context.error_message}",
            extra={
                "error_context": error_context.to_dict(),
                "category": error_context.category.value,
                "severity": error_context.severity.value
            }
        )
    
    async def handle_error(self, error_context: ErrorContext) -> bool:
        """Handle an error using appropriate recovery strategy.
        
        Args:
            error_context: Error context
            
        Returns:
            True if error was recovered, False otherwise
        """
        self.record_error(error_context)
        
        # Check if we have a specific handler for this category
        if error_context.category in self.recovery_handlers:
            try:
                handler = self.recovery_handlers[error_context.category]
                recovery_success = await handler(error_context)
                
                if recovery_success:
                    logger.info(f"Successfully recovered from {error_context.error_type}")
                    return True
                
            except Exception as e:
                logger.error(f"Recovery handler failed: {e}")
        
        # Default recovery strategies
        return await self._default_recovery(error_context)
    
    async def _default_recovery(self, error_context: ErrorContext) -> bool:
        """Default recovery strategies based on error category.
        
        Args:
            error_context: Error context
            
        Returns:
            True if recovery was attempted
        """
        strategy = error_context.recovery_strategy
        
        if strategy == RecoveryStrategy.RETRY_WITH_BACKOFF:
            if error_context.should_retry():
                backoff_time = 2 ** error_context.retry_count
                logger.info(f"Retrying after {backoff_time}s backoff")
                await asyncio.sleep(backoff_time)
                return True
        
        elif strategy == RecoveryStrategy.RETRY_IMMEDIATE:
            if error_context.should_retry():
                logger.info("Retrying immediately")
                return True
        
        elif strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            logger.warning("Entering graceful degradation mode")
            # Implementation would depend on the specific operation
            return True
        
        elif strategy == RecoveryStrategy.FALLBACK_MODE:
            logger.warning("Switching to fallback mode")
            # Implementation would depend on the specific operation
            return True
        
        return False
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Error summary statistics
        """
        cutoff_time = time.time() - (hours * 3600)
        recent_errors = [
            error for error in self.error_history 
            if error.timestamp >= cutoff_time
        ]
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        
        for error in recent_errors:
            category_counts[error.category.value] = category_counts.get(error.category.value, 0) + 1
            severity_counts[error.severity.value] = severity_counts.get(error.severity.value, 0) + 1
        
        return {
            "time_period_hours": hours,
            "total_errors": len(recent_errors),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "error_rate": len(recent_errors) / hours if hours > 0 else 0,
            "most_common_patterns": sorted(
                self.error_patterns.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        }


class ErrorBoundary:
    """Context manager for error boundary with automatic recovery."""
    
    def __init__(self, operation_name: str, recovery_manager: ErrorRecoveryManager,
                 max_retries: int = 3, timeout_seconds: Optional[float] = None):
        """Initialize error boundary.
        
        Args:
            operation_name: Name of the operation being protected
            recovery_manager: Error recovery manager
            max_retries: Maximum retry attempts
            timeout_seconds: Optional timeout for the operation
        """
        self.operation_name = operation_name
        self.recovery_manager = recovery_manager
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.attempt_count = 0
    
    @asynccontextmanager
    async def execute(self):
        """Execute operation with error boundary protection."""
        while self.attempt_count <= self.max_retries:
            try:
                # Set up timeout if specified
                if self.timeout_seconds:
                    async with asyncio.timeout(self.timeout_seconds):
                        yield
                else:
                    yield
                
                # Success - exit retry loop
                break
                
            except asyncio.TimeoutError:
                error_context = ErrorContext(
                    error_type="TimeoutError",
                    error_message=f"Operation {self.operation_name} timed out after {self.timeout_seconds}s",
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.TIMEOUT,
                    operation_name=self.operation_name,
                    recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    retry_count=self.attempt_count,
                    max_retries=self.max_retries
                )
                
                await self._handle_error_and_retry(error_context)
            
            except LogAnalyzerException as e:
                # Update retry count in context
                e.context.retry_count = self.attempt_count
                e.context.max_retries = self.max_retries
                
                await self._handle_error_and_retry(e.context)
            
            except Exception as e:
                # Convert unknown exceptions to LogAnalyzerException
                error_context = ErrorContext(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.UNKNOWN,
                    operation_name=self.operation_name,
                    stack_trace=traceback.format_exc(),
                    recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                    retry_count=self.attempt_count,
                    max_retries=self.max_retries
                )
                
                await self._handle_error_and_retry(error_context)
    
    async def _handle_error_and_retry(self, error_context: ErrorContext) -> None:
        """Handle error and determine if retry should occur.
        
        Args:
            error_context: Error context
        """
        self.attempt_count += 1
        
        # Try to recover
        recovery_success = await self.recovery_manager.handle_error(error_context)
        
        # If we've exhausted retries or recovery failed, raise the error
        if self.attempt_count > self.max_retries or not recovery_success:
            raise LogAnalyzerException(
                f"Operation {self.operation_name} failed after {self.attempt_count} attempts: {error_context.error_message}",
                error_context
            )


# Global error recovery manager
_global_recovery_manager: Optional[ErrorRecoveryManager] = None


def get_error_recovery_manager() -> ErrorRecoveryManager:
    """Get global error recovery manager."""
    global _global_recovery_manager
    if _global_recovery_manager is None:
        _global_recovery_manager = ErrorRecoveryManager()
    return _global_recovery_manager


def error_boundary(operation_name: str, max_retries: int = 3, 
                  timeout_seconds: Optional[float] = None):
    """Decorator for creating error boundaries around functions.
    
    Args:
        operation_name: Name of the operation
        max_retries: Maximum retry attempts
        timeout_seconds: Optional timeout
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            recovery_manager = get_error_recovery_manager()
            boundary = ErrorBoundary(operation_name, recovery_manager, max_retries, timeout_seconds)
            
            async with boundary.execute():
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def safe_operation(operation_name: str, max_retries: int = 3):
    """Context manager for safe operations with error handling.
    
    Args:
        operation_name: Name of the operation
        max_retries: Maximum retry attempts
    """
    recovery_manager = get_error_recovery_manager()
    return ErrorBoundary(operation_name, recovery_manager, max_retries).execute() 