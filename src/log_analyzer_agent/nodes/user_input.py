"""User input handling node."""

import json
from typing import Any, Dict, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from ..state import State


def handle_user_input(
    state: State, *, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Process user input for follow-up requests.
    
    This node is triggered when the agent needs additional information from the user.
    It processes the pending request and the user's response.
    """
    # Get the last message which should contain the request for additional info
    messages = state.get("messages", [])
    last_ai_message = None
    
    # Find the last AI message with tool calls
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            last_ai_message = msg
            break
    
    if not last_ai_message:
        return {
            "needs_user_input": False,
            "messages": [
                HumanMessage(content="No pending information request found. Continuing analysis...")
            ]
        }
    
    # Extract the request details
    request_info = None
    for tool_call in last_ai_message.tool_calls:
        if tool_call["name"] == "request_additional_info":
            request_info = tool_call["args"]["request"]
            break
    
    if not request_info:
        return {
            "needs_user_input": False,
            "messages": [
                HumanMessage(content="No specific information request found. Continuing analysis...")
            ]
        }
    
    # Get user input from the state
    user_response = state.get("user_response", "")
    
    if not user_response:
        # If no user response is provided, prompt for it
        prompt_message = f"""
Additional information needed:

Question: {request_info.get('question', 'Unknown question')}
Reason: {request_info.get('reason', 'Not specified')}
How to retrieve: {request_info.get('how_to_retrieve', 'Not specified')}

Please provide the requested information:
"""
        return {
            "needs_user_input": True,
            "pending_request": request_info,
            "messages": [
                AIMessage(content=prompt_message)
            ]
        }
    
    # Process the user response
    response_message = f"""
User provided additional information:

Original request: {request_info.get('question', 'Unknown question')}
User response: {user_response}

This information will be incorporated into the analysis.
"""
    
    # Clear the user response and mark that we no longer need input
    return {
        "needs_user_input": False,
        "user_response": "",  # Clear the response
        "messages": [
            HumanMessage(content=response_message)
        ],
        "additional_context": {
            "user_provided_info": {
                "question": request_info.get('question', ''),
                "response": user_response
            }
        }
    }