"""Async context managers for proper resource management.

This module provides context managers for handling async resources
properly, including cleanup, timeouts, and cancellation.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List, AsyncIterator
import signal
import time
from functools import wraps

from .logging import get_logger
from .config import Config


logger = get_logger("log_analyzer.context")


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


class CancellationError(Exception):
    """Raised when an operation is cancelled."""
    pass


@asynccontextmanager
async def timeout_context(seconds: int, message: str = "Operation timed out"):
    """Context manager for operations with timeout.
    
    Args:
        seconds: Timeout in seconds
        message: Error message on timeout
        
    Yields:
        None
        
    Raises:
        TimeoutError: If operation exceeds timeout
    """
    async def timeout_handler():
        await asyncio.sleep(seconds)
        raise TimeoutError(message)
    
    timeout_task = asyncio.create_task(timeout_handler())
    
    try:
        yield
    finally:
        timeout_task.cancel()
        try:
            await timeout_task
        except asyncio.CancelledError:
            pass
        except TimeoutError:
            raise


@asynccontextmanager
async def resource_pool(max_resources: int = 10):
    """Context manager for resource pooling.
    
    Args:
        max_resources: Maximum concurrent resources
        
    Yields:
        ResourcePool instance
    """
    pool = ResourcePool(max_resources)
    try:
        yield pool
    finally:
        await pool.cleanup()


class ResourcePool:
    """Manages a pool of async resources."""
    
    def __init__(self, max_size: int):
        """Initialize resource pool.
        
        Args:
            max_size: Maximum pool size
        """
        self.max_size = max_size
        self.semaphore = asyncio.Semaphore(max_size)
        self.resources: List[Any] = []
        self.logger = get_logger("log_analyzer.resource_pool")
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a resource from the pool."""
        async with self.semaphore:
            resource = await self._create_resource()
            self.resources.append(resource)
            try:
                yield resource
            finally:
                await self._release_resource(resource)
                self.resources.remove(resource)
    
    async def _create_resource(self):
        """Create a new resource."""
        # Override in subclasses
        return object()
    
    async def _release_resource(self, resource):
        """Release a resource."""
        # Override in subclasses
        pass
    
    async def cleanup(self):
        """Clean up all resources."""
        self.logger.info(f"Cleaning up {len(self.resources)} resources")
        cleanup_tasks = [self._release_resource(r) for r in self.resources]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        self.resources.clear()


@asynccontextmanager
async def database_session(db_url: str, echo: bool = False):
    """Context manager for database sessions.
    
    Args:
        db_url: Database URL
        echo: Whether to echo SQL
        
    Yields:
        Database session
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    engine = create_async_engine(db_url, echo=echo)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    await engine.dispose()


@asynccontextmanager
async def model_context(config: Config):
    """Context manager for language models with proper cleanup.
    
    Args:
        config: Configuration
        
    Yields:
        Dictionary of initialized models
    """
    models = {}
    
    try:
        # Initialize models
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_groq import ChatGroq
        
        if config.primary_model.provider.value == "google":
            models["primary"] = ChatGoogleGenerativeAI(
                model=config.primary_model.model_name,
                temperature=config.primary_model.temperature,
                google_api_key=config.primary_model.get_api_key()
            )
        
        if config.orchestration_model.provider.value == "groq":
            models["orchestration"] = ChatGroq(
                model=config.orchestration_model.model_name,
                temperature=config.orchestration_model.temperature,
                groq_api_key=config.orchestration_model.get_api_key()
            )
        
        yield models
        
    finally:
        # Clean up models
        for name, model in models.items():
            logger.debug(f"Cleaning up model: {name}")
            # Most LangChain models don't need explicit cleanup
            # but we can add it here if needed


class ExecutionContext:
    """Manages execution context with cancellation support."""
    
    def __init__(self, timeout: Optional[int] = None):
        """Initialize execution context.
        
        Args:
            timeout: Optional timeout in seconds
        """
        self.timeout = timeout
        self._cancelled = False
        self._tasks: List[asyncio.Task] = []
        self.logger = get_logger("log_analyzer.execution_context")
    
    def cancel(self):
        """Cancel all tasks in this context."""
        self._cancelled = True
        for task in self._tasks:
            if not task.done():
                task.cancel()
        self.logger.info(f"Cancelled {len(self._tasks)} tasks")
    
    @property
    def is_cancelled(self) -> bool:
        """Check if context is cancelled."""
        return self._cancelled
    
    async def run(self, coro):
        """Run a coroutine in this context.
        
        Args:
            coro: Coroutine to run
            
        Returns:
            Coroutine result
            
        Raises:
            CancellationError: If cancelled
            TimeoutError: If timeout exceeded
        """
        if self._cancelled:
            raise CancellationError("Execution context is cancelled")
        
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        
        try:
            if self.timeout:
                return await asyncio.wait_for(task, timeout=self.timeout)
            else:
                return await task
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation exceeded timeout of {self.timeout}s")
        except asyncio.CancelledError:
            raise CancellationError("Operation was cancelled")
        finally:
            self._tasks.remove(task)
    
    async def gather(self, *coros, return_exceptions: bool = False):
        """Run multiple coroutines concurrently.
        
        Args:
            *coros: Coroutines to run
            return_exceptions: Whether to return exceptions
            
        Returns:
            List of results
        """
        tasks = [self.run(coro) for coro in coros]
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)


@asynccontextmanager
async def graceful_shutdown():
    """Context manager for graceful shutdown handling."""
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        shutdown_event.set()
    
    # Register signal handlers
    old_sigint = signal.signal(signal.SIGINT, signal_handler)
    old_sigterm = signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        yield shutdown_event
    finally:
        # Restore original handlers
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)


def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for async functions with retry logic.
    
    Args:
        max_attempts: Maximum retry attempts
        delay: Initial delay between retries
        backoff_factor: Delay multiplier for each retry
        exceptions: Exceptions to catch and retry
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


@asynccontextmanager
async def performance_monitor(operation_name: str):
    """Context manager for monitoring operation performance.
    
    Args:
        operation_name: Name of the operation
        
    Yields:
        PerformanceMetrics instance
    """
    metrics = PerformanceMetrics(operation_name)
    metrics.start()
    
    try:
        yield metrics
    finally:
        metrics.stop()
        logger.info(
            f"Performance metrics for {operation_name}",
            extra=metrics.to_dict()
        )


class PerformanceMetrics:
    """Tracks performance metrics for an operation."""
    
    def __init__(self, operation_name: str):
        """Initialize metrics.
        
        Args:
            operation_name: Name of the operation
        """
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.checkpoints: Dict[str, float] = {}
    
    def start(self):
        """Start timing."""
        self.start_time = time.time()
    
    def stop(self):
        """Stop timing."""
        self.end_time = time.time()
    
    def checkpoint(self, name: str):
        """Record a checkpoint."""
        self.checkpoints[name] = time.time()
    
    @property
    def duration(self) -> Optional[float]:
        """Get total duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "operation": self.operation_name,
            "duration_seconds": self.duration,
        }
        
        if self.checkpoints and self.start_time:
            result["checkpoints"] = {
                name: time - self.start_time
                for name, time in self.checkpoints.items()
            }
        
        return result