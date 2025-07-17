#!/usr/bin/env python3
"""Simple test to verify the agent works."""

import asyncio
import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from log_analyzer_agent.graph import create_interactive_graph
from log_analyzer_agent.state import State


async def test_simple_analysis():
    """Test basic log analysis."""
    print("Testing Simple Log Analysis...")
    
    # Create the graph
    graph = create_interactive_graph()
    
    # Create test state
    state = State(
        log_content="""
        2023-08-15T14:25:12.345Z ERROR [app.main] Failed to connect to database: Connection refused
        2023-08-15T14:25:12.567Z INFO [app.main] Retrying database connection (attempt 1/5)
        2023-08-15T14:25:13.123Z ERROR [app.main] Retry failed: Connection refused
        2023-08-15T14:25:14.123Z FATAL [app.main] Application startup failed: Database connection error
        """,
        environment_details={
            "database": "PostgreSQL 14.5",
            "environment": "production"
        }
    )
    
    config = {
        "configurable": {
            "model": "gemini:gemini-2.5-flash",
            "max_search_results": 3,
        }
    }
    
    print("Running analysis...")
    result = None
    event_count = 0
    
    try:
        async for event in graph.astream(
            state.__dict__,
            config,
            stream_mode="values"
        ):
            event_count += 1
            print(f"  Event {event_count}: {list(event.keys())}")
            
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]
                break
                
            # Safety check to prevent infinite loops
            if event_count > 20:
                print("✗ Too many events, stopping to prevent infinite loop")
                break
        
        if result:
            print(f"✓ Analysis completed successfully")
            print(f"  - Issues found: {len(result.get('issues', []))}")
            print(f"  - Suggestions: {len(result.get('suggestions', []))}")
            
            # Pretty print the first issue
            if result.get('issues'):
                first_issue = result['issues'][0]
                print(f"  - First issue: {first_issue.get('description', 'No description')}")
        else:
            print("✗ No analysis result produced")
        
        return result is not None
        
    except Exception as e:
        print(f"✗ Analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the test."""
    print("Simple Log Analyzer Test")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check required environment variables
    required_vars = ["GEMINI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"✗ Missing required environment variables: {missing_vars}")
        print("Please set these in your .env file")
        return False
    
    print("✓ All required environment variables are set")
    
    # Run test
    success = await test_simple_analysis()
    
    if success:
        print("\n🎉 Test passed! The agent is working correctly.")
    else:
        print("\n❌ Test failed. Please check the logs above.")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)