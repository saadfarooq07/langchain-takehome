"""TypedDict definitions for LangGraph state management."""

from typing import List, Dict, Any, Optional, Annotated, Sequence
from typing_extensions import TypedDict, NotRequired
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class State(TypedDict, total=False):
    """Main state for the log analyzer graph.
    
    This is the TypedDict version required by LangGraph.
    
    Note: total=False means all fields are optional by default.
    Only fields that should be required from user input need to be explicitly marked.
    """
    # Messages with reducer (managed by LangGraph)
    messages: Annotated[Sequence[AnyMessage], add_messages]
    
    # The only truly required field from user input
    log_content: str
    
    # All other fields are optional/internal
    log_metadata: Dict[str, Any]
    analysis_result: Optional[Dict[str, Any]]
    validation_status: Optional[str]
    
    # Tracking (initialized internally)
    node_visits: Dict[str, int]
    tool_calls: List[str]
    token_count: int
    start_time: float
    
    # Features (initialized internally)
    enabled_features: List[str]
    
    # Interactive features (optional)
    user_interaction_required: Optional[bool]
    pending_questions: Optional[List[str]]
    user_responses: Optional[Dict[str, str]]
    
    # Memory features (optional)
    memory_matches: Optional[List[Dict[str, Any]]]
    application_context: Optional[Dict[str, Any]]
    
    # Streaming features (optional)
    is_streaming: Optional[bool]
    current_chunk_index: Optional[int]
    total_chunks: Optional[int]
    chunk_results: Optional[List[Dict[str, Any]]]