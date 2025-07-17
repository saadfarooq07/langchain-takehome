"""Main entry point for the Log Analyzer Agent.

This script demonstrates how to use the Log Analyzer Agent 
to analyze log files and get actionable insights.
"""

import os
import sys
from typing import Dict, Any, Optional
from dotenv import load_dotenv
# Removed unused imports
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

# Import our log analyzer agent
from src.log_analyzer_agent import graph, InputState, Configuration
from src.log_analyzer_agent.validation import APIKeyValidator

# Load environment variables
load_dotenv()

# Validate and set API keys from environment variables
def validate_and_set_api_keys():
    """Validate API keys and set them in environment."""
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    groq_key = os.getenv("GROQ_API_KEY", "")
    tavily_key = os.getenv("TAVILY_API_KEY", "")
    
    # Validate keys
    errors = []
    
    is_valid, error = APIKeyValidator.validate_gemini_api_key(gemini_key)
    if not is_valid:
        errors.append(f"GEMINI_API_KEY: {error}")
    
    is_valid, error = APIKeyValidator.validate_groq_api_key(groq_key)
    if not is_valid:
        errors.append(f"GROQ_API_KEY: {error}")
    
    is_valid, error = APIKeyValidator.validate_tavily_api_key(tavily_key)
    if not is_valid:
        errors.append(f"TAVILY_API_KEY: {error}")
    
    if errors:
        print("API Key Validation Errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check your .env file and ensure all API keys are correctly set.")
        sys.exit(1)
    
    # Set validated keys
    os.environ["GEMINI_API_KEY"] = gemini_key
    os.environ["GROQ_API_KEY"] = groq_key
    os.environ["TAVILY_API_KEY"] = tavily_key

# Validate API keys on module load
validate_and_set_api_keys()


def setup_memory():
    """Set up memory saver for the graph."""
    return MemorySaver()


def process_log(log_content: str, environment_details: Optional[Dict[str, Any]] = None):
    """Process a log file and get analysis results.
    
    Args:
        log_content: The content of the log file to analyze
        environment_details: Optional details about the software and runtime environment
        
    Returns:
        Analysis results and any follow-up requests
    """
    # Set up memory for the graph
    memory = setup_memory()
    
    # Compile the graph with checkpointer
    configured_graph = graph.with_checkpointer(memory)
    
    # Prepare the input state
    input_state = {
        "log_content": log_content,
    }
    
    # Add environment details if provided
    if environment_details:
        input_state["environment_details"] = environment_details
    
    # Configuration for the graph
    config = {
        "configurable": {
            "model": "gemini:2.5-flash",
            "max_search_results": 3,
        }
    }
    
    # Stream the events from the graph
    events = configured_graph.stream(
        input_state,
        config,
        stream_mode="values",
    )
    
    # Process the events
    result = None
    for event in events:
        if "analysis_result" in event and event["analysis_result"]:
            result = event["analysis_result"]
        if "messages" in event:
            # Print the latest message for demonstration
            latest_message = event["messages"][-1]
            print(f"{latest_message.type}: {latest_message.content[:100]}...")
    
    return result


def main():
    """Main function to run the log analyzer."""
    # Example log file
    example_log = """
    2023-08-15T14:25:12.345Z ERROR [app.main] Failed to connect to database: Connection refused
    2023-08-15T14:25:12.567Z INFO [app.main] Retrying database connection (attempt 1/5)
    2023-08-15T14:25:13.123Z ERROR [app.main] Retry failed: Connection refused
    2023-08-15T14:25:13.234Z INFO [app.main] Retrying database connection (attempt 2/5)
    2023-08-15T14:25:13.789Z ERROR [app.main] Retry failed: Connection refused
    2023-08-15T14:25:13.890Z WARN [app.config] Using default configuration due to missing config file
    2023-08-15T14:25:14.012Z ERROR [app.main] Max retries exceeded. Could not connect to database
    2023-08-15T14:25:14.123Z FATAL [app.main] Application startup failed: Database connection error
    """
    
    # Example environment details
    environment_details = {
        "software": "MyApp v1.2.3",
        "database": "PostgreSQL 14.5",
        "runtime": "Python 3.9 on Ubuntu 22.04",
        "deployment": "Docker container in AWS ECS"
    }
    
    # Process the log file
    result = process_log(example_log, environment_details)
    
    # Print the result
    if result:
        print("\nAnalysis Result:")
        print("=" * 50)
        for issue in result.get("issues", []):
            print(f"Issue: {issue['description']}")
            print(f"Severity: {issue['severity']}")
            print("-" * 30)
        
        print("\nSuggestions:")
        print("=" * 50)
        for suggestion in result.get("suggestions", []):
            print(f"- {suggestion}")
        
        print("\nDocumentation References:")
        print("=" * 50)
        for ref in result.get("documentation_references", []):
            print(f"- {ref['title']}: {ref['url']}")
    else:
        print("No analysis result was produced.")


if __name__ == "__main__":
    main()