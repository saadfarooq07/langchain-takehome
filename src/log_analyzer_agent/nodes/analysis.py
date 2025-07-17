"""Refactored log analysis node that adapts to available state fields."""

import json
import time
from typing import Any, Dict, Optional, cast
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore

from ..configuration import Configuration
from ..state import CoreState, InteractiveState, MemoryState
from ..tools import request_additional_info, search_documentation, submit_analysis
from ..utils import format_environment_context, init_model_async, preprocess_log
from ..validation import LogValidator
from ..services.memory_service import MemoryService


def has_memory_features(state: CoreState) -> bool:
    """Check if state has memory features enabled."""
    return isinstance(state, MemoryState) or hasattr(state, 'user_id')


def has_interactive_features(state: CoreState) -> bool:
    """Check if state has interactive features enabled."""
    return isinstance(state, (InteractiveState, MemoryState)) or hasattr(state, 'user_response')


async def analyze_logs(
    state: CoreState, *, config: Optional[RunnableConfig] = None, store: BaseStore = None
) -> Dict[str, Any]:
    """Analyze log content with adaptive feature support.
    
    This node adapts to the available state fields, enabling memory
    and interactive features only when the state supports them.
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Validate log content first
    is_valid, error_msg, sanitized_info = LogValidator.validate_log_content(state.log_content)
    if not is_valid:
        # Return error as analysis result
        return {
            "messages": [AIMessage(content=f"Error: {error_msg}")],
            "analysis_result": {
                "error": error_msg,
                "issues": [{
                    "type": "validation_error",
                    "description": error_msg,
                    "severity": "critical"
                }],
                "suggestions": ["Please provide a valid log file that meets the size and format requirements"]
            },
            "needs_user_input": False,
        }
    
    # Sanitize and preprocess the log
    sanitized_log = LogValidator.sanitize_log_content(state.log_content)
    processed_log = preprocess_log(sanitized_log)
    
    # Initialize memory context if available
    memory_context = ""
    state_updates = {}
    
    # Only use memory features if state supports it and store is available
    if has_memory_features(state) and store and getattr(state, 'user_id', None):
        memory_service = MemoryService(store)
        user_id = state.user_id
        application_name = getattr(state, 'application_name', 'unknown')
        
        try:
            # Search for similar issues
            similar_issues = await memory_service.search_similar_issues(
                user_id, application_name, processed_log
            )
            
            # Get application context
            app_context = await memory_service.get_application_context(
                user_id, application_name
            )
            
            # Get user preferences
            user_prefs = await memory_service.get_user_preferences(user_id)
            
            # Update state with memory context
            state_updates = {
                "similar_issues": similar_issues,
                "user_preferences": user_prefs,
                "memory_search_count": getattr(state, 'memory_search_count', 0) + 3
            }
            
            # Create memory context for the prompt
            memory_context = f"""
            
MEMORY CONTEXT:
Previous Similar Issues:
{json.dumps(similar_issues, indent=2) if similar_issues else "No similar issues found"}

Application Context:
{json.dumps(app_context, indent=2) if app_context else "No application context available"}

User Preferences:
{json.dumps(user_prefs, indent=2) if user_prefs else "No user preferences set"}
            """
        except Exception as e:
            # Memory features failed, continue without them
            print(f"Memory features unavailable: {e}")
    
    # Format environment context if available
    environment_context = ""
    if getattr(state, "environment_details", None):
        environment_context = format_environment_context(state.environment_details)
    
    # Prepare the prompt
    prompt = configuration.prompt.format(
        log_content=processed_log,
        environment_context=environment_context + memory_context
    )
    
    # Create messages list
    messages = [HumanMessage(content=prompt)] + getattr(state, "messages", None)
    
    # Initialize model with tools
    raw_model = await init_model_async(config)
    
    # Determine which tools to bind based on state capabilities
    tools = [search_documentation, submit_analysis]
    if has_interactive_features(state):
        tools.append(request_additional_info)
    
    model = raw_model.bind_tools(tools, tool_choice="any")
    
    response = cast(AIMessage, await model.ainvoke(messages))
    
    # Check if analysis is complete or more info needed
    analysis_result = None
    needs_user_input = False
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "submit_analysis":
                analysis_result = tool_call["args"]
            elif tool_call["name"] == "request_additional_info" and has_interactive_features(state):
                needs_user_input = True
    
    # Store analysis result in memory if complete and memory features available
    if analysis_result and has_memory_features(state) and store and getattr(state, 'user_id', None):
        try:
            performance_metrics = {
                "response_time": time.time() - getattr(state, 'start_time', time.time()),
                "memory_searches": getattr(state, 'memory_search_count', 0),
                "similar_issues_found": len(state_updates.get('similar_issues', [])),
                "tokens_used": len(str(messages)) + len(str(response))  # Rough estimate
            }
            
            await memory_service.store_analysis_result(
                state.user_id,
                getattr(state, 'application_name', 'unknown'),
                state.log_content,
                analysis_result,
                performance_metrics
            )
        except Exception as e:
            print(f"Error storing analysis result in memory: {e}")
    
    # Build response with only the fields the state supports
    response_dict = {
        "messages": [response],
        "analysis_result": analysis_result,
    }
    
    # Only add interactive fields if state supports them
    if has_interactive_features(state):
        response_dict["needs_user_input"] = needs_user_input
    
    # Add memory updates if applicable
    response_dict.update(state_updates)
    
    return response_dict