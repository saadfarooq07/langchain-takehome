"""Refactored state definitions with progressive enhancement.

This module provides a lightweight core state with optional features
that can be enabled as needed.
"""

import operator
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Annotated, Any, Dict, List, Optional, Set, Type

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


@dataclass(kw_only=True)
class InputState:
    """Input state defines the interface between the graph and the user (external API)."""

    log_content: str
    "The log content to be analyzed."

    environment_details: Optional[Dict[str, Any]] = field(default=None)
    "Optional details about the software and runtime environment."


@dataclass(kw_only=True)
class CoreState(InputState):
    """Minimal state for basic log analysis.

    This is the lightest state containing only essential fields
    for performing log analysis without any advanced features.
    """

    messages: Annotated[List[BaseMessage], add_messages] = field(default_factory=list)
    """Messages track the primary execution state of the agent."""

    _message_count: int = field(default=0, init=False)
    """Internal counter for message count (for efficiency)."""

    analysis_result: Optional[Dict[str, Any]] = field(default=None)
    "The current analysis result for the log content."

    needs_user_input: bool = field(default=False)
    "Flag indicating whether the agent is awaiting user input."

    def __getstate__(self):
        """Custom serialization for cleaner display in LangGraph Studio."""
        state = asdict(self)
        # Convert messages to a more readable format
        if "messages" in state and state["messages"]:
            state["messages"] = [
                {
                    "type": msg.__class__.__name__,
                    "content": (
                        getattr(msg, "content", str(msg))[:200] + "..."
                        if len(str(getattr(msg, "content", str(msg)))) > 200
                        else getattr(msg, "content", str(msg))
                    ),
                }
                for msg in state["messages"]
            ]
        return state


@dataclass(kw_only=True)
class InteractiveState(CoreState):
    """State with user interaction support.

    Extends CoreState with fields needed for interactive sessions
    where the agent may need to request additional information.
    """

    user_response: str = field(default="")
    "The user's response to a request for additional information."

    pending_request: Optional[Dict[str, Any]] = field(default=None)
    "The current pending request for user information."

    additional_context: Optional[Dict[str, Any]] = field(default=None)
    "Additional context gathered from user interactions."

    follow_up_requests: List[Dict[str, Any]] = field(default_factory=list)
    "Requests for additional information needed from the user."


@dataclass(kw_only=True)
class MemoryState(InteractiveState):
    """State with memory/persistence support.

    Extends InteractiveState with fields needed for memory-based
    features like context retention and performance tracking.
    """

    # Identity management
    thread_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    "Unique thread identifier for this analysis session."

    user_id: Optional[str] = field(default=None)
    "User identifier for memory and personalization."

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    "Session identifier for this analysis."

    # Application context
    application_name: Optional[str] = field(default=None)
    "Name of the application being analyzed."

    application_version: Optional[str] = field(default=None)
    "Version of the application being analyzed."

    environment_type: Optional[str] = field(default=None)
    "Environment type: dev, staging, prod, etc."

    # Performance tracking
    start_time: float = field(default_factory=time.time)
    "Timestamp when analysis started."

    memory_search_count: int = field(default=0)
    "Number of memory searches performed."

    # Retrieved context
    similar_issues: List[Dict[str, Any]] = field(default_factory=list)
    "Similar issues found in memory."

    previous_solutions: List[Dict[str, Any]] = field(default_factory=list)
    "Previous solutions that worked for similar issues."

    user_preferences: Dict[str, Any] = field(default_factory=dict)
    "User preferences for analysis style and output."


@dataclass(kw_only=True)
class OutputState:
    """The response object for the end user."""

    analysis_result: Dict[str, Any]
    """
    A dictionary containing the analyzed log information,
    identified issues, suggested solutions, and documentation references.
    """

    follow_up_requests: Optional[List[Dict[str, Any]]] = None
    "Optional requests for additional information needed to complete or refine the analysis."


# Type alias for the full state (backward compatibility)
State = MemoryState


def create_state_class(features: Optional[Set[str]] = None) -> Type[CoreState]:
    """Dynamically select the appropriate state class based on enabled features.

    Args:
        features: Set of feature flags. Supported values:
            - "interactive": Enable user interaction support
            - "memory": Enable memory/persistence support (implies interactive)

    Returns:
        The appropriate state class for the requested features
    """
    features = features or set()

    # Memory implies interactive
    if "memory" in features:
        return MemoryState
    elif "interactive" in features:
        return InteractiveState
    else:
        return CoreState


def migrate_legacy_state(
    legacy_state: Dict[str, Any], target_class: Type[CoreState]
) -> Dict[str, Any]:
    """Migrate a legacy state dictionary to the new state structure.

    Args:
        legacy_state: State dictionary from the old system
        target_class: The target state class to migrate to

    Returns:
        Migrated state dictionary compatible with the target class
    """
    # Get all field names from the target class
    target_fields = {f.name for f in target_class.__dataclass_fields__.values()}

    # Filter legacy state to only include fields that exist in target
    migrated = {
        key: value for key, value in legacy_state.items() if key in target_fields
    }

    return migrated


def get_state_features(state: Dict[str, Any]) -> Set[str]:
    """Detect which features are being used based on state content.

    Args:
        state: State dictionary to analyze

    Returns:
        Set of detected features
    """
    features = set()

    # Check for interactive features
    interactive_fields = {"user_response", "pending_request", "additional_context"}
    if any(field in state and state[field] for field in interactive_fields):
        features.add("interactive")

    # Check for memory features
    memory_fields = {"user_id", "thread_id", "similar_issues", "user_preferences"}
    if any(field in state and state[field] for field in memory_fields):
        features.add("memory")

    return features
