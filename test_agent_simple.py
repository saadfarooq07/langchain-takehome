#!/usr/bin/env python3
"""Simple test to verify the agent works."""

import asyncio
from log_analyzer_agent.graph import graph
from log_analyzer_agent.state import State

async def test_agent():
    """Test the agent with a simple log."""
    test_log = """
    2024-01-15 10:23:45 ERROR [main] Connection refused: Unable to connect to database server at localhost:5432
    2024-01-15 10:23:46 ERROR [main] java.net.ConnectException: Connection refused
    2024-01-15 10:23:47 WARN [main] Retrying connection in 5 seconds...
    """
    
    # Create initial state with only the fields that exist
    initial_state = State(
        log_content=test_log,
        messages=[],
        analysis_result=None,
        needs_user_input=False,
        user_response=""
    )
    
    print("Running agent...")
    try:
        result = await graph.ainvoke(initial_state)
        print("\nAgent completed successfully!")
        print("\nFull result type:", type(result))
        print("\nFull result keys:", result.keys() if hasattr(result, 'keys') else 'Not a dict')
        
        # Check the analysis_result structure
        analysis_result = result.get("analysis_result")
        if analysis_result:
            print("\nAnalysis result type:", type(analysis_result))
            print("Analysis result keys:", analysis_result.keys() if hasattr(analysis_result, 'keys') else 'Not a dict')
            
            # Check if analysis is a string that needs parsing
            if "analysis" in analysis_result and isinstance(analysis_result["analysis"], str):
                import json
                try:
                    parsed = json.loads(analysis_result["analysis"])
                    print("\nParsed analysis:")
                    print(json.dumps(parsed, indent=2))
                except:
                    print("\nRaw analysis:", analysis_result["analysis"])
    except Exception as e:
        print(f"\nError running agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent())