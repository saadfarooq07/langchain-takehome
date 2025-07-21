"""Enhanced graph implementation with Generative UI support."""

from typing import Dict, Any, Set, Optional, Literal, Union
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer
from langchain_core.messages import HumanMessage
import functools
import time
from datetime import datetime

from .state import CoreWorkingState, InteractiveWorkingState, MemoryWorkingState
from .state_typeddict import State
from .nodes.ui_analysis import analyze_logs_with_ui
from .nodes.validation import validate_analysis
from .nodes.user_input import handle_user_input
from .ui_tools import UI_TOOLS
from .tools import search_documentation, request_additional_info
from .utils import count_node_visits, count_tool_calls


# Enhanced state with UI support
class UIState(State):
    """State that includes UI message support."""
    ui: list[AnyUIMessage] = []


def route_after_analysis(state: Dict[str, Any]) -> Literal["validate_analysis", "tools", END]:
    """Route after analysis based on the analysis result and any tool calls."""
    messages = state.get("messages", [])
    if not messages:
        return END
    
    last_message = messages[-1]
    
    # Check if the last message has tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Check if analysis was submitted
    analysis_result = state.get("analysis_result")
    if analysis_result:
        return "validate_analysis"
    
    return END


def route_after_tools(state: Dict[str, Any]) -> Literal["analyze_logs_with_ui", "validate_analysis", END]:
    """Route after tool execution."""
    # Check if analysis was submitted via tools
    analysis_result = state.get("analysis_result")
    if analysis_result:
        return "validate_analysis"
    
    # Check if we need more analysis
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if hasattr(last_message, "content") and "more analysis" in last_message.content.lower():
            return "analyze_logs_with_ui"
    
    return END


def route_after_validation(state: Dict[str, Any]) -> Literal["handle_user_input", END]:
    """Route after validation based on validation result."""
    validation_status = state.get("validation_status", "")
    needs_user_input = state.get("needs_user_input", False)
    
    if needs_user_input or validation_status == "needs_more_info":
        return "handle_user_input"
    
    return END


def route_after_user_input(state: Dict[str, Any]) -> Literal["analyze_logs_with_ui", END]:
    """Route after handling user input."""
    # Always return to analysis after user input
    return "analyze_logs_with_ui"


def should_continue(state: Dict[str, Any]) -> Literal["continue", END]:
    """General continuation check."""
    # Check visit counts to prevent infinite loops
    node_visits = state.get("node_visits", {})
    tool_calls = state.get("tool_calls", {})
    
    # Limit visits to prevent loops
    max_analysis_visits = 3
    max_total_tool_calls = 10
    
    analysis_visits = node_visits.get("analyze_logs_with_ui", 0)
    total_tool_calls = sum(tool_calls.values())
    
    if analysis_visits >= max_analysis_visits or total_tool_calls >= max_total_tool_calls:
        return END
    
    return "continue"


def create_ui_graph(
    enable_memory: bool = True,
    enable_cache: bool = True,
    interactive_mode: bool = True,
    **kwargs
) -> StateGraph:
    """Create the enhanced UI-enabled graph.
    
    Args:
        enable_memory: Enable memory/context features
        enable_cache: Enable result caching
        interactive_mode: Enable interactive features
        **kwargs: Additional configuration options
        
    Returns:
        Compiled StateGraph ready for execution
    """
    
    # Choose state class based on features
    if enable_memory and interactive_mode:
        state_class = MemoryWorkingState
    elif interactive_mode:
        state_class = InteractiveWorkingState
    else:
        state_class = CoreWorkingState
    
    # Create the graph
    workflow = StateGraph(state_class)
    
    # Add nodes
    workflow.add_node("analyze_logs_with_ui", analyze_logs_with_ui)
    workflow.add_node("validate_analysis", validate_analysis)
    workflow.add_node("handle_user_input", handle_user_input)
    
    # Add tool node with UI tools
    all_tools = UI_TOOLS + [search_documentation, request_additional_info]
    workflow.add_node("tools", ToolNode(all_tools))
    
    # Add edges from START
    workflow.add_edge(START, "analyze_logs_with_ui")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "analyze_logs_with_ui",
        route_after_analysis,
        ["validate_analysis", "tools", END]
    )
    
    workflow.add_conditional_edges(
        "tools",
        route_after_tools,
        ["analyze_logs_with_ui", "validate_analysis", END]
    )
    
    workflow.add_conditional_edges(
        "validate_analysis",
        route_after_validation,
        ["handle_user_input", END]
    )
    
    workflow.add_conditional_edges(
        "handle_user_input",
        route_after_user_input,
        ["analyze_logs_with_ui", END]
    )
    
    # Compile the graph
    return workflow.compile()


# Create the default UI-enabled graph
ui_graph = create_ui_graph()

# Alias for backward compatibility
graph = ui_graph
