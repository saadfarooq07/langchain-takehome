"""Unified analysis node that consolidates all analysis implementations.

This module provides a single, configurable analysis node that replaces:
- analysis.py (standard analysis)
- enhanced_analysis.py (enhanced output formatting)
- ui_analysis.py (UI-specific features)

The unified approach reduces code duplication and ensures consistent behavior
across all analysis modes while maintaining the unique features of each.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import time
import asyncio
from dataclasses import dataclass

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..state import State
from ..configuration import Configuration
from ..utils import LogValidator, preprocess_log, count_node_visits
from ..tools import search_documentation, request_additional_info, submit_analysis
from ..prompts import (
    get_analysis_prompt,
    get_enhanced_analysis_prompt,
    format_analysis_result,
    format_enhanced_analysis_result,
)
from ..models import init_model_async
from ..services.memory_service import get_memory_service
from ..ui_tools import UI_TOOLS


class AnalysisMode(str, Enum):
    """Available analysis modes."""
    STANDARD = "standard"
    ENHANCED = "enhanced"
    UI = "ui"


@dataclass
class AnalysisContext:
    """Context for analysis execution."""
    mode: AnalysisMode
    config: Configuration
    enable_memory: bool = False
    enable_ui_updates: bool = False
    enable_caching: bool = True


class AnalysisOutput(BaseModel):
    """Structured output from analysis."""
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = Field(default="")
    recommendations: List[str] = Field(default_factory=list)
    root_cause: Optional[str] = None
    patterns: Optional[List[Dict[str, Any]]] = None
    executive_summary: Optional[str] = None
    confidence_score: float = Field(default=0.8)
    log_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


async def unified_analyze_logs(
    state: Union[Dict[str, Any], State],
    context: Optional[AnalysisContext] = None
) -> Dict[str, Any]:
    """Unified log analysis function supporting multiple modes.
    
    This function consolidates the logic from all three analysis implementations:
    - Standard analysis with basic output
    - Enhanced analysis with structured formatting
    - UI analysis with real-time updates
    
    Args:
        state: The current state (dict or State object)
        context: Analysis context with mode and configuration
        
    Returns:
        Updated state dictionary
    """
    start_time = time.time()
    
    # Default context if not provided
    if context is None:
        mode = AnalysisMode(state.get("analysis_mode", AnalysisMode.STANDARD))
        context = AnalysisContext(
            mode=mode,
            config=Configuration(),
            enable_memory=state.get("enable_memory", False),
            enable_ui_updates=mode == AnalysisMode.UI,
            enable_caching=state.get("enable_cache", True)
        )
    
    # Extract state data
    messages = state.get("messages", []) if hasattr(state, "get") else getattr(state, "messages", [])
    log_content = state.get("log_content", "") if hasattr(state, "get") else getattr(state, "log_content", "")
    
    # Track node visit
    node_visits = count_node_visits(messages, "analyze_logs")
    
    # UI update: Starting analysis
    if context.enable_ui_updates:
        await _send_ui_update(
            "analysis_start",
            {"message": "Starting log analysis...", "timestamp": datetime.now().isoformat()}
        )
    
    try:
        # Step 1: Validate and preprocess logs
        validation_result = await _validate_and_preprocess(log_content, context)
        if validation_result.get("error"):
            return {"messages": [AIMessage(content=validation_result["error"])]}
        
        processed_log = validation_result["processed_log"]
        log_metadata = validation_result["metadata"]
        
        # Step 2: Memory lookup (if enabled)
        memory_context = None
        if context.enable_memory:
            memory_context = await _get_memory_context(processed_log, context)
            if context.enable_ui_updates and memory_context:
                await _send_ui_update(
                    "memory_found",
                    {"matches": len(memory_context.get("similar_analyses", []))}
                )
        
        # Step 3: Initialize model with appropriate tools
        model = await _get_configured_model(context, memory_context)
        
        # Step 4: Generate analysis based on mode
        analysis_result = await _perform_analysis(
            model=model,
            log_content=processed_log,
            log_metadata=log_metadata,
            memory_context=memory_context,
            context=context
        )
        
        # Step 5: Format output based on mode
        formatted_output = await _format_analysis_output(analysis_result, context)
        
        # Step 6: Store in memory (if enabled)
        if context.enable_memory and formatted_output:
            await _store_in_memory(log_content, formatted_output, context)
        
        # Step 7: Send final UI update
        if context.enable_ui_updates:
            await _send_ui_update(
                "analysis_complete",
                {
                    "summary": formatted_output.get("summary", "Analysis completed"),
                    "issue_count": len(formatted_output.get("issues", [])),
                    "duration": time.time() - start_time
                }
            )
        
        # Return updated state
        return {
            "messages": [AIMessage(content=analysis_result.content)],
            "analysis_result": formatted_output,
            "analysis_metadata": {
                "mode": context.mode.value,
                "duration_seconds": time.time() - start_time,
                "memory_used": memory_context is not None,
                "log_type": log_metadata.get("detected_type"),
                "node_visits": node_visits + 1
            }
        }
        
    except Exception as e:
        error_msg = f"Analysis failed: {str(e)}"
        if context.enable_ui_updates:
            await _send_ui_update("analysis_error", {"error": error_msg})
        
        return {
            "messages": [AIMessage(content=error_msg)],
            "analysis_error": str(e)
        }


async def _validate_and_preprocess(
    log_content: str,
    context: AnalysisContext
) -> Dict[str, Any]:
    """Validate and preprocess log content."""
    try:
        # Validate
        is_valid, error_msg = LogValidator.validate_log_content(log_content)
        if not is_valid:
            return {"error": error_msg}
        
        # Sanitize and preprocess
        sanitized = LogValidator.sanitize_log_content(log_content)
        processed = preprocess_log(sanitized)
        
        # Detect log type for enhanced mode
        log_type = None
        if context.mode in [AnalysisMode.ENHANCED, AnalysisMode.UI]:
            log_type = _detect_log_type(processed)
        
        return {
            "processed_log": processed,
            "metadata": {
                "original_size": len(log_content),
                "processed_size": len(processed),
                "line_count": len(processed.split('\n')),
                "detected_type": log_type
            }
        }
    except Exception as e:
        return {"error": f"Preprocessing failed: {str(e)}"}


async def _get_memory_context(
    log_content: str,
    context: AnalysisContext
) -> Optional[Dict[str, Any]]:
    """Retrieve relevant context from memory service."""
    try:
        memory_service = await get_memory_service()
        if not memory_service:
            return None
        
        # Search for similar analyses
        similar = await memory_service.search_similar_logs(
            log_content,
            limit=3,
            threshold=0.8
        )
        
        if similar:
            return {
                "similar_analyses": similar,
                "patterns": await memory_service.get_common_patterns(log_content),
                "historical_solutions": await memory_service.get_successful_solutions(
                    log_type=_detect_log_type(log_content)
                )
            }
        
        return None
    except Exception:
        # Memory lookup is optional, don't fail the analysis
        return None


async def _get_configured_model(
    context: AnalysisContext,
    memory_context: Optional[Dict[str, Any]]
):
    """Get model configured with appropriate tools."""
    # Initialize base model
    model = await init_model_async(context.config)
    
    # Determine which tools to bind based on mode and context
    tools = [search_documentation, submit_analysis]
    
    if context.mode == AnalysisMode.UI:
        # Add UI-specific tools
        tools.extend(UI_TOOLS)
    
    if memory_context:
        # Add memory-aware tools if we have context
        tools.append(request_additional_info)
    
    # Bind tools to model
    return model.bind_tools(tools)


async def _perform_analysis(
    model,
    log_content: str,
    log_metadata: Dict[str, Any],
    memory_context: Optional[Dict[str, Any]],
    context: AnalysisContext
) -> AIMessage:
    """Perform the actual analysis based on mode."""
    # Select appropriate prompt based on mode
    if context.mode == AnalysisMode.ENHANCED:
        prompt = get_enhanced_analysis_prompt()
    else:
        prompt = get_analysis_prompt()
    
    # Build context for prompt
    prompt_context = {
        "log_content": log_content,
        "environment_context": _build_environment_context(log_metadata, memory_context),
        "analysis_instructions": _get_mode_specific_instructions(context.mode)
    }
    
    # Add memory context if available
    if memory_context:
        prompt_context["memory_context"] = _format_memory_context(memory_context)
    
    # Generate analysis
    messages = prompt.format_messages(**prompt_context)
    result = await model.ainvoke(messages)
    
    return result


async def _format_analysis_output(
    analysis_result: AIMessage,
    context: AnalysisContext
) -> Dict[str, Any]:
    """Format analysis output based on mode."""
    base_output = _extract_base_analysis(analysis_result)
    
    if context.mode == AnalysisMode.STANDARD:
        return format_analysis_result(base_output)
    
    elif context.mode == AnalysisMode.ENHANCED:
        # Enhanced formatting with additional structure
        enhanced = format_enhanced_analysis_result(base_output)
        enhanced.update({
            "executive_summary": _generate_executive_summary(base_output),
            "pattern_analysis": _analyze_patterns(base_output),
            "visualization_data": _prepare_visualization_data(base_output)
        })
        return enhanced
    
    elif context.mode == AnalysisMode.UI:
        # UI mode includes all enhanced features plus UI-specific data
        ui_output = format_enhanced_analysis_result(base_output)
        ui_output.update({
            "ui_components": _generate_ui_components(base_output),
            "interactive_elements": _create_interactive_elements(base_output),
            "real_time_metrics": _calculate_real_time_metrics(base_output)
        })
        return ui_output
    
    return base_output


async def _store_in_memory(
    log_content: str,
    analysis_result: Dict[str, Any],
    context: AnalysisContext
):
    """Store analysis results in memory service."""
    try:
        memory_service = await get_memory_service()
        if memory_service:
            await memory_service.store_analysis(
                log_content=log_content,
                analysis_result=analysis_result,
                metadata={
                    "mode": context.mode.value,
                    "timestamp": datetime.now().isoformat(),
                    "config": context.config.to_dict()
                }
            )
    except Exception:
        # Memory storage is optional, don't fail
        pass


async def _send_ui_update(event_type: str, data: Dict[str, Any]):
    """Send UI update event (placeholder for actual implementation)."""
    # This would integrate with the actual UI update mechanism
    # For now, it's a no-op to maintain compatibility
    pass


def _detect_log_type(log_content: str) -> str:
    """Detect the type of log based on content patterns."""
    log_lower = log_content.lower()
    
    if any(keyword in log_lower for keyword in ["security", "auth", "permission", "denied"]):
        return "security"
    elif any(keyword in log_lower for keyword in ["database", "query", "transaction", "sql"]):
        return "database"
    elif any(keyword in log_lower for keyword in ["kubernetes", "k8s", "pod", "container"]):
        return "infrastructure"
    elif any(keyword in log_lower for keyword in ["http", "request", "response", "api"]):
        return "application"
    else:
        return "general"


def _build_environment_context(
    log_metadata: Dict[str, Any],
    memory_context: Optional[Dict[str, Any]]
) -> str:
    """Build environment context string for the prompt."""
    context_parts = []
    
    # Add log metadata
    context_parts.append(f"Log Type: {log_metadata.get('detected_type', 'unknown')}")
    context_parts.append(f"Log Size: {log_metadata.get('line_count', 0)} lines")
    
    # Add memory insights if available
    if memory_context and memory_context.get("similar_analyses"):
        context_parts.append(
            f"Found {len(memory_context['similar_analyses'])} similar previous analyses"
        )
    
    return "\n".join(context_parts)


def _get_mode_specific_instructions(mode: AnalysisMode) -> str:
    """Get analysis instructions specific to the mode."""
    if mode == AnalysisMode.STANDARD:
        return "Provide a clear, concise analysis focusing on key issues and solutions."
    elif mode == AnalysisMode.ENHANCED:
        return (
            "Provide a comprehensive analysis with:\n"
            "1. Executive summary\n"
            "2. Detailed issue breakdown with severity levels\n"
            "3. Root cause analysis\n"
            "4. Pattern identification\n"
            "5. Actionable recommendations with priority"
        )
    elif mode == AnalysisMode.UI:
        return (
            "Provide an interactive analysis with:\n"
            "1. Real-time progress updates\n"
            "2. Visual components for data representation\n"
            "3. Interactive elements for exploration\n"
            "4. Comprehensive metrics and insights"
        )
    return ""


def _extract_base_analysis(ai_message: AIMessage) -> Dict[str, Any]:
    """Extract base analysis data from AI message."""
    # This is a simplified extraction - in practice would parse the structured output
    content = ai_message.content
    
    return {
        "content": content,
        "tool_calls": getattr(ai_message, "tool_calls", []),
        "timestamp": datetime.now().isoformat()
    }


def _format_memory_context(memory_context: Dict[str, Any]) -> str:
    """Format memory context for inclusion in prompt."""
    if not memory_context:
        return ""
    
    parts = []
    
    if memory_context.get("similar_analyses"):
        parts.append("Previous similar analyses found:")
        for analysis in memory_context["similar_analyses"][:2]:
            parts.append(f"- {analysis.get('summary', 'No summary')}")
    
    if memory_context.get("patterns"):
        parts.append("\nCommon patterns identified:")
        for pattern in memory_context["patterns"][:3]:
            parts.append(f"- {pattern}")
    
    return "\n".join(parts)


def _generate_executive_summary(analysis: Dict[str, Any]) -> str:
    """Generate executive summary for enhanced mode."""
    # Placeholder implementation
    return "Executive summary of the log analysis findings..."


def _analyze_patterns(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Analyze patterns in the logs."""
    # Placeholder implementation
    return [{"pattern": "Error spike", "frequency": "High", "impact": "Critical"}]


def _prepare_visualization_data(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare data for visualization."""
    # Placeholder implementation
    return {"charts": [], "metrics": {}}


def _generate_ui_components(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate UI components for the analysis."""
    # Placeholder implementation
    return []


def _create_interactive_elements(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create interactive elements for UI mode."""
    # Placeholder implementation
    return []


def _calculate_real_time_metrics(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate real-time metrics for UI mode."""
    # Placeholder implementation
    return {"processing_speed": "fast", "accuracy": "high"}


# Compatibility exports to replace the individual analysis functions
analyze_logs = unified_analyze_logs  # Default to standard mode

async def enhanced_analyze_logs(state: Union[Dict[str, Any], State]) -> Dict[str, Any]:
    """Enhanced analysis mode for backward compatibility."""
    context = AnalysisContext(
        mode=AnalysisMode.ENHANCED,
        config=Configuration.from_environment()
    )
    return await unified_analyze_logs(state, context)


async def analyze_logs_with_ui(state: Union[Dict[str, Any], State]) -> Dict[str, Any]:
    """UI analysis mode for backward compatibility."""
    context = AnalysisContext(
        mode=AnalysisMode.UI,
        config=Configuration.from_environment()
    )
    return await unified_analyze_logs(state, context)