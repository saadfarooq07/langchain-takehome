"""Enhanced analysis node with Generative UI capabilities."""

from typing import Dict, Any, List, Optional, Union, cast
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from dataclasses import dataclass
from datetime import datetime
import json
import re

from ..ui_tools import (
    submit_analysis_with_ui,
    emit_progress_update,
    emit_issue_found,
    emit_suggestion,
)
from ..state_typeddict import State
from ..tools import search_documentation, request_additional_info
from ..utils import count_node_visits, count_tool_calls
from ..configuration import Configuration
from ..services.memory_service import get_memory_service


@dataclass
class AnalysisProgress:
    """Track analysis progress for UI updates."""
    current_step: str = "Initializing"
    progress: int = 0
    issues_found: List[Dict[str, Any]] = None
    suggestions: List[str] = None
    
    def __post_init__(self):
        if self.issues_found is None:
            self.issues_found = []
        if self.suggestions is None:
            self.suggestions = []


async def analyze_logs_with_ui(state: State) -> Dict[str, Any]:
    """Enhanced log analysis with real-time UI updates."""
    config = cast(RunnableConfig, state.get("config", {}))
    configuration = Configuration.from_runnable_config(config)
    
    # Initialize progress tracking
    progress = AnalysisProgress()
    
    # Emit initial progress
    await emit_progress_update.ainvoke(
        {"step": "Starting analysis", "progress": 10},
        config={"metadata": {"state": state}}
    )
    
    # Get the appropriate model
    from ..models import get_model
    model = get_model(configuration.analysis_model)
    
    # Bind tools for structured analysis
    tools = [
        submit_analysis_with_ui,
        emit_progress_update,
        emit_issue_found,
        emit_suggestion,
        search_documentation,
        request_additional_info,
    ]
    
    model_with_tools = model.bind_tools(tools)
    
    # Progress update: Preparing analysis
    progress.current_step = "Preparing log analysis"
    progress.progress = 20
    await emit_progress_update.ainvoke(
        {"step": progress.current_step, "progress": progress.progress},
        config={"metadata": {"state": state}}
    )
    
    # Prepare the analysis prompt
    log_content = state.get("log_content", "")
    
    # Get memory context if enabled
    memory_context = ""
    if configuration.enable_memory:
        try:
            memory_service = get_memory_service()
            if hasattr(state, "application_name") and state.application_name:
                memories = await memory_service.search_memories(
                    query=f"Application: {state.application_name}",
                    limit=3
                )
                if memories:
                    memory_context = "\n\nRelevant context from previous analyses:\n"
                    memory_context += "\n".join([f"- {m.content}" for m in memories])
        except Exception as e:
            print(f"Memory service error: {e}")
    
    # Progress update: Analyzing content
    progress.current_step = "Analyzing log content"
    progress.progress = 40
    await emit_progress_update.ainvoke(
        {"step": progress.current_step, "progress": progress.progress},
        config={"metadata": {"state": state}}
    )
    
    # Create enhanced analysis prompt
    analysis_prompt = f"""
You are an expert log analyzer. Analyze the following log content and provide insights.

IMPORTANT: Use the available tools to emit real-time updates as you analyze:
1. Use `emit_progress_update` to show analysis progress
2. Use `emit_issue_found` for each issue you identify 
3. Use `emit_suggestion` for each recommendation you have
4. Use `submit_analysis_with_ui` to provide the final comprehensive analysis

Log Content:
{log_content}

{memory_context}

Please analyze this log content step by step:

1. First, scan for obvious errors, warnings, and critical issues
2. Identify patterns that might indicate problems
3. Provide detailed explanations for each issue found
4. Suggest specific remediation steps
5. Recommend diagnostic commands for further investigation
6. Reference relevant documentation when applicable

Use the tools to provide real-time updates as you work through the analysis.
Start by updating progress to 60% and begin your detailed analysis.
"""

    # Invoke the model with the analysis prompt
    messages = [HumanMessage(content=analysis_prompt)]
    
    # Add any previous conversation context
    if hasattr(state, "messages") and state.messages:
        # Include recent conversation context but prioritize the analysis task
        recent_messages = state.messages[-3:] if len(state.messages) > 3 else state.messages
        messages = list(recent_messages) + messages
    
    try:
        # Stream the analysis with tool calls
        response = await model_with_tools.ainvoke(messages, config=config)
        
        # Process any tool calls in the response
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # The model made tool calls - process them
            tool_messages = []
            
            for tool_call in response.tool_calls:
                try:
                    # Execute the tool call
                    if tool_call['name'] == 'submit_analysis_with_ui':
                        # Final analysis submission
                        await submit_analysis_with_ui.ainvoke(
                            tool_call['args'],
                            config={"metadata": {"state": state}}
                        )
                    elif tool_call['name'] == 'emit_progress_update':
                        await emit_progress_update.ainvoke(
                            tool_call['args'],
                            config={"metadata": {"state": state}}
                        )
                    elif tool_call['name'] == 'emit_issue_found':
                        await emit_issue_found.ainvoke(
                            tool_call['args'],
                            config={"metadata": {"state": state}}
                        )
                    elif tool_call['name'] == 'emit_suggestion':
                        await emit_suggestion.ainvoke(
                            tool_call['args'],
                            config={"metadata": {"state": state}}
                        )
                    
                    # Create tool message for the response
                    tool_messages.append(
                        ToolMessage(
                            content=f"Tool {tool_call['name']} executed successfully",
                            tool_call_id=tool_call.get('id', ''),
                        )
                    )
                except Exception as e:
                    tool_messages.append(
                        ToolMessage(
                            content=f"Error executing {tool_call['name']}: {str(e)}",
                            tool_call_id=tool_call.get('id', ''),
                        )
                    )
            
            # Add tool messages to the conversation
            new_messages = [response] + tool_messages
        else:
            # No tool calls - fallback to regular analysis
            new_messages = [response]
            
            # Emit a fallback completion update
            await emit_progress_update.ainvoke(
                {"step": "Analysis completed", "progress": 100},
                config={"metadata": {"state": state}}
            )
    
    except Exception as e:
        # Handle errors gracefully
        error_message = f"Error during analysis: {str(e)}"
        new_messages = [AIMessage(content=error_message)]
        
        # Emit error state
        await emit_progress_update.ainvoke(
            {"step": "Analysis failed", "progress": 0, "details": error_message},
            config={"metadata": {"state": state}}
        )
    
    # Update visit count
    count_node_visits(state, "analyze_logs_with_ui")
    
    # Store memory if enabled
    if configuration.enable_memory and hasattr(state, "application_name") and state.application_name:
        try:
            memory_service = get_memory_service()
            # Create a summary for memory storage
            summary = f"Log analysis for {state.application_name}: "
            if hasattr(state, "analysis_result") and state.analysis_result:
                issues_count = len(state.analysis_result.get("issues", []))
                summary += f"Found {issues_count} issues"
            else:
                summary += "Analysis completed"
            
            await memory_service.store_memory(
                content=summary,
                metadata={
                    "application": state.application_name,
                    "timestamp": str(datetime.now()),
                    "type": "analysis_summary"
                }
            )
        except Exception as e:
            print(f"Memory storage error: {e}")
    
    return {"messages": new_messages}


# Alias for backward compatibility
analyze_logs_ui = analyze_logs_with_ui
