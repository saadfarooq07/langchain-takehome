"""
Test configuration and utilities for the Log Analyzer Agent test suite.
"""

import os
import pytest
from pathlib import Path
from typing import Dict, Any, List


class TestConfig:
    """Test configuration class."""
    
    # Test data paths
    PROJECT_ROOT = Path(__file__).parent.parent
    TEST_ROOT = Path(__file__).parent
    FIXTURES_DIR = TEST_ROOT / "fixtures"
    LOG_SAMPLES_DIR = FIXTURES_DIR / "log_samples"
    
    # Test timeouts (in seconds)
    UNIT_TEST_TIMEOUT = 30
    INTEGRATION_TEST_TIMEOUT = 120
    FUNCTIONAL_TEST_TIMEOUT = 300
    E2E_TEST_TIMEOUT = 600
    PERFORMANCE_TEST_TIMEOUT = 1800
    
    # Performance thresholds
    SMALL_LOG_MAX_TIME = 30.0  # seconds
    MEDIUM_LOG_MAX_TIME = 60.0
    LARGE_LOG_MAX_TIME = 180.0
    
    SMALL_LOG_MAX_MEMORY = 200  # MB
    MEDIUM_LOG_MAX_MEMORY = 500
    LARGE_LOG_MAX_MEMORY = 1000
    
    # Test data sizes
    SMALL_LOG_SIZE = 1  # MB
    MEDIUM_LOG_SIZE = 10
    LARGE_LOG_SIZE = 50
    XLARGE_LOG_SIZE = 100
    
    # API configuration
    REQUIRED_ENV_VARS = [
        "GEMINI_API_KEY",
        "GROQ_API_KEY", 
        "TAVILY_API_KEY"
    ]
    
    OPTIONAL_ENV_VARS = [
        "OPENAI_API_KEY",
        "USE_IMPROVED_LOG_ANALYZER",
        "LOG_LEVEL"
    ]
    
    @classmethod
    def get_test_config(cls, test_type: str = "unit") -> Dict[str, Any]:
        """Get configuration for specific test type."""
        base_config = {
            "configurable": {
                "primary_model": "gemini-2.5-flash",
                "orchestration_model": "kimi-k2",
                "max_iterations": 3,
                "enable_streaming": False,
                "enable_memory": False,
                "enable_ui_mode": False,
                "enable_subgraphs": False,
                "enable_circuit_breaker": False,
                "enable_rate_limiting": False
            }
        }
        
        if test_type == "performance":
            base_config["configurable"].update({
                "max_iterations": 2,  # Reduced for performance
                "enable_streaming": True,
                "enable_circuit_breaker": True,
                "chunk_size": 5000,
                "max_chunk_overlap": 200
            })
        elif test_type == "integration":
            base_config["configurable"].update({
                "enable_streaming": True,
                "enable_subgraphs": True
            })
        elif test_type == "e2e":
            base_config["configurable"].update({
                "enable_streaming": True,
                "enable_subgraphs": True,
                "enable_circuit_breaker": True,
                "enable_rate_limiting": True
            })
        
        return base_config
    
    @classmethod
    def check_environment(cls) -> Dict[str, bool]:
        """Check environment setup."""
        env_status = {}
        
        # Check required environment variables
        for var in cls.REQUIRED_ENV_VARS:
            env_status[var] = bool(os.getenv(var))
        
        # Check optional environment variables
        for var in cls.OPTIONAL_ENV_VARS:
            env_status[f"{var}_optional"] = bool(os.getenv(var))
        
        # Check if package is installed
        try:
            import src.log_analyzer_agent
            env_status["package_installed"] = True
        except ImportError:
            env_status["package_installed"] = False
        
        # Check test data directories
        env_status["fixtures_exist"] = cls.FIXTURES_DIR.exists()
        env_status["log_samples_exist"] = cls.LOG_SAMPLES_DIR.exists()
        
        return env_status
    
    @classmethod
    def get_skip_reasons(cls) -> Dict[str, str]:
        """Get reasons for skipping tests."""
        env_status = cls.check_environment()
        skip_reasons = {}
        
        if not env_status["package_installed"]:
            skip_reasons["package"] = "Package not installed in editable mode"
        
        missing_api_keys = [
            var for var in cls.REQUIRED_ENV_VARS 
            if not env_status[var]
        ]
        if missing_api_keys:
            skip_reasons["api_keys"] = f"Missing API keys: {', '.join(missing_api_keys)}"
        
        if not env_status["fixtures_exist"]:
            skip_reasons["fixtures"] = "Test fixtures directory not found"
        
        return skip_reasons


class TestMarkers:
    """Test markers for pytest."""
    
    UNIT = "unit"
    INTEGRATION = "integration"
    FUNCTIONAL = "functional"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SLOW = "slow"
    REQUIRES_API = "requires_api"
    REQUIRES_DB = "requires_db"


class MockResponses:
    """Standard mock responses for testing."""
    
    ANALYSIS_SUCCESS = """
    {
        "summary": "Mock analysis completed successfully",
        "issues": [
            {
                "severity": "medium",
                "category": "mock",
                "description": "Mock issue for testing",
                "affected_components": ["MockComponent"],
                "first_occurrence": "2024-01-15 10:30:00",
                "frequency": 1
            }
        ],
        "suggestions": [
            {
                "priority": "medium",
                "category": "testing",
                "description": "Mock suggestion for testing",
                "implementation": "Mock implementation",
                "estimated_impact": "Mock impact"
            }
        ]
    }
    """
    
    VALIDATION_SUCCESS = """
    {
        "is_valid": true,
        "completeness_score": 0.8,
        "accuracy_score": 0.8,
        "feedback": "Mock validation successful"
    }
    """
    
    SEARCH_RESULTS = {
        "results": [
            {
                "title": "Mock Documentation",
                "url": "https://docs.example.com/mock",
                "content": "Mock documentation content for testing"
            }
        ]
    }
    
    TOOL_CALL_RESPONSE = """
    I need to search for more information.
    
    <tool_call>
    search_documentation("mock query for testing")
    </tool_call>
    """


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", f"{TestMarkers.UNIT}: Unit tests"
    )
    config.addinivalue_line(
        "markers", f"{TestMarkers.INTEGRATION}: Integration tests"
    )
    config.addinivalue_line(
        "markers", f"{TestMarkers.FUNCTIONAL}: Functional tests"
    )
    config.addinivalue_line(
        "markers", f"{TestMarkers.E2E}: End-to-end tests"
    )
    config.addinivalue_line(
        "markers", f"{TestMarkers.PERFORMANCE}: Performance tests"
    )
    config.addinivalue_line(
        "markers", f"{TestMarkers.SLOW}: Slow running tests"
    )
    config.addinivalue_line(
        "markers", f"{TestMarkers.REQUIRES_API}: Tests that require API keys"
    )
    config.addinivalue_line(
        "markers", f"{TestMarkers.REQUIRES_DB}: Tests that require database"
    )


def skip_if_no_api_keys():
    """Skip test if required API keys are not available."""
    skip_reasons = TestConfig.get_skip_reasons()
    if "api_keys" in skip_reasons:
        pytest.skip(skip_reasons["api_keys"])


def skip_if_package_not_installed():
    """Skip test if package is not installed."""
    skip_reasons = TestConfig.get_skip_reasons()
    if "package" in skip_reasons:
        pytest.skip(skip_reasons["package"])


def skip_if_no_fixtures():
    """Skip test if fixtures are not available."""
    skip_reasons = TestConfig.get_skip_reasons()
    if "fixtures" in skip_reasons:
        pytest.skip(skip_reasons["fixtures"])