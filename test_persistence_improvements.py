#!/usr/bin/env python3
"""Test script to verify persistence and reliability improvements."""

import asyncio
import time
from src.log_analyzer_agent.persistence_utils import (
    log_debug, log_info, log_warning, log_error,
    save_to_file, save_json_to_file, read_from_file, read_json_from_file,
    generate_deterministic_id, generate_analysis_id, generate_memory_id,
    get_workflow_timestamp,
    idempotent, idempotent_operation,
    cleanup_idempotency_cache
)


async def test_logging():
    """Test task-wrapped logging functions."""
    print("\n=== Testing Task-Wrapped Logging ===")
    
    await log_debug("This is a debug message")
    await log_info("This is an info message")
    await log_warning("This is a warning message")
    await log_error("This is an error message")
    
    print("✓ Logging functions work correctly")


async def test_file_operations():
    """Test task-wrapped file operations."""
    print("\n=== Testing Task-Wrapped File Operations ===")
    
    # Test text file operations
    test_file = "/tmp/test_persistence.txt"
    test_content = "Hello, persistence!"
    
    await save_to_file(test_file, test_content)
    read_content = await read_from_file(test_file)
    
    assert read_content == test_content, f"Expected '{test_content}', got '{read_content}'"
    print("✓ Text file operations work correctly")
    
    # Test JSON file operations
    test_json_file = "/tmp/test_persistence.json"
    test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
    
    await save_json_to_file(test_json_file, test_data)
    read_data = await read_json_from_file(test_json_file)
    
    assert read_data == test_data, f"Expected {test_data}, got {read_data}"
    print("✓ JSON file operations work correctly")


def test_deterministic_ids():
    """Test deterministic ID generation."""
    print("\n=== Testing Deterministic ID Generation ===")
    
    # Test basic deterministic ID
    content = "test content"
    id1 = generate_deterministic_id(content, "test")
    id2 = generate_deterministic_id(content, "test")
    
    assert id1 == id2, f"IDs should be identical: {id1} != {id2}"
    print(f"✓ Deterministic ID: {id1}")
    
    # Test analysis ID
    log_content = "Error: Connection timeout"
    analysis_id1 = generate_analysis_id(log_content, 1234567890)
    analysis_id2 = generate_analysis_id(log_content, 1234567890)
    
    assert analysis_id1 == analysis_id2, f"Analysis IDs should be identical: {analysis_id1} != {analysis_id2}"
    print(f"✓ Analysis ID: {analysis_id1}")
    
    # Test memory ID
    user_id = "user123"
    memory_id1 = generate_memory_id(user_id, content, "test_op")
    memory_id2 = generate_memory_id(user_id, content, "test_op")
    
    assert memory_id1 == memory_id2, f"Memory IDs should be identical: {memory_id1} != {memory_id2}"
    print(f"✓ Memory ID: {memory_id1}")


async def test_workflow_timestamp():
    """Test workflow timestamp consistency."""
    print("\n=== Testing Workflow Timestamp ===")
    
    state = {}
    
    # First call should create timestamp
    ts1 = await get_workflow_timestamp(state)
    await asyncio.sleep(0.1)  # Small delay
    
    # Second call should return same timestamp
    ts2 = await get_workflow_timestamp(state)
    
    assert ts1 == ts2, f"Timestamps should be identical: {ts1} != {ts2}"
    assert "_workflow_timestamp" in state, "Timestamp should be stored in state"
    print(f"✓ Consistent timestamp: {ts1}")


async def test_idempotency():
    """Test idempotency utilities."""
    print("\n=== Testing Idempotency ===")
    
    # Counter to track function calls
    call_count = 0
    
    async def expensive_operation(x: int, y: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)  # Simulate expensive operation
        return x + y
    
    # First call should execute
    result1 = await idempotent_operation("add", expensive_operation, 5, 3)
    assert result1 == 8, f"Expected 8, got {result1}"
    assert call_count == 1, f"Expected 1 call, got {call_count}"
    
    # Second call should use cache
    result2 = await idempotent_operation("add", expensive_operation, 5, 3)
    assert result2 == 8, f"Expected 8, got {result2}"
    assert call_count == 1, f"Expected 1 call (cached), got {call_count}"
    
    print("✓ Idempotency caching works correctly")
    
    # Test decorator
    @idempotent("multiply")
    async def multiply(x: int, y: int) -> int:
        return x * y
    
    result3 = await multiply(4, 5)
    assert result3 == 20, f"Expected 20, got {result3}"
    
    print("✓ Idempotent decorator works correctly")


async def test_api_simulation():
    """Simulate idempotent API calls."""
    print("\n=== Testing API Call Idempotency ===")
    
    api_call_count = 0
    
    @idempotent("api_search")
    async def search_documentation(query: str) -> dict:
        nonlocal api_call_count
        api_call_count += 1
        # Simulate API call
        await asyncio.sleep(0.1)
        return {
            "results": [
                {"title": f"Result for {query}", "url": "https://example.com"}
            ],
            "call_count": api_call_count
        }
    
    # First call
    result1 = await search_documentation("error handling")
    assert api_call_count == 1, f"Expected 1 API call, got {api_call_count}"
    
    # Second call with same query should be cached
    result2 = await search_documentation("error handling")
    assert api_call_count == 1, f"Expected 1 API call (cached), got {api_call_count}"
    assert result1 == result2, "Results should be identical"
    
    # Different query should make new call
    result3 = await search_documentation("performance tuning")
    assert api_call_count == 2, f"Expected 2 API calls, got {api_call_count}"
    
    print("✓ API call idempotency works correctly")


async def main():
    """Run all tests."""
    print("Testing Persistence and Reliability Improvements")
    print("=" * 50)
    
    try:
        await test_logging()
        await test_file_operations()
        test_deterministic_ids()
        await test_workflow_timestamp()
        await test_idempotency()
        await test_api_simulation()
        
        # Cleanup
        await cleanup_idempotency_cache()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)