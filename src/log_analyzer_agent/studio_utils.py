"""Utilities for better LangGraph Studio integration."""

from typing import Any, Dict, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage


def serialize_message(msg: BaseMessage) -> Dict[str, Any]:
    """Serialize a message for cleaner display in Studio."""
    base_dict = {
        "type": msg.__class__.__name__,
        "content": msg.content if hasattr(msg, 'content') else str(msg),
    }
    
    # Add role-specific fields
    if isinstance(msg, HumanMessage):
        base_dict["role"] = "human"
    elif isinstance(msg, AIMessage):
        base_dict["role"] = "assistant"
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            base_dict["tool_calls"] = [
                {
                    "name": tc.get("name", "unknown"),
                    "args": tc.get("args", {})
                }
                for tc in msg.tool_calls
            ]
    elif isinstance(msg, SystemMessage):
        base_dict["role"] = "system"
    elif isinstance(msg, ToolMessage):
        base_dict["role"] = "tool"
        base_dict["tool_name"] = getattr(msg, 'name', 'unknown')
        base_dict["status"] = getattr(msg, 'status', 'unknown')
    
    # Truncate long content for readability
    if len(base_dict["content"]) > 300:
        base_dict["content"] = base_dict["content"][:297] + "..."
    
    return base_dict


def clean_state_for_studio(state: Dict[str, Any]) -> Dict[str, Any]:
    """Clean state dictionary for better display in LangGraph Studio."""
    cleaned = {}
    
    for key, value in state.items():
        if key == "messages" and isinstance(value, list):
            # Serialize messages for readability
            cleaned[key] = [
                serialize_message(msg) if isinstance(msg, BaseMessage) else msg
                for msg in value
            ]
        elif key == "analysis_result" and isinstance(value, dict):
            # Ensure analysis result is clean
            cleaned[key] = {
                "issues": value.get("issues", [])[:3],  # Show first 3 issues
                "suggestions": value.get("suggestions", [])[:3],  # Show first 3 suggestions
                "has_more": len(value.get("issues", [])) > 3 or len(value.get("suggestions", [])) > 3
            }
        elif key == "log_content" and isinstance(value, str) and len(value) > 500:
            # Truncate long log content
            cleaned[key] = value[:497] + "..."
        elif key == "environment_details" and isinstance(value, dict):
            # Keep environment details but ensure it's serializable
            cleaned[key] = {k: str(v) for k, v in value.items()}
        elif value is None or isinstance(value, (str, int, float, bool, list, dict)):
            # Keep simple types as-is
            cleaned[key] = value
        else:
            # Convert complex types to string
            cleaned[key] = str(value)
    
    return cleaned