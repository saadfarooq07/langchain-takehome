"""Simplified Log Analyzer Agent graph definition.

Following LangGraph best practices with cleaner structure.
"""

from typing import Literal
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from .configuration import Configuration
from .state import State, InputState, OutputState
from .nodes import analyze_logs, validate_analysis, handle_user_input
from .tools import search_documentation, request_additional_info


def route_after_analysis(
    state: State,
) -> Literal["validate_analysis", "tools", "analyze_logs", "handle_user_input"]:
    """Route based on the analysis state."""
    last_message = state.get("messages", [])[-1] if state.get("messages") else None
    
    # Check if user input is needed
    if state.get("needs_user_input"):
        return "handle_user_input"
    
    # Check if we have an AI message with tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        # If analysis was submitted, validate it
        if last_message.tool_calls[0]["name"] == "submit_analysis":
            return "validate_analysis"
        # Otherwise, execute the tools
        return "tools"
    
    # Default: continue analysis
    return "analyze_logs"


def route_after_validation(
    state: State,
) -> Literal["__end__", "analyze_logs"]:
    """Route after validation - either end or continue improving."""
    last_message = state.get("messages", [])[-1] if state.get("messages") else None
    
    if isinstance(last_message, ToolMessage):
        # If validation passed, we're done
        if last_message.status == "success":
            return "__end__"
        # Otherwise, continue improving the analysis
        return "analyze_logs"
    
    return "__end__"


# Build the graph
workflow = StateGraph(State, input=InputState, output=OutputState, config_schema=Configuration)

# Add nodes
workflow.add_node("analyze_logs", analyze_logs)
workflow.add_node("validate_analysis", validate_analysis)
workflow.add_node("handle_user_input", handle_user_input)
workflow.add_node("tools", ToolNode([search_documentation]))

# Define the flow
workflow.add_edge(START, "analyze_logs")
workflow.add_conditional_edges("analyze_logs", route_after_analysis)
workflow.add_edge("tools", "analyze_logs")
workflow.add_conditional_edges("validate_analysis", route_after_validation)
workflow.add_edge("handle_user_input", "analyze_logs")

# Compile the graph
graph = workflow.compile()
graph.name = "LogAnalyzer"