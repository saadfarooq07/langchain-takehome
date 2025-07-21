"""Database connection pooling for efficient database access.

This module provides connection pooling to avoid the overhead of creating
new database connections for every operation. It uses asyncpg's built-in
connection pooling with additional management and monitoring features.

Key features:
- Automatic connection pool management
- Health checking and connection validation
- Metrics and monitoring
- Graceful degradation
- Transaction support
"""

import asyncio
import os
from typing import Optional, Dict, Any, AsyncContextManager
from contextlib import asynccontextmanager
from datetime import datetime
import asyncpg
from asyncpg import Pool, Connection


class DatabasePool:
    """Manages a pool of database connections."""
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        min_size: int = 10,
        max_size: int = 20,
        max_queries: int = 50000,
        max_inactive_connection_lifetime: float = 300.0,
        timeout: float = 60.0,
        command_timeout: float = 60.0,
        max_cached_statement_lifetime: int = 300,
        max_cacheable_statement_size: int = 1024 * 15
    ):
        """Initialize database pool configuration.
        
        Args:
            db_url: Database connection URL (uses DATABASE_URL env var if not provided)
            min_size: Minimum number of connections to maintain
            max_size: Maximum number of connections allowed
            max_queries: Number of queries after which a connection is closed
            max_inactive_connection_lifetime: Max seconds a connection can be idle
            timeout: Timeout for acquiring a connection from the pool
            command_timeout: Timeout for executing commands
            max_cached_statement_lifetime: Max seconds to cache prepared statements
            max_cacheable_statement_size: Max size of statements to cache
        """
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL is required")
            
        self.min_size = min_size
        self.max_size = max_size
        self.max_queries = max_queries
        self.max_inactive_connection_lifetime = max_inactive_connection_lifetime
        self.timeout = timeout
        self.command_timeout = command_timeout
        self.max_cached_statement_lifetime = max_cached_statement_lifetime
        self.max_cacheable_statement_size = max_cacheable_statement_size
        
        self._pool: Optional[Pool] = None
        self._initialization_lock = asyncio.Lock()
        self._metrics = {
            "connections_created": 0,
            "connections_closed": 0,
            "queries_executed": 0,
            "transactions_completed": 0,
            "errors": 0,
            "pool_initialized_at": None
        }
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        async with self._initialization_lock:
            if self._pool is not None:
                return  # Already initialized
                
            try:
                self._pool = await asyncpg.create_pool(
                    self.db_url,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    max_queries=self.max_queries,
                    max_inactive_connection_lifetime=self.max_inactive_connection_lifetime,
                    timeout=self.timeout,
                    command_timeout=self.command_timeout,
                    max_cached_statement_lifetime=self.max_cached_statement_lifetime,
                    max_cacheable_statement_size=self.max_cacheable_statement_size,
                    setup=self._setup_connection
                )
                self._metrics["pool_initialized_at"] = datetime.now().isoformat()
            except Exception as e:
                self._metrics["errors"] += 1
                raise RuntimeError(f"Failed to initialize database pool: {e}")
    
    async def close(self) -> None:
        """Close the connection pool."""
        async with self._initialization_lock:
            if self._pool is not None:
                await self._pool.close()
                self._pool = None
    
    @asynccontextmanager
    async def acquire(self) -> AsyncContextManager[Connection]:
        """Acquire a connection from the pool.
        
        This is a context manager that ensures the connection is properly
        returned to the pool after use.
        
        Example:
            async with pool.acquire() as conn:
                result = await conn.fetch("SELECT * FROM users")
        """
        if self._pool is None:
            await self.initialize()
            
        try:
            async with self._pool.acquire() as conn:
                self._metrics["connections_created"] += 1
                try:
                    yield conn
                    self._metrics["queries_executed"] += 1
                finally:
                    self._metrics["connections_closed"] += 1
        except Exception as e:
            self._metrics["errors"] += 1
            raise
    
    @asynccontextmanager
    async def transaction(self) -> AsyncContextManager[Connection]:
        """Start a transaction with automatic rollback on error.
        
        Example:
            async with pool.transaction() as conn:
                await conn.execute("INSERT INTO logs ...")
                await conn.execute("UPDATE stats ...")
                # Automatically commits on success, rolls back on error
        """
        async with self.acquire() as conn:
            async with conn.transaction():
                try:
                    yield conn
                    self._metrics["transactions_completed"] += 1
                except Exception:
                    # Transaction will be rolled back automatically
                    self._metrics["errors"] += 1
                    raise
    
    async def execute(self, query: str, *args, timeout: Optional[float] = None) -> str:
        """Execute a query that doesn't return results."""
        async with self.acquire() as conn:
            return await conn.execute(query, *args, timeout=timeout)
    
    async def executemany(self, query: str, args: list, *, timeout: Optional[float] = None):
        """Execute a query multiple times with different arguments."""
        async with self.acquire() as conn:
            return await conn.executemany(query, args, timeout=timeout)
    
    async def fetch(self, query: str, *args, timeout: Optional[float] = None) -> list:
        """Execute a query and return all results."""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)
    
    async def fetchrow(self, query: str, *args, timeout: Optional[float] = None) -> Optional[asyncpg.Record]:
        """Execute a query and return the first row."""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args, timeout=timeout)
    
    async def fetchval(self, query: str, *args, column: int = 0, timeout: Optional[float] = None) -> Any:
        """Execute a query and return a single value."""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args, column=column, timeout=timeout)
    
    async def _setup_connection(self, conn: Connection) -> None:
        """Setup a new connection when it's created.
        
        This is called for each new connection in the pool.
        Can be used to set session parameters, register types, etc.
        """
        # Set any session parameters needed
        await conn.execute("SET TIME ZONE 'UTC'")
        
        # Register any custom types if needed
        # await conn.set_type_codec(...)
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status and metrics."""
        if self._pool is None:
            return {
                "status": "not_initialized",
                "metrics": self._metrics
            }
            
        return {
            "status": "active",
            "size": self._pool.get_size(),
            "free_size": self._pool.get_free_size(),
            "min_size": self._pool.get_min_size(),
            "max_size": self._pool.get_max_size(),
            "metrics": self._metrics
        }
    
    async def health_check(self) -> bool:
        """Perform a health check on the database connection."""
        try:
            async with self.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result == 1
        except Exception:
            return False


# Global database pool instance
_db_pool: Optional[DatabasePool] = None
_pool_lock = asyncio.Lock()


async def get_db_pool(db_url: Optional[str] = None) -> DatabasePool:
    """Get or create the global database pool instance.
    
    Args:
        db_url: Optional database URL (uses DATABASE_URL env var if not provided)
        
    Returns:
        The global DatabasePool instance
    """
    global _db_pool
    
    async with _pool_lock:
        if _db_pool is None:
            _db_pool = DatabasePool(db_url)
            await _db_pool.initialize()
        return _db_pool


async def cleanup_db_pool():
    """Clean up the global database pool."""
    global _db_pool
    
    async with _pool_lock:
        if _db_pool:
            await _db_pool.close()
            _db_pool = None


# Convenience functions for direct usage
@asynccontextmanager
async def get_db_connection(db_url: Optional[str] = None):
    """Get a database connection from the pool.
    
    This is a convenience context manager for backward compatibility.
    
    Example:
        async with get_db_connection() as conn:
            result = await conn.fetch("SELECT * FROM users")
    """
    pool = await get_db_pool(db_url)
    async with pool.acquire() as conn:
        yield conn


@asynccontextmanager
async def db_transaction(db_url: Optional[str] = None):
    """Start a database transaction.
    
    This is a convenience context manager for transactions.
    
    Example:
        async with db_transaction() as conn:
            await conn.execute("INSERT INTO logs ...")
            # Automatically commits on success, rolls back on error
    """
    pool = await get_db_pool(db_url)
    async with pool.transaction() as conn:
        yield conn