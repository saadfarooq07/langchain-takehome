"""Simplified configuration for the Log Analyzer Agent."""

from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

DEFAULT_PROMPT = """You are an expert log analyzer. Your task is to analyze the provided log content and:
1. Identify issues, errors, or anomalies in the logs
2. Provide accurate explanations of what the issues mean
3. Suggest solutions or next steps
4. Reference relevant documentation where applicable

{environment_context}

Always be specific in your analysis and recommendations. If you need additional information to provide a complete analysis, 
make sure to request it clearly with instructions on how the user can retrieve it.

Log Content:
{log_content}
"""


class Configuration(BaseModel):
    """Simplified configuration for the Log Analyzer Agent."""

    model: str = Field(
        default="gemini:gemini-2.5-flash",
        description="The model to use for log analysis",
    )

    max_search_results: int = Field(
        default=3,
        description="Maximum number of search results to return",
        ge=1,
        le=10,
    )

    max_analysis_iterations: int = Field(
        default=10,
        description="Maximum number of analysis iterations to prevent infinite loops",
        ge=1,
        le=50,
    )

    max_validation_retries: int = Field(
        default=3,
        description="Maximum number of validation retry attempts",
        ge=1,
        le=10,
    )

    max_tool_calls: int = Field(
        default=20,
        description="Maximum total number of tool calls allowed",
        ge=1,
        le=100,
    )

    prompt: ChatPromptTemplate = Field(
        default_factory=lambda: ChatPromptTemplate.from_template(DEFAULT_PROMPT),
        description="The prompt template to use for log analysis",
    )

    # Cache Configuration
    enable_cache: bool = Field(
        default=True,
        description="Enable caching of analysis results",
    )

    cache_max_size: int = Field(
        default=100,
        description="Maximum number of cache entries",
        ge=1,
        le=1000,
    )

    cache_ttl_seconds: int = Field(
        default=3600,  # 1 hour
        description="Time-to-live for cache entries in seconds",
        ge=60,
        le=86400,  # Max 24 hours
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Extract configuration from a RunnableConfig object."""
        config = config or {}
        configurable = config.get("configurable", {})
        return cls(**configurable)
