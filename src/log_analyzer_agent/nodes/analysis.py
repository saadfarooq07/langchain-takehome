"""Log analysis node for the Log Analyzer Agent."""

from typing import Any, Dict, Optional, cast
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode

from ..configuration import Configuration
from ..state import State
from ..tools import request_additional_info, search_documentation, submit_analysis
from ..utils import format_environment_context, init_model_async, preprocess_log
from ..validation import LogValidator


async def analyze_logs(
    state: State, *, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Analyze log content using the primary model.
    
    This is the main analysis node that:
    1. Validates and preprocesses the log content
    2. Formats environment context if available
    3. Invokes the LLM with tools
    4. Processes the response
    """
    configuration = Configuration.from_runnable_config(config)
    
    # Validate log content first
    is_valid, error_msg, sanitized_info = LogValidator.validate_log_content(state["log_content"])
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
    sanitized_log = LogValidator.sanitize_log_content(state["log_content"])
    processed_log = preprocess_log(sanitized_log)
    
    # Format environment context if available
    environment_context = ""
    if state.get("environment_details"):
        environment_context = format_environment_context(state["environment_details"])
    
    # Prepare the prompt
    prompt = configuration.prompt.format(
        log_content=processed_log,
        environment_context=environment_context
    )
    
    # Create messages list
    messages = [HumanMessage(content=prompt)] + state.get("messages", [])
    
    # Initialize model with tools
    raw_model = await init_model_async(config)
    model = raw_model.bind_tools(
        [search_documentation, request_additional_info, submit_analysis], 
        tool_choice="any"
    )
    
    response = cast(AIMessage, await model.ainvoke(messages))
    
    # Check if analysis is complete or more info needed
    analysis_result = None
    needs_user_input = False
    
    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "submit_analysis":
                analysis_result = tool_call["args"]
            elif tool_call["name"] == "request_additional_info":
                needs_user_input = True
    
    return {
        "messages": [response],
        "analysis_result": analysis_result,
        "needs_user_input": needs_user_input,
    }