"""Consolidated graph implementation for the log analyzer agent.

This module provides a clean, maintainable graph implementation that combines
the best features from all versions while removing unnecessary complexity.

For UI-enhanced features, use ui_graph.py instead.
"""

# Apply SSE compatibility patch
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    import patch_sse
except ImportError:
    pass

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from typing import Dict, Any, Set, Optional, Literal, Union
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage
import functools
import time
import os
from datetime import datetime

from .state import CoreWorkingState, InteractiveWorkingState, MemoryWorkingState
from .state_typeddict import State
from .nodes.analysis import analyze_logs as _analyze_logs_impl
from .nodes.validation import validate_analysis as _validate_analysis_impl
from .nodes.user_input import handle_user_input as _handle_user_input_impl
from .tools import search_documentation, request_additional_info, submit_analysis
from .utils import count_node_visits, count_tool_calls
from .cycle_detector import CycleDetector, CycleType
from .persistence_utils import (
    log_debug, log_info, log_warning, log_error,
    get_workflow_timestamp, generate_deterministic_id
)


# Simple in-memory cache for repeated analyses
_analysis_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


async def initialize_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize state with default values for missing fields.
    
    This ensures all internal fields have proper defaults even when
    the user only provides minimal input (just log_content).
    """
    # Ensure messages field exists
    if "messages" not in state:
        state["messages"] = []
    
    # Initialize tracking fields
    if "node_visits" not in state:
        state["node_visits"] = {}
    if "tool_calls" not in state:
        state["tool_calls"] = []
    if "token_count" not in state:
        state["token_count"] = 0
    if "start_time" not in state:
        # Use deterministic timestamp for the workflow
        state["start_time"] = await get_workflow_timestamp(state)
    
    # Initialize metadata
    if "log_metadata" not in state:
        state["log_metadata"] = {}
    
    # Initialize features
    if "enabled_features" not in state:
        state["enabled_features"] = []
    
    return state

# Configurable iteration limits
MAX_ANALYSIS_ITERATIONS = int(os.getenv("MAX_ANALYSIS_ITERATIONS", "10"))
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "20"))
MAX_VALIDATION_RETRIES = int(os.getenv("MAX_VALIDATION_RETRIES", "3"))

# Global cycle detector instance with configurable limits
_cycle_detector = CycleDetector(
    max_history=int(os.getenv("CYCLE_DETECTION_WINDOW", "20")),
    detection_threshold=int(os.getenv("MAX_SIMPLE_LOOPS", "3"))
)


# Wrapper functions to handle dict-based state
async def analyze_logs(state: Dict[str, Any], *, config: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Wrapper for analyze_logs that handles dict state."""
    # Initialize state with defaults
    state = await initialize_state(state)
    
    # Create a minimal CoreWorkingState for the implementation
    from langchain_core.messages import HumanMessage
    if not state.get("messages"):
        state["messages"] = [HumanMessage(content=f"Analyze this log:\n{state.get('log_content', '')}")] 
    
    working_state = CoreWorkingState(
        messages=state.get("messages", []),
        log_content=state.get("log_content", ""),
        log_metadata=state.get("log_metadata", {}),
        analysis_result=state.get("analysis_result"),
        validation_status=state.get("validation_status"),
        node_visits=state.get("node_visits", {}),
        tool_calls=state.get("tool_calls", []),
        token_count=state.get("token_count", 0),
        start_time=state.get("start_time", time.time()),
        enabled_features=set(state.get("enabled_features", []))
    )
    
    # Call the implementation with config
    result = await _analyze_logs_impl(working_state, config=config, **kwargs)
    
    # Merge results back into state
    return {**state, **result}


async def validate_analysis(state: Dict[str, Any], *, config: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Wrapper for validate_analysis that handles dict state."""
    # Initialize state with defaults
    state = await initialize_state(state)
    
    # Create a minimal state for the implementation
    working_state = CoreWorkingState(
        messages=state.get("messages", []),
        log_content=state.get("log_content", ""),
        log_metadata=state.get("log_metadata", {}),
        analysis_result=state.get("analysis_result"),
        validation_status=state.get("validation_status"),
        node_visits=state.get("node_visits", {}),
        tool_calls=state.get("tool_calls", []),
        token_count=state.get("token_count", 0),
        start_time=state.get("start_time", time.time()),
        enabled_features=set(state.get("enabled_features", []))
    )
    
    # Call the implementation with config
    result = await _validate_analysis_impl(working_state, config=config, **kwargs)
    
    # Merge results back into state
    return {**state, **result}


async def handle_user_input(state: Dict[str, Any], *, config: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Wrapper for handle_user_input that handles dict state."""
    # Initialize state with defaults  
    state = await initialize_state(state)
    
    # Create an InteractiveWorkingState for the implementation
    working_state = InteractiveWorkingState(
        messages=state.get("messages", []),
        log_content=state.get("log_content", ""),
        log_metadata=state.get("log_metadata", {}),
        analysis_result=state.get("analysis_result"),
        validation_status=state.get("validation_status"),
        node_visits=state.get("node_visits", {}),
        tool_calls=state.get("tool_calls", []),
        token_count=state.get("token_count", 0),
        start_time=state.get("start_time", time.time()),
        enabled_features=set(state.get("enabled_features", [])),
        user_input=state.get("user_input"),
        pending_questions=state.get("pending_questions"),
        user_interaction_required=state.get("user_interaction_required", False),
        interaction_history=state.get("interaction_history", [])
    )
    
    # Call the implementation with config
    result = await _handle_user_input_impl(working_state, config=config, **kwargs)
    
    # Merge results back into state
    return {**state, **result}


def cache_analysis(func):
    """Simple caching decorator for analysis results."""
    @functools.wraps(func)
    async def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure state is initialized
        state = await initialize_state(state)
        
        # Create deterministic cache key
        log_content = state.get("log_content", "")
        cache_key = generate_deterministic_id(log_content, "cache")
        
        # Check cache
        if cache_key in _analysis_cache:
            cached = _analysis_cache[cache_key]
            workflow_time = await get_workflow_timestamp(state)
            if workflow_time - cached["timestamp"] < CACHE_TTL_SECONDS:
                await log_debug(f"Retrieved analysis from cache (key: {cache_key[:8]}...)")
                return {
                    "analysis_result": cached["result"],
                    "messages": [HumanMessage(content="Retrieved from cache")]
                }
        
        # Run analysis
        result = await func(state)
        
        # Cache result if successful
        if result.get("analysis_result"):
            workflow_time = await get_workflow_timestamp(state)
            _analysis_cache[cache_key] = {
                "result": result["analysis_result"],
                "timestamp": workflow_time
            }
            await log_debug(f"Cached analysis result (key: {cache_key[:8]}...)")
        
        return result
    
    return wrapper


def should_retry(state: Union[Dict[str, Any], Any]) -> bool:
    """Check if we should retry the analysis."""
    # Handle both dict and dataclass
    if hasattr(state, "get"):
        messages = state.get("messages", [])
        validation_status = state.get("validation_status")
    else:
        messages = getattr(state, "messages", [])
        validation_status = getattr(state, "validation_status", None)
    
    # Simple retry logic based on node visits
    visits = count_node_visits(messages, "analyze_logs")
    return visits < MAX_VALIDATION_RETRIES and validation_status == "invalid"


def route_after_analysis(state: Union[Dict[str, Any], Any]) -> Union[
    Literal["validate_analysis"],
    Literal["tools"],
    Literal["__end__"]
]:
    """Route after the analysis node."""
    # Handle both dict and dataclass
    if hasattr(state, "get"):
        messages = state.get("messages", [])
        analysis_result = state.get("analysis_result")
    else:
        messages = getattr(state, "messages", [])
        analysis_result = getattr(state, "analysis_result", None)
    
    # Use async context for logging
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(log_debug(f"route_after_analysis: analysis_result = {analysis_result is not None}"))
    
    last_message = messages[-1] if messages else None
    
    # Add transition to cycle detector
    state_dict = {"messages": messages, "analysis_result": analysis_result}
    cycle = _cycle_detector.add_transition("analyze_logs", "route", state_dict)
    
    # Check for cycles using advanced detection
    if cycle:
        loop.create_task(log_info(f"[CycleDetector] Breaking {cycle.cycle_type} cycle: {' -> '.join(cycle.pattern)}"))
        return "__end__"
    
    # Fallback to simple limits
    analysis_count = count_node_visits(messages, "analyze_logs")
    tool_count = count_tool_calls(messages)
    
    if analysis_count >= MAX_ANALYSIS_ITERATIONS or tool_count >= MAX_TOOL_CALLS:
        return "__end__"
    
    # Check for tool calls
    if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Go to validation
    return "validate_analysis"


def route_after_validation(state: Union[Dict[str, Any], Any]) -> Union[
    Literal["analyze_logs"],
    Literal["handle_user_input"],
    Literal["__end__"]
]:
    """Route after validation."""
    # Handle both dict and dataclass
    if hasattr(state, "get"):
        status = state.get("validation_status", "")
        messages = state.get("messages", [])
    else:
        status = getattr(state, "validation_status", "")
        messages = getattr(state, "messages", [])
    
    # Add transition to cycle detector
    state_dict = {"messages": messages, "validation_status": status}
    cycle = _cycle_detector.add_transition("validate_analysis", "route", state_dict)
    
    # If valid, we're done
    if status == "valid":
        return "__end__"
    
    # Check for validation retry cycles
    if cycle and cycle.cycle_type in [CycleType.OSCILLATION, CycleType.DEADLOCK]:
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(log_info(f"[CycleDetector] Breaking validation {cycle.cycle_type}: {' -> '.join(cycle.pattern)}"))
        return "__end__"
    
    # If invalid and interactive features are enabled, ask user
    if hasattr(state, "get"):
        user_interaction_required = state.get("user_interaction_required")
    else:
        user_interaction_required = getattr(state, "user_interaction_required", None)
    
    if user_interaction_required and "needs_user_input" in status:
        return "handle_user_input"
    
    # Otherwise, retry analysis if under limit
    if should_retry(state):
        return "analyze_logs"
    
    # Otherwise end
    return "__end__"


def route_after_tools(state: Union[Dict[str, Any], Any]) -> Union[
    Literal["analyze_logs"],
    Literal["handle_user_input"],
    Literal["__end__"]
]:
    """Route after tool execution."""
    # Handle both dict and dataclass
    if hasattr(state, "get"):
        messages = state.get("messages", [])
    else:
        messages = getattr(state, "messages", [])
    
    # Add transition to cycle detector
    state_dict = {"messages": messages}
    cycle = _cycle_detector.add_transition("tools", "route", state_dict)
    
    # Check for tool execution cycles
    if cycle:
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(log_info(f"[CycleDetector] Breaking tool {cycle.cycle_type}: {' -> '.join(cycle.pattern)}"))
        return "__end__"
    
    # Check limits
    if count_node_visits(messages, "analyze_logs") >= MAX_ANALYSIS_ITERATIONS:
        return "__end__"
    
    # If we have an analysis result, validate it
    if hasattr(state, "get"):
        analysis_result = state.get("analysis_result")
    else:
        analysis_result = getattr(state, "analysis_result", None)
    
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(log_debug(f"route_after_tools: analysis_result = {analysis_result is not None}"))
    
    if analysis_result:
        return "validate_analysis"
    
    # Otherwise, analyze again
    return "analyze_logs"


def create_graph(features: Optional[Set[str]] = None) -> StateGraph:
    """Create a graph with the specified features.
    
    Args:
        features: Set of features to enable. Options:
            - "interactive": Enable user interaction
            - "memory": Enable memory features (requires database)
            - "caching": Enable result caching
            
    Returns:
        Compiled StateGraph
    """
    if features is None:
        features = set()
    
    # Create graph with TypedDict State
    workflow = StateGraph(State)
    
    # Add nodes
    if "caching" in features:
        workflow.add_node("analyze_logs", cache_analysis(analyze_logs))
    else:
        workflow.add_node("analyze_logs", analyze_logs)
    
    workflow.add_node("validate_analysis", validate_analysis)
    
    # Add tool node
    tools = [search_documentation, submit_analysis]
    if "interactive" in features:
        tools.append(request_additional_info)
        workflow.add_node("handle_user_input", handle_user_input)
    
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)
    
    # Define edges
    workflow.add_edge(START, "analyze_logs")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "analyze_logs",
        route_after_analysis,
        {
            "validate_analysis": "validate_analysis",
            "tools": "tools",
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "validate_analysis",
        route_after_validation,
        {
            "analyze_logs": "analyze_logs",
            "handle_user_input": "handle_user_input" if "interactive" in features else END,
            "__end__": END
        }
    )
    
    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "validate_analysis": "validate_analysis",
            "analyze_logs": "analyze_logs",
            "__end__": END
        }
    )
    
    if "interactive" in features:
        workflow.add_edge("handle_user_input", "analyze_logs")
    
    # Compile
    checkpointer = None
    if "memory" in features:
        # Only add checkpointer if memory features are enabled
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)


# Convenience functions for common configurations
def create_minimal_graph():
    """Create a minimal graph with no extra features."""
    return create_graph(features=set())


def create_interactive_graph():
    """Create a graph with interactive features."""
    return create_graph(features={"interactive"})


def create_memory_graph():
    """Create a graph with memory features."""
    return create_graph(features={"memory", "interactive"})


def create_full_graph():
    """Create a graph with all features."""
    return create_graph(features={"memory", "interactive", "caching"})


# Simple performance tracking
_performance_metrics: Dict[str, list] = {
    "analysis_times": [],
    "cache_hits": 0,
    "cache_misses": 0
}


def get_performance_metrics() -> Dict[str, Any]:
    """Get simple performance metrics."""
    analysis_times = _performance_metrics["analysis_times"]
    return {
        "total_analyses": len(analysis_times),
        "average_time": sum(analysis_times) / len(analysis_times) if analysis_times else 0,
        "cache_hit_rate": (_performance_metrics["cache_hits"] / 
                          (_performance_metrics["cache_hits"] + _performance_metrics["cache_misses"])
                          if _performance_metrics["cache_hits"] + _performance_metrics["cache_misses"] > 0 
                          else 0)
    }


def clear_cache():
    """Clear the analysis cache."""
    _analysis_cache.clear()
    _performance_metrics["cache_hits"] = 0
    _performance_metrics["cache_misses"] = 0


# Create enhanced graph for API usage
def create_enhanced_graph():
    """Create an enhanced graph with optimal features for API usage.
    
    This is the recommended graph for production API usage with:
    - Interactive features for better analysis
    - Caching for performance
    - No memory features (handled by API layer)
    """
    return create_graph(features={"interactive", "caching"})


# For now, use the standard graph to avoid import issues
# The improved features are still available through the enhanced nodes
graph = create_interactive_graph()

# Log initialization asynchronously
import asyncio
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

loop.create_task(log_info("Using standard interactive graph with enhanced analysis nodes"))