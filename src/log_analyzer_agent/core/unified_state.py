"""Unified state management for the log analyzer agent.

This module provides a single, flexible state class that replaces the 
previous CoreState, InteractiveState, and MemoryState classes.
"""

from typing import Dict, Any, List, Optional, Set, Annotated, Sequence
from datetime import datetime
from dataclasses import dataclass, field
from langchain_core.messages import BaseMessage, AnyMessage
from langgraph.graph.message import add_messages


@dataclass
class UnifiedState:
    """Single unified state class with feature-based capabilities.
    
    This state class uses composition over inheritance, with features
    enabled through flags rather than separate classes.
    """
    # Core fields (always present)
    messages: Annotated[Sequence[AnyMessage], add_messages]
    log_content: str
    log_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Analysis state
    analysis_result: Optional[Dict[str, Any]] = None
    chunk_results: List[Dict[str, Any]] = field(default_factory=list)
    validation_status: Optional[str] = None
    
    # Feature flags
    features: Set[str] = field(default_factory=set)
    
    # Optional context (populated based on features)
    environment_details: Optional[Dict[str, Any]] = None
    memory_context: Optional[Dict[str, Any]] = None
    user_context: Optional[Dict[str, Any]] = None
    
    # Streaming support
    is_streaming: bool = False
    current_chunk_index: int = 0
    total_chunks: int = 0
    
    # Checkpointing support
    checkpoint_id: Optional[str] = None
    last_checkpoint: Optional[datetime] = None
    
    # Execution tracking (replaces manual counting)
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_feature(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return feature in self.features
    
    def enable_feature(self, feature: str) -> None:
        """Enable a feature."""
        self.features.add(feature)
    
    def disable_feature(self, feature: str) -> None:
        """Disable a feature."""
        self.features.discard(feature)
    
    @property
    def supports_memory(self) -> bool:
        """Check if memory features are enabled."""
        return self.has_feature("memory")
    
    @property
    def supports_interaction(self) -> bool:
        """Check if interactive features are enabled."""
        return self.has_feature("interactive")
    
    @property
    def supports_streaming(self) -> bool:
        """Check if streaming is enabled."""
        return self.has_feature("streaming") or self.is_streaming
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get a summary of the analysis state."""
        return {
            "has_result": self.analysis_result is not None,
            "chunk_count": len(self.chunk_results),
            "is_validated": self.validation_status == "valid",
            "features_enabled": list(self.features),
            "is_streaming": self.is_streaming
        }


# Input/Output schemas for better type safety
@dataclass
class LogAnalysisInput:
    """Input schema for log analysis."""
    log_content: str
    environment_details: Optional[Dict[str, Any]] = None
    enable_features: Set[str] = field(default_factory=set)
    streaming_threshold_mb: float = 10.0
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass 
class LogAnalysisOutput:
    """Output schema for log analysis."""
    issues: List[Dict[str, Any]]
    root_cause: str
    recommendations: List[str]
    documentation_references: List[Dict[str, str]]
    diagnostic_commands: List[Dict[str, str]]
    confidence_score: float
    analysis_metadata: Dict[str, Any] = field(default_factory=dict) 