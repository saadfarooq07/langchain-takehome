"""Simplified improved graph with all enhancements built-in.

This module provides a streamlined implementation with all improvements:
- Streaming for large logs
- Specialized analyzers
- Circuit breaker and rate limiting
- All features enabled by default
"""

import asyncio
from typing import Dict, Any, Literal, Optional, List
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage
import logging

from .state_typeddict import State
from .streaming import stream_and_analyze_log
from .nodes.enhanced_analysis import enhanced_analyze_logs
from .nodes.validation import validate_analysis
from .nodes.user_input import handle_user_input
from .tools import search_documentation, request_additional_info, submit_analysis
from .cycle_detector import CycleDetector
from .cache import BoundedCache
from .core.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from .core.rate_limiter import RateLimiter, RateLimitConfig, RateLimitExceeded

logger = logging.getLogger(__name__)

# Initialize components
cache = BoundedCache(max_size=100, ttl_seconds=300)
cycle_detector = CycleDetector(max_simple_loops=3)

# Circuit breakers
analysis_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=60.0,
    name="analysis"
)

# Rate limiters
gemini_limiter = RateLimiter(
    config=RateLimitConfig(calls_per_minute=60, burst_size=10),
    name="gemini"
)


async def analyze_logs_with_streaming(state: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced analyze logs with automatic streaming for large files."""
    log_content = state.get("log_content", "")
    log_size = len(log_content.encode('utf-8'))
    
    # Auto-enable streaming for large logs (>10MB)
    if log_size > 10 * 1024 * 1024:
        logger.info(f"Large log detected ({log_size} bytes), using streaming")
        return await _streaming_analysis(state)
    
    # Check cache for small logs
    cache_key = f"analysis_{hash(log_content)}"
    cached = cache.get(cache_key)
    if cached:
        logger.info("Returning cached analysis")
        return {"analysis_result": cached}
    
    # Regular analysis with circuit breaker
    try:
        result = await analysis_breaker.call_async(enhanced_analyze_logs, state)
        
        # Cache successful results
        if result.get("analysis_result"):
            cache.put(cache_key, result["analysis_result"])
        
        return result
        
    except CircuitBreakerOpen:
        logger.error("Analysis circuit breaker is open")
        return {
            "messages": [AIMessage(content="Analysis service temporarily unavailable. Please try again later.")],
            "analysis_result": None
        }


async def _streaming_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Process large logs using streaming."""
    
    async def analyze_chunk(chunk_content: str) -> Dict[str, Any]:
        """Analyze a single chunk with rate limiting."""
        try:
            # Apply rate limiting
            await gemini_limiter.acquire()
            
            # Create chunk state
            chunk_state = {
                "messages": [],
                "log_content": chunk_content,
                "log_metadata": state.get("log_metadata", {})
            }
            
            # Analyze chunk
            result = await enhanced_analyze_logs(chunk_state)
            return result.get("analysis_result", {})
            
        except RateLimitExceeded as e:
            logger.warning(f"Rate limit hit, waiting {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            return await analyze_chunk(chunk_content)
    
    # Stream and analyze
    aggregated = await stream_and_analyze_log(
        state.get("log_content", ""),
        analyze_chunk,
        chunk_size_mb=10,
        max_concurrent=3
    )
    
    return {
        "analysis_result": aggregated,
        "messages": [AIMessage(content=f"Completed streaming analysis of {aggregated['metadata']['chunks_processed']} chunks")]
    }


def route_after_analysis(state: Dict[str, Any]) -> Literal["validate_analysis", "tools", "__end__"]:
    """Route after analysis with cycle detection."""
    # Add to cycle detector
    cycle_detector.add_transition("analyze_logs", "route", state)
    
    if cycle_detector.should_break_cycle():
        logger.warning("Breaking analysis cycle")
        return "__end__"
    
    # Check for analysis result
    if not state.get("analysis_result"):
        return "__end__"
    
    # Check for tool calls
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
    
    return "validate_analysis"


def route_after_validation(state: Dict[str, Any]) -> Literal["specialized_analysis", "analyze_logs", "__end__"]:
    """Route after validation."""
    validation_status = state.get("validation_status")
    
    if validation_status == "valid":
        # Check if we should use specialized analyzer
        if _should_use_specialized_analyzer(state):
            return "specialized_analysis"
        return "__end__"
    
    elif validation_status == "needs_improvement":
        # Retry with specialized analyzer if available
        if _should_use_specialized_analyzer(state):
            return "specialized_analysis"
        return "analyze_logs"
    
    return "__end__"


def _should_use_specialized_analyzer(state: Dict[str, Any]) -> bool:
    """Check if specialized analyzer should be used."""
    log_content = state.get("log_content", "")
    log_sample = log_content[:1000].lower()
    metadata = state.get("log_metadata", {})
    
    # Don't use specialized if already tried
    if metadata.get("specialized_used"):
        return False
    
    # Detect log type
    if any(term in log_sample for term in ["hdfs", "namenode", "datanode"]):
        metadata["detected_type"] = "hdfs"
        return True
    elif any(term in log_sample for term in ["failed login", "authentication", "permission denied", "unauthorized"]):
        metadata["detected_type"] = "security"
        return True
    elif any(term in log_sample for term in ["http", "error", "exception", "servlet", "api"]):
        metadata["detected_type"] = "application"
        return True
    
    return False


async def specialized_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run specialized analysis based on detected log type."""
    log_type = state.get("log_metadata", {}).get("detected_type", "general")
    
    logger.info(f"Running specialized {log_type} analyzer")
    
    # Mark as used to prevent loops
    state.setdefault("log_metadata", {})["specialized_used"] = True
    
    # Import and run appropriate analyzer
    try:
        if log_type == "hdfs":
            from .subgraphs.hdfs_analyzer import analyze_hdfs_logs
            # Convert state format
            from .core.unified_state import UnifiedState
            unified = UnifiedState(
                log_content=state.get("log_content", ""),
                messages=state.get("messages", []),
                log_metadata=state.get("log_metadata", {})
            )
            result = await analyze_hdfs_logs(unified)
            
        elif log_type == "security":
            from .subgraphs.security_analyzer import analyze_security_logs
            from .core.unified_state import UnifiedState
            unified = UnifiedState(
                log_content=state.get("log_content", ""),
                messages=state.get("messages", []),
                log_metadata=state.get("log_metadata", {})
            )
            result = await analyze_security_logs(unified)
            
        elif log_type == "application":
            from .subgraphs.application_analyzer import analyze_application_logs
            from .core.unified_state import UnifiedState
            unified = UnifiedState(
                log_content=state.get("log_content", ""),
                messages=state.get("messages", []),
                log_metadata=state.get("log_metadata", {})
            )
            result = await analyze_application_logs(unified)
            
        else:
            # Fallback to enhanced analysis
            result = await enhanced_analyze_logs(state)
        
        return result
        
    except Exception as e:
        logger.error(f"Specialized analyzer failed: {e}")
        # Fallback to regular analysis
        return await enhanced_analyze_logs(state)


def route_after_tools(state: Dict[str, Any]) -> Literal["validate_analysis", "analyze_logs", "__end__"]:
    """Route after tool execution."""
    # Check if we have results to validate
    if state.get("analysis_result"):
        return "validate_analysis"
    
    # Check iteration limits
    messages = state.get("messages", [])
    if len(messages) > 50:  # Simple limit
        return "__end__"
    
    return "analyze_logs"


# Create the improved graph
workflow = StateGraph(State)

# Add all nodes
workflow.add_node("analyze_logs", analyze_logs_with_streaming)
workflow.add_node("validate_analysis", validate_analysis)
workflow.add_node("specialized_analysis", specialized_analysis)
workflow.add_node("handle_user_input", handle_user_input)

# Add tools
tools = [search_documentation, request_additional_info, submit_analysis]
tool_node = ToolNode(tools)
workflow.add_node("tools", tool_node)

# Define edges
workflow.add_edge(START, "analyze_logs")

# Conditional routing
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
        "specialized_analysis": "specialized_analysis",
        "analyze_logs": "analyze_logs",
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

# Fixed edges
workflow.add_edge("specialized_analysis", "validate_analysis")
workflow.add_edge("handle_user_input", "analyze_logs")

# Compile the graph
improved_graph = workflow.compile()

# Export
__all__ = ["improved_graph"]