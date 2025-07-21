#!/usr/bin/env python3
"""Test script for the improved log analyzer implementation."""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Enable improved implementation
os.environ["USE_IMPROVED_LOG_ANALYZER"] = "true"


async def test_improved_graph():
    """Test the improved graph implementation."""
    print("Testing improved log analyzer implementation...\n")
    
    # Sample log content
    sample_log = """
    2024-01-15 10:23:45 ERROR [DataNode] java.lang.OutOfMemoryError: Java heap space
    2024-01-15 10:23:46 ERROR [NameNode] Failed to process block report from DataNode
    2024-01-15 10:23:47 WARN [HDFS] Under-replicated block blk_1234567890. Target Replicas is 3. Current Replica(s) is 1
    2024-01-15 10:23:48 ERROR [Security] Failed authentication for user admin from 192.168.1.100
    2024-01-15 10:23:49 ERROR [Security] Failed authentication for user admin from 192.168.1.100
    2024-01-15 10:23:50 ERROR [Security] Failed authentication for user admin from 192.168.1.100
    2024-01-15 10:23:51 ERROR [Application] HTTP/1.1" 500 Internal Server Error
    2024-01-15 10:23:52 ERROR [Application] java.lang.NullPointerException at UserService.getUser(UserService.java:45)
    """
    
    try:
        # Import and test the graph
        from src.log_analyzer_agent.graph import graph
        
        print("✅ Graph imported successfully")
        print(f"   Graph type: {type(graph)}")
        
        # Create initial state
        from langchain_core.messages import HumanMessage
        
        initial_state = {
            "messages": [HumanMessage(content=f"Please analyze this log:\n{sample_log}")],
            "log_content": sample_log,
            "log_metadata": {"source": "test"},
            "analysis_result": None,
            "validation_status": None,
            "node_visits": {},
            "tool_calls": [],
            "token_count": 0,
            "start_time": 0,
            "enabled_features": ["streaming", "specialized", "circuit_breaker", "rate_limiting"]
        }
        
        print("\n🔧 Running analysis...")
        
        # Run the graph
        result = await graph.ainvoke(initial_state)
        
        print("\n✅ Analysis completed!")
        
        # Display results
        if "analysis_result" in result and result["analysis_result"]:
            analysis = result["analysis_result"]
            print(f"\n📊 Summary: {analysis.get('summary', 'No summary')}")
            print(f"📋 Issues found: {len(analysis.get('issues', []))}")
            print(f"💡 Recommendations: {len(analysis.get('recommendations', []))}")
            
            # Check if specialized analyzer was used
            if "log_type" in analysis:
                print(f"🎯 Specialized analyzer used: {analysis['log_type']}")
        else:
            print("\n❌ No analysis result returned")
            print(f"   State keys: {list(result.keys())}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_improved_graph())