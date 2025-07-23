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
from ..prompt_registry import get_prompt_registry
# Import functions directly from utils.py to avoid circular imports
from ..utils import format_environment_context, preprocess_log

# Import init_model_async directly from utils.py
from ..utils import init_model_async
from ..model_pool import pooled_model
from ..cache_utils.cache import get_cache
from ..validation import LogValidator
from ..services.memory_service import MemoryService

from dotenv import load_dotenv
load_dotenv()

# Import persistence utilities
from ..persistence_utils import (
    log_debug, log_warning, log_error,
    get_workflow_timestamp, generate_analysis_id
)

def has_memory_features(state: CoreState) -> bool:
    """Check if state has memory features enabled."""
    return isinstance(state, MemoryState) or hasattr(state, "user_id")


def has_interactive_features(state: CoreState) -> bool:
    """Check if state has interactive features enabled."""
    return isinstance(state, (InteractiveState, MemoryState)) or hasattr(
        state, "user_response"
    )


async def analyze_logs(
    state: CoreState,
    *,
    config: Optional[RunnableConfig] = None,
    store: BaseStore = None,
) -> Dict[str, Any]:
    """Analyze log content with adaptive feature support and recursion prevention.

    This node adapts to the available state fields, enabling memory
    and interactive features only when the state supports them.
    """
    configuration = Configuration.from_runnable_config(config)

    # Check if we've exceeded iteration limits
    messages = getattr(state, "messages", [])
    ai_message_count = sum(1 for msg in messages if isinstance(msg, AIMessage))
    if ai_message_count >= configuration.max_analysis_iterations:
        # Force submit analysis to terminate gracefully
        return {
            "messages": [
                AIMessage(
                    content="Maximum analysis iterations reached. Submitting current analysis.",
                    tool_calls=[
                        {
                            "id": f"submit_{ai_message_count}",
                            "name": "submit_analysis",
                            "args": {
                                "issues": [
                                    {
                                        "type": "iteration_limit",
                                        "description": "Analysis terminated due to iteration limit",
                                        "severity": "info",
                                    }
                                ],
                                "suggestions": ["Review the analysis results"],
                                "documentation_references": [],
                            },
                        }
                    ],
                )
            ],
            "needs_user_input": False,
        }

    # Check cache if enabled
    cached_result = None
    if configuration.enable_cache:
        cache = get_cache()
        # Configure cache with settings from configuration
        cache.max_size = configuration.cache_max_size
        cache.ttl_seconds = configuration.cache_ttl_seconds
        
        environment_details = getattr(state, "environment_details", None)
        cached_result = cache.get(state.log_content, environment_details)
    
    if cached_result is not None:
        # Return cached result
        return {
            "messages": [
                AIMessage(
                    content="Retrieved analysis from cache.",
                    tool_calls=[
                        {
                            "id": f"submit_cached_{ai_message_count}",
                            "name": "submit_analysis",
                            "args": cached_result,
                        }
                    ],
                )
            ],
            "analysis_result": cached_result,
            "needs_user_input": False,
        }

    # Validate log content
    is_valid, error_msg, sanitized_info = LogValidator.validate_log_content(
        state.log_content
    )
    if not is_valid:
        # Return error as analysis result
        return {
            "messages": [AIMessage(content=f"Error: {error_msg}")],
            "analysis_result": {
                "error": error_msg,
                "issues": [
                    {
                        "type": "validation_error",
                        "description": error_msg,
                        "severity": "critical",
                    }
                ],
                "suggestions": [
                    "Please provide a valid log file that meets the size and format requirements"
                ],
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
    if has_memory_features(state) and store and getattr(state, "user_id", None):
        memory_service = MemoryService(store)
        user_id = state.user_id
        application_name = getattr(state, "application_name", "unknown")

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
                "memory_search_count": getattr(state, "memory_search_count", 0) + 3,
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
            await log_warning(f"Memory features unavailable: {e}")

    # Format environment context if available
    environment_context = ""
    if getattr(state, "environment_details", None):
        environment_context = format_environment_context(state.environment_details)

    # Get prompt from registry or use legacy prompt
    if configuration.prompt_config.use_langsmith and configuration.prompt is None:
        # Use LangSmith prompt
        registry = get_prompt_registry()
        prompt_name = configuration.get_prompt_name_for_node("analyze_logs")
        prompt_version = configuration.get_prompt_version("main")
        
        try:
            prompt_template = await registry.get_prompt(prompt_name, version=prompt_version)
            prompt_content = prompt_template.format(
                log_content=processed_log,
                environment_context=environment_context + memory_context,
            )
        except Exception as e:
            # Fallback to default prompt if LangSmith fails
            from ..prompts import main_prompt_template
            prompt_content = main_prompt_template.format(
                log_content=processed_log,
                environment_context=environment_context + memory_context,
            )
    else:
        # Use legacy prompt
        from ..configuration import DEFAULT_PROMPT
        prompt_template = configuration.prompt or DEFAULT_PROMPT
        prompt_content = prompt_template.format(
            log_content=processed_log,
            environment_context=environment_context + memory_context,
        )

    # Create messages list
    existing_messages = getattr(state, "messages", [])
    # Filter out any messages with empty content
    filtered_messages = [msg for msg in existing_messages if msg.content.strip()]
    # Append new message to the end (chronological order)
    messages = list(filtered_messages) + [HumanMessage(content=prompt_content)]

    # Use pooled model with tools
    async with pooled_model(configuration.primary_model) as raw_model:
        # Determine which tools to bind based on state capabilities
        tools = [search_documentation, submit_analysis]
        if has_interactive_features(state):
            tools.append(request_additional_info)

        # Bind tools - model can choose to use them
        model = raw_model.bind_tools(tools, tool_choice="auto")

        response = cast(AIMessage, await model.ainvoke(messages))

    # Check if analysis is complete or more info needed
    analysis_result = None
    needs_user_input = False

    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "submit_analysis":
                analysis_result = tool_call["args"]
                # Handle case where args might be a JSON string
                if isinstance(analysis_result, str):
                    try:
                        import json
                        analysis_result = json.loads(analysis_result)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, keep as string and let validation handle it
                        pass
            elif tool_call[
                "name"
            ] == "request_additional_info" and has_interactive_features(state):
                needs_user_input = True
    
    # Fallback: If no submit_analysis tool call but response has content, 
    # treat it as incomplete analysis that needs tool usage
    if not analysis_result and not needs_user_input and response.content:
        # The model provided analysis in text form but didn't call submit_analysis
        # Add a message to force tool usage on next iteration
        await log_warning("Model provided analysis without calling submit_analysis tool")
        
        # Add a system message to force tool usage
        from langchain_core.messages import SystemMessage
        system_message = SystemMessage(
            content="You MUST use the submit_analysis tool to provide your analysis. "
                   "Do not provide analysis in text form. Use the tool with a properly structured dictionary."
        )
        
        # Update the response to include this system message
        response_dict = {
            "messages": [response, system_message],
            "analysis_result": None,  # Explicitly set to None to trigger validation
        }
        
        if has_interactive_features(state):
            response_dict["needs_user_input"] = False
            
        return response_dict

    # Store analysis result in memory if complete and memory features available
    if (
        analysis_result
        and has_memory_features(state)
        and store
        and getattr(state, "user_id", None)
    ):
        try:
            # Use consistent timestamp from state
            state_dict = {"start_time": getattr(state, "start_time", None)}
            workflow_timestamp = await get_workflow_timestamp(state_dict)
            
            performance_metrics = {
                "response_time": workflow_timestamp - getattr(state, "start_time", workflow_timestamp),
                "memory_searches": getattr(state, "memory_search_count", 0),
                "similar_issues_found": len(state_updates.get("similar_issues", [])),
                "tokens_used": len(str(messages)) + len(str(response)),  # Rough estimate
            }

            await memory_service.store_analysis_result(
                state.user_id,
                getattr(state, "application_name", "unknown"),
                state.log_content,
                analysis_result,
                performance_metrics,
                state=state_dict,
            )
        except Exception as e:
            await log_error(f"Error storing analysis result in memory: {e}")

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