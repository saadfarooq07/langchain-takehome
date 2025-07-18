"""Optimized graph with recursion prevention and efficiency improvements.

This module provides a flexible graph construction that adapts to the
features needed, with built-in safeguards against infinite loops.
"""

import os
from typing import Literal, Optional, Set, Type, List
from langchain_core.messages import AIMessage, ToolMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

from .configuration import Configuration
from .state import (
    CoreState,
    InteractiveState,
    MemoryState,
    InputState,
    OutputState,
    create_state_class,
)
from .nodes import analyze_logs, validate_analysis, handle_user_input
from .tools import search_documentation, request_additional_info, submit_analysis
from .typed_state import (
    CoreStateDict,
    InteractiveStateDict,
    MemoryStateDict,
    InputStateDict,
    OutputStateDict,
)


def count_node_visits(messages: List[BaseMessage], node_name: str) -> int:
    """Count how many times a specific node has been visited based on message patterns."""
    count = 0
    for msg in messages:
        if node_name == "analyze_logs" and isinstance(msg, AIMessage):
            count += 1
        elif (
            node_name == "validate_analysis"
            and isinstance(msg, ToolMessage)
            and msg.name == "submit_analysis"
        ):
            count += 1
    return count


def count_tool_calls(messages: List[BaseMessage]) -> int:
    """Count total number of tool calls made."""
    count = 0
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            count += len(msg.tool_calls)
    return count


def route_after_analysis_minimal(
    state: CoreState,
) -> Literal["validate_analysis", "tools", "analyze_logs", "__end__"]:
    """Route based on the analysis state (minimal version) with recursion prevention."""
    messages = getattr(state, "messages", [])
    last_message = messages[-1] if messages else None

    # Count iterations to prevent infinite loops
    analysis_count = count_node_visits(messages, "analyze_logs")
    if analysis_count >= 10:  # Max 10 analysis iterations
        return "__end__"

    # Check if we have an AI message with tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        # If analysis was submitted, validate it
        if last_message.tool_calls[0]["name"] == "submit_analysis":
            # Check validation retry limit
            validation_count = count_node_visits(messages, "validate_analysis")
            if validation_count >= 3:
                return "__end__"
            return "validate_analysis"
        # Otherwise, execute the tools
        return "tools"

    # Default: continue analysis
    return "analyze_logs"


def route_after_analysis(
    state: CoreState,
) -> Literal[
    "validate_analysis", "tools", "analyze_logs", "handle_user_input", "__end__"
]:
    """Route based on the analysis state (full version) with recursion prevention."""
    messages = getattr(state, "messages", [])
    last_message = messages[-1] if messages else None

    # Count iterations to prevent infinite loops
    analysis_count = count_node_visits(messages, "analyze_logs")
    tool_count = count_tool_calls(messages)

    # Prevent excessive iterations
    if analysis_count >= 10 or tool_count >= 20:
        return "__end__"

    # Check if user input is needed (only if interactive features enabled)
    if hasattr(state, "needs_user_input") and getattr(state, "needs_user_input", False):
        return "handle_user_input"

    # Check if we have an AI message with tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        # If analysis was submitted, validate it
        if last_message.tool_calls[0]["name"] == "submit_analysis":
            # Check validation retry limit
            validation_count = count_node_visits(messages, "validate_analysis")
            if validation_count >= 3:
                return "__end__"
            return "validate_analysis"
        # Otherwise, execute the tools
        return "tools"

    # Default: continue analysis
    return "analyze_logs"


def route_after_validation(
    state: CoreState,
) -> Literal["__end__", "analyze_logs"]:
    """Route after validation - either end or continue improving."""
    messages = getattr(state, "messages", [])
    last_message = messages[-1] if messages else None

    if isinstance(last_message, ToolMessage):
        # If validation passed, we're done
        if last_message.status == "success":
            return "__end__"

        # Check retry limit before continuing
        validation_count = count_node_visits(messages, "validate_analysis")
        if validation_count >= 3:  # Max 3 validation attempts
            return "__end__"

        # Otherwise, continue improving the analysis
        return "analyze_logs"

    return "__end__"


def create_graph(
    features: Optional[Set[str]] = None, lightweight: bool = False
) -> StateGraph:
    """Create a graph with the appropriate state class and features.

    Args:
        features: Set of features to enable. Options:
            - "interactive": Enable user interaction
            - "memory": Enable memory/persistence (implies interactive)
        lightweight: If True, creates minimal graph with no extra features

    Returns:
        Compiled LangGraph workflow
    """
    # Determine features
    if lightweight:
        features = set()
    elif features is None:
        # Default to interactive but no memory for backward compatibility
        features = {"interactive"}

    # Select appropriate state class
    StateClass = create_state_class(features)

    # Build the graph
    workflow = StateGraph(
        StateClass, input=InputState, output=OutputState, config_schema=Configuration
    )

    # Always add core nodes
    workflow.add_node("analyze_logs", analyze_logs)
    workflow.add_node("validate_analysis", validate_analysis)
    workflow.add_node("tools", ToolNode([search_documentation]))

    # Add interactive nodes if feature enabled
    if "interactive" in features:
        workflow.add_node("handle_user_input", handle_user_input)

    # Define the flow
    workflow.add_edge(START, "analyze_logs")

    # Use appropriate routing function based on features
    if "interactive" in features:
        workflow.add_conditional_edges("analyze_logs", route_after_analysis)
        workflow.add_edge("handle_user_input", "analyze_logs")
    else:
        workflow.add_conditional_edges("analyze_logs", route_after_analysis_minimal)

    workflow.add_edge("tools", "analyze_logs")
    workflow.add_conditional_edges("validate_analysis", route_after_validation)

    # Compile the graph
    graph = workflow.compile()
    graph.name = "LogAnalyzer"

    return graph


async def create_graph_with_memory(
    db_uri: Optional[str] = None, features: Optional[Set[str]] = None
):
    """Create graph with PostgreSQL memory backend.

    Args:
        db_uri: Database connection string. If not provided, uses DATABASE_URL env var
        features: Additional features to enable beyond memory

    Returns:
        Tuple of (graph, store, checkpointer)
    """
    # Ensure memory feature is included
    features = features or set()
    features.add("memory")

    # Get database URI
    if not db_uri:
        db_uri = os.getenv(
            "DATABASE_URL",
            "postgresql://loganalyzer:password@localhost:5432/loganalyzer",
        )

    # Initialize PostgreSQL store and checkpointer
    store = AsyncPostgresStore.from_conn_string(db_uri)
    checkpointer = AsyncPostgresSaver.from_conn_string(db_uri)

    # Setup tables
    await store.setup()
    await checkpointer.setup()

    # Create state class with memory features
    StateClass = create_state_class(features)

    # Build the graph
    workflow = StateGraph(
        StateClass, input=InputState, output=OutputState, config_schema=Configuration
    )

    # Add all nodes (memory-aware versions)
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

    # Compile with memory backend
    graph = workflow.compile(checkpointer=checkpointer, store=store)
    graph.name = "LogAnalyzerWithMemory"

    return graph, store, checkpointer


# Convenience functions for common configurations
def create_minimal_graph():
    """Create the most lightweight graph possible."""
    return create_graph(lightweight=True)


def create_interactive_graph():
    """Create graph with interactive features but no persistence."""
    return create_graph(features={"interactive"})


def create_full_graph():
    """Create graph with all features enabled (requires DB setup)."""
    # This returns a regular graph but with MemoryState
    # Actual memory features require using create_graph_with_memory
    return create_graph(features={"memory"})


# For backward compatibility
graph = create_interactive_graph()


def create_studio_friendly_graph(features: Optional[Set[str]] = None):
    """Create a graph with TypedDict states for better Studio display."""
    features = features or {"interactive"}

    # Select appropriate state type
    if "memory" in features:
        StateDict = MemoryStateDict
    elif "interactive" in features:
        StateDict = InteractiveStateDict
    else:
        StateDict = CoreStateDict

    # Build the graph with TypedDict
    workflow = StateGraph(
        StateDict,
        input=InputStateDict,
        output=OutputStateDict,
        config_schema=Configuration,
    )

    # Add nodes
    workflow.add_node("analyze_logs", analyze_logs)
    workflow.add_node("validate_analysis", validate_analysis)
    workflow.add_node("tools", ToolNode([search_documentation]))

    if "interactive" in features:
        workflow.add_node("handle_user_input", handle_user_input)

    # Define the flow
    workflow.add_edge(START, "analyze_logs")

    if "interactive" in features:
        workflow.add_conditional_edges("analyze_logs", route_after_analysis)
        workflow.add_edge("handle_user_input", "analyze_logs")
    else:
        workflow.add_conditional_edges("analyze_logs", route_after_analysis_minimal)

    workflow.add_edge("tools", "analyze_logs")
    workflow.add_conditional_edges("validate_analysis", route_after_validation)

    # Compile the graph
    compiled_graph = workflow.compile()
    compiled_graph.name = "LogAnalyzer"

    return compiled_graph
