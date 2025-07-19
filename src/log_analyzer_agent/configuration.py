"""Configuration for the Log Analyzer Agent."""

import os
from typing import Optional, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, field_validator

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


class ModelConfig(BaseModel):
    """Configuration for a language model."""
    
    provider: str = Field(
        default="gemini",
        description="Model provider (gemini, groq, openai, etc.)"
    )
    model_name: str = Field(
        default="gemini-2.0-flash-exp",
        description="Model name/identifier"
    )
    temperature: float = Field(
        default=0.0,
        description="Model temperature",
        ge=0.0,
        le=2.0
    )
    api_key_env_var: Optional[str] = Field(
        default=None,
        description="Environment variable name for API key"
    )
    
    def get_model_string(self) -> str:
        """Get the model string in provider:model format."""
        return f"{self.provider}:{self.model_name}"
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        if self.api_key_env_var:
            return os.getenv(self.api_key_env_var)
        # Default environment variable names
        default_vars = {
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        return os.getenv(default_vars.get(self.provider))


class Configuration(BaseModel):
    """Configuration for the Log Analyzer Agent."""

    # Model configurations
    primary_model: ModelConfig = Field(
        default_factory=lambda: ModelConfig(
            provider="gemini",
            model_name="gemini-2.0-flash-exp",
            temperature=0.0,
            api_key_env_var="GEMINI_API_KEY"
        ),
        description="Primary model for log analysis"
    )
    
    orchestration_model: ModelConfig = Field(
        default_factory=lambda: ModelConfig(
            provider="groq",
            model_name="deepseek-r1-distill-llama-70b",
            temperature=0.3,
            api_key_env_var="GROQ_API_KEY"
        ),
        description="Model for orchestration and routing"
    )

    # Execution limits
    max_search_results: int = Field(
        default=3,
        description="Maximum number of search results to return",
        ge=1,
        le=10
    )

    max_analysis_iterations: int = Field(
        default=10,
        description="Maximum number of analysis iterations",
        ge=1,
        le=50
    )

    max_validation_retries: int = Field(
        default=3,
        description="Maximum number of validation retry attempts",
        ge=1,
        le=10
    )

    max_tool_calls: int = Field(
        default=20,
        description="Maximum total number of tool calls allowed",
        ge=1,
        le=100
    )

    # Feature flags
    enable_cache: bool = Field(
        default=True,
        description="Enable caching of analysis results"
    )
    
    enable_interactive: bool = Field(
        default=True,
        description="Enable interactive mode for user feedback"
    )
    
    enable_memory: bool = Field(
        default=False,
        description="Enable memory features (requires database)"
    )

    # Cache configuration
    cache_max_size: int = Field(
        default=100,
        description="Maximum number of cache entries",
        ge=1,
        le=1000
    )

    cache_ttl_seconds: int = Field(
        default=3600,  # 1 hour
        description="Time-to-live for cache entries in seconds",
        ge=60,
        le=86400  # Max 24 hours
    )

    # Prompt configuration
    prompt: ChatPromptTemplate = Field(
        default_factory=lambda: ChatPromptTemplate.from_template(DEFAULT_PROMPT),
        description="The prompt template to use for log analysis"
    )
    
    # Tool configuration
    tavily_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("TAVILY_API_KEY"),
        description="API key for Tavily search"
    )

    def validate_config(self) -> None:
        """Validate the configuration."""
        # Check API keys
        if not self.primary_model.get_api_key():
            raise ValueError(
                f"API key not found for primary model. "
                f"Please set {self.primary_model.api_key_env_var or 'GEMINI_API_KEY'}"
            )
        
        if not self.orchestration_model.get_api_key():
            raise ValueError(
                f"API key not found for orchestration model. "
                f"Please set {self.orchestration_model.api_key_env_var or 'GROQ_API_KEY'}"
            )
        
        # Check tool configuration
        if not self.tavily_api_key:
            print("Warning: Tavily API key not configured. Web search will be disabled.")

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "Configuration":
        """Extract configuration from a RunnableConfig object."""
        config = config or {}
        configurable = config.get("configurable", {})
        
        # Handle model string format (provider:model)
        if "model" in configurable:
            provider, model_name = configurable["model"].split(":", 1)
            configurable["primary_model"] = ModelConfig(
                provider=provider,
                model_name=model_name
            )
        
        # Extract relevant fields
        extracted = {}
        for key in ["max_search_results", "max_analysis_iterations", "enable_cache"]:
            if key in configurable:
                extracted[key] = configurable[key]
        
        return cls(**extracted)
    
    @classmethod
    def from_environment(cls) -> "Configuration":
        """Create configuration from environment variables."""
        return cls(
            primary_model=ModelConfig(
                provider=os.getenv("PRIMARY_MODEL_PROVIDER", "gemini"),
                model_name=os.getenv("PRIMARY_MODEL_NAME", "gemini-2.0-flash-exp"),
                temperature=float(os.getenv("PRIMARY_MODEL_TEMPERATURE", "0.0")),
            ),
            orchestration_model=ModelConfig(
                provider=os.getenv("ORCHESTRATION_MODEL_PROVIDER", "groq"),
                model_name=os.getenv("ORCHESTRATION_MODEL_NAME", "deepseek-r1-distill-llama-70b"),
                temperature=float(os.getenv("ORCHESTRATION_MODEL_TEMPERATURE", "0.3")),
            ),
            max_analysis_iterations=int(os.getenv("MAX_ANALYSIS_ITERATIONS", "10")),
            max_tool_calls=int(os.getenv("MAX_TOOL_CALLS", "20")),
            enable_cache=os.getenv("ENABLE_CACHE", "true").lower() == "true",
            enable_interactive=os.getenv("ENABLE_INTERACTIVE", "true").lower() == "true",
            enable_memory=os.getenv("ENABLE_MEMORY", "false").lower() == "true",
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for logging/debugging."""
        return {
            "primary_model": self.primary_model.get_model_string(),
            "orchestration_model": self.orchestration_model.get_model_string(),
            "limits": {
                "max_iterations": self.max_analysis_iterations,
                "max_tool_calls": self.max_tool_calls,
                "max_search_results": self.max_search_results,
            },
            "features": {
                "cache": self.enable_cache,
                "interactive": self.enable_interactive,
                "memory": self.enable_memory,
            }
        }


# Backward compatibility
def get_configuration(config: Optional[RunnableConfig] = None) -> Configuration:
    """Get configuration from RunnableConfig or defaults.
    
    This is for backward compatibility with existing code.
    """
    return Configuration.from_runnable_config(config)