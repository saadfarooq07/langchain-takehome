"""Updated main entry point with support for lightweight state."""

import asyncio
import os
import sys
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Import graph factory and state adapter
from src.log_analyzer_agent.graph_factory import GraphFactory
from src.log_analyzer_agent.state_compat import StateAdapter
from src.log_analyzer_agent.validation import APIKeyValidator

# Load environment variables
load_dotenv()


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


async def process_log_minimal(
    log_content: str,
    environment_details: Optional[Dict[str, Any]] = None
):
    """Process a log file with minimal overhead.
    
    Args:
        log_content: The content of the log file to analyze
        environment_details: Optional environment context
        
    Returns:
        Analysis results
    """
    # Create minimal graph
    graph = GraphFactory.create_graph(mode="minimal")
    
    # Create minimal state
    state = {
        "log_content": log_content,
        "environment_details": environment_details or {}
    }
    
    # Configuration
    config = {
        "configurable": {
            "model": "gemini:gemini-1.5-flash",
            "max_search_results": 3,
        }
    }
    
    # Process
    result = None
    async for event in graph.astream(
        state,
        config,
        stream_mode="values"
    ):
        if "analysis_result" in event and event["analysis_result"]:
            result = event["analysis_result"]
    
    return result


async def process_log_interactive(
    log_content: str,
    environment_details: Optional[Dict[str, Any]] = None
):
    """Process a log file with interactive support.
    
    Args:
        log_content: The content of the log file to analyze
        environment_details: Optional environment context
        
    Returns:
        Analysis results
    """
    # Create interactive graph
    graph = GraphFactory.create_graph(mode="interactive")
    
    # Create state
    input_state = {
        "log_content": log_content,
        "environment_details": environment_details or {}
    }
    
    # Configuration
    config = {
        "configurable": {
            "model": "gemini:gemini-1.5-flash",
            "max_search_results": 3,
        }
    }
    
    # Process
    result = None
    needs_input = False
    
    async for event in graph.astream(
        input_state,
        config,
        stream_mode="values"
    ):
        if "analysis_result" in event and event["analysis_result"]:
            result = event["analysis_result"]
        if "needs_user_input" in event:
            needs_input = event["needs_user_input"]
        if "pending_request" in event and event["pending_request"]:
            print(f"\nAdditional information needed:")
            print(f"Question: {event['pending_request']['question']}")
            print(f"Reason: {event['pending_request']['reason']}")
    
    return result, needs_input


async def process_log_with_memory(
    log_content: str,
    user_id: str = "demo_user",
    application_name: str = "demo_app",
    environment_details: Optional[Dict[str, Any]] = None
):
    """Process a log file with full memory support.
    
    Args:
        log_content: The content of the log file to analyze
        user_id: User identifier for memory context
        application_name: Application name for memory context
        environment_details: Optional environment context
        
    Returns:
        Analysis results
    """
    # Create graph with memory
    graph, store, checkpointer = await GraphFactory.create_graph_async(mode="memory")
    
    try:
        # Create state with memory fields
        state = {
            "log_content": log_content,
            "environment_details": environment_details or {},
            "user_id": user_id,
            "application_name": application_name,
            "start_time": time.time()
        }
        
        # Configuration
        config = {
            "configurable": {
                "user_id": user_id,
                "thread_id": state.get("thread_id", ""),
                "model": "gemini:gemini-1.5-flash",
                "max_search_results": 3,
            }
        }
        
        # Process
        result = None
        async for event in graph.astream(
            state,
            config,
            stream_mode="values"
        ):
            if "analysis_result" in event and event["analysis_result"]:
                result = event["analysis_result"]
        
        return result
    
    finally:
        # Clean up connections
        await store.close()
        await checkpointer.close()


def print_analysis_result(result, title):
    """Print analysis result in a formatted way."""
    if result:
        print(f"\n{title}:")
        print("=" * 50)
        
        # Issues
        issues = result.get("issues", [])
        if issues:
            print("\nIdentified Issues:")
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue.get('description', 'No description')}")
                print(f"   Severity: {issue.get('severity', 'Unknown')}")
        
        # Suggestions
        suggestions = result.get("suggestions", [])
        if suggestions:
            print("\nSuggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"{i}. {suggestion}")
        
        # Documentation
        docs = result.get("documentation_references", [])
        if docs:
            print("\nRelevant Documentation:")
            for doc in docs[:3]:  # Limit to 3
                print(f"- {doc.get('title', 'No title')}")
                print(f"  {doc.get('url', 'No URL')}")
        
        # Commands
        commands = result.get("diagnostic_commands", [])
        if commands:
            print("\nDiagnostic Commands:")
            for cmd in commands[:5]:  # Limit to 5
                print(f"$ {cmd.get('command', 'No command')}")
                print(f"  # {cmd.get('description', 'No description')}")
    else:
        print("No analysis result was produced.")


async def benchmark_modes():
    """Benchmark different modes to show performance differences."""
    example_log = """
    2023-08-15T14:25:12.345Z ERROR [app.main] Failed to connect to database: Connection refused
    2023-08-15T14:25:14.123Z FATAL [app.main] Application startup failed: Database connection error
    """
    
    print("Benchmarking different modes...")
    print("=" * 60)
    
    # Minimal mode
    start = time.time()
    result = await process_log_minimal(example_log)
    minimal_time = time.time() - start
    print(f"Minimal mode: {minimal_time:.2f}s")
    
    # Interactive mode
    start = time.time()
    result, _ = await process_log_interactive(example_log)
    interactive_time = time.time() - start
    print(f"Interactive mode: {interactive_time:.2f}s")
    
    # Memory mode (if available)
    if os.getenv("DATABASE_URL"):
        try:
            start = time.time()
            result = await process_log_with_memory(example_log)
            memory_time = time.time() - start
            print(f"Memory mode: {memory_time:.2f}s")
        except Exception as e:
            print(f"Memory mode: Failed ({e})")
    
    print("\nPerformance comparison:")
    print(f"Interactive overhead: {((interactive_time/minimal_time) - 1) * 100:.1f}%")


async def main():
    """Main function demonstrating different modes."""
    # Example log file
    example_log = """
    2023-08-15T14:25:12.345Z ERROR [app.main] Failed to connect to database: Connection refused
    2023-08-15T14:25:12.567Z INFO [app.main] Retrying database connection (attempt 1/5)
    2023-08-15T14:25:13.123Z ERROR [app.main] Retry failed: Connection refused
    2023-08-15T14:25:14.123Z FATAL [app.main] Application startup failed: Database connection error
    """
    
    # Example environment details
    environment_details = {
        "software": "MyApp v1.2.3",
        "database": "PostgreSQL 14.5",
        "runtime": "Python 3.9 on Ubuntu 22.04"
    }
    
    print("Log Analyzer Agent - Lightweight Mode Demo")
    print("=" * 60)
    
    # Test minimal mode
    print("\n1. Testing MINIMAL mode (lightest)...")
    result = await process_log_minimal(example_log, environment_details)
    print_analysis_result(result, "Minimal Analysis")
    
    # Test interactive mode
    print("\n2. Testing INTERACTIVE mode...")
    result, needs_input = await process_log_interactive(example_log, environment_details)
    print_analysis_result(result, "Interactive Analysis")
    
    # Test memory mode if database is available
    if os.getenv("DATABASE_URL"):
        print("\n3. Testing MEMORY mode (full features)...")
        try:
            result = await process_log_with_memory(
                example_log,
                user_id="demo_user",
                application_name="MyApp",
                environment_details=environment_details
            )
            print_analysis_result(result, "Memory-Enhanced Analysis")
        except Exception as e:
            print(f"Memory mode failed: {e}")
    else:
        print("\n3. MEMORY mode skipped (no DATABASE_URL)")
    
    # Run benchmark
    print("\n" + "=" * 60)
    await benchmark_modes()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Log Analyzer Agent v2")
    parser.add_argument("--mode", choices=["demo", "benchmark", "minimal", "interactive", "memory"], 
                       default="demo", help="Run mode")
    parser.add_argument("--log-file", help="Path to log file to analyze")
    
    args = parser.parse_args()
    
    if args.mode == "benchmark":
        asyncio.run(benchmark_modes())
    elif args.mode in ["minimal", "interactive", "memory"] and args.log_file:
        # Process a specific log file
        with open(args.log_file, 'r') as f:
            log_content = f.read()
        
        if args.mode == "minimal":
            result = asyncio.run(process_log_minimal(log_content))
        elif args.mode == "interactive":
            result, _ = asyncio.run(process_log_interactive(log_content))
        else:  # memory
            result = asyncio.run(process_log_with_memory(log_content))
        
        print_analysis_result(result, f"{args.mode.title()} Analysis")
    else:
        asyncio.run(main())