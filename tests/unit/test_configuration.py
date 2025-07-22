"""
Unit tests for configuration management in the Log Analyzer Agent.
"""

import pytest
import os
from unittest.mock import patch, Mock
from typing import Dict, Any

from src.log_analyzer_agent.configuration import Configuration, ModelConfig, PromptConfiguration


class TestModelConfig:
    """Test the ModelConfig class."""
    
    def test_default_model_config(self):
        """Test default ModelConfig values."""
        config = ModelConfig()
        
        assert config.provider == "gemini"
        assert config.model_name == "gemini-1.5-flash"
        assert config.temperature == 0.0
        assert config.api_key_env_var is None
    
    def test_custom_model_config(self):
        """Test ModelConfig with custom values."""
        config = ModelConfig(
            provider="groq",
            model_name="mixtral-8x7b",
            temperature=0.5,
            api_key_env_var="GROQ_API_KEY"
        )
        
        assert config.provider == "groq"
        assert config.model_name == "mixtral-8x7b"
        assert config.temperature == 0.5
        assert config.api_key_env_var == "GROQ_API_KEY"
    
    def test_get_model_string(self):
        """Test get_model_string method."""
        config = ModelConfig(provider="gemini", model_name="gemini-2.5-flash")
        assert config.get_model_string() == "gemini:gemini-2.5-flash"
        
        config = ModelConfig(provider="groq", model_name="mixtral-8x7b")
        assert config.get_model_string() == "groq:mixtral-8x7b"
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_get_api_key_with_env_var(self):
        """Test get_api_key with explicit environment variable."""
        config = ModelConfig(provider="gemini", api_key_env_var="GEMINI_API_KEY")
        assert config.get_api_key() == "test_key"
    
    @patch.dict(os.environ, {"GROQ_API_KEY": "groq_key"})
    def test_get_api_key_default_mapping(self):
        """Test get_api_key with default provider mapping."""
        config = ModelConfig(provider="groq")
        assert config.get_api_key() == "groq_key"


class TestConfiguration:
    """Test the Configuration class."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = Configuration()
        
        assert config.model is None  # Backward compatibility field
        assert config.primary_model.provider == "gemini"
        assert config.primary_model.model_name == "gemini-1.5-flash"
        assert config.orchestration_model.provider == "groq"
        assert config.orchestration_model.model_name == "deepseek-r1-distill-llama-70b"
        assert config.max_analysis_iterations == 10
        assert config.max_search_results == 3
        assert config.enable_cache is True
        assert config.enable_interactive is True
        assert config.enable_memory is False
        assert config.cache_max_size == 100
        assert config.cache_ttl_seconds == 3600
    
    def test_custom_configuration(self):
        """Test configuration with custom values."""
        primary_model = ModelConfig(provider="gemini", model_name="gemini-ultra")
        orchestration_model = ModelConfig(provider="groq", model_name="mixtral-8x7b")
        
        config = Configuration(
            primary_model=primary_model,
            orchestration_model=orchestration_model,
            max_analysis_iterations=5,
            max_search_results=5,
            enable_cache=False,
            enable_interactive=False,
            enable_memory=True,
            cache_max_size=50,
            cache_ttl_seconds=1800
        )
        
        assert config.primary_model.model_name == "gemini-ultra"
        assert config.orchestration_model.model_name == "mixtral-8x7b"
        assert config.max_analysis_iterations == 5
        assert config.max_search_results == 5
        assert config.enable_cache is False
        assert config.enable_interactive is False
        assert config.enable_memory is True
        assert config.cache_max_size == 50
        assert config.cache_ttl_seconds == 1800
    
    def test_from_runnable_config_none(self):
        """Test from_runnable_config with None input."""
        config = Configuration.from_runnable_config(None)
        
        assert config.model == "gemini:gemini-1.5-flash"
        assert config.primary_model.provider == "gemini"
        assert config.max_analysis_iterations == 10
    
    def test_from_runnable_config_empty(self):
        """Test from_runnable_config with empty config."""
        config = Configuration.from_runnable_config({})
        
        assert config.model == "gemini:gemini-1.5-flash"
        assert config.primary_model.provider == "gemini"
        assert config.max_analysis_iterations == 10
    
    def test_from_runnable_config_with_values(self):
        """Test from_runnable_config with custom values."""
        runnable_config = {
            "configurable": {
                "model": "gemini:gemini-ultra",
                "max_analysis_iterations": 15,
                "max_search_results": 7,
                "enable_cache": False
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        
        assert config.model == "gemini:gemini-ultra"
        assert config.primary_model.provider == "gemini"
        assert config.primary_model.model_name == "gemini-ultra"
        assert config.max_analysis_iterations == 15
        assert config.max_search_results == 7
        assert config.enable_cache is False
    
    def test_from_runnable_config_partial_values(self):
        """Test from_runnable_config with partial values."""
        runnable_config = {
            "configurable": {
                "model": "groq:mixtral-8x7b",
                "max_analysis_iterations": 8
            }
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        
        assert config.model == "groq:mixtral-8x7b"
        assert config.primary_model.provider == "groq"
        assert config.primary_model.model_name == "mixtral-8x7b"
        assert config.max_analysis_iterations == 8
        # Other values should be defaults
        assert config.max_search_results == 3
    
    def test_configuration_validation_boundaries(self):
        """Test configuration validation with boundary values."""
        # Test minimum values
        config = Configuration(
            max_analysis_iterations=1,
            max_search_results=1,
            max_validation_retries=1,  # Minimum is 1
            cache_max_size=1,
            cache_ttl_seconds=60
        )
        
        assert config.max_analysis_iterations == 1
        assert config.max_search_results == 1
        assert config.max_validation_retries == 1
        assert config.cache_max_size == 1
        assert config.cache_ttl_seconds == 60
        
        # Test maximum values
        config = Configuration(
            max_analysis_iterations=50,
            max_search_results=10,
            max_validation_retries=10,
            cache_max_size=1000,
            cache_ttl_seconds=86400
        )
        
        assert config.max_analysis_iterations == 50
        assert config.max_search_results == 10
        assert config.max_validation_retries == 10
        assert config.cache_max_size == 1000
        assert config.cache_ttl_seconds == 86400
    
    def test_configuration_model_names(self):
        """Test configuration with various model names."""
        models = [
            ("gemini", "gemini-2.5-flash"),
            ("gemini", "gemini-ultra"),
            ("groq", "mixtral-8x7b"),
            ("openai", "gpt-4")
        ]
        
        for provider, model_name in models:
            primary_model = ModelConfig(provider=provider, model_name=model_name)
            config = Configuration(primary_model=primary_model)
            assert config.primary_model.provider == provider
            assert config.primary_model.model_name == model_name
    
    def test_configuration_feature_flags(self):
        """Test configuration feature flags."""
        config = Configuration(
            enable_cache=False,
            enable_interactive=False,
            enable_memory=True
        )
        
        assert not config.enable_cache
        assert not config.enable_interactive
        assert config.enable_memory
    
    def test_configuration_cache_settings(self):
        """Test configuration cache settings."""
        config = Configuration(
            cache_max_size=200,
            cache_ttl_seconds=7200
        )
        
        assert config.cache_max_size == 200
        assert config.cache_ttl_seconds == 7200
    
    @patch.dict(os.environ, {"TAVILY_API_KEY": "test_tavily_key"})
    def test_configuration_api_keys(self):
        """Test configuration API key handling."""
        config = Configuration()
        assert config.tavily_api_key == "test_tavily_key"
    
    def test_configuration_prompt_config(self):
        """Test configuration prompt configuration."""
        config = Configuration()
        
        assert isinstance(config.prompt_config, PromptConfiguration)
        assert config.prompt_config.use_langsmith is True
        assert config.prompt_config.cache_prompts is True
        assert "main" in config.prompt_config.prompt_versions
    
    def test_get_prompt_name_for_node(self):
        """Test get_prompt_name_for_node method."""
        config = Configuration()
        
        assert config.get_prompt_name_for_node("analyze_logs") == "main"
        assert config.get_prompt_name_for_node("validate_analysis") == "validation"
        assert config.get_prompt_name_for_node("handle_user_input") == "followup"
        assert config.get_prompt_name_for_node("search_documentation") == "doc-search"
        assert config.get_prompt_name_for_node("unknown_node") == "main"
    
    def test_get_prompt_version(self):
        """Test get_prompt_version method."""
        config = Configuration()
        
        assert config.get_prompt_version("main") == "latest"
        assert config.get_prompt_version("validation") == "latest"
        assert config.get_prompt_version("unknown") == "latest"
    
    def test_to_dict(self):
        """Test to_dict method."""
        config = Configuration()
        config_dict = config.to_dict()
        
        assert "primary_model" in config_dict
        assert "orchestration_model" in config_dict
        assert "limits" in config_dict
        assert "features" in config_dict
        assert "prompt_config" in config_dict
        
        assert config_dict["primary_model"] == "gemini:gemini-1.5-flash"
        assert config_dict["limits"]["max_iterations"] == 10
        assert config_dict["features"]["cache"] is True
    
    @patch.dict(os.environ, {
        "PRIMARY_MODEL_PROVIDER": "groq",
        "PRIMARY_MODEL_NAME": "mixtral-8x7b",
        "MAX_ANALYSIS_ITERATIONS": "15",
        "ENABLE_CACHE": "false"
    })
    def test_from_environment(self):
        """Test from_environment method."""
        config = Configuration.from_environment()
        
        assert config.primary_model.provider == "groq"
        assert config.primary_model.model_name == "mixtral-8x7b"
        assert config.max_analysis_iterations == 15
        assert config.enable_cache is False


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions for Configuration."""
    
    def test_from_runnable_config_missing_configurable(self):
        """Test from_runnable_config with missing configurable key."""
        runnable_config = {
            "model": "gemini:test"  # Not under 'configurable'
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        
        # Should use defaults since 'configurable' key is missing
        assert config.model == "gemini:gemini-1.5-flash"
    
    def test_from_runnable_config_non_dict_configurable(self):
        """Test from_runnable_config with non-dict configurable."""
        runnable_config = {
            "configurable": "not_a_dict"
        }
        
        config = Configuration.from_runnable_config(runnable_config)
        
        # Should use defaults since configurable is not a dict
        assert config.model == "gemini:gemini-1.5-flash"
    
    def test_invalid_validation_retries(self):
        """Test configuration with invalid validation retries."""
        with pytest.raises(Exception):  # Should raise validation error
            Configuration(max_validation_retries=0)  # Below minimum
    
    def test_invalid_temperature(self):
        """Test ModelConfig with invalid temperature."""
        with pytest.raises(Exception):  # Should raise validation error
            ModelConfig(temperature=3.0)  # Above maximum
        
        with pytest.raises(Exception):  # Should raise validation error
            ModelConfig(temperature=-1.0)  # Below minimum
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_config_missing_api_keys(self):
        """Test validate_config with missing API keys."""
        config = Configuration()
        
        with pytest.raises(ValueError, match="API key not found"):
            config.validate_config()
    
    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "test_gemini",
        "GROQ_API_KEY": "test_groq",
        "TAVILY_API_KEY": "test_tavily"
    })
    def test_validate_config_success(self):
        """Test validate_config with all required API keys."""
        config = Configuration()
        
        # Should not raise any exceptions
        config.validate_config()


class TestPromptConfiguration:
    """Test the PromptConfiguration class."""
    
    def test_default_prompt_configuration(self):
        """Test default PromptConfiguration values."""
        config = PromptConfiguration()
        
        assert config.use_langsmith is True
        assert config.cache_prompts is True
        assert config.prompt_cache_ttl == 3600
        assert "main" in config.prompt_versions
        assert "validation" in config.prompt_versions
        assert config.prompt_versions["main"] == "latest"
    
    def test_custom_prompt_configuration(self):
        """Test PromptConfiguration with custom values."""
        config = PromptConfiguration(
            use_langsmith=False,
            cache_prompts=False,
            prompt_cache_ttl=7200,
            prompt_versions={"main": "v1.0.0", "validation": "v2.0.0"}
        )
        
        assert config.use_langsmith is False
        assert config.cache_prompts is False
        assert config.prompt_cache_ttl == 7200
        assert config.prompt_versions["main"] == "v1.0.0"
        assert config.prompt_versions["validation"] == "v2.0.0"
    
    @patch.dict(os.environ, {"LANGSMITH_API_KEY": "test_langsmith_key"})
    def test_langsmith_api_key_from_env(self):
        """Test LangSmith API key from environment."""
        config = PromptConfiguration()
        assert config.langsmith_api_key == "test_langsmith_key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])