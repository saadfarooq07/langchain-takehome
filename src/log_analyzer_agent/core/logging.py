"""Structured logging configuration for the log analyzer agent.

This module provides centralized logging configuration with support for:
- Structured JSON logging
- Context injection
- Performance tracking
- Error tracking with proper sanitization
"""

import logging
import logging.handlers
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path
from contextlib import contextmanager
import time
from functools import wraps

from .config import LoggingConfig, LogLevel


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_traceback: bool = True):
        super().__init__()
        self.include_traceback = include_traceback
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "pathname", "process", "processName", "relativeCreated",
                          "thread", "threadName", "getMessage"]:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info and self.include_traceback:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data)


class LoggerAdapter(logging.LoggerAdapter):
    """Adapter to inject context into log messages."""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message with context."""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


class LogManager:
    """Centralized log management."""
    
    _instance: Optional['LogManager'] = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._context: Dict[str, Any] = {}
    
    def configure(self, config: LoggingConfig) -> None:
        """Configure logging based on config."""
        # Set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(config.level.value)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        if config.enable_json_logging:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(logging.Formatter(config.format))
        root_logger.addHandler(console_handler)
        
        # File handler if configured
        if config.file_path:
            config.file_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                config.file_path,
                maxBytes=config.max_file_size_mb * 1024 * 1024,
                backupCount=config.backup_count
            )
            if config.enable_json_logging:
                file_handler.setFormatter(StructuredFormatter())
            else:
                file_handler.setFormatter(logging.Formatter(config.format))
            root_logger.addHandler(file_handler)
    
    def get_logger(self, name: str, context: Optional[Dict[str, Any]] = None) -> Union[logging.Logger, LoggerAdapter]:
        """Get a logger with optional context."""
        if name not in self._loggers:
            self._loggers[name] = logging.getLogger(name)
        
        logger = self._loggers[name]
        
        if context:
            # Merge with global context
            full_context = {**self._context, **context}
            return LoggerAdapter(logger, full_context)
        elif self._context:
            return LoggerAdapter(logger, self._context)
        else:
            return logger
    
    def set_context(self, **kwargs) -> None:
        """Set global context for all loggers."""
        self._context.update(kwargs)
    
    def clear_context(self) -> None:
        """Clear global context."""
        self._context.clear()
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for temporary context."""
        old_context = self._context.copy()
        self._context.update(kwargs)
        try:
            yield
        finally:
            self._context = old_context


# Global log manager instance
log_manager = LogManager()


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> Union[logging.Logger, LoggerAdapter]:
    """Get a logger instance."""
    return log_manager.get_logger(name, context)


@contextmanager
def log_context(**kwargs):
    """Context manager for adding temporary log context."""
    with log_manager.context(**kwargs):
        yield


def log_execution_time(logger_name: str):
    """Decorator to log execution time of functions."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            start_time = time.time()
            
            logger.debug(f"Starting {func.__name__}", extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"Completed {func.__name__}", extra={
                    "function": func.__name__,
                    "execution_time_seconds": round(execution_time, 3),
                    "status": "success"
                })
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.error(f"Failed {func.__name__}", extra={
                    "function": func.__name__,
                    "execution_time_seconds": round(execution_time, 3),
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }, exc_info=True)
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            start_time = time.time()
            
            logger.debug(f"Starting {func.__name__}", extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"Completed {func.__name__}", extra={
                    "function": func.__name__,
                    "execution_time_seconds": round(execution_time, 3),
                    "status": "success"
                })
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.error(f"Failed {func.__name__}", extra={
                    "function": func.__name__,
                    "execution_time_seconds": round(execution_time, 3),
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }, exc_info=True)
                
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive data from logs."""
    sensitive_keys = {
        "password", "token", "api_key", "secret", "credential",
        "private_key", "access_token", "refresh_token"
    }
    
    def _sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: "***REDACTED***" if any(sk in k.lower() for sk in sensitive_keys) else _sanitize(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_sanitize(item) for item in obj]
        else:
            return obj
    
    return _sanitize(data)


# Convenience loggers for different components
class Loggers:
    """Namespace for component-specific loggers."""
    
    @staticmethod
    def graph() -> logging.Logger:
        """Logger for graph operations."""
        return get_logger("log_analyzer.graph")
    
    @staticmethod
    def nodes() -> logging.Logger:
        """Logger for node operations."""
        return get_logger("log_analyzer.nodes")
    
    @staticmethod
    def tools() -> logging.Logger:
        """Logger for tool operations."""
        return get_logger("log_analyzer.tools")
    
    @staticmethod
    def state() -> logging.Logger:
        """Logger for state operations."""
        return get_logger("log_analyzer.state")
    
    @staticmethod
    def api() -> logging.Logger:
        """Logger for API operations."""
        return get_logger("log_analyzer.api")
    
    @staticmethod
    def memory() -> logging.Logger:
        """Logger for memory operations."""
        return get_logger("log_analyzer.memory")