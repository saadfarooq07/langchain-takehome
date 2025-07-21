"""Wrapper functions to bridge TypedDict state with UnifiedState for improved graph.

This module provides wrapper functions that convert between LangGraph's TypedDict
state and our UnifiedState for the improved implementation.
"""

from typing import Dict, Any, Literal
from langchain_core.messages import AIMessage

from .unified_state import UnifiedState
from .circuit_breaker import CircuitBreakerOpen
from .rate_limiter import APIRateLimiters, RateLimitExceeded
from ..streaming import stream_and_analyze_log
from ..nodes.enhanced_analysis import enhanced_analyze_logs as original_enhanced_analyze
from ..nodes.validation import validate_analysis as original_validate
import logging

logger = logging.getLogger(__name__)


def dict_to_unified_state(state_dict: Dict[str, Any]) -> UnifiedState:
    """Convert TypedDict state to UnifiedState."""
    # Extract features from enabled_features list
    features = set(state_dict.get("enabled_features", []))
    
    # Map known features
    feature_mapping = {
        "interactive": "interactive",
        "memory": "memory",
        "streaming": "streaming",
        "caching": "caching",
        "specialized": "specialized"
    }
    
    # Create unified state
    unified = UnifiedState(
        messages=state_dict.get("messages", []),
        log_content=state_dict.get("log_content", ""),
        log_metadata=state_dict.get("log_metadata", {}),
        analysis_result=state_dict.get("analysis_result"),
        validation_status=state_dict.get("validation_status"),
        features=features,
        node_visits=state_dict.get("node_visits", {}),
        tool_calls=state_dict.get("tool_calls", []),
        token_count=state_dict.get("token_count", 0),
        start_time=state_dict.get("start_time", 0)
    )
    
    # Copy interactive features if enabled
    if "interactive" in features:
        unified.user_interaction_required = state_dict.get("user_interaction_required", False)
        unified.pending_questions = state_dict.get("pending_questions", [])
        unified.user_responses = state_dict.get("user_responses", {})
    
    # Copy memory features if enabled
    if "memory" in features:
        unified.memory_matches = state_dict.get("memory_matches", [])
        unified.application_context = state_dict.get("application_context", {})
    
    # Copy streaming features if enabled
    if "streaming" in features:
        unified.is_streaming = state_dict.get("is_streaming", False)
        unified.current_chunk_index = state_dict.get("current_chunk_index", 0)
        unified.total_chunks = state_dict.get("total_chunks", 0)
        unified.chunk_results = state_dict.get("chunk_results", [])
    
    return unified


def unified_state_to_dict_update(unified: UnifiedState) -> Dict[str, Any]:
    """Convert UnifiedState changes back to dict for state update."""
    update = {
        "messages": unified.messages,
        "analysis_result": unified.analysis_result,
        "validation_status": unified.validation_status,
        "node_visits": unified.node_visits,
        "tool_calls": unified.tool_calls,
        "token_count": unified.token_count,
        "enabled_features": list(unified.features)
    }
    
    # Add feature-specific fields
    if unified.has_feature("interactive"):
        update.update({
            "user_interaction_required": unified.user_interaction_required,
            "pending_questions": unified.pending_questions,
            "user_responses": unified.user_responses
        })
    
    if unified.has_feature("memory"):
        update.update({
            "memory_matches": unified.memory_matches,
            "application_context": unified.application_context
        })
    
    if unified.has_feature("streaming"):
        update.update({
            "is_streaming": unified.is_streaming,
            "current_chunk_index": unified.current_chunk_index,
            "total_chunks": unified.total_chunks,
            "chunk_results": unified.chunk_results
        })
    
    return update


async def streaming_analyze_logs(state: Dict[str, Any]) -> Dict[str, Any]:
    """Wrapper for streaming analysis that handles TypedDict state."""
    # Convert to unified state
    unified = dict_to_unified_state(state)
    
    # Check if streaming is needed
    if unified.should_enable_streaming() and not unified.is_streaming:
        unified.enable_feature("streaming")
        unified.is_streaming = True
    
    if not unified.is_streaming:
        # Regular analysis for small logs
        return await original_enhanced_analyze(state)
    
    # Use streaming for large logs
    logger.info(f"Using streaming analysis for large log ({len(unified.log_content)} bytes)")
    
    # Create rate-limited analysis function
    from .circuit_breaker import get_circuit_breaker
    
    gemini_limiter = APIRateLimiters.gemini()
    analysis_circuit = get_circuit_breaker("analysis")
    
    @analysis_circuit.decorator
    async def analyze_chunk(chunk_content: str) -> Dict[str, Any]:
        """Analyze a single chunk with circuit breaker and rate limiting."""
        try:
            # Apply rate limiting
            await gemini_limiter.acquire()
            
            # Create temporary state for chunk analysis
            chunk_state = {
                "messages": [],
                "log_content": chunk_content,
                "log_metadata": state.get("log_metadata", {}),
                "enabled_features": ["streaming"]
            }
            
            # Analyze chunk
            result = await original_enhanced_analyze(chunk_state)
            return result.get("analysis_result", {})
            
        except RateLimitExceeded as e:
            logger.warning(f"Rate limit hit, waiting {e.retry_after}s")
            import asyncio
            await asyncio.sleep(e.retry_after)
            return await analyze_chunk(chunk_content)  # Retry
    
    try:
        # Stream and analyze
        aggregated_results = await stream_and_analyze_log(
            unified.log_content,
            analyze_chunk,
            chunk_size_mb=10,
            max_concurrent=3
        )
        
        # Update unified state
        unified.analysis_result = aggregated_results
        unified.chunk_results = aggregated_results.get("metadata", {}).get("chunk_results", [])
        unified.add_message(AIMessage(
            content=f"Completed streaming analysis of {aggregated_results['metadata']['chunks_processed']} chunks"
        ))
        
        # Convert back to dict update
        return unified_state_to_dict_update(unified)
        
    except CircuitBreakerOpen as e:
        logger.error(f"Circuit breaker open: {e}")
        unified.add_message(AIMessage(
            content="Analysis temporarily unavailable due to repeated failures. Please try again later."
        ))
        return unified_state_to_dict_update(unified)


def route_after_analysis(state: Dict[str, Any]) -> Literal["validate_analysis", "tools", "__end__"]:
    """Route after analysis using improved logic."""
    if not state.get("analysis_result"):
        return "__end__"
    
    # Check for tool calls in the last message
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
    
    # Validate if we have results
    if state.get("analysis_result"):
        return "validate_analysis"
    
    return "__end__"


def route_after_validation(state: Dict[str, Any]) -> Literal["specialized_analysis", "handle_user_input", "__end__"]:
    """Route after validation with support for specialized analyzers."""
    validation_status = state.get("validation_status")
    features = set(state.get("enabled_features", []))
    
    if validation_status == "valid":
        # Check if specialized analysis is needed
        if "specialized" in features and should_use_specialized_analyzer(state):
            return "specialized_analysis"
        return "__end__"
    
    elif validation_status == "needs_improvement":
        if "interactive" in features:
            return "handle_user_input"
        # Let LangGraph handle retry limits automatically
        return "specialized_analysis" if "specialized" in features else "__end__"
    
    return "__end__"


def should_use_specialized_analyzer(state: Dict[str, Any]) -> bool:
    """Determine if specialized analyzer should be used based on log content."""
    log_content = state.get("log_content", "")
    log_sample = log_content[:1000].lower()
    log_metadata = state.get("log_metadata", {})
    
    # Check for specific log types
    if "hdfs" in log_sample or "namenode" in log_sample or "datanode" in log_sample:
        log_metadata["detected_type"] = "hdfs"
        return True
    elif "security" in log_sample or "auth" in log_sample or "permission denied" in log_sample:
        log_metadata["detected_type"] = "security"
        return True
    elif "application" in log_sample or "webapp" in log_sample or "servlet" in log_sample:
        log_metadata["detected_type"] = "application"
        return True
    
    return False


async def specialized_analysis_router(state: Dict[str, Any]) -> Dict[str, Any]:
    """Route to specialized analyzers based on log type."""
    log_type = state.get("log_metadata", {}).get("detected_type", "general")
    
    logger.info(f"Routing to specialized analyzer for {log_type} logs")
    
    # Convert to unified state for specialized analyzers
    unified = dict_to_unified_state(state)
    
    # Import specialized analyzers dynamically
    if log_type == "hdfs":
        from ..subgraphs.hdfs_analyzer import analyze_hdfs_logs
        result = await analyze_hdfs_logs(unified)
    elif log_type == "security":
        from ..subgraphs.security_analyzer import analyze_security_logs
        result = await analyze_security_logs(unified)
    elif log_type == "application":
        from ..subgraphs.application_analyzer import analyze_application_logs
        result = await analyze_application_logs(unified)
    else:
        # Fallback to enhanced analysis
        result = await streaming_analyze_logs(state)
    
    # Merge results back into state
    if isinstance(result, dict):
        return result
    else:
        return unified_state_to_dict_update(unified)