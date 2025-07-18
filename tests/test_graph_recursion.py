"""Test script to verify the graph has no recursion issues."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the graph
from src.log_analyzer_agent.graph import create_minimal_graph, create_interactive_graph, create_full_graph


async def test_graph_execution():
    """Test different graph configurations to ensure no infinite loops."""
    
    # Sample log content that might trigger multiple iterations
    test_log = """
    2024-01-15 10:23:45 ERROR [main] Database connection failed: Connection refused
    2024-01-15 10:23:46 ERROR [main] Retry attempt 1 failed
    2024-01-15 10:23:47 ERROR [main] Retry attempt 2 failed
    2024-01-15 10:23:48 FATAL [main] Maximum retry attempts exceeded
    2024-01-15 10:23:49 ERROR [worker-1] Worker thread terminated unexpectedly
    2024-01-15 10:23:50 ERROR [worker-2] Worker thread terminated unexpectedly
    """
    
    print("Testing graph configurations for recursion issues...\n")
    
    # Test 1: Minimal graph
    print("1. Testing minimal graph...")
    try:
        graph = create_minimal_graph()
        result = await graph.ainvoke({
            "log_content": test_log,
            "environment_details": {"os": "Linux", "version": "Ubuntu 22.04"}
        })
        print("✓ Minimal graph completed successfully")
        print(f"  - Messages processed: {len(result.get('messages', []))}")
        print(f"  - Analysis result: {'Present' if result.get('analysis_result') else 'None'}\n")
    except Exception as e:
        print(f"✗ Minimal graph failed: {e}\n")
    
    # Test 2: Interactive graph
    print("2. Testing interactive graph...")
    try:
        graph = create_interactive_graph()
        result = await graph.ainvoke({
            "log_content": test_log,
            "environment_details": {"os": "Linux", "version": "Ubuntu 22.04"}
        })
        print("✓ Interactive graph completed successfully")
        print(f"  - Messages processed: {len(result.get('messages', []))}")
        print(f"  - Analysis result: {'Present' if result.get('analysis_result') else 'None'}\n")
    except Exception as e:
        print(f"✗ Interactive graph failed: {e}\n")
    
    # Test 3: Full graph (without actual DB)
    print("3. Testing full graph structure...")
    try:
        graph = create_full_graph()
        # Note: This won't have actual memory features without DB setup
        result = await graph.ainvoke({
            "log_content": test_log,
            "environment_details": {"os": "Linux", "version": "Ubuntu 22.04"}
        })
        print("✓ Full graph completed successfully")
        print(f"  - Messages processed: {len(result.get('messages', []))}")
        print(f"  - Analysis result: {'Present' if result.get('analysis_result') else 'None'}\n")
    except Exception as e:
        print(f"✗ Full graph failed: {e}\n")
    
    # Test 4: Edge case - empty log
    print("4. Testing edge case: empty log...")
    try:
        graph = create_minimal_graph()
        result = await graph.ainvoke({
            "log_content": "",
            "environment_details": {}
        })
        print("✓ Empty log handled successfully")
        print(f"  - Error handling: {'Proper' if 'error' in str(result.get('analysis_result', {})) else 'Missing'}\n")
    except Exception as e:
        print(f"✗ Empty log test failed: {e}\n")
    
    # Test 5: Edge case - very large log (simulated)
    print("5. Testing edge case: large log...")
    large_log = "\n".join([f"2024-01-15 10:23:{i:02d} INFO [app] Processing request {i}" for i in range(60)])
    try:
        graph = create_minimal_graph()
        result = await graph.ainvoke({
            "log_content": large_log,
            "environment_details": {"os": "Linux", "version": "Ubuntu 22.04"}
        })
        print("✓ Large log handled successfully")
        print(f"  - Messages processed: {len(result.get('messages', []))}")
        print(f"  - Completed without timeout\n")
    except Exception as e:
        print(f"✗ Large log test failed: {e}\n")
    
    print("Testing complete!")
    
    # Analyze message flow for recursion patterns
    print("\nAnalyzing message flow patterns:")
    if 'result' in locals() and 'messages' in result:
        ai_messages = sum(1 for msg in result['messages'] if msg.__class__.__name__ == 'AIMessage')
        tool_messages = sum(1 for msg in result['messages'] if msg.__class__.__name__ == 'ToolMessage')
        human_messages = sum(1 for msg in result['messages'] if msg.__class__.__name__ == 'HumanMessage')
        
        print(f"  - AI Messages: {ai_messages}")
        print(f"  - Tool Messages: {tool_messages}")
        print(f"  - Human Messages: {human_messages}")
        print(f"  - Total Messages: {len(result['messages'])}")
        
        # Check for excessive iterations
        if ai_messages > 10:
            print("  ⚠️  Warning: High number of AI messages detected")
        if len(result['messages']) > 30:
            print("  ⚠️  Warning: High total message count detected")


if __name__ == "__main__":
    # Check for required API keys
    required_keys = ["GEMINI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print(f"Error: Missing required API keys: {', '.join(missing_keys)}")
        print("Please set these in your .env file")
        exit(1)
    
    # Run the tests
    asyncio.run(test_graph_execution())