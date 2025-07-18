"""Validation node for checking analysis quality."""

import json
from typing import Any, Dict, Optional, cast
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from ..state import CoreState
from ..utils import init_model_async
from .. import prompts


class AnalysisQualityCheck(BaseModel):
    """Model for validating analysis completeness."""

    is_complete: bool = Field(description="Whether the analysis is complete and ready.")
    improvement_suggestions: Optional[str] = Field(
        description="Suggestions for improvement if not complete.",
        default=None,
    )


async def validate_analysis(
    state: CoreState, *, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """Validate the quality and completeness of the analysis.

    Uses the orchestrator model to check if the analysis is ready
    to be presented to the user.
    """
    if not getattr(state, "analysis_result", None):
        return {
            "messages": [
                HumanMessage(
                    content="Analysis is not complete. Please continue analyzing."
                )
            ]
        }

    last_message = state.messages[-1]
    if not isinstance(last_message, AIMessage):
        raise ValueError("Expected last message to be an AI message with tool calls.")

    # Format prompt for quality check
    checker_prompt = prompts.ANALYSIS_CHECKER_PROMPT.format(
        analysis=json.dumps(state.analysis_result, indent=2)
    )

    # Use orchestrator model for validation
    raw_model = await init_model_async(config)
    bound_model = raw_model.with_structured_output(AnalysisQualityCheck)
    response = cast(AnalysisQualityCheck, await bound_model.ainvoke(checker_prompt))

    # Create appropriate tool message based on validation result
    tool_message = ToolMessage(
        tool_call_id=last_message.tool_calls[0]["id"],
        content=(
            "Analysis validated and complete."
            if response.is_complete
            else f"Analysis needs improvement: {response.improvement_suggestions}"
        ),
        name="submit_analysis",
        status="success" if response.is_complete else "error",
    )

    return {"messages": [tool_message]}
