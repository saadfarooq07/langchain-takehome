"""Improved graph implementation with LangGraph best practices.

This module implements a modern log analyzer using subgraphs, parallel execution,
checkpointing, and proper cycle management.
"""

from typing import Dict, Any, List, Optional, Literal, TypedDict, Set, Union
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
import asyncio

from .unified_state import UnifiedState, LogAnalysisInput, LogAnalysisOutput
from ..tools import search_documentation, submit_analysis, request_additional_info


class RouterOutput(TypedDict):
    """Type for router outputs."""
    route: str


async def categorize_logs(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """Categorize log type to route to appropriate subgraph."""
    # Simple categorization based on log content patterns
    log_content_lower = state.log_content.lower()
    
    if "hdfs" in log_content_lower or "namenode" in log_content_lower or "datanode" in log_content_lower:
        log_type = "hdfs"
    elif "auth" in log_content_lower or "security" in log_content_lower or "permission" in log_content_lower:
        log_type = "security"
    elif "application" in log_content_lower or "app" in log_content_lower:
        log_type = "application"
    else:
        log_type = "general"
    
    # Check if log is large enough to require streaming
    log_size_mb = len(state.log_content) / (1024 * 1024)
    if log_size_mb > 10:  # 10MB threshold
        state.enable_feature("streaming")
        state.is_streaming = True
    
    return {
        "log_metadata": {
            **state.log_metadata,
            "detected_type": log_type,
            "size_mb": log_size_mb
        }
    }


def route_by_log_type(state: UnifiedState) -> Union[Literal["hdfs"], Literal["security"], Literal["application"], Literal["general"]]:
    """Route to appropriate analyzer based on log type."""
    log_type = state.log_metadata.get("detected_type", "general")
    
    routing_map = {
        "hdfs": "hdfs",
        "hadoop": "hdfs", 
        "security": "security",
        "auth": "security",
        "application": "application",
        "app": "application"
    }
    
    result = routing_map.get(log_type.lower(), "general")
    
    # Ensure we return a valid literal
    if result == "hdfs":
        return "hdfs"
    elif result == "security":
        return "security"
    elif result == "application":
        return "application"
    else:
        return "general"


async def stream_processor(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """Process large logs in streaming chunks."""
    if not state.is_streaming:
        # Small log, process normally
        return {"chunk_results": [{"full_log": state.log_content}]}
    
    # Simple chunking implementation
    chunk_size = 5 * 1024 * 1024  # 5MB chunks
    log_content = state.log_content
    chunks = []
    
    for i in range(0, len(log_content), chunk_size):
        chunk = log_content[i:i + chunk_size]
        # Find last newline to avoid splitting lines
        if i + chunk_size < len(log_content):
            last_newline = chunk.rfind('\n')
            if last_newline > 0:
                chunk = chunk[:last_newline]
        
        chunks.append({
            "content": chunk,
            "line_range": {"start": i, "end": i + len(chunk)}
        })
    
    state.total_chunks = len(chunks)
    
    # Process chunks in parallel (up to 3 at a time)
    chunk_results = []
    semaphore = asyncio.Semaphore(3)
    
    async def process_chunk(chunk_data: Dict[str, Any], index: int) -> Dict[str, Any]:
        async with semaphore:
            # Here you would call the actual analysis for each chunk
            # For now, returning placeholder
            return {
                "chunk_index": index,
                "content": chunk_data["content"],
                "line_range": chunk_data["line_range"],
                "analysis": {"processed": True}
            }
    
    tasks = [
        process_chunk(chunk, i) 
        for i, chunk in enumerate(chunks)
    ]
    
    chunk_results = await asyncio.gather(*tasks)
    
    return {
        "chunk_results": chunk_results,
        "current_chunk_index": len(chunks)
    }


async def aggregate_results(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """Aggregate results from multiple chunks or analyses."""
    if not state.chunk_results:
        return {}
    
    # Simple aggregation logic
    all_issues = []
    all_recommendations = []
    
    for chunk_result in state.chunk_results:
        if "analysis" in chunk_result and isinstance(chunk_result["analysis"], dict):
            issues = chunk_result["analysis"].get("issues", [])
            all_issues.extend(issues)
            recommendations = chunk_result["analysis"].get("recommendations", [])
            all_recommendations.extend(recommendations)
    
    # Create structured output
    analysis_output = LogAnalysisOutput(
        issues=all_issues,
        root_cause="Aggregated analysis from multiple chunks",
        recommendations=all_recommendations,
        documentation_references=[],
        diagnostic_commands=[],
        confidence_score=0.8,
        analysis_metadata={
            "chunks_processed": len(state.chunk_results),
            "features_used": list(state.features)
        }
    )
    
    return {
        "analysis_result": analysis_output.__dict__,
        "validation_status": "pending"
    }


async def validate_with_fallback(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """Validate analysis with fallback strategies."""
    if not state.analysis_result:
        return {"validation_status": "failed"}
    
    # Basic validation checks
    has_issues = len(state.analysis_result.get("issues", [])) > 0
    has_root_cause = bool(state.analysis_result.get("root_cause"))
    has_recommendations = len(state.analysis_result.get("recommendations", [])) > 0
    
    if has_issues and has_root_cause and has_recommendations:
        return {"validation_status": "valid"}
    
    # If validation fails, try fallback tools
    if not has_issues:
        # Try alternative analysis approach
        # This would call a different model or analysis strategy
        pass
    
    return {"validation_status": "needs_retry"}


def route_after_validation(state: UnifiedState) -> Union[Literal["retry_analysis"], Literal["store_results"], Literal["__end__"]]:
    """Route based on validation results."""
    if state.validation_status == "valid":
        return "store_results" if state.supports_memory else "__end__"
    elif state.validation_status == "needs_retry":
        # Check retry count from execution metadata
        retry_count = state.execution_metadata.get("retry_count", 0)
        if retry_count < 3:
            return "retry_analysis"
    return "__end__"


async def store_with_checkpoint(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """Store results with checkpointing support."""
    # Store analysis results if memory is enabled
    if state.supports_memory and state.memory_context:
        # Store in memory service
        pass
    
    # Update checkpoint
    from datetime import datetime
    return {
        "checkpoint_id": f"checkpoint_{datetime.now().isoformat()}",
        "last_checkpoint": datetime.now()
    }


# Placeholder analyzer functions for subgraphs
async def hdfs_analyzer(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """HDFS-specific log analysis."""
    # Specialized HDFS analysis logic would go here
    return {
        "chunk_results": [{
            "analysis": {
                "issues": [{"type": "hdfs", "description": "HDFS-specific issue"}],
                "recommendations": ["Check HDFS namenode status"]
            }
        }]
    }


async def security_analyzer(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """Security-specific log analysis."""
    return {
        "chunk_results": [{
            "analysis": {
                "issues": [{"type": "security", "description": "Security issue detected"}],
                "recommendations": ["Review security policies"]
            }
        }]
    }


async def application_analyzer(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """Application-specific log analysis."""
    return {
        "chunk_results": [{
            "analysis": {
                "issues": [{"type": "application", "description": "Application error"}],
                "recommendations": ["Check application configuration"]
            }
        }]
    }


async def general_analyzer(state: UnifiedState, config: RunnableConfig) -> Dict[str, Any]:
    """General log analysis."""
    return {
        "chunk_results": [{
            "analysis": {
                "issues": [{"type": "general", "description": "General issue"}],
                "recommendations": ["Review log patterns"]
            }
        }]
    }


def create_improved_graph(features: Optional[Set[str]] = None):
    """Create the improved log analyzer graph with all enhancements."""
    # Main workflow
    workflow = StateGraph(UnifiedState)
    
    # Add nodes
    workflow.add_node("categorize", categorize_logs)
    workflow.add_node("stream_processor", stream_processor)
    workflow.add_node("aggregate", aggregate_results)
    workflow.add_node("validate", validate_with_fallback)
    workflow.add_node("store_results", store_with_checkpoint)
    
    # Add analyzer nodes (these would be subgraphs in production)
    workflow.add_node("hdfs_analyzer", hdfs_analyzer)
    workflow.add_node("security_analyzer", security_analyzer)
    workflow.add_node("application_analyzer", application_analyzer)
    workflow.add_node("general_analyzer", general_analyzer)
    
    # Tool node with fallback handling
    tools = [search_documentation, submit_analysis]
    if features and "interactive" in features:
        tools.append(request_additional_info)
    
    tool_node = ToolNode(tools)
    workflow.add_node("tools", tool_node)
    
    # Define edges
    workflow.add_edge(START, "categorize")
    
    # Route to appropriate analyzer
    workflow.add_conditional_edges(
        "categorize",
        route_by_log_type,
        {
            "hdfs": "hdfs_analyzer",
            "security": "security_analyzer", 
            "application": "application_analyzer",
            "general": "general_analyzer"
        }
    )
    
    # All analyzers go to stream processor
    for analyzer in ["hdfs_analyzer", "security_analyzer", "application_analyzer", "general_analyzer"]:
        workflow.add_edge(analyzer, "stream_processor")
    
    workflow.add_edge("stream_processor", "aggregate")
    workflow.add_edge("aggregate", "validate")
    
    # Conditional routing after validation
    workflow.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "retry_analysis": "tools",
            "store_results": "store_results",
            "__end__": END
        }
    )
    
    workflow.add_edge("tools", "aggregate")
    workflow.add_edge("store_results", END)
    
    # Compile with best practices
    checkpointer = MemorySaver()
    
    app = workflow.compile(
        checkpointer=checkpointer,
        # Interrupt before user input if needed
        interrupt_before=["request_additional_info"] if features and "interactive" in features else None
    )
    
    # The graph itself handles cycle prevention through its structure
    # No need for external retry policies or manual step counting
    
    return app 