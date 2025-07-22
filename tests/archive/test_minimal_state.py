#!/usr/bin/env python3
"""Test that the graph accepts minimal state input."""

import asyncio
from src.log_analyzer_agent.graph import graph
from langchain_core.messages import HumanMessage

async def test_minimal_state():
    """Test the graph with minimal input - just log_content."""
    
    # Test 1: Minimal state with just log_content
    print("Test 1: Minimal state input")
    minimal_state = {
        "log_content": """
        2024-01-15 10:30:45 ERROR [Application] Connection timeout to database
        2024-01-15 10:30:46 ERROR [Application] Failed to connect to primary database
        2024-01-15 10:30:47 WARN [Application] Switching to backup database
        """
    }
    
    try:
        result = await graph.ainvoke(minimal_state)
        print("✅ Success with minimal state!")
        print(f"   - Messages: {len(result.get('messages', []))}")
        print(f"   - Analysis result exists: {bool(result.get('analysis_result'))}")
    except Exception as e:
        print(f"❌ Failed with minimal state: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: State with log_content and messages
    print("\nTest 2: State with log_content and messages")
    state_with_messages = {
        "log_content": "2024-01-15 10:30:45 ERROR Connection timeout",
        "messages": [HumanMessage(content="Analyze this error log")]
    }
    
    try:
        result = await graph.ainvoke(state_with_messages)
        print("✅ Success with messages!")
    except Exception as e:
        print(f"❌ Failed with messages: {e}")
    
    # Test 3: Check what fields are initialized
    print("\nTest 3: Check initialized fields")
    test_state = {"log_content": "test log"}
    
    try:
        result = await graph.ainvoke(test_state)
        print("✅ Initialized fields:")
        for key in ['node_visits', 'tool_calls', 'token_count', 'start_time', 'enabled_features']:
            if key in result:
                print(f"   - {key}: {type(result[key])}")
    except Exception as e:
        print(f"❌ Failed to check fields: {e}")

if __name__ == "__main__":
    asyncio.run(test_minimal_state())