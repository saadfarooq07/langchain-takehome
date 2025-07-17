"""TypedDict-based state definitions for better LangGraph Studio display."""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class InputStateDict(TypedDict):
    """Input state as TypedDict."""
    log_content: str
    environment_details: Optional[Dict[str, Any]]


class CoreStateDict(InputStateDict):
    """Core state as TypedDict for cleaner serialization."""
    messages: Annotated[List[BaseMessage], add_messages]
    analysis_result: Optional[Dict[str, Any]]
    needs_user_input: bool


class InteractiveStateDict(CoreStateDict):
    """Interactive state as TypedDict."""
    user_response: str
    pending_request: Optional[Dict[str, Any]]
    additional_context: Optional[Dict[str, Any]]
    follow_up_requests: List[Dict[str, Any]]


class MemoryStateDict(InteractiveStateDict):
    """Memory state as TypedDict."""
    thread_id: str
    user_id: Optional[str]
    session_id: str
    application_name: Optional[str]
    application_version: Optional[str]
    environment_type: Optional[str]
    start_time: float
    memory_search_count: int
    similar_issues: List[Dict[str, Any]]
    previous_solutions: List[Dict[str, Any]]
    user_preferences: Dict[str, Any]


class OutputStateDict(TypedDict):
    """Output state as TypedDict."""
    analysis_result: Dict[str, Any]
    follow_up_requests: Optional[List[Dict[str, Any]]]