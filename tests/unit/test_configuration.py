"""Unit tests for configuration module."""

import pytest
from unittest.mock import MagicMock

from src.log_analyzer_agent.configuration import Configuration


class TestConfiguration:
    """Test Configuration class."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = Configuration()
        
        # Test default values
        assert config.model == "gemini:2.5-flash"
        assert config.orchestrator_model == "kimi:k2"
        assert config.max_iterations == 10
        assert config.max_analysis_iterations == 3
        assert config.max_tool_calls == 20
        assert config.max_validation_retries == 3
        assert config.enable_memory is False
        assert config.enable_interactivity is False
        assert config.max_search_results == 5
        assert config.log_processing_chunk_size == 50000
        assert config.postgres_connection_string is None
        assert config.llm_temperature == 0.0
    
    def test_custom_configuration(self):
        """Test creating configuration with custom values."""
        config = Configuration(
            model="gemini:1.5-pro",
            max_iterations=5,
            enable_memory=True,
            postgres_connection_string="postgresql://localhost/test",
            llm_temperature=0.7
        )
        
        assert config.model == "gemini:1.5-pro"
        assert config.max_iterations == 5
        assert config.enable_memory is True
        assert config.postgres_connection_string == "postgresql://localhost/test"
        assert config.llm_temperature == 0.7
        
        # Other values should remain default
        assert config.orchestrator_model == "kimi:k2"
        assert config.max_search_results == 5
    
    def test_from_runnable_config_none(self):
        """Test creating configuration from None runnable config."""
        config = Configuration.from_runnable_config(None)
        
        # Should return default configuration
        assert config.model == "gemini:2.5-flash"
        assert config.enable_memory is False
    
    def test_from_runnable_config_empty(self):
        """Test creating configuration from empty runnable config."""
        mock_config = MagicMock()
        mock_config.get.return_value = {}
        
        config = Configuration.from_runnable_config(mock_config)
        
        # Should return default configuration
        assert config.model == "gemini:2.5-flash"
        assert config.enable_memory is False
    
    def test_from_runnable_config_with_values(self):
        """Test creating configuration from runnable config with values."""
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "configurable": {
                "model": "gemini:ultra",
                "max_iterations": 15,
                "enable_memory": True,
                "enable_interactivity": True,
                "llm_temperature": 0.5
            }
        }
        
        config = Configuration.from_runnable_config(mock_config)
        
        assert config.model == "gemini:ultra"
        assert config.max_iterations == 15
        assert config.enable_memory is True
        assert config.enable_interactivity is True
        assert config.llm_temperature == 0.5
    
    def test_from_runnable_config_partial_values(self):
        """Test creating configuration with partial values."""
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "configurable": {
                "model": "kimi:k1",
                "max_search_results": 10
            }
        }
        
        config = Configuration.from_runnable_config(mock_config)
        
        # Specified values should be set
        assert config.model == "kimi:k1"
        assert config.max_search_results == 10
        
        # Other values should be default
        assert config.max_iterations == 10
        assert config.enable_memory is False
    
    def test_configuration_validation_boundaries(self):
        """Test configuration value boundaries."""
        # Test minimum values
        config = Configuration(
            max_iterations=1,
            max_analysis_iterations=1,
            max_tool_calls=1,
            max_validation_retries=0,
            max_search_results=1,
            log_processing_chunk_size=1000,
            llm_temperature=0.0
        )
        
        assert config.max_iterations == 1
        assert config.llm_temperature == 0.0
        
        # Test maximum values
        config = Configuration(
            max_iterations=100,
            llm_temperature=2.0
        )
        
        assert config.max_iterations == 100
        assert config.llm_temperature == 2.0
    
    def test_configuration_model_names(self):
        """Test various model name formats."""
        # Test Gemini models
        for model in ["gemini:1.5-flash", "gemini:2.5-flash", "gemini:1.5-pro"]:
            config = Configuration(model=model)
            assert config.model == model
        
        # Test Kimi models
        for model in ["kimi:k1", "kimi:k2", "kimi:k3"]:
            config = Configuration(orchestrator_model=model)
            assert config.orchestrator_model == model
    
    def test_configuration_feature_flags(self):
        """Test feature flag combinations."""
        # Test no features
        config = Configuration(
            enable_memory=False,
            enable_interactivity=False
        )
        assert not config.enable_memory
        assert not config.enable_interactivity
        
        # Test only memory
        config = Configuration(
            enable_memory=True,
            enable_interactivity=False
        )
        assert config.enable_memory
        assert not config.enable_interactivity
        
        # Test only interactivity
        config = Configuration(
            enable_memory=False,
            enable_interactivity=True
        )
        assert not config.enable_memory
        assert config.enable_interactivity
        
        # Test both features
        config = Configuration(
            enable_memory=True,
            enable_interactivity=True
        )
        assert config.enable_memory
        assert config.enable_interactivity
    
    def test_configuration_postgres_string(self):
        """Test PostgreSQL connection string handling."""
        # Test with None
        config = Configuration(postgres_connection_string=None)
        assert config.postgres_connection_string is None
        
        # Test with empty string
        config = Configuration(postgres_connection_string="")
        assert config.postgres_connection_string == ""
        
        # Test with valid connection string
        conn_str = "postgresql://user:pass@localhost:5432/dbname"
        config = Configuration(postgres_connection_string=conn_str)
        assert config.postgres_connection_string == conn_str
    
    def test_configuration_immutability(self):
        """Test that configuration values are properly set."""
        config = Configuration(
            model="gemini:test",
            max_iterations=20
        )
        
        # Values should be accessible
        assert config.model == "gemini:test"
        assert config.max_iterations == 20
        
        # Should be able to create new instance with different values
        config2 = Configuration(
            model="kimi:test",
            max_iterations=30
        )
        
        # Original should be unchanged
        assert config.model == "gemini:test"
        assert config.max_iterations == 20
        
        # New instance should have new values
        assert config2.model == "kimi:test"
        assert config2.max_iterations == 30


class TestConfigurationEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_from_runnable_config_missing_configurable(self):
        """Test handling missing 'configurable' key."""
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "model": "gemini:test"  # Not under 'configurable'
        }
        
        config = Configuration.from_runnable_config(mock_config)
        
        # Should use defaults since 'configurable' is missing
        assert config.model == "gemini:2.5-flash"
    
    def test_from_runnable_config_non_dict_configurable(self):
        """Test handling non-dict 'configurable' value."""
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "configurable": "not a dict"
        }
        
        config = Configuration.from_runnable_config(mock_config)
        
        # Should use defaults
        assert config.model == "gemini:2.5-flash"
    
    def test_negative_values(self):
        """Test that negative values are handled appropriately."""
        # This depends on whether the Configuration class validates inputs
        # For now, test that it accepts the values
        config = Configuration(
            max_iterations=-1,  # Should probably be validated in real code
            llm_temperature=-0.5  # Should probably be validated in real code
        )
        
        # Current implementation likely doesn't validate
        assert config.max_iterations == -1
        assert config.llm_temperature == -0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])