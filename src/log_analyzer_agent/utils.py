"""Utility functions for the Log Analyzer Agent.

This module contains helper functions for model initialization,
log processing, and other auxiliary tasks.
"""

import asyncio
import os
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from .configuration import Configuration


def _init_model_sync(config: Optional[RunnableConfig] = None) -> BaseChatModel:
    """Initialize the appropriate LLM based on configuration.

    Args:
        config: Optional configuration for the model

    Returns:
        An initialized chat model
    """
    configuration = Configuration.from_runnable_config(config)

    if configuration.model.startswith("gemini:"):
        model_name = configuration.model.split(":", 1)[1]
        # Use GEMINI_API_KEY if available, otherwise fall back to GOOGLE_API_KEY
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required for Gemini models"
            )
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
    elif configuration.model.startswith("kimi:"):
        # Using Groq API to access Kimi-K2
        if "GROQ_API_KEY" not in os.environ:
            raise ValueError(
                "GROQ_API_KEY environment variable is required for Kimi models"
            )

        # Extract model name if format is "kimi:k2"
        if configuration.model == "kimi:k2":
            model_name = "moonshotai/kimi-k2-instruct"
        else:
            # Handle other potential model names
            model_name = "moonshotai/kimi-k2-instruct"

        return ChatGroq(
            model=model_name,
            max_tokens=None,  # Use model default
            temperature=0.3,  # Lower temperature for more deterministic responses
        )
    else:
        # Default to gemini-flash if model not recognized
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required for Gemini models"
            )
        return ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)


async def init_model_async(config: Optional[RunnableConfig] = None) -> BaseChatModel:
    """Initialize the appropriate LLM based on configuration asynchronously.

    This wrapper ensures the model initialization happens in a thread pool
    to avoid blocking the async event loop.

    Args:
        config: Optional configuration for the model

    Returns:
        An initialized chat model
    """
    # Run the blocking initialization in a thread
    return await asyncio.to_thread(_init_model_sync, config)


def init_model(config: Optional[RunnableConfig] = None) -> BaseChatModel:
    """Initialize the appropriate LLM based on configuration.

    NOTE: This is the synchronous version. Use init_model_async() in async contexts.

    Args:
        config: Optional configuration for the model

    Returns:
        An initialized chat model
    """
    return _init_model_sync(config)


def format_environment_context(environment_details: Optional[dict] = None) -> str:
    """Format environment details for inclusion in prompts.

    Args:
        environment_details: Optional dictionary of environment information

    Returns:
        Formatted string describing the environment
    """
    if not environment_details:
        return "No environment details provided."

    context = "Environment Context:\n"
    for category, details in environment_details.items():
        context += f"- {category}: {details}\n"

    return context


def preprocess_log(log_content: str) -> str:
    """Preprocess log content to improve analysis quality.

    This function implements various preprocessing steps like:
    - Extracting environment information
    - Normalizing timestamp formats
    - Highlighting error patterns
    - Detecting runtime packages and versions

    Args:
        log_content: Raw log content

    Returns:
        Preprocessed log content with metadata
    """
    import re
    from collections import defaultdict

    # Initialize environment discovery
    environment_info = {
        "detected_os": None,
        "runtime_versions": {},
        "packages": {},
        "services": {},
        "containers": {},
        "errors": defaultdict(int),
        "log_format": None,
    }

    lines = log_content.split("\n")
    processed_lines = []

    # Common patterns for environment detection
    patterns = {
        # OS/Platform patterns
        "os_linux": r"(Ubuntu|Debian|CentOS|RedHat|Alpine|Linux)",
        "os_windows": r"(Windows|Win32|Win64)",
        "os_mac": r"(Darwin|macOS|Mac OS)",
        # Runtime version patterns
        "python": r"Python[\/\s]+(\d+\.\d+\.\d+)",
        "node": r"(node|Node\.js)[\/\s]+v?(\d+\.\d+\.\d+)",
        "java": r"(Java|JDK|JRE)[\/\s]+(\d+\.\d+\.\d+(?:_\d+)?)",
        "ruby": r"Ruby[\/\s]+(\d+\.\d+\.\d+)",
        "go": r"go[\/\s]+(\d+\.\d+(?:\.\d+)?)",
        "dotnet": r"\.NET[\/\s]+(?:Core[\/\s]+)?(\d+\.\d+(?:\.\d+)?)",
        # Package managers
        "npm_package": r"npm\s+(?:WARN|ERR|info)?\s*([a-zA-Z0-9\-\.@\/]+)@(\d+\.\d+\.\d+)",
        "pip_package": r"([a-zA-Z0-9\-_]+)==(\d+\.\d+\.\d+)",
        "gem_package": r"gem\s+'([a-zA-Z0-9\-_]+)'(?:,\s*')?(?:~>|>=)?\s*(\d+\.\d+\.\d+)",
        # Database/Services
        "postgres": r"PostgreSQL[\/\s]+(\d+\.\d+)",
        "mysql": r"MySQL[\/\s]+(\d+\.\d+\.\d+)",
        "redis": r"Redis[\/\s]+(?:server[\/\s]+)?v?(\d+\.\d+\.\d+)",
        "mongodb": r"MongoDB[\/\s]+(?:server[\/\s]+)?(?:version[\/\s]+)?(\d+\.\d+\.\d+)",
        "elasticsearch": r"Elasticsearch[\/\s]+(\d+\.\d+\.\d+)",
        # Container/Orchestration
        "docker": r"Docker[\/\s]+(?:version[\/\s]+)?(\d+\.\d+\.\d+)",
        "kubernetes": r"(?:Kubernetes|kubectl)[\/\s]+v?(\d+\.\d+\.\d+)",
        "container_id": r"container[_\s]?(?:id|ID)?[:\s]+([a-f0-9]{12,64})",
        # Error patterns
        "error": r"(?:ERROR|FATAL|CRITICAL|SEVERE)",
        "warning": r"(?:WARN|WARNING)",
        "stacktrace": r"(?:Traceback|at\s+\w+\.|Exception|Error:|Stack trace:)",
        # Common log formats
        "timestamp_iso": r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}",
        "timestamp_unix": r"\b\d{10}\b",
        "log_level": r"\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|TRACE)\b",
    }

    # Process each line
    for line in lines:
        # Skip empty lines
        if not line.strip():
            processed_lines.append(line)
            continue

        # Detect OS/Platform
        for os_key, os_pattern in [
            (k, v) for k, v in patterns.items() if k.startswith("os_")
        ]:
            if match := re.search(os_pattern, line, re.IGNORECASE):
                environment_info["detected_os"] = match.group(1)

        # Detect runtime versions
        for runtime in ["python", "node", "java", "ruby", "go", "dotnet"]:
            if match := re.search(patterns[runtime], line, re.IGNORECASE):
                version = match.group(2) if runtime == "node" else match.group(1)
                environment_info["runtime_versions"][runtime] = version

        # Detect packages
        for pkg_pattern_key in ["npm_package", "pip_package", "gem_package"]:
            for match in re.finditer(patterns[pkg_pattern_key], line):
                pkg_name = match.group(1)
                pkg_version = match.group(2)
                environment_info["packages"][pkg_name] = pkg_version

        # Detect services
        for service in ["postgres", "mysql", "redis", "mongodb", "elasticsearch"]:
            if match := re.search(patterns[service], line, re.IGNORECASE):
                environment_info["services"][service] = match.group(1)

        # Detect container info
        if match := re.search(patterns["docker"], line, re.IGNORECASE):
            environment_info["containers"]["docker_version"] = match.group(1)
        if match := re.search(patterns["kubernetes"], line, re.IGNORECASE):
            environment_info["containers"]["kubernetes_version"] = match.group(1)
        if match := re.search(patterns["container_id"], line):
            environment_info["containers"]["container_id"] = match.group(1)

        # Count error types
        if re.search(patterns["error"], line):
            environment_info["errors"]["error"] += 1
        if re.search(patterns["warning"], line):
            environment_info["errors"]["warning"] += 1
        if re.search(patterns["stacktrace"], line):
            environment_info["errors"]["stacktrace"] += 1

        # Detect log format
        if not environment_info["log_format"]:
            if re.search(patterns["timestamp_iso"], line):
                environment_info["log_format"] = "ISO timestamp"
            elif re.search(patterns["timestamp_unix"], line):
                environment_info["log_format"] = "Unix timestamp"

        processed_lines.append(line)

    # Build enhanced log content with metadata
    metadata_section = "\n=== ENVIRONMENT DISCOVERY ===\n"

    if environment_info["detected_os"]:
        metadata_section += f"Operating System: {environment_info['detected_os']}\n"

    if environment_info["runtime_versions"]:
        metadata_section += "\nRuntime Versions:\n"
        for runtime, version in environment_info["runtime_versions"].items():
            metadata_section += f"  - {runtime.capitalize()}: {version}\n"

    if environment_info["packages"]:
        metadata_section += "\nDetected Packages:\n"
        for pkg, version in list(environment_info["packages"].items())[
            :10
        ]:  # Limit to first 10
            metadata_section += f"  - {pkg}: {version}\n"
        if len(environment_info["packages"]) > 10:
            metadata_section += (
                f"  ... and {len(environment_info['packages']) - 10} more\n"
            )

    if environment_info["services"]:
        metadata_section += "\nDetected Services:\n"
        for service, version in environment_info["services"].items():
            metadata_section += f"  - {service.capitalize()}: {version}\n"

    if environment_info["containers"]:
        metadata_section += "\nContainer Environment:\n"
        for key, value in environment_info["containers"].items():
            metadata_section += f"  - {key.replace('_', ' ').title()}: {value}\n"

    if environment_info["errors"]:
        metadata_section += "\nError Summary:\n"
        for error_type, count in environment_info["errors"].items():
            metadata_section += f"  - {error_type.upper()}: {count} occurrences\n"

    if environment_info["log_format"]:
        metadata_section += f"\nLog Format: {environment_info['log_format']}\n"

    metadata_section += "=== END ENVIRONMENT DISCOVERY ===\n\n"

    # Return enhanced log content
    return metadata_section + "\n".join(processed_lines)


def count_node_visits(messages: list, node_name: str) -> int:
    """Count how many times a specific node has been visited.
    
    Args:
        messages: List of messages in the conversation
        node_name: Name of the node to count
        
    Returns:
        Number of times the node has been visited
    """
    count = 0
    for msg in messages:
        if hasattr(msg, "name") and msg.name == node_name:
            count += 1
        elif hasattr(msg, "additional_kwargs"):
            kwargs = msg.additional_kwargs
            if kwargs.get("name") == node_name:
                count += 1
    return count


def count_tool_calls(messages: list) -> int:
    """Count total number of tool calls in the conversation.
    
    Args:
        messages: List of messages in the conversation
        
    Returns:
        Total number of tool calls
    """
    count = 0
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            count += len(msg.tool_calls)
    return count
