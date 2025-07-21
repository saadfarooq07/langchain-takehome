"""Enhanced graph with improved analysis output quality."""

from typing import Dict, Any, Set, Optional, Union
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage

from .state import CoreWorkingState, InteractiveWorkingState, MemoryWorkingState
from .state_typeddict import State
from .nodes.enhanced_analysis import enhanced_analyze_logs
from .nodes.validation import validate_analysis
from .nodes.user_input import handle_user_input
from .tools import search_documentation, request_additional_info, submit_analysis
from .graph import (
    route_after_analysis,
    route_after_validation,
    route_after_tools,
    cache_analysis
)


def create_enhanced_graph(features: Optional[Set[str]] = None) -> StateGraph:
    """Create an enhanced graph with improved analysis output.
    
    This graph uses the enhanced analysis node that produces better structured,
    more actionable output with clear formatting and comprehensive recommendations.
    
    Args:
        features: Set of features to enable. Options:
            - "interactive": Enable user interaction
            - "memory": Enable memory/persistence
            - "caching": Enable result caching
    
    Returns:
        Compiled StateGraph
    """
    features = features or set()
    
    # Create workflow with TypedDict State
    workflow = StateGraph(State)
    
    # Add nodes - use enhanced analysis instead of regular
    if "caching" in features:
        workflow.add_node("analyze_logs", cache_analysis(enhanced_analyze_logs))
    else:
        workflow.add_node("analyze_logs", enhanced_analyze_logs)
    
    workflow.add_node("validate_analysis", validate_analysis)
    
    # Add tools
    tools = [search_documentation, submit_analysis]
    if "interactive" in features:
        tools.append(request_additional_info)
        workflow.add_node("handle_user_input", handle_user_input)
    
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)
    
    # Define edges (same as regular graph)
    workflow.add_edge(START, "analyze_logs")
    
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
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)


# Export the enhanced graph as the default when improved mode is enabled
import os
if os.getenv("USE_ENHANCED_ANALYSIS", "").lower() == "true":
    graph = create_enhanced_graph()
else:
    # Import regular graph
    from .graph import graph