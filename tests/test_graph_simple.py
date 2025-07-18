"""Simple test to verify graph execution without recursion issues."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the graph
from src.log_analyzer_agent.graph import graph


async def test_simple_execution():
    """Test basic graph execution."""
    
    # Simple test log
    test_log = """
    2024-01-15 10:23:45 ERROR [main] Database connection failed: Connection refused
    2024-01-15 10:23:46 ERROR [main] Application startup failed
    """
    
    print("Testing graph execution...")
    print(f"Graph name: {graph.name}")
    print(f"Graph nodes: {list(graph.nodes.keys())}")
    print()
    
    try:
        # Run with a timeout to prevent infinite loops
        result = await asyncio.wait_for(
            graph.ainvoke({
                "log_content": test_log,
                "environment_details": {"os": "Linux", "version": "Ubuntu 22.04"}
            }),
            timeout=30.0  # 30 second timeout
        )
        
        print("✓ Graph completed successfully!")
        print(f"Messages processed: {len(result.get('messages', []))}")
        print(f"Analysis result present: {'Yes' if result.get('analysis_result') else 'No'}")
        
        # Check message types
        if 'messages' in result:
            message_types = [msg.__class__.__name__ for msg in result['messages']]
            print(f"Message types: {message_types}")
            
            # Check for excessive iterations
            ai_count = message_types.count('AIMessage')
            if ai_count > 10:
                print(f"⚠️  Warning: High AI message count: {ai_count}")
            else:
                print(f"✓ AI message count is reasonable: {ai_count}")
                
    except asyncio.TimeoutError:
        print("✗ Graph execution timed out - possible infinite loop!")
    except Exception as e:
        print(f"✗ Graph execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check for required API keys
    required_keys = ["GEMINI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print(f"Error: Missing required API keys: {', '.join(missing_keys)}")
        print("Please set these in your .env file")
        exit(1)
    
    # Run the test
    asyncio.run(test_simple_execution())