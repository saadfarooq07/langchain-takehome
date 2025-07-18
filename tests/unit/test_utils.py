"""Unit tests for utility functions."""

import pytest
import os
from unittest.mock import patch, MagicMock

from src.log_analyzer_agent.utils import (
    format_environment_context,
    preprocess_log,
    init_model,
    _init_model_sync
)


class TestEnvironmentFormatting:
    """Test environment context formatting."""
    
    def test_format_empty_environment(self):
        """Test formatting with no environment details."""
        result = format_environment_context(None)
        assert result == "No environment details provided."
        
        result = format_environment_context({})
        assert result == "Environment Context:\n"
    
    def test_format_single_environment_detail(self):
        """Test formatting with single environment detail."""
        env = {"os": "Linux"}
        result = format_environment_context(env)
        assert "Environment Context:" in result
        assert "- os: Linux" in result
    
    def test_format_multiple_environment_details(self):
        """Test formatting with multiple environment details."""
        env = {
            "os": "Ubuntu 22.04",
            "runtime": "Python 3.11",
            "memory": "16GB",
            "cpu": "Intel i7"
        }
        result = format_environment_context(env)
        lines = result.strip().split('\n')
        assert lines[0] == "Environment Context:"
        assert "- os: Ubuntu 22.04" in result
        assert "- runtime: Python 3.11" in result
        assert "- memory: 16GB" in result
        assert "- cpu: Intel i7" in result


class TestLogPreprocessing:
    """Test log preprocessing functionality."""
    
    def test_preprocess_empty_log(self):
        """Test preprocessing empty log."""
        result = preprocess_log("")
        assert "=== ENVIRONMENT DISCOVERY ===" in result
        assert "=== END ENVIRONMENT DISCOVERY ===" in result
    
    def test_detect_operating_system(self):
        """Test OS detection in logs."""
        # Test Linux detection
        log = "Starting service on Ubuntu 22.04 LTS"
        result = preprocess_log(log)
        assert "Operating System: Ubuntu" in result
        
        # Test Windows detection
        log = "Windows Server 2019 startup sequence"
        result = preprocess_log(log)
        assert "Operating System: Windows" in result
        
        # Test macOS detection
        log = "Darwin kernel version 21.6.0"
        result = preprocess_log(log)
        assert "Operating System: Darwin" in result
    
    def test_detect_runtime_versions(self):
        """Test runtime version detection."""
        log = """
        Python 3.11.5 initializing
        Node.js v18.16.0 server starting
        Java 17.0.8 runtime loaded
        """
        result = preprocess_log(log)
        assert "Runtime Versions:" in result
        assert "Python: 3.11.5" in result
        assert "Node: 18.16.0" in result
        assert "Java: 17.0.8" in result
    
    def test_detect_packages(self):
        """Test package detection."""
        log = """
        npm WARN deprecated request@2.88.2
        Installing package numpy==1.24.3
        gem 'rails', '~> 7.0.4'
        """
        result = preprocess_log(log)
        assert "Detected Packages:" in result
        assert "request: 2.88.2" in result
        assert "numpy: 1.24.3" in result
        assert "rails: 7.0.4" in result
    
    def test_detect_services(self):
        """Test service detection."""
        log = """
        PostgreSQL 14.5 on x86_64-pc-linux-gnu
        Redis server v=7.0.11
        MongoDB server version: 6.0.5
        """
        result = preprocess_log(log)
        assert "Detected Services:" in result
        assert "Postgres: 14.5" in result
        assert "Redis: 7.0.11" in result
        assert "Mongodb: 6.0.5" in result
    
    def test_detect_container_environment(self):
        """Test container/orchestration detection."""
        log = """
        Docker version 24.0.5
        Kubernetes v1.28.2
        container_id: abc123def456
        """
        result = preprocess_log(log)
        assert "Container Environment:" in result
        assert "Docker Version: 24.0.5" in result
        assert "Kubernetes Version: 1.28.2" in result
        assert "Container Id: abc123def456" in result
    
    def test_error_counting(self):
        """Test error pattern counting."""
        log = """
        ERROR: Database connection failed
        WARNING: High memory usage detected
        FATAL: System crash imminent
        WARN: Disk space low
        Traceback (most recent call last):
        """
        result = preprocess_log(log)
        assert "Error Summary:" in result
        assert "ERROR: 2" in result  # ERROR and FATAL
        assert "WARNING: 2" in result  # WARNING and WARN
        assert "STACKTRACE: 1" in result
    
    def test_log_format_detection(self):
        """Test log format detection."""
        # ISO timestamp
        log = "2024-01-15 10:23:45 INFO Starting service"
        result = preprocess_log(log)
        assert "Log Format: ISO timestamp" in result
        
        # Unix timestamp
        log = "1705312425 INFO Service started"
        result = preprocess_log(log)
        assert "Log Format: Unix timestamp" in result
    
    def test_package_limit(self):
        """Test that package list is limited to 10 entries."""
        log = "\n".join([f"numpy=={i}.0.0" for i in range(15)])
        result = preprocess_log(log)
        assert "... and 5 more" in result


class TestModelInitialization:
    """Test model initialization functions."""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("src.log_analyzer_agent.utils.ChatGoogleGenerativeAI")
    def test_init_gemini_model(self, mock_gemini):
        """Test initializing Gemini model."""
        mock_config = MagicMock()
        mock_config.get.return_value = {"configurable": {"model": "gemini:2.5-flash"}}
        
        _init_model_sync(mock_config)
        
        mock_gemini.assert_called_once_with(
            model="2.5-flash",
            google_api_key="test-key"
        )
    
    @patch.dict(os.environ, {"GROQ_API_KEY": "test-groq-key"})
    @patch("src.log_analyzer_agent.utils.ChatGroq")
    def test_init_kimi_model(self, mock_groq):
        """Test initializing Kimi model via Groq."""
        mock_config = MagicMock()
        mock_config.get.return_value = {"configurable": {"model": "kimi:k2"}}
        
        _init_model_sync(mock_config)
        
        mock_groq.assert_called_once_with(
            model="moonshotai/kimi-k2-instruct",
            max_tokens=None,
            temperature=0.3
        )
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_model_missing_api_key(self):
        """Test error when API key is missing."""
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            _init_model_sync(None)
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "GOOGLE_API_KEY": "google-key"})
    @patch("src.log_analyzer_agent.utils.ChatGoogleGenerativeAI")
    def test_gemini_prefers_gemini_api_key(self, mock_gemini):
        """Test that GEMINI_API_KEY is preferred over GOOGLE_API_KEY."""
        _init_model_sync(None)
        
        # Should use GEMINI_API_KEY, not GOOGLE_API_KEY
        mock_gemini.assert_called_once()
        call_kwargs = mock_gemini.call_args[1]
        assert call_kwargs["google_api_key"] == "test-key"
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "google-key"})
    @patch("src.log_analyzer_agent.utils.ChatGoogleGenerativeAI")
    def test_fallback_to_google_api_key(self, mock_gemini):
        """Test fallback to GOOGLE_API_KEY when GEMINI_API_KEY not set."""
        _init_model_sync(None)
        
        mock_gemini.assert_called_once()
        call_kwargs = mock_gemini.call_args[1]
        assert call_kwargs["google_api_key"] == "google-key"


class TestAsyncModelInit:
    """Test async model initialization."""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    @patch("src.log_analyzer_agent.utils.ChatGoogleGenerativeAI")
    async def test_init_model_async(self, mock_gemini):
        """Test async model initialization wrapper."""
        from src.log_analyzer_agent.utils import init_model_async
        
        mock_model = MagicMock()
        mock_gemini.return_value = mock_model
        
        result = await init_model_async()
        
        assert result == mock_model
        mock_gemini.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])