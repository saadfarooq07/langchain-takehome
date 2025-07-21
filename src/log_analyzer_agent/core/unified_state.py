"""Unified state management for the log analyzer agent.

This module consolidates the three separate state classes (CoreState, InteractiveState, 
MemoryState) into a single unified state with feature flags. This simplifies state 
management and enables dynamic feature composition.
"""

from typing import List, Dict, Any, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage


@dataclass
class UnifiedState:
    """Unified state for the log analyzer graph with feature-based composition.
    
    This state class consolidates all functionality from CoreState, InteractiveState,
    and MemoryState into a single class with feature flags to enable/disable
    specific capabilities.
    
    Features:
        - "interactive": Enable user interaction capabilities
        - "memory": Enable memory/persistence features
        - "streaming": Enable streaming for large logs
        - "caching": Enable result caching
        - "specialized": Enable specialized subgraph analyzers
    """
    
    # Core fields (always present)
    messages: List[AnyMessage] = field(default_factory=list)
    log_content: str = ""
    log_metadata: Dict[str, Any] = field(default_factory=dict)
    analysis_result: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None
    
    # Feature flags
    features: Set[str] = field(default_factory=set)
    
    # Tracking fields
    node_visits: Dict[str, int] = field(default_factory=dict)
    tool_calls: List[str] = field(default_factory=list)
    token_count: int = 0
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    
    # Interactive features (enabled with "interactive" feature)
    user_interaction_required: bool = False
    pending_questions: List[str] = field(default_factory=list)
    user_responses: Dict[str, str] = field(default_factory=dict)
    
    # Memory features (enabled with "memory" feature)
    memory_matches: List[Dict[str, Any]] = field(default_factory=list)
    application_context: Dict[str, Any] = field(default_factory=dict)
    tenant_id: Optional[str] = None
    
    # Streaming features (enabled with "streaming" feature)
    is_streaming: bool = False
    current_chunk_index: int = 0
    total_chunks: int = 0
    chunk_results: List[Dict[str, Any]] = field(default_factory=list)
    
    # Circuit breaker state (for reliability)
    circuit_breaker_state: str = "closed"  # closed, open, half_open
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    
    def has_feature(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return feature in self.features
    
    def enable_feature(self, feature: str) -> None:
        """Enable a feature."""
        self.features.add(feature)
        
        # Initialize feature-specific fields when enabled
        if feature == "streaming" and not self.is_streaming:
            # Check if log is large enough to warrant streaming
            log_size = len(self.log_content.encode('utf-8'))
            if log_size > 10 * 1024 * 1024:  # 10MB
                self.is_streaming = True
    
    def disable_feature(self, feature: str) -> None:
        """Disable a feature."""
        self.features.discard(feature)
    
    def add_message(self, message: AnyMessage) -> None:
        """Add a message to the state."""
        self.messages.append(message)
        
        # Update token count (simplified estimation)
        if isinstance(message, (HumanMessage, AIMessage)):
            content = message.content if isinstance(message.content, str) else str(message.content)
            self.token_count += len(content.split()) * 1.3  # Rough token estimate
    
    def increment_node_visit(self, node_name: str) -> None:
        """Increment the visit count for a node."""
        self.node_visits[node_name] = self.node_visits.get(node_name, 0) + 1
    
    def add_tool_call(self, tool_name: str) -> None:
        """Record a tool call."""
        self.tool_calls.append(tool_name)
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since state creation."""
        return datetime.now().timestamp() - self.start_time
    
    def should_enable_streaming(self) -> bool:
        """Check if streaming should be enabled based on log size."""
        if self.has_feature("streaming"):
            log_size = len(self.log_content.encode('utf-8'))
            return log_size > 10 * 1024 * 1024  # 10MB threshold
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary format for serialization."""
        return {
            "messages": self.messages,
            "log_content": self.log_content,
            "log_metadata": self.log_metadata,
            "analysis_result": self.analysis_result,
            "validation_status": self.validation_status,
            "features": list(self.features),
            "node_visits": self.node_visits,
            "tool_calls": self.tool_calls,
            "token_count": self.token_count,
            "start_time": self.start_time,
            "user_interaction_required": self.user_interaction_required,
            "pending_questions": self.pending_questions,
            "user_responses": self.user_responses,
            "memory_matches": self.memory_matches,
            "application_context": self.application_context,
            "tenant_id": self.tenant_id,
            "is_streaming": self.is_streaming,
            "current_chunk_index": self.current_chunk_index,
            "total_chunks": self.total_chunks,
            "chunk_results": self.chunk_results,
            "circuit_breaker_state": self.circuit_breaker_state,
            "consecutive_failures": self.consecutive_failures,
            "last_failure_time": self.last_failure_time,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedState":
        """Create state from dictionary format."""
        state = cls()
        
        # Restore core fields
        state.messages = data.get("messages", [])
        state.log_content = data.get("log_content", "")
        state.log_metadata = data.get("log_metadata", {})
        state.analysis_result = data.get("analysis_result")
        state.validation_status = data.get("validation_status")
        
        # Restore features
        state.features = set(data.get("features", []))
        
        # Restore tracking
        state.node_visits = data.get("node_visits", {})
        state.tool_calls = data.get("tool_calls", [])
        state.token_count = data.get("token_count", 0)
        state.start_time = data.get("start_time", datetime.now().timestamp())
        
        # Restore feature-specific fields
        if "interactive" in state.features:
            state.user_interaction_required = data.get("user_interaction_required", False)
            state.pending_questions = data.get("pending_questions", [])
            state.user_responses = data.get("user_responses", {})
        
        if "memory" in state.features:
            state.memory_matches = data.get("memory_matches", [])
            state.application_context = data.get("application_context", {})
            state.tenant_id = data.get("tenant_id")
        
        if "streaming" in state.features:
            state.is_streaming = data.get("is_streaming", False)
            state.current_chunk_index = data.get("current_chunk_index", 0)
            state.total_chunks = data.get("total_chunks", 0)
            state.chunk_results = data.get("chunk_results", [])
        
        # Restore circuit breaker state
        state.circuit_breaker_state = data.get("circuit_breaker_state", "closed")
        state.consecutive_failures = data.get("consecutive_failures", 0)
        state.last_failure_time = data.get("last_failure_time")
        
        return state


def create_unified_state(
    log_content: str,
    features: Optional[Set[str]] = None,
    **kwargs
) -> UnifiedState:
    """Factory function to create a unified state with specified features.
    
    Args:
        log_content: The log content to analyze
        features: Set of features to enable
        **kwargs: Additional fields to set on the state
        
    Returns:
        Configured UnifiedState instance
    """
    state = UnifiedState(
        log_content=log_content,
        features=features or set(),
        **kwargs
    )
    
    # Auto-enable streaming for large logs
    if state.should_enable_streaming():
        state.enable_feature("streaming")
        state.is_streaming = True
    
    return state