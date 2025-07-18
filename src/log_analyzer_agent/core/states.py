"""Clean state management system with clear boundaries.

This module provides a clear separation of concerns for state management:
- InputState: User-provided data (immutable)
- WorkingState: Agent's internal state (mutable during execution)
- OutputState: Results to return to the user (immutable)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, FrozenSet
from datetime import datetime
from enum import Enum
from langchain_core.messages import BaseMessage
import hashlib
import json


class StateType(Enum):
    """Types of states in the system."""
    INPUT = "input"
    WORKING = "working"
    OUTPUT = "output"


@dataclass(frozen=True)
class InputState:
    """Immutable state representing user input.
    
    This state contains only the data provided by the user and should
    never be modified during execution.
    """
    log_content: str
    environment_details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate input state."""
        if not self.log_content:
            raise ValueError("log_content cannot be empty")
        if len(self.log_content) > 10_000_000:  # 10MB limit
            raise ValueError("log_content exceeds maximum size of 10MB")
    
    def get_hash(self) -> str:
        """Get a hash of the input for caching purposes."""
        content = f"{self.log_content}{json.dumps(self.environment_details, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class WorkingState:
    """Mutable state for agent's working memory.
    
    This state is used internally by the agent during execution and
    contains all intermediate results and metadata.
    """
    # Core working data
    messages: List[BaseMessage] = field(default_factory=list)
    current_analysis: Optional[Dict[str, Any]] = None
    
    # Execution tracking
    node_visits: Dict[str, int] = field(default_factory=dict)
    tool_calls: Dict[str, int] = field(default_factory=dict)
    iteration_count: int = 0
    
    # Feature flags (composition over inheritance)
    features: FrozenSet[str] = field(default_factory=frozenset)
    
    # Interactive features (only used if 'interactive' in features)
    needs_user_input: bool = False
    pending_request: Optional[Dict[str, Any]] = None
    user_response: Optional[str] = None
    
    # Memory features (only used if 'memory' in features)
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    similar_issues: List[Dict[str, Any]] = field(default_factory=list)
    previous_solutions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance tracking
    start_time: float = field(default_factory=lambda: datetime.utcnow().timestamp())
    token_count: int = 0
    
    def increment_node_visit(self, node_name: str) -> None:
        """Increment visit count for a node."""
        self.node_visits[node_name] = self.node_visits.get(node_name, 0) + 1
        self.iteration_count += 1
    
    def increment_tool_call(self, tool_name: str) -> None:
        """Increment call count for a tool."""
        self.tool_calls[tool_name] = self.tool_calls.get(tool_name, 0) + 1
    
    def has_feature(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return feature in self.features
    
    def get_total_tool_calls(self) -> int:
        """Get total number of tool calls."""
        return sum(self.tool_calls.values())
    
    def should_continue(self, max_iterations: int = 50, max_tool_calls: int = 20) -> bool:
        """Check if execution should continue based on limits."""
        return (
            self.iteration_count < max_iterations and
            self.get_total_tool_calls() < max_tool_calls
        )


@dataclass(frozen=True)
class OutputState:
    """Immutable state representing the final output.
    
    This state contains the results to be returned to the user.
    """
    analysis_result: Dict[str, Any]
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    follow_up_requests: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate output state."""
        if not self.analysis_result:
            raise ValueError("analysis_result cannot be empty")
        
        # Ensure required fields in analysis result
        required_fields = ["issues", "root_cause", "recommendations"]
        missing = [f for f in required_fields if f not in self.analysis_result]
        if missing:
            raise ValueError(f"analysis_result missing required fields: {missing}")
    
    def to_user_response(self) -> Dict[str, Any]:
        """Convert to user-friendly response format."""
        return {
            "analysis": self.analysis_result,
            "metadata": {
                "execution_time": self.execution_metadata.get("execution_time_seconds", 0),
                "tokens_used": self.execution_metadata.get("token_count", 0),
                "tools_called": self.execution_metadata.get("tools_called", []),
            },
            "follow_up_available": len(self.follow_up_requests) > 0
        }


class StateTransition:
    """Manages transitions between state types."""
    
    @staticmethod
    def create_working_state(
        input_state: InputState,
        features: Optional[Set[str]] = None
    ) -> WorkingState:
        """Create a working state from input state."""
        return WorkingState(
            features=frozenset(features or set()),
            thread_id=input_state.request_id,
        )
    
    @staticmethod
    def create_output_state(
        working_state: WorkingState,
        analysis_result: Dict[str, Any]
    ) -> OutputState:
        """Create output state from working state."""
        execution_time = datetime.utcnow().timestamp() - working_state.start_time
        
        metadata = {
            "execution_time_seconds": round(execution_time, 2),
            "token_count": working_state.token_count,
            "iterations": working_state.iteration_count,
            "node_visits": dict(working_state.node_visits),
            "tools_called": list(working_state.tool_calls.keys()),
            "features_used": list(working_state.features),
        }
        
        return OutputState(
            analysis_result=analysis_result,
            execution_metadata=metadata,
        )


class StateValidator:
    """Validates state transitions and constraints."""
    
    @staticmethod
    def validate_feature_requirements(state: WorkingState) -> None:
        """Validate that required features are properly configured."""
        if state.has_feature("memory"):
            if not state.thread_id or not state.session_id:
                raise ValueError("Memory feature requires thread_id and session_id")
        
        if state.has_feature("interactive"):
            if state.needs_user_input and not state.pending_request:
                raise ValueError("Interactive feature requires pending_request when needs_user_input is True")
    
    @staticmethod
    def validate_limits(state: WorkingState, config: Dict[str, Any]) -> None:
        """Validate execution limits."""
        max_iterations = config.get("max_iterations", 50)
        max_tool_calls = config.get("max_tool_calls", 20)
        
        if state.iteration_count >= max_iterations:
            raise RuntimeError(f"Exceeded maximum iterations: {max_iterations}")
        
        if state.get_total_tool_calls() >= max_tool_calls:
            raise RuntimeError(f"Exceeded maximum tool calls: {max_tool_calls}")