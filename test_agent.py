#!/usr/bin/env python3
"""Test script to verify the log analyzer agent tool calling functionality."""

import asyncio
from src.log_analyzer_agent.graph import create_minimal_graph

async def test_agent():
    """Test the agent with a sample log that should trigger tool calls."""
    
    # Create a minimal graph
    graph = create_minimal_graph()
    
    # Sample log content that should trigger analysis
    test_log = """
2024-01-22 10:15:32 ERROR [main] Application failed to start
2024-01-22 10:15:32 ERROR [main] java.lang.OutOfMemoryError: Java heap space
2024-01-22 10:15:33 ERROR [main] at com.example.Application.main(Application.java:42)
2024-01-22 10:15:33 ERROR [main] Caused by: Insufficient memory allocation
2024-01-22 10:15:34 WARN  [gc] GC overhead limit exceeded
2024-01-22 10:15:35 ERROR [main] Application terminated with exit code 1
"""
    
    # Run the agent
    print("Running log analyzer agent...")
    print("=" * 50)
    
    try:
        result = await graph.ainvoke({
            "log_content": test_log,
            "messages": []
        })
        
        print("Agent completed successfully!")
        print("=" * 50)
        
        # Check messages for tool calls
        messages = result.get("messages", [])
        print(f"Total messages: {len(messages)}")
        
        for i, msg in enumerate(messages):
            print(f"\nMessage {i + 1}:")
            print(f"  Type: {type(msg).__name__}")
            if hasattr(msg, "content") and msg.content:
                print(f"  Content: {msg.content[:200]}...")
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                print(f"  Tool calls: {len(msg.tool_calls)}")
                for tc in msg.tool_calls:
                    print(f"    - {tc.get('name', 'unknown')}")
        
        # Check final analysis result
        if "analysis_result" in result and result["analysis_result"]:
            print("\nFinal Analysis Result:")
            print(f"  Issues found: {len(result['analysis_result'].get('issues', []))}")
            print(f"  Has suggestions: {'suggestions' in result['analysis_result']}")
            print(f"  Has documentation references: {'documentation_references' in result['analysis_result']}")
        
    except Exception as e:
        print(f"Error running agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())