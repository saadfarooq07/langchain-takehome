"""Consolidated graph implementation for the log analyzer agent.

This module provides a clean, maintainable graph implementation that combines
the best features from all versions while removing unnecessary complexity.
"""

from typing import Dict, Any, Set, Optional, Literal, Union
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage
import functools
import time
from datetime import datetime

from .state import CoreWorkingState, InteractiveWorkingState, MemoryWorkingState
from .nodes.analysis import analyze_logs
from .nodes.validation import validate_analysis
from .nodes.user_input import handle_user_input
from .tools import search_documentation, request_additional_info, submit_analysis
from .utils import count_node_visits, count_tool_calls


# Simple in-memory cache for repeated analyses
_analysis_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def cache_analysis(func):
    """Simple caching decorator for analysis results."""
    @functools.wraps(func)
    def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
        # Create cache key from log content hash
        import hashlib
        cache_key = hashlib.md5(state.get("log_content", "").encode()).hexdigest()
        
        # Check cache
        if cache_key in _analysis_cache:
            cached = _analysis_cache[cache_key]
            if time.time() - cached["timestamp"] < CACHE_TTL_SECONDS:
                return {
                    "analysis_result": cached["result"],
                    "messages": [HumanMessage(content="Retrieved from cache")]
                }
        
        # Run analysis
        result = func(state)
        
        # Cache result if successful
        if result.get("analysis_result"):
            _analysis_cache[cache_key] = {
                "result": result["analysis_result"],
                "timestamp": time.time()
            }
        
        return result
    
    return wrapper


def should_retry(state: Dict[str, Any]) -> bool:
    """Check if we should retry the analysis."""
    # Simple retry logic based on node visits
    visits = count_node_visits(state.get("messages", []), "analyze_logs")
    return visits < 3 and state.get("validation_status") == "invalid"


def route_after_analysis(state: Dict[str, Any]) -> Union[
    Literal["validate_analysis"],
    Literal["tools"],
    Literal["__end__"]
]:
    """Route after the analysis node."""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    
    # Check recursion limits
    analysis_count = count_node_visits(messages, "analyze_logs")
    tool_count = count_tool_calls(messages)
    
    if analysis_count >= 10 or tool_count >= 20:
        return "__end__"
    
    # Check for tool calls
    if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Go to validation
    return "validate_analysis"


def route_after_validation(state: Dict[str, Any]) -> Union[
    Literal["analyze_logs"],
    Literal["handle_user_input"],
    Literal["__end__"]
]:
    """Route after validation."""
    status = state.get("validation_status", "")
    
    # If valid, we're done
    if status == "valid":
        return "__end__"
    
    # If interactive mode and needs input
    if state.get("user_interaction_required") and "needs_user_input" in status:
        return "handle_user_input"
    
    # Retry if should retry
    if should_retry(state):
        return "analyze_logs"
    
    # Otherwise end
    return "__end__"


def route_after_tools(state: Dict[str, Any]) -> Union[
    Literal["validate_analysis"],
    Literal["analyze_logs"],
    Literal["__end__"]
]:
    """Route after tool execution."""
    messages = state.get("messages", [])
    
    # Check limits
    if count_node_visits(messages, "analyze_logs") >= 10:
        return "__end__"
    
    # If we have an analysis result, validate it
    if state.get("analysis_result"):
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
    
    # Determine state class based on features
    if "memory" in features:
        state_class = MemoryWorkingState
    elif "interactive" in features:
        state_class = InteractiveWorkingState
    else:
        state_class = CoreWorkingState
    
    # Create graph
    workflow = StateGraph(state_class)
    
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


# Default graph export for LangGraph
graph = create_interactive_graph()