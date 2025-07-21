"""Store manager for production-ready memory backend."""

import os
from typing import Optional, Tuple
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver


class StoreManager:
    """Manages store and checkpointer instances for the application."""
    
    _store: Optional[BaseStore] = None
    _checkpointer: Optional[BaseCheckpointSaver] = None
    
    @classmethod
    def get_store(cls) -> BaseStore:
        """Get or create the store instance.
        
        In production, this would use PostgreSQL or another persistent store.
        For now, we use InMemoryStore.
        """
        if cls._store is None:
            # TODO: In production, use PostgreSQL store
            # Example:
            # from langgraph.store.postgres import PostgresStore
            # db_url = os.getenv("DATABASE_URL")
            # cls._store = PostgresStore(db_url)
            
            # For now, use in-memory store
            cls._store = InMemoryStore()
        
        return cls._store
    
    @classmethod
    def get_checkpointer(cls) -> BaseCheckpointSaver:
        """Get or create the checkpointer instance.
        
        In production, this would use PostgreSQL or another persistent checkpointer.
        For now, we use MemorySaver.
        """
        if cls._checkpointer is None:
            # TODO: In production, use PostgreSQL checkpointer
            # Example:
            # from langgraph.checkpoint.postgres import PostgresSaver
            # db_url = os.getenv("DATABASE_URL")
            # cls._checkpointer = PostgresSaver(db_url)
            
            # For now, use memory saver
            cls._checkpointer = MemorySaver()
        
        return cls._checkpointer
    
    @classmethod
    def get_store_and_checkpointer(cls) -> Tuple[BaseStore, BaseCheckpointSaver]:
        """Get both store and checkpointer instances."""
        return cls.get_store(), cls.get_checkpointer()
    
    @classmethod
    async def close_all(cls):
        """Close all connections (for cleanup)."""
        if cls._store and hasattr(cls._store, 'close'):
            await cls._store.close()
        if cls._checkpointer and hasattr(cls._checkpointer, 'close'):
            await cls._checkpointer.close()
        
        # Reset instances
        cls._store = None
        cls._checkpointer = None