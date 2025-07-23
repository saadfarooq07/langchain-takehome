"""Prompt Registry for managing prompts with LangSmith.

This module provides a centralized way to manage prompts using LangSmith's
prompt management API. It supports pushing, pulling, and caching prompts
with version control and fallback mechanisms.
"""

import os
import asyncio
from typing import Dict, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate, BasePromptTemplate
from pydantic import BaseModel, Field

from .prompts import (
    main_prompt_template,
    analysis_checker_template,
    followup_template,
    documentation_search_template,
)
from .persistence_utils import (
    save_json_to_file, read_json_from_file,
    log_debug, log_info, log_warning, log_error
)

logger = logging.getLogger(__name__)


class PromptConfig(BaseModel):
    """Configuration for a prompt in the registry."""
    
    name: str = Field(description="Prompt name in LangSmith")
    version: Optional[str] = Field(default="latest", description="Version to use")
    fallback_template: Optional[BasePromptTemplate] = Field(
        default=None, 
        description="Local fallback if LangSmith is unavailable"
    )
    cache_ttl: int = Field(
        default=3600,  # 1 hour
        description="Cache time-to-live in seconds"
    )


class PromptCacheEntry(BaseModel):
    """Cache entry for a prompt."""
    
    prompt: BasePromptTemplate
    fetched_at: datetime
    version: str
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() - self.fetched_at > timedelta(seconds=ttl_seconds)


class PromptRegistry:
    """Registry for managing prompts with LangSmith integration.
    
    This class provides:
    - Centralized prompt management
    - Version control through LangSmith
    - Local caching with TTL
    - Fallback to local prompts
    - Async support for non-blocking operations
    """
    
    # Default prompt configurations (base names, prefix added dynamically)
    DEFAULT_PROMPTS = {
        "main": PromptConfig(
            name="main",
            fallback_template=main_prompt_template
        ),
        "validation": PromptConfig(
            name="validation",
            fallback_template=analysis_checker_template
        ),
        "followup": PromptConfig(
            name="followup",
            fallback_template=followup_template
        ),
        "doc-search": PromptConfig(
            name="doc-search",
            fallback_template=documentation_search_template
        ),
    }
    
    def __init__(
        self,
        client: Optional[Client] = None,
        cache_dir: Optional[Path] = None,
        enable_cache: bool = True,
        enable_langsmith: bool = True,
        prompt_prefix: Optional[str] = None,
    ):
        """Initialize the prompt registry.
        
        Args:
            client: LangSmith client instance
            cache_dir: Directory for local cache
            enable_cache: Whether to enable caching
            enable_langsmith: Whether to use LangSmith (if False, only uses local)
            prompt_prefix: Prefix for prompt names (e.g., 'myorg' -> 'myorg/main')
                         If None, uses environment variable LANGSMITH_PROMPT_PREFIX
                         If empty string, uses no prefix (just 'main', 'validation', etc.)
        """
        self.enable_langsmith = enable_langsmith and os.getenv("LANGSMITH_API_KEY")
        
        # Set prompt prefix from parameter, env var, or default
        if prompt_prefix is None:
            prompt_prefix = os.getenv("LANGSMITH_PROMPT_PREFIX", "log-analyzer")
        self.prompt_prefix = prompt_prefix
        
        if self.enable_langsmith:
            self.client = client or Client()
        else:
            self.client = None
            asyncio.create_task(log_info("LangSmith integration disabled or API key not found"))
        
        self.enable_cache = enable_cache
        self.cache_dir = cache_dir or Path.home() / ".langchain" / "prompt_cache"
        self.memory_cache: Dict[str, PromptCacheEntry] = {}
        
        if self.enable_cache:
            # Use asyncio.to_thread to avoid blocking the event loop
            import asyncio
            try:
                asyncio.get_running_loop()
                # We're in an async context, defer mkdir
                self._cache_dir_created = False
            except RuntimeError:
                # We're in a sync context, safe to create
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self._cache_dir_created = True
    
    async def _ensure_cache_dir(self):
        """Ensure cache directory exists (async-safe)."""
        if self.enable_cache and not getattr(self, '_cache_dir_created', True):
            import asyncio
            # Check if directory exists first
            if not await asyncio.to_thread(self.cache_dir.exists):
                await asyncio.to_thread(self.cache_dir.mkdir, parents=True, exist_ok=True)
            self._cache_dir_created = True
    
    def _format_prompt_name(self, prompt_name: str) -> str:
        """Format prompt name with prefix if needed.
        
        Args:
            prompt_name: Base prompt name (e.g., 'main', 'validation')
            
        Returns:
            Formatted prompt name with prefix if configured
        """
        # If prompt already contains a slash, assume it's fully qualified
        if "/" in prompt_name:
            return prompt_name
        
        # If no prefix configured, return as-is
        if not self.prompt_prefix:
            return prompt_name
            
        # Add prefix
        return f"{self.prompt_prefix}/{prompt_name}"
    
    async def get_prompt(
        self,
        prompt_name: str,
        version: Optional[str] = None,
        force_refresh: bool = False,
    ) -> BasePromptTemplate:
        """Get a prompt by name, with caching and fallback support.
        
        Args:
            prompt_name: Name of the prompt in LangSmith
            version: Specific version to fetch (default: latest)
            force_refresh: Force refresh from LangSmith
            
        Returns:
            The prompt template
        """
        # Ensure cache directory exists
        await self._ensure_cache_dir()
        
        # Format the prompt name with prefix
        formatted_name = self._format_prompt_name(prompt_name)
        
        # Get configuration (check both formatted and original names for backward compatibility)
        config = self.DEFAULT_PROMPTS.get(formatted_name) or self.DEFAULT_PROMPTS.get(prompt_name)
        if not config:
            config = PromptConfig(name=formatted_name, version=version or "latest")
        elif version:
            config.version = version
        
        # Check memory cache first
        cache_key = f"{formatted_name}:{config.version}"
        if not force_refresh and self.enable_cache:
            cached = await self._get_from_cache(cache_key, config.cache_ttl)
            if cached:
                return cached
        
        # Try to fetch from LangSmith
        if self.enable_langsmith:
            try:
                prompt = await self._fetch_from_langsmith(formatted_name, config.version)
                if prompt:
                    await self._save_to_cache(cache_key, prompt, config.version)
                    return prompt
            except Exception as e:
                await log_warning(f"Failed to fetch prompt from LangSmith: {e}")
        
        # Fall back to local template
        if config.fallback_template:
            await log_info(f"Using local fallback for prompt: {prompt_name}")
            return config.fallback_template
        
        raise ValueError(f"Prompt not found and no fallback available: {prompt_name}")
    
    async def push_prompt(
        self,
        prompt_name: str,
        prompt: BasePromptTemplate,
        description: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> str:
        """Push a prompt to LangSmith.
        
        Args:
            prompt_name: Name for the prompt in LangSmith
            prompt: The prompt template to push
            description: Optional description
            tags: Optional tags
            
        Returns:
            Version identifier of the pushed prompt
        """
        if not self.enable_langsmith:
            raise RuntimeError("LangSmith integration is disabled")
        
        try:
            # Format the prompt name with prefix
            formatted_name = self._format_prompt_name(prompt_name)
            
            # Push to LangSmith
            result = await asyncio.to_thread(
                self.client.push_prompt,
                formatted_name,
                object=prompt,
                description=description,
                tags=tags or ["log-analyzer"],
                is_public=False,  # Keep prompts private to avoid tenant configuration issues
            )
            
            # Invalidate cache for this prompt
            await self._invalidate_cache(formatted_name)
            
            await log_info(f"Successfully pushed prompt: {formatted_name}")
            # Result is a string containing the commit hash/version
            return result if isinstance(result, str) else result.get("version", "unknown")
            
        except Exception as e:
            await log_error(f"Failed to push prompt to LangSmith: {e}")
            raise
    
    def list_prompts(self) -> Dict[str, PromptConfig]:
        """List all registered prompts."""
        return self.DEFAULT_PROMPTS.copy()
    
    async def _fetch_from_langsmith(
        self,
        prompt_name: str,
        version: str = "latest"
    ) -> Optional[BasePromptTemplate]:
        """Fetch a prompt from LangSmith."""
        try:
            # LangSmith pull_prompt is synchronous, so we run it in a thread
            # Note: pull_prompt includes version in the name (e.g., "my-prompt:version-id")
            full_name = prompt_name if version == "latest" else f"{prompt_name}:{version}"
            prompt = await asyncio.to_thread(
                self.client.pull_prompt,
                full_name
            )
            return prompt
        except Exception as e:
            await log_error(f"Error fetching prompt {prompt_name}:{version} - {e}")
            return None
    
    async def _get_from_cache(self, cache_key: str, ttl: int) -> Optional[BasePromptTemplate]:
        """Get prompt from cache if not expired."""
        # Check memory cache
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            if not entry.is_expired(ttl):
                await log_debug(f"Using memory cached prompt: {cache_key}")
                return entry.prompt
        
        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key.replace('/', '_')}.json"
        import asyncio
        if await asyncio.to_thread(cache_file.exists):
            try:
                data = await self._read_cache_file_async(cache_file)
                entry = PromptCacheEntry(
                    prompt=ChatPromptTemplate.from_template(data["template"]),
                    fetched_at=datetime.fromisoformat(data["fetched_at"]),
                    version=data["version"]
                )
                if not entry.is_expired(ttl):
                    await log_debug(f"Using disk cached prompt: {cache_key}")
                    self.memory_cache[cache_key] = entry
                    return entry.prompt
            except Exception as e:
                await log_warning(f"Failed to load cached prompt: {e}")
        
        return None
    
    async def _read_cache_file_async(self, cache_file):
        """Helper method to read cache file asynchronously."""
        import asyncio
        return await read_json_from_file(cache_file)
    
    async def _save_to_cache(
        self,
        cache_key: str,
        prompt: BasePromptTemplate,
        version: str
    ) -> None:
        """Save prompt to cache."""
        entry = PromptCacheEntry(
            prompt=prompt,
            fetched_at=datetime.now(),
            version=version
        )
        
        # Save to memory cache
        self.memory_cache[cache_key] = entry
        
        # Save to disk cache
        try:
            cache_file = self.cache_dir / f"{cache_key.replace('/', '_')}.json"
            # Extract template string for serialization
            template_str = prompt.messages[0].prompt.template if hasattr(prompt, 'messages') else str(prompt)
            
            # Use aiofiles for async file operations
            await self._write_cache_file_async(cache_file, {
                "template": template_str,
                "fetched_at": entry.fetched_at.isoformat(),
                "version": version
            })
        except Exception as e:
            await log_warning(f"Failed to save prompt to disk cache: {e}")
    
    async def _write_cache_file_async(self, cache_file, data):
        """Helper method to write cache file asynchronously."""
        import asyncio
        await save_json_to_file(cache_file, data)
    
    async def _invalidate_cache(self, prompt_name: str) -> None:
        """Invalidate all cached versions of a prompt."""
        # Remove from memory cache
        keys_to_remove = [k for k in self.memory_cache if k.startswith(f"{prompt_name}:")]
        for key in keys_to_remove:
            del self.memory_cache[key]
        
        # Remove from disk cache
        import asyncio
        pattern = f"{prompt_name.replace('/', '_')}*.json"
        cache_files = await asyncio.to_thread(list, self.cache_dir.glob(pattern))
        for cache_file in cache_files:
            try:
                await asyncio.to_thread(cache_file.unlink)
            except Exception as e:
                await log_warning(f"Failed to remove cache file: {e}")


# Singleton instance
_registry: Optional[PromptRegistry] = None


def get_prompt_registry() -> PromptRegistry:
    """Get the singleton prompt registry instance."""
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry


async def get_prompt(name: str, version: Optional[str] = None) -> BasePromptTemplate:
    """Convenience function to get a prompt from the registry."""
    registry = get_prompt_registry()
    return await registry.get_prompt(name, version)