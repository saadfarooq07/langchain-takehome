"""Improved graph implementation with all Phase 2, 3, and 4 enhancements.

This module provides the fully improved log analyzer graph that includes:
- Unified state management (Phase 3)
- Streaming support for large logs (Phase 2)
- Circuit breaker and rate limiting (Phase 4)
- Specialized subgraph routing (Phase 4)
- Built-in LangGraph features for cycle prevention (Phase 3)
"""

import os
import asyncio
from typing import Dict, Any, Optional, Set, Literal, Union, List
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage
import logging

from .unified_state import UnifiedState, create_unified_state
from .improved_graph_wrapper import (
    streaming_analyze_logs,
    route_after_analysis,
    route_after_validation,
    specialized_analysis_router
)
from ..nodes.validation import validate_analysis
from ..nodes.user_input import handle_user_input
from ..tools import search_documentation, request_additional_info, submit_analysis

logger = logging.getLogger(__name__)


def create_improved_graph(features: Optional[Set[str]] = None) -> StateGraph:
    """Create the fully improved graph with all enhancements.
    
    Features:
        - "interactive": Enable user interaction
        - "memory": Enable memory/persistence
        - "streaming": Enable streaming for large logs (auto-enabled)
        - "caching": Enable result caching
        - "specialized": Enable specialized subgraph analyzers
    
    Returns:
        Compiled StateGraph with all improvements
    """
    features = features or set()
    
    # Import the TypedDict State for LangGraph compatibility
    from ..state_typeddict import State
    
    # Create workflow with TypedDict State
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("analyze_logs", streaming_analyze_logs)
    workflow.add_node("validate_analysis", validate_analysis)
    
    # Add specialized analysis router if enabled
    if "specialized" in features:
        workflow.add_node("specialized_analysis", specialized_analysis_router)
    
    # Add tools
    tools = [search_documentation, submit_analysis]
    if "interactive" in features:
        tools.append(request_additional_info)
        workflow.add_node("handle_user_input", handle_user_input)
    
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)
    
    # Define edges
    workflow.add_edge(START, "analyze_logs")
    
    # Conditional routing after analysis
    workflow.add_conditional_edges(
        "analyze_logs",
        route_after_analysis,
        {
            "validate_analysis": "validate_analysis",
            "tools": "tools",
            "__end__": END
        }
    )
    
    # Conditional routing after validation
    validation_routes = {
        "__end__": END
    }
    if "specialized" in features:
        validation_routes["specialized_analysis"] = "specialized_analysis"
    if "interactive" in features:
        validation_routes["handle_user_input"] = "handle_user_input"
    
    workflow.add_conditional_edges(
        "validate_analysis",
        route_after_validation,
        validation_routes
    )
    
    # Tools always route back to validation
    workflow.add_edge("tools", "validate_analysis")
    
    # Interactive input routes back to analysis
    if "interactive" in features:
        workflow.add_edge("handle_user_input", "analyze_logs")
    
    # Specialized analysis routes to validation
    if "specialized" in features:
        workflow.add_edge("specialized_analysis", "validate_analysis")
    
    # Compile with checkpointer if memory is enabled
    checkpointer = None
    if "memory" in features:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()
    
    # Compile the graph
    compiled = workflow.compile(
        checkpointer=checkpointer,
        # LangGraph will handle retry limits automatically
    )
    
    return compiled


# Helper function to run the improved graph
async def run_improved_analysis(
    log_content: str,
    features: Optional[Set[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Run log analysis with the improved graph.
    
    Args:
        log_content: Log content to analyze
        features: Set of features to enable
        metadata: Additional metadata about the log
        
    Returns:
        Analysis results
    """
    # Create initial state in TypedDict format
    initial_state = {
        "messages": [HumanMessage(content=f"Please analyze this log:\n{log_content}")],
        "log_content": log_content,
        "log_metadata": metadata or {},
        "analysis_result": None,
        "validation_status": None,
        "node_visits": {},
        "tool_calls": [],
        "token_count": 0,
        "start_time": UnifiedState().start_time,
        "enabled_features": list(features or {"streaming", "specialized"})
    }
    
    # Add feature-specific fields
    if "interactive" in (features or set()):
        initial_state.update({
            "user_interaction_required": False,
            "pending_questions": [],
            "user_responses": {}
        })
    
    if "memory" in (features or set()):
        initial_state.update({
            "memory_matches": [],
            "application_context": {}
        })
    
    if "streaming" in (features or set()):
        initial_state.update({
            "is_streaming": False,
            "current_chunk_index": 0,
            "total_chunks": 0,
            "chunk_results": []
        })
    
    # Create and run graph
    graph = create_improved_graph(features or {"streaming", "specialized"})
    
    # Run analysis
    result = await graph.ainvoke(initial_state)
    
    return result.get("analysis_result", {})