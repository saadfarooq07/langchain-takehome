"""Validation node for checking analysis quality."""

import json
from typing import Any, Dict, Optional, cast
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from ..state import CoreState
from ..utils import init_model_async
from ..model_pool import pooled_model
from ..configuration import Configuration
from ..prompt_registry import get_prompt_registry
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
        # If no AI message, skip validation
        return {
            "validation_status": "valid",
            "messages": []
        }

    # Get configuration
    configuration = Configuration.from_runnable_config(config)
    
    # Get prompt from registry or use legacy prompt
    if configuration.prompt_config.use_langsmith:
        registry = get_prompt_registry()
        prompt_name = configuration.get_prompt_name_for_node("validate_analysis")
        prompt_version = configuration.get_prompt_version("validation")
        
        try:
            prompt_template = await registry.get_prompt(prompt_name, version=prompt_version)
            checker_prompt = prompt_template.format(
                analysis=json.dumps(state.analysis_result, indent=2)
            )
        except Exception as e:
            # Fallback to default prompt
            checker_prompt = prompts.ANALYSIS_CHECKER_PROMPT.format(
                analysis=json.dumps(state.analysis_result, indent=2)
            )
    else:
        # Use legacy prompt
        checker_prompt = prompts.ANALYSIS_CHECKER_PROMPT.format(
            analysis=json.dumps(state.analysis_result, indent=2)
        )

    # Use pooled orchestrator model for validation
    async with pooled_model(config) as raw_model:
        bound_model = raw_model.with_structured_output(AnalysisQualityCheck)
        response = cast(AnalysisQualityCheck, await bound_model.ainvoke(checker_prompt))

    # Create appropriate message based on validation result
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        # If there was a tool call, create a tool message
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
    else:
        # If no tool call (e.g., enhanced analysis), just return validation status
        return {
            "validation_status": "valid" if response.is_complete else "invalid",
            "messages": []
        }
