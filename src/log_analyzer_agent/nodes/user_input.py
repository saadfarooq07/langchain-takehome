"""Refactored user input handling node."""

from typing import Any, Dict, Optional
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from ..state import InteractiveState
from ..configuration import Configuration


async def handle_user_input(
    state: InteractiveState, *, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Handle user input for interactive sessions.
    
    This node is only added to the graph when interactive features are enabled.
    It processes user responses to requests for additional information.
    """
    # Check if we have a pending request
    last_message = getattr(state, "messages", None)[-1] if getattr(state, "messages", None) else None
    
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        # No pending request, return empty update
        return {
            "messages": [],
            "needs_user_input": False,
        }
    
    # Find the request_additional_info tool call
    request_tool_call = None
    for tool_call in last_message.tool_calls:
        if tool_call["name"] == "request_additional_info":
            request_tool_call = tool_call
            break
    
    if not request_tool_call:
        # No request for additional info found
        return {
            "messages": [],
            "needs_user_input": False,
        }
    
    # Extract request details
    request_info = request_tool_call["args"]["request"]
    
    # Check if we have a user response
    user_response = getattr(state, 'user_response', '')
    
    if not user_response:
        # Still waiting for user input
        return {
            "messages": [],
            "needs_user_input": True,
            "pending_request": request_info,
        }
    
    # Process the user response
    tool_message = ToolMessage(
        content=f"User provided additional information: {user_response}",
        tool_call_id=request_tool_call["id"],
        status="success"
    )
    
    # Create a new human message with the additional context
    human_message = HumanMessage(
        content=f"""Based on the additional information provided:

User response: {user_response}

Please continue with the log analysis incorporating this new information."""
    )
    
    # Build response
    response = {
        "messages": [tool_message, human_message],
        "needs_user_input": False,
        "user_response": "",  # Clear the response
    }
    
    # Add additional context if state supports it
    if hasattr(state, 'additional_context'):
        response["additional_context"] = {
            "request": request_info,
            "response": user_response
        }
    
    return response