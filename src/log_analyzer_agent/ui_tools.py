"""UI-enhanced tools for the log analyzer agent using LangGraph's Generative UI capabilities."""

from typing import Dict, Any, List, Optional, Annotated
from langchain_core.tools import tool
from langgraph.graph.ui import push_ui_message
from langchain_core.messages import AIMessage
import uuid

from .state_typeddict import State
from .tools import InjectedState, CommandSuggestionEngine, get_cache, Configuration


@tool
async def submit_analysis_with_ui(
    analysis: Dict[str, Any],
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Submit the final analysis with rich UI components.

    Args:
        analysis: A dictionary containing:
            - "issues": List of identified issues, each with description and severity
            - "explanations": Detailed explanations of what each issue means
            - "suggestions": Recommended solutions or next steps for each issue
            - "documentation_references": Relevant documentation links for further reading
            - "diagnostic_commands": Recommended commands to run for further investigation
            - "summary": Optional high-level summary of the analysis

    Returns:
        A confirmation that the analysis was submitted
    """
    # Generate command suggestions if not already included
    if "diagnostic_commands" not in analysis:
        engine = CommandSuggestionEngine()
        environment_info = (
            state.environment_info if hasattr(state, "environment_info") else {}
        )
        analysis["diagnostic_commands"] = engine.suggest_commands(
            environment_info=environment_info, issues=analysis.get("issues", [])
        )

    # Create an AI message for the analysis
    message = AIMessage(
        id=str(uuid.uuid4()),
        content=f"Analysis complete. Found {len(analysis.get('issues', []))} issues with {len(analysis.get('suggestions', []))} recommendations.",
    )

    # Store in state for backward compatibility
    state.analysis_result = analysis
    
    # Emit UI component with structured data
    push_ui_message(
        "analysis_results",
        analysis,
        message=message
    )

    # Also emit individual issue components for granular interaction
    for i, issue in enumerate(analysis.get("issues", [])):
        issue_message = AIMessage(
            id=str(uuid.uuid4()),
            content=f"Issue {i+1}: {issue.get('type', 'Unknown')}"
        )
        push_ui_message(
            "issue",
            issue,
            message=issue_message
        )
    
    # Cache the analysis result if enabled
    from langchain_core.runnables import RunnableConfig
    config = state.get("config", {}) if hasattr(state, "get") else {}
    configuration = Configuration.from_runnable_config(config)
    
    if configuration.enable_cache:
        cache = get_cache()
        log_content = getattr(state, "log_content", None)
        environment_details = getattr(state, "environment_details", None)
        
        if log_content:
            cache.put(log_content, analysis, environment_details)
    
    return "Analysis completed and submitted successfully with rich UI components."


@tool
async def emit_progress_update(
    step: str,
    progress: int,
    details: Optional[str] = None,
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Emit a progress update during analysis.

    Args:
        step: Current analysis step
        progress: Progress percentage (0-100)
        details: Optional additional details

    Returns:
        Confirmation message
    """
    message = AIMessage(
        id=str(uuid.uuid4()),
        content=f"Analysis progress: {step}"
    )

    push_ui_message(
        "progress",
        {
            "step": step,
            "progress": progress,
            "details": details,
            "timestamp": str(uuid.uuid4())  # Use as unique identifier
        },
        message=message
    )

    return f"Progress update emitted: {step} ({progress}%)"


@tool
async def emit_issue_found(
    issue: Dict[str, Any],
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Emit an individual issue as soon as it's found during analysis.

    Args:
        issue: Issue details containing type, description, severity, etc.

    Returns:
        Confirmation message
    """
    message = AIMessage(
        id=str(uuid.uuid4()),
        content=f"Issue detected: {issue.get('type', 'Unknown issue')}"
    )

    push_ui_message(
        "issue",
        issue,
        message=message
    )

    return f"Issue emitted: {issue.get('type', 'Unknown')}"


@tool
async def emit_suggestion(
    suggestion: str,
    category: Optional[str] = None,
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Emit a suggestion during analysis.

    Args:
        suggestion: The suggestion text
        category: Optional category for the suggestion

    Returns:
        Confirmation message
    """
    message = AIMessage(
        id=str(uuid.uuid4()),
        content=f"Suggestion: {suggestion[:50]}..."
    )

    push_ui_message(
        "suggestion",
        {
            "text": suggestion,
            "category": category,
            "timestamp": str(uuid.uuid4())
        },
        message=message
    )

    return f"Suggestion emitted: {category or 'General'}"


# Enhanced tool list including UI tools
UI_TOOLS = [
    submit_analysis_with_ui,
    emit_progress_update,
    emit_issue_found,
    emit_suggestion,
]
