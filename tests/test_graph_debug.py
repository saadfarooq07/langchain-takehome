"""Debug test to trace graph execution."""

import asyncio
import os
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage

# Load environment variables
load_dotenv()

# Import the graph
from src.log_analyzer_agent.graph import graph


class DebugGraph:
    """Wrapper to add debugging to graph execution."""
    
    def __init__(self, original_graph):
        self.graph = original_graph
        self.execution_count = {}
        
    async def ainvoke(self, input_data):
        """Execute graph with debugging."""
        print("Starting graph execution...")
        print(f"Input: {input_data}")
        
        # Track node executions
        node_executions = []
        
        # Patch the graph to add logging
        original_nodes = {}
        for node_name, node_func in self.graph.nodes.items():
            if node_name not in ['__start__', '__end__']:
                original_nodes[node_name] = node_func
                
                async def logged_node(state, *, config=None, _name=node_name, _original=node_func):
                    print(f"\n>>> Executing node: {_name}")
                    print(f"    Messages so far: {len(getattr(state, 'messages', []))}")
                    
                    # Count executions
                    self.execution_count[_name] = self.execution_count.get(_name, 0) + 1
                    print(f"    Execution count for {_name}: {self.execution_count[_name]}")
                    
                    if self.execution_count[_name] > 5:
                        print(f"    ⚠️  WARNING: Node {_name} executed {self.execution_count[_name]} times!")
                    
                    # Execute original node
                    result = await _original(state, config=config)
                    
                    print(f"<<< Node {_name} completed")
                    return result
                
                self.graph.nodes[node_name] = logged_node
        
        try:
            # Run with timeout
            result = await asyncio.wait_for(
                self.graph.ainvoke(input_data),
                timeout=60.0
            )
            
            print("\n✓ Graph execution completed!")
            return result
            
        except asyncio.TimeoutError:
            print("\n✗ Graph execution timed out!")
            print(f"Execution counts: {self.execution_count}")
            raise
        finally:
            # Restore original nodes
            for name, func in original_nodes.items():
                self.graph.nodes[name] = func


async def test_debug_execution():
    """Test with detailed debugging."""
    
    # Simple test log
    test_log = """
    2024-01-15 10:23:45 ERROR [main] Database connection failed
    """
    
    debug_graph = DebugGraph(graph)
    
    try:
        result = await debug_graph.ainvoke({
            "log_content": test_log,
            "environment_details": {}
        })
        
        print(f"\nFinal execution counts: {debug_graph.execution_count}")
        
    except Exception as e:
        print(f"\nExecution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check for required API keys
    required_keys = ["GEMINI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print(f"Error: Missing required API keys: {', '.join(missing_keys)}")
        exit(1)
    
    # Run the test
    asyncio.run(test_debug_execution())