"""Centralized configuration management with validation.

This module provides a type-safe, validated configuration system for the log analyzer agent.
All configuration is centralized here with proper validation and environment variable support.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, List, Union
from enum import Enum
from pathlib import Path
import json
import yaml
from functools import lru_cache


class ModelProvider(Enum):
    """Supported model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    AZURE = "azure"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ModelConfig:
    """Configuration for a language model."""
    provider: ModelProvider
    model_name: str
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    timeout: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    api_key_env_var: Optional[str] = None
    
    def __post_init__(self):
        """Validate model configuration."""
        if not 0 <= self.temperature <= 2:
            raise ValueError(f"Temperature must be between 0 and 2, got {self.temperature}")
        if self.timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {self.timeout}")
        if self.retry_attempts < 0:
            raise ValueError(f"Retry attempts must be non-negative, got {self.retry_attempts}")
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from environment."""
        if self.api_key_env_var:
            return os.getenv(self.api_key_env_var)
        # Default environment variable names
        default_vars = {
            ModelProvider.OPENAI: "OPENAI_API_KEY",
            ModelProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
            ModelProvider.GOOGLE: "GEMINI_API_KEY",
            ModelProvider.GROQ: "GROQ_API_KEY",
            ModelProvider.AZURE: "AZURE_API_KEY",
        }
        return os.getenv(default_vars.get(self.provider))


@dataclass
class ExecutionLimits:
    """Limits for graph execution."""
    max_iterations: int = 50
    max_tool_calls: int = 20
    max_validation_attempts: int = 3
    max_log_size_mb: int = 10
    max_execution_time_seconds: int = 300
    
    def __post_init__(self):
        """Validate limits."""
        for field_name, value in self.__dict__.items():
            if value <= 0:
                raise ValueError(f"{field_name} must be positive, got {value}")


@dataclass
class FeatureFlags:
    """Feature flags for the agent."""
    enable_memory: bool = False
    enable_interactive: bool = True
    enable_streaming: bool = False
    enable_caching: bool = True
    enable_telemetry: bool = False
    
    def to_set(self) -> Set[str]:
        """Convert enabled features to a set."""
        features = set()
        if self.enable_memory:
            features.add("memory")
        if self.enable_interactive:
            features.add("interactive")
        if self.enable_streaming:
            features.add("streaming")
        if self.enable_caching:
            features.add("caching")
        if self.enable_telemetry:
            features.add("telemetry")
        return features


@dataclass
class DatabaseConfig:
    """Database configuration for memory features."""
    url: Optional[str] = None
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False
    
    def __post_init__(self):
        """Load from environment if not provided."""
        if not self.url:
            self.url = os.getenv("DATABASE_URL")
    
    @property
    def is_configured(self) -> bool:
        """Check if database is properly configured."""
        return bool(self.url)


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[Path] = None
    max_file_size_mb: int = 100
    backup_count: int = 5
    enable_json_logging: bool = False


@dataclass
class ToolConfig:
    """Configuration for tools."""
    tavily_api_key: Optional[str] = field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))
    search_max_results: int = 5
    search_timeout: int = 30
    enable_web_search: bool = True
    enable_command_suggestions: bool = True
    
    @property
    def has_search_capability(self) -> bool:
        """Check if search is properly configured."""
        return bool(self.tavily_api_key and self.enable_web_search)


@dataclass
class Config:
    """Main configuration class."""
    # Model configurations
    primary_model: ModelConfig
    orchestration_model: ModelConfig
    validation_model: Optional[ModelConfig] = None
    
    # Execution settings
    execution_limits: ExecutionLimits = field(default_factory=ExecutionLimits)
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)
    
    # Infrastructure
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    
    # Prompts configuration
    prompt_version: str = "1.0.0"
    custom_prompts_path: Optional[Path] = None
    
    def validate(self) -> None:
        """Validate the entire configuration."""
        # Check API keys are available
        if not self.primary_model.get_api_key():
            raise ValueError(f"API key not found for primary model ({self.primary_model.provider})")
        if not self.orchestration_model.get_api_key():
            raise ValueError(f"API key not found for orchestration model ({self.orchestration_model.provider})")
        
        # Check memory feature requirements
        if self.feature_flags.enable_memory and not self.database.is_configured:
            raise ValueError("Memory feature requires database configuration")
        
        # Check tool requirements
        if self.tools.enable_web_search and not self.tools.has_search_capability:
            raise ValueError("Web search enabled but Tavily API key not configured")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "primary_model": {
                "provider": self.primary_model.provider.value,
                "model_name": self.primary_model.model_name,
                "temperature": self.primary_model.temperature,
            },
            "orchestration_model": {
                "provider": self.orchestration_model.provider.value,
                "model_name": self.orchestration_model.model_name,
                "temperature": self.orchestration_model.temperature,
            },
            "features": list(self.feature_flags.to_set()),
            "limits": {
                "max_iterations": self.execution_limits.max_iterations,
                "max_tool_calls": self.execution_limits.max_tool_calls,
            },
        }


class ConfigBuilder:
    """Builder for creating configurations."""
    
    @staticmethod
    def from_environment() -> Config:
        """Build configuration from environment variables."""
        return Config(
            primary_model=ModelConfig(
                provider=ModelProvider.GOOGLE,
                model_name="gemini-2.0-flash-exp",
                temperature=0.0,
                api_key_env_var="GEMINI_API_KEY",
            ),
            orchestration_model=ModelConfig(
                provider=ModelProvider.GROQ,
                model_name="deepseek-r1-distill-llama-70b",
                temperature=0.3,
                api_key_env_var="GROQ_API_KEY",
            ),
            execution_limits=ExecutionLimits(
                max_iterations=int(os.getenv("MAX_ITERATIONS", "50")),
                max_tool_calls=int(os.getenv("MAX_TOOL_CALLS", "20")),
            ),
            feature_flags=FeatureFlags(
                enable_memory=os.getenv("ENABLE_MEMORY", "false").lower() == "true",
                enable_interactive=os.getenv("ENABLE_INTERACTIVE", "true").lower() == "true",
                enable_streaming=os.getenv("ENABLE_STREAMING", "false").lower() == "true",
            ),
        )
    
    @staticmethod
    def from_file(path: Path) -> Config:
        """Load configuration from file (JSON or YAML)."""
        with open(path) as f:
            if path.suffix == ".json":
                data = json.load(f)
            elif path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")
        
        return ConfigBuilder._from_dict(data)
    
    @staticmethod
    def _from_dict(data: Dict[str, Any]) -> Config:
        """Build configuration from dictionary."""
        # Parse model configs
        primary_model = ModelConfig(
            provider=ModelProvider(data["primary_model"]["provider"]),
            model_name=data["primary_model"]["model_name"],
            temperature=data["primary_model"].get("temperature", 0.0),
        )
        
        orchestration_model = ModelConfig(
            provider=ModelProvider(data["orchestration_model"]["provider"]),
            model_name=data["orchestration_model"]["model_name"],
            temperature=data["orchestration_model"].get("temperature", 0.3),
        )
        
        # Parse other configs
        limits = data.get("execution_limits", {})
        execution_limits = ExecutionLimits(
            max_iterations=limits.get("max_iterations", 50),
            max_tool_calls=limits.get("max_tool_calls", 20),
        )
        
        features = data.get("feature_flags", {})
        feature_flags = FeatureFlags(
            enable_memory=features.get("enable_memory", False),
            enable_interactive=features.get("enable_interactive", True),
            enable_streaming=features.get("enable_streaming", False),
        )
        
        return Config(
            primary_model=primary_model,
            orchestration_model=orchestration_model,
            execution_limits=execution_limits,
            feature_flags=feature_flags,
        )
    
    @staticmethod
    def for_testing() -> Config:
        """Create a minimal configuration for testing."""
        return Config(
            primary_model=ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                temperature=0.0,
            ),
            orchestration_model=ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                temperature=0.0,
            ),
            feature_flags=FeatureFlags(
                enable_memory=False,
                enable_interactive=False,
                enable_streaming=False,
                enable_telemetry=False,
            ),
            execution_limits=ExecutionLimits(
                max_iterations=10,
                max_tool_calls=5,
            ),
        )


# Global configuration instance (lazy loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        # Try to load from file first
        config_path = os.getenv("LOG_ANALYZER_CONFIG")
        if config_path and Path(config_path).exists():
            _config = ConfigBuilder.from_file(Path(config_path))
        else:
            # Fall back to environment variables
            _config = ConfigBuilder.from_environment()
        
        # Validate configuration
        _config.validate()
    
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    config.validate()
    _config = config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None