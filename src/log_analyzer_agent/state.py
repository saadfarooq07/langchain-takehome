"""State definitions for the Log Analyzer Agent.


State is the interface between the graph and end user as well as the
data model used internally by the graph.
"""

import operator
from dataclasses import dataclass, field
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


@dataclass(kw_only=True)
class InputState:
    """Input state defines the interface between the graph and the user (external API)."""

    log_content: str
    "The log content to be analyzed."

    environment_details: Optional[Dict[str, Any]] = field(default=None)
    "Optional details about the software and runtime environment."


@dataclass(kw_only=True)
class State(InputState):
    """State for the Log Analyzer Agent.
    
    This defines the structure of data passed between nodes, default values,
    and reducers that determine how to apply updates to the state.
    """

    messages: Annotated[List[BaseMessage], add_messages] = field(default_factory=list)
    """
    Messages track the primary execution state of the agent.
    """

    analysis_result: Optional[Dict[str, Any]] = field(default=None)
    "The current analysis result for the log content, including issues, suggestions, and reference documentation."

    follow_up_requests: List[Dict[str, Any]] = field(default_factory=list)
    "Requests for additional information needed from the user to complete analysis."
    
    needs_user_input: bool = field(default=False)
    "Flag indicating whether the agent is awaiting user input for follow-up questions."

    loop_step: Annotated[int, operator.add] = field(default=0)
    "Counter to track iterations through the workflow."


@dataclass(kw_only=True)
class OutputState:
    """The response object for the end user."""

    analysis_result: Dict[str, Any]
    """
    A dictionary containing the analyzed log information,
    identified issues, suggested solutions, and documentation references.
    """
    
    follow_up_requests: Optional[List[Dict[str, Any]]] = None
    "Optional requests for additional information needed to complete or refine the analysis."