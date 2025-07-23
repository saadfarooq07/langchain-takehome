"""Tools for log analysis.

This module contains functions that are directly exposed to the LLM as tools.
These tools can be used for tasks such as searching documentation,
requesting additional information, and providing analysis results.
"""

import json
from typing import Any, Dict, List, Optional, Union, cast

import aiohttp
from langchain_tavily import TavilySearch
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from .configuration import Configuration
from .state import State
from .cache_utils.cache import get_cache

# Import init_model directly from utils.py to avoid circular imports
from .utils import init_model

# Import persistence utilities
from .persistence_utils import (
    log_debug, log_warning, log_error,
    idempotent, generate_idempotency_key,
    idempotent_operation
)


class CommandSuggestionEngine:
    """Engine for suggesting diagnostic commands based on identified issues."""

    def suggest_commands(
        self, environment_info: Dict[str, Any], issues: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Generate command suggestions based on environment and issues.

        Args:
            environment_info: Information about the system environment
            issues: List of identified issues

        Returns:
            List of command suggestions with descriptions
        """
        suggestions = []

        # Analyze issues and suggest relevant commands
        for issue in issues:
            issue_type = issue.get("type", "").lower()
            issue_desc = issue.get("description", "").lower()

            # Memory-related issues
            if any(
                keyword in issue_desc
                for keyword in ["memory", "heap", "oom", "out of memory"]
            ):
                suggestions.extend(
                    [
                        {
                            "command": "free -h",
                            "description": "Check current memory usage",
                        },
                        {
                            "command": "ps aux --sort=-%mem | head -20",
                            "description": "Show top memory-consuming processes",
                        },
                        {
                            "command": "dmesg | grep -i memory",
                            "description": "Check kernel memory messages",
                        },
                    ]
                )

            # Disk-related issues
            elif any(
                keyword in issue_desc
                for keyword in ["disk", "space", "filesystem", "mount"]
            ):
                suggestions.extend(
                    [
                        {"command": "df -h", "description": "Check disk space usage"},
                        {
                            "command": "du -sh /* 2>/dev/null | sort -h",
                            "description": "Find large directories",
                        },
                        {"command": "lsblk", "description": "List block devices"},
                    ]
                )

            # Network-related issues
            elif any(
                keyword in issue_desc
                for keyword in ["network", "connection", "timeout", "socket"]
            ):
                suggestions.extend(
                    [
                        {
                            "command": "netstat -tuln",
                            "description": "Show listening ports",
                        },
                        {
                            "command": "ss -s",
                            "description": "Socket statistics summary",
                        },
                        {
                            "command": "ip addr show",
                            "description": "Show network interfaces",
                        },
                    ]
                )

            # Process/service issues
            elif any(
                keyword in issue_desc
                for keyword in ["process", "service", "daemon", "crashed"]
            ):
                suggestions.extend(
                    [
                        {
                            "command": "systemctl status",
                            "description": "Check system service status",
                        },
                        {
                            "command": "journalctl -xe --since '1 hour ago'",
                            "description": "Recent system logs",
                        },
                        {
                            "command": "ps aux | grep -v grep | grep <service_name>",
                            "description": "Check if specific service is running",
                        },
                    ]
                )

            # Permission issues
            elif any(
                keyword in issue_desc
                for keyword in ["permission", "denied", "access", "forbidden"]
            ):
                suggestions.extend(
                    [
                        {
                            "command": "ls -la <path>",
                            "description": "Check file permissions",
                        },
                        {
                            "command": "id",
                            "description": "Show current user and groups",
                        },
                        {"command": "sudo -l", "description": "List sudo permissions"},
                    ]
                )

        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            cmd = suggestion["command"]
            if cmd not in seen:
                seen.add(cmd)
                unique_suggestions.append(suggestion)

        # Add general diagnostic commands if no specific ones were added
        if not unique_suggestions:
            unique_suggestions = [
                {"command": "uname -a", "description": "Show system information"},
                {"command": "uptime", "description": "Show system uptime and load"},
                {
                    "command": "tail -50 /var/log/syslog",
                    "description": "Recent system logs",
                },
            ]

        return unique_suggestions


@tool
async def search_documentation(
    query: str, *, config: Annotated[RunnableConfig, InjectedToolArg]
) -> Optional[List[Dict[str, Any]]]:
    """Search for relevant documentation based on the log analysis.

    This function queries the web to find documentation, guides, or forum posts
    that are relevant to the issues identified in the logs.

    Args:
        query: A specific query targeting documentation for the identified issue

    Returns:
        A list of relevant documentation sources with titles, snippets, and URLs
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Make the search idempotent
    async def _perform_search():
        wrapped = TavilySearch(max_results=configuration.max_search_results)
        
        try:
            result = await wrapped.ainvoke({"query": query})
            # Extract results from the response
            if isinstance(result, dict):
                result = result.get("results", [])
            elif isinstance(result, list):
                # Sometimes TavilySearch returns results directly
                pass
            else:
                # Unexpected format
                return []

            # Enhance results with evidence tracking
            enhanced_results = []
            for item in cast(List[Dict[str, Any]], result):
                enhanced_item = {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("snippet", ""),
                    "evidence_type": "documentation",
                    "relevance_score": item.get("score", 0.0),
                    "source_type": _categorize_source(item.get("url", "")),
                }
                enhanced_results.append(enhanced_item)

            return enhanced_results
        except Exception as e:
            # Log the error for debugging but don't fail the analysis
            await log_warning(f"Documentation search failed: {e}")
            return []
    
    # Execute with idempotency
    return await idempotent_operation(
        "search_documentation",
        _perform_search,
        query,
        max_results=configuration.max_search_results,
        cache_result=True
    )


def _categorize_source(url: str) -> str:
    """Categorize the source type based on URL patterns."""
    url_lower = url.lower()

    if "github.com" in url_lower:
        return "github"
    elif "stackoverflow.com" in url_lower:
        return "stackoverflow"
    elif any(doc_site in url_lower for doc_site in ["docs.", "documentation", "wiki"]):
        return "official_docs"
    elif any(forum in url_lower for forum in ["forum", "discuss", "community"]):
        return "forum"
    elif any(blog in url_lower for blog in ["blog", "medium.com", "dev.to"]):
        return "blog"
    else:
        return "other"


@tool
async def request_additional_info(
    request: Dict[str, Any],
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Request additional information from the user to complete the analysis.

    Use this tool when you need more details from the user to provide an accurate analysis.

    Args:
        request: A dictionary containing:
            - "question": The specific question you need answered
            - "reason": Why this information is needed
            - "how_to_retrieve": Instructions on how the user can retrieve this information

    Returns:
        A confirmation that the request was registered
    """
    # Mark that we need user input
    state.needs_user_input = True
    return f"Request for additional information: {request['question']}. Reason: {request['reason']}"


@tool
async def submit_analysis(
    analysis: Union[Dict[str, Any], str],
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Submit the final analysis of the log content.

    Args:
        analysis: A dictionary or JSON string containing:
            - "issues": List of identified issues, each with description and severity
            - "explanations": Detailed explanations of what each issue means
            - "suggestions": Recommended solutions or next steps for each issue
            - "documentation_references": Relevant documentation links for further reading
            - "diagnostic_commands": Recommended commands to run for further investigation

    Returns:
        A confirmation that the analysis was submitted
    """
    import json
    
    # Handle case where analysis is passed as JSON string
    if isinstance(analysis, str):
        try:
            analysis = json.loads(analysis)
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON format in analysis: {e}"
    
    # Ensure analysis is a dictionary
    if not isinstance(analysis, dict):
        return "Error: Analysis must be a dictionary or valid JSON string"
    # Generate command suggestions if not already included
    if "diagnostic_commands" not in analysis:
        engine = CommandSuggestionEngine()
        environment_info = (
            state.environment_info if hasattr(state, "environment_info") else {}
        )
        analysis["diagnostic_commands"] = engine.suggest_commands(
            environment_info=environment_info, issues=analysis.get("issues", [])
        )

    # Use async logging
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(log_debug(f"submit_analysis called with analysis keys: {list(analysis.keys()) if isinstance(analysis, dict) else 'not a dict'}"))
    loop.create_task(log_debug(f"Setting state.analysis_result"))
    state.analysis_result = analysis
    loop.create_task(log_debug(f"State.analysis_result set to: {state.analysis_result is not None}"))
    
    # Cache the analysis result if enabled
    from langchain_core.runnables import RunnableConfig
    config = cast(RunnableConfig, state.get("config", {})) if hasattr(state, "get") else {}
    configuration = Configuration.from_runnable_config(config)
    
    if configuration.enable_cache:
        cache = get_cache()
        log_content = getattr(state, "log_content", None)
        environment_details = getattr(state, "environment_details", None)
        
        if log_content:
            cache.put(log_content, analysis, environment_details)
    
    return "Analysis completed and submitted successfully."