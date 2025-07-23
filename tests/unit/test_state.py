"""Unit tests for state management."""

import pytest
from datetime import datetime
from typing import List

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.log_analyzer_agent.state import (
    CoreWorkingState,
    InteractiveWorkingState,
    MemoryWorkingState,
    create_state_class
)
from src.log_analyzer_agent.state_compat import _get_state_features as get_state_features


class TestCoreState:
    """Test the basic CoreState functionality."""
    
    def test_core_state_initialization(self):
        """Test that CoreWorkingState can be initialized with minimal fields."""
        state = CoreWorkingState(
            messages=[],
            log_content="test log"
        )
        assert state.messages == []
        assert state.log_content == "test log"
        assert state.analysis_result is None
        assert state.token_count == 0
        assert state.node_visits == {}
    
    def test_core_state_with_messages(self):
        """Test CoreWorkingState with messages."""
        messages = [
            HumanMessage(content="Analyze this log"),
            AIMessage(content="I'll analyze it")
        ]
        state = CoreWorkingState(
            messages=messages,
            log_content="error log"
        )
        assert len(state.messages) == 2
    
    def test_core_state_fields(self):
        """Test CoreWorkingState has expected fields."""
        state = CoreWorkingState(
            messages=[HumanMessage(content="test")],
            log_content="log"
        )
        # Check required fields exist
        assert hasattr(state, 'messages')
        assert hasattr(state, 'log_content')
        assert hasattr(state, 'analysis_result')
        assert hasattr(state, 'node_visits')
        assert hasattr(state, 'tool_calls')


class TestInteractiveState:
    """Test the InteractiveState with user interaction features."""
    
    def test_interactive_state_extends_core(self):
        """Test that InteractiveWorkingState has all CoreWorkingState fields."""
        state = InteractiveWorkingState(
            messages=[],
            log_content="test"
        )
        # Should have core fields
        assert hasattr(state, "messages")
        assert hasattr(state, "log_content")
        assert hasattr(state, "analysis_result")
        
        # Should have interactive fields
        assert state.user_input is None
        assert state.pending_questions is None
        assert state.interaction_history == []
    
    def test_interactive_state_with_user_response(self):
        """Test setting user response."""
        state = InteractiveWorkingState(
            messages=[],
            log_content="test",
            user_input="Additional info: running on AWS",
            user_interaction_required=True
        )
        assert state.user_input == "Additional info: running on AWS"
        assert state.user_interaction_required is True


class TestMemoryState:
    """Test the full MemoryState with all features."""
    
    def test_memory_state_initialization(self):
        """Test MemoryWorkingState with full feature set."""
        state = MemoryWorkingState(
            messages=[],
            log_content="test",
            thread_id="thread-123",
            session_id="session-789"
        )
        # Should have all parent fields
        assert hasattr(state, "messages")
        assert hasattr(state, "user_input")
        
        # Should have memory fields
        assert state.thread_id == "thread-123"
        assert state.session_id == "session-789"
        
        # Should have default values
        assert state.memory_matches is None
        assert state.application_context is None
        assert state.save_count == 0
    
    def test_memory_state_with_context(self):
        """Test MemoryWorkingState with retrieved context."""
        state = MemoryWorkingState(
            messages=[],
            log_content="test",
            memory_matches=[
                {"issue": "Database timeout", "solution": "Increase pool size"}
            ],
            application_context={"detail_level": "verbose"}
        )
        assert len(state.memory_matches) == 1
        assert state.memory_matches[0]["issue"] == "Database timeout"
        assert state.application_context["detail_level"] == "verbose"
    
    def test_memory_state_performance_tracking(self):
        """Test performance metric fields."""
        start = datetime.now()
        state = MemoryWorkingState(
            messages=[],
            log_content="test",
            last_saved=start,
            save_count=5
        )
        assert state.last_saved == start
        assert state.save_count == 5


class TestStateFeatures:
    """Test state feature detection."""
    
    def test_get_state_features_core(self):
        """Test feature detection for core state."""
        state = {
            "messages": [],
            "log_content": "test",
            "analysis_result": None
        }
        features = get_state_features(state)
        assert features == set()  # No advanced features
    
    def test_get_state_features_interactive(self):
        """Test feature detection for interactive state."""
        state = {
            "messages": [],
            "log_content": "test",
            "user_interaction_required": True
        }
        features = get_state_features(state)
        assert "interactive" in features
    
    def test_get_state_features_memory(self):
        """Test feature detection for memory state."""
        state = {
            "messages": [],
            "log_content": "test",
            "memory_matches": [{"test": "match"}]
        }
        features = get_state_features(state)
        assert "memory" in features


class TestStateFactory:
    """Test the state factory function."""
    
    def test_create_minimal_state(self):
        """Test creating minimal CoreWorkingState."""
        state_class = create_state_class(None)
        assert state_class == CoreWorkingState
        
        state_class = create_state_class(set())
        assert state_class == CoreWorkingState
    
    def test_create_interactive_state(self):
        """Test creating InteractiveWorkingState."""
        state_class = create_state_class({"interactive"})
        assert state_class == InteractiveWorkingState
    
    def test_create_memory_state(self):
        """Test creating MemoryWorkingState."""
        state_class = create_state_class({"memory"})
        assert state_class == MemoryWorkingState
    
    def test_memory_state_with_multiple_features(self):
        """Test that memory state is created with multiple features."""
        state_class = create_state_class({"memory", "interactive"})
        assert state_class == MemoryWorkingState


if __name__ == "__main__":
    pytest.main([__file__, "-v"])