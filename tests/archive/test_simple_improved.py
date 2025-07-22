#!/usr/bin/env python3
"""Simple test for the improved graph."""

import asyncio
from langchain_core.messages import HumanMessage

async def test():
    """Test the improved graph."""
    from src.log_analyzer_agent.graph import graph
    
    # Test log with various issues
    test_log = """
    2024-01-15 10:23:45 ERROR [NameNode] java.lang.OutOfMemoryError: Java heap space
    2024-01-15 10:23:46 ERROR [DataNode] Failed to connect to NameNode
    2024-01-15 10:23:47 WARN [HDFS] Under-replicated block blk_1234567890. Target Replicas is 3. Current Replica(s) is 1
    2024-01-15 10:23:48 ERROR [Security] Failed authentication for user admin from 192.168.1.100
    2024-01-15 10:23:50 ERROR [App] HTTP/1.1 500 Internal Server Error
    2024-01-15 10:23:51 ERROR [App] java.lang.NullPointerException at UserService.java:45
    """
    
    # Create initial state
    initial_state = {
        "messages": [HumanMessage(content=f"Analyze this log:\n{test_log}")],
        "log_content": test_log,
        "log_metadata": {"source": "test"},
        "analysis_result": None,
        "validation_status": None,
        "node_visits": {},
        "tool_calls": [],
        "token_count": 0,
        "start_time": 0,
        "enabled_features": []
    }
    
    print("Running improved graph analysis...")
    result = await graph.ainvoke(initial_state)
    
    if result.get("analysis_result"):
        print("\n✅ Analysis successful!")
        analysis = result["analysis_result"]
        print(f"Summary: {analysis.get('summary', 'N/A')}")
        print(f"Issues: {len(analysis.get('issues', []))}")
        print(f"Log type: {analysis.get('log_type', 'general')}")
    else:
        print("\n❌ No analysis result")
        print("Messages:", [m.content[:100] for m in result.get("messages", [])])

if __name__ == "__main__":
    asyncio.run(test())