"""Unit tests for state management."""

import pytest
from datetime import datetime
from typing import List

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src.log_analyzer_agent.state import (
    CoreState,
    InteractiveState,
    MemoryState,
    create_state_class,
    get_state_features
)


class TestCoreState:
    """Test the basic CoreState functionality."""
    
    def test_core_state_initialization(self):
        """Test that CoreState can be initialized with minimal fields."""
        state = CoreState(
            messages=[],
            log_content="test log"
        )
        assert state.messages == []
        assert state.log_content == "test log"
        assert hasattr(state, '_message_count')
        assert state.analysis_result is None
        assert state.needs_user_input is False
    
    def test_core_state_with_messages(self):
        """Test CoreState with messages."""
        messages = [
            HumanMessage(content="Analyze this log"),
            AIMessage(content="I'll analyze it")
        ]
        state = CoreState(
            messages=messages,
            log_content="error log"
        )
        assert len(state.messages) == 2
    
    def test_core_state_fields(self):
        """Test CoreState has expected fields."""
        state = CoreState(
            messages=[HumanMessage(content="test")],
            log_content="log"
        )
        # Check required fields exist
        assert hasattr(state, 'messages')
        assert hasattr(state, 'log_content')
        assert hasattr(state, 'analysis_result')
        assert hasattr(state, 'needs_user_input')


class TestInteractiveState:
    """Test the InteractiveState with user interaction features."""
    
    def test_interactive_state_extends_core(self):
        """Test that InteractiveState has all CoreState fields."""
        state = InteractiveState(
            messages=[],
            log_content="test"
        )
        # Should have core fields
        assert hasattr(state, "messages")
        assert hasattr(state, "log_content")
        assert hasattr(state, "analysis_result")
        
        # Should have interactive fields
        assert state.user_response is None
        assert state.pending_request is None
        assert state.additional_context is None
        assert state.follow_up_requests == []
    
    def test_interactive_state_with_user_response(self):
        """Test setting user response."""
        state = InteractiveState(
            messages=[],
            log_content="test",
            user_response="Additional info: running on AWS",
            pending_request={"question": "What cloud provider?"}
        )
        assert state.user_response == "Additional info: running on AWS"
        assert state.pending_request["question"] == "What cloud provider?"


class TestMemoryState:
    """Test the full MemoryState with all features."""
    
    def test_memory_state_initialization(self):
        """Test MemoryState with full feature set."""
        state = MemoryState(
            messages=[],
            log_content="test",
            thread_id="thread-123",
            user_id="user-456",
            session_id="session-789"
        )
        # Should have all parent fields
        assert hasattr(state, "messages")
        assert hasattr(state, "user_response")
        
        # Should have memory fields
        assert state.thread_id == "thread-123"
        assert state.user_id == "user-456"
        assert state.session_id == "session-789"
        
        # Should have default values
        assert state.application_name == "Unknown"
        assert state.environment_type == "Unknown"
        assert state.similar_issues == []
        assert state.memory_search_count == 0
    
    def test_memory_state_with_context(self):
        """Test MemoryState with retrieved context."""
        state = MemoryState(
            messages=[],
            log_content="test",
            similar_issues=[
                {"issue": "Database timeout", "solution": "Increase pool size"}
            ],
            previous_solutions=["Restart service", "Check network"],
            user_preferences={"detail_level": "verbose"}
        )
        assert len(state.similar_issues) == 1
        assert state.similar_issues[0]["issue"] == "Database timeout"
        assert len(state.previous_solutions) == 2
        assert state.user_preferences["detail_level"] == "verbose"
    
    def test_memory_state_performance_tracking(self):
        """Test performance metric fields."""
        start = datetime.now()
        state = MemoryState(
            messages=[],
            log_content="test",
            start_time=start,
            memory_search_count=5
        )
        assert state.start_time == start
        assert state.memory_search_count == 5


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
            "user_response": "test response"
        }
        features = get_state_features(state)
        assert "interactivity" in features
    
    def test_get_state_features_memory(self):
        """Test feature detection for memory state."""
        state = {
            "messages": [],
            "log_content": "test",
            "thread_id": "test-thread"
        }
        features = get_state_features(state)
        assert "memory" in features


class TestStateFactory:
    """Test the state factory function."""
    
    def test_create_minimal_state(self):
        """Test creating minimal CoreState."""
        state_class = create_state_class(None)
        assert state_class == CoreState
        
        state_class = create_state_class(set())
        assert state_class == CoreState
    
    def test_create_interactive_state(self):
        """Test creating InteractiveState."""
        state_class = create_state_class({"interactivity"})
        assert state_class == InteractiveState
    
    def test_create_memory_state(self):
        """Test creating MemoryState."""
        state_class = create_state_class({"memory"})
        assert state_class == MemoryState
    
    def test_memory_state_with_multiple_features(self):
        """Test that memory state is created with multiple features."""
        state_class = create_state_class({"memory", "interactivity"})
        assert state_class == MemoryState


if __name__ == "__main__":
    pytest.main([__file__, "-v"])