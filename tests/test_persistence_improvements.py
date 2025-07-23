"""Tests for persistence improvements and deterministic behavior."""

import pytest
import asyncio
import time
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.log_analyzer_agent.persistence_utils import (
    generate_deterministic_id,
    generate_analysis_id,
    get_workflow_timestamp,
    idempotent_operation,
    idempotent,
    save_json_to_file,
    read_json_from_file,
    IdempotencyCache,
    log_debug, log_info
)
from src.log_analyzer_agent.persistence_fixes import (
    DeterministicCache,
    capture_decision_time,
    use_captured_time,
    deterministic_control_flow,
    immutable_update,
    immutable_append,
    immutable_increment
)
from src.log_analyzer_agent.graph import initialize_state, cache_analysis


class TestDeterministicOperations:
    """Test deterministic ID and timestamp generation."""
    
    def test_deterministic_id_generation(self):
        """Test that IDs are deterministic based on content."""
        content = "test log content"
        
        # Same content should produce same ID
        id1 = generate_deterministic_id(content, "test")
        id2 = generate_deterministic_id(content, "test")
        assert id1 == id2
        
        # Different content should produce different ID
        id3 = generate_deterministic_id("different content", "test")
        assert id1 != id3
        
        # Different prefix should produce different ID
        id4 = generate_deterministic_id(content, "other")
        assert id1 != id4
    
    def test_analysis_id_generation(self):
        """Test analysis ID generation."""
        log_content = "error in module X"
        
        # With fixed timestamp
        id1 = generate_analysis_id(log_content, timestamp=1000.0)
        id2 = generate_analysis_id(log_content, timestamp=1000.0)
        assert id1 == id2
        
        # Different timestamps should produce different IDs
        id3 = generate_analysis_id(log_content, timestamp=2000.0)
        assert id1 != id3
    
    @pytest.mark.asyncio
    async def test_workflow_timestamp_persistence(self):
        """Test that workflow timestamp is captured once and persisted."""
        state = {}
        
        # First call should set the timestamp
        ts1 = await get_workflow_timestamp(state)
        assert "_workflow_timestamp" in state
        assert state["_workflow_timestamp"] == ts1
        
        # Subsequent calls should return the same timestamp
        await asyncio.sleep(0.1)  # Ensure time passes
        ts2 = await get_workflow_timestamp(state)
        assert ts1 == ts2
        assert state["_workflow_timestamp"] == ts1


class TestIdempotency:
    """Test idempotency support."""
    
    @pytest.mark.asyncio
    async def test_idempotent_operation(self):
        """Test idempotent operation execution."""
        call_count = 0
        
        def test_operation(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call should execute
        result1 = await idempotent_operation("test_op", test_operation, 5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = await idempotent_operation("test_op", test_operation, 5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        
        # Different arguments should execute again
        result3 = await idempotent_operation("test_op", test_operation, 10)
        assert result3 == 20
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_idempotent_decorator(self):
        """Test idempotent decorator."""
        call_count = 0
        
        @idempotent("multiply")
        async def multiply(x: int, y: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * y
        
        # First call
        result1 = await multiply(3, 4)
        assert result1 == 12
        assert call_count == 1
        
        # Cached call
        result2 = await multiply(3, 4)
        assert result2 == 12
        assert call_count == 1
        
        # Different args
        result3 = await multiply(5, 6)
        assert result3 == 30
        assert call_count == 2
    
    def test_idempotency_cache_expiry(self):
        """Test idempotency cache TTL."""
        cache = IdempotencyCache(ttl_seconds=1)
        
        # Add entry
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiry
        time.sleep(1.1)
        assert cache.get("key1") is None


class TestDeterministicCache:
    """Test deterministic cache implementation."""
    
    @pytest.mark.asyncio
    async def test_cache_with_workflow_timestamp(self):
        """Test cache uses workflow timestamp for expiry."""
        cache = DeterministicCache(ttl_seconds=100)
        state = {"_workflow_timestamp": 1000.0}
        
        # Set value
        await cache.set("key1", "value1", state)
        
        # Get value within TTL
        result = await cache.get("key1", state)
        assert result == "value1"
        
        # Simulate time passing in workflow
        state["_workflow_timestamp"] = 1050.0
        result = await cache.get("key1", state)
        assert result == "value1"  # Still within TTL
        
        # Simulate expiry
        state["_workflow_timestamp"] = 1101.0
        result = await cache.get("key1", state)
        assert result is None  # Expired


class TestStateImmutability:
    """Test state immutability helpers."""
    
    def test_immutable_update(self):
        """Test immutable state updates."""
        original = {"a": 1, "b": 2}
        
        # Update should create new dict
        updated = immutable_update(original, {"b": 3, "c": 4})
        
        # Original should be unchanged
        assert original == {"a": 1, "b": 2}
        
        # Updated should have new values
        assert updated == {"a": 1, "b": 3, "c": 4}
        
        # Should be different objects
        assert original is not updated
    
    def test_immutable_append(self):
        """Test immutable list append."""
        original = {"items": [1, 2, 3]}
        
        # Append should create new dict with new list
        updated = immutable_append(original, "items", 4)
        
        # Original unchanged
        assert original == {"items": [1, 2, 3]}
        
        # Updated has new item
        assert updated == {"items": [1, 2, 3, 4]}
        
        # Lists should be different objects
        assert original["items"] is not updated["items"]
    
    def test_immutable_increment(self):
        """Test immutable counter increment."""
        original = {"count": 5}
        
        # Increment
        updated = immutable_increment(original, "count", 3)
        
        assert original == {"count": 5}
        assert updated == {"count": 8}
        
        # Test with missing key
        original2 = {}
        updated2 = immutable_increment(original2, "count")
        assert original2 == {}
        assert updated2 == {"count": 1}


class TestDecisionTimeCapture:
    """Test decision time capture for deterministic control flow."""
    
    @pytest.mark.asyncio
    async def test_capture_decision_time(self):
        """Test decision time is captured once."""
        state = {}
        
        @capture_decision_time("cache_check")
        async def check_cache(state):
            return state.get("decision_times", {}).get("cache_check")
        
        # First call captures time
        time1 = await check_cache(state)
        assert "decision_times" in state
        assert "cache_check" in state["decision_times"]
        assert time1 is not None
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Second call uses captured time
        time2 = await check_cache(state)
        assert time1 == time2  # Same time
    
    def test_use_captured_time(self):
        """Test retrieving captured decision times."""
        state = {
            "decision_times": {
                "cache_check": 1000.0,
                "retry_check": 2000.0
            }
        }
        
        # Get existing time
        get_cache_time = use_captured_time("cache_check")
        assert get_cache_time(state) == 1000.0
        
        # Get with default
        get_missing_time = use_captured_time("missing", default=3000.0)
        assert get_missing_time(state) == 3000.0
        
        # Get without default falls back to current time
        get_current = use_captured_time("missing")
        current_time = get_current(state)
        assert current_time > 1000.0  # Should be current time


class TestFileOperations:
    """Test task-wrapped file operations."""
    
    @pytest.mark.asyncio
    async def test_save_and_read_json(self, tmp_path):
        """Test JSON file operations are task-wrapped."""
        test_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 42}
        
        # Save
        await save_json_to_file(test_file, test_data)
        
        # Verify file exists
        assert test_file.exists()
        
        # Read back
        loaded_data = await read_json_from_file(test_file)
        assert loaded_data == test_data
        
        # Verify JSON is properly formatted
        with open(test_file) as f:
            content = f.read()
            assert json.loads(content) == test_data


class TestWorkflowDeterminism:
    """Test that workflows produce deterministic results."""
    
    @pytest.mark.asyncio
    async def test_initialize_state_determinism(self):
        """Test state initialization is deterministic."""
        # Initialize state twice with same input
        input_state = {"log_content": "test log"}
        
        state1 = await initialize_state(input_state.copy())
        state2 = await initialize_state(input_state.copy())
        
        # Both should have same structure
        assert set(state1.keys()) == set(state2.keys())
        
        # Non-time fields should be identical
        for key in ["messages", "node_visits", "tool_calls", "token_count", 
                    "log_metadata", "enabled_features"]:
            assert state1[key] == state2[key]
    
    @pytest.mark.asyncio
    async def test_cache_analysis_determinism(self):
        """Test cached analysis is deterministic."""
        # Mock the analysis function
        async def mock_analysis(state):
            return {
                "analysis_result": {
                    "issues": ["test issue"],
                    "suggestions": ["test suggestion"]
                }
            }
        
        # Wrap with cache decorator
        cached_analysis = cache_analysis(mock_analysis)
        
        # First call
        state1 = {"log_content": "error log"}
        result1 = await cached_analysis(state1)
        
        # Second call with same content
        state2 = {"log_content": "error log"}
        result2 = await cached_analysis(state2)
        
        # Results should be identical (from cache)
        assert result1["analysis_result"] == result2["analysis_result"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])