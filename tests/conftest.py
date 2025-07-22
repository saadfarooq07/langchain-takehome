"""
Pytest configuration and shared fixtures for the Log Analyzer Agent test suite.
"""

import os
import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List, Optional

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "fixtures" / "test_data"
LOG_SAMPLES_DIR = Path(__file__).parent / "fixtures" / "log_samples"

# Ensure test data directories exist
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "GEMINI_API_KEY": "test_gemini_key",
        "GROQ_API_KEY": "test_groq_key", 
        "TAVILY_API_KEY": "test_tavily_key",
        "OPENAI_API_KEY": "test_openai_key",
        "USE_IMPROVED_LOG_ANALYZER": "false",
        "LOG_LEVEL": "INFO"
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def sample_log_content():
    """Sample log content for testing."""
    return """
2024-01-15 10:30:15 ERROR [DatabaseConnection] Connection failed: timeout after 30s
2024-01-15 10:30:16 INFO [RetryManager] Retrying connection attempt 1/3
2024-01-15 10:30:20 ERROR [DatabaseConnection] Connection failed: timeout after 30s
2024-01-15 10:30:21 INFO [RetryManager] Retrying connection attempt 2/3
2024-01-15 10:30:25 ERROR [DatabaseConnection] Connection failed: timeout after 30s
2024-01-15 10:30:26 ERROR [RetryManager] Max retries exceeded, giving up
2024-01-15 10:30:27 CRITICAL [Application] Database unavailable, shutting down
"""


@pytest.fixture
def sample_hdfs_log():
    """Sample HDFS log content for testing."""
    return """
2024-01-15 10:30:15,123 INFO org.apache.hadoop.hdfs.server.datanode.DataNode: Receiving BP-123456789-10.0.0.1-1234567890123 src: /10.0.0.2:50010 dest: /10.0.0.1:50010
2024-01-15 10:30:16,456 WARN org.apache.hadoop.hdfs.server.datanode.DataNode: Slow BlockReceiver write packet to mirror took 1500ms (threshold=300ms)
2024-01-15 10:30:17,789 ERROR org.apache.hadoop.hdfs.server.datanode.DataNode: DatanodeRegistration(10.0.0.1:50010, datanodeUuid=12345678-1234-1234-1234-123456789012, infoPort=50075, infoSecurePort=0, ipcPort=50020, storageInfo=lv=-57;cid=CID-12345678-1234-1234-1234-123456789012;nsid=123456789;c=1234567890123)
2024-01-15 10:30:18,012 FATAL org.apache.hadoop.hdfs.server.datanode.DataNode: Initialization failed for Block pool BP-123456789-10.0.0.1-1234567890123 (Datanode Uuid 12345678-1234-1234-1234-123456789012) service to namenode/10.0.0.1:9000
"""


@pytest.fixture
def sample_security_log():
    """Sample security log content for testing."""
    return """
2024-01-15 10:30:15 INFO [AuthService] User login attempt: user@example.com from IP 192.168.1.100
2024-01-15 10:30:16 WARN [AuthService] Failed login attempt: user@example.com from IP 192.168.1.100 - invalid password
2024-01-15 10:30:17 WARN [AuthService] Failed login attempt: user@example.com from IP 192.168.1.100 - invalid password
2024-01-15 10:30:18 WARN [AuthService] Failed login attempt: user@example.com from IP 192.168.1.100 - invalid password
2024-01-15 10:30:19 ERROR [SecurityMonitor] Multiple failed login attempts detected for user@example.com from IP 192.168.1.100
2024-01-15 10:30:20 CRITICAL [SecurityMonitor] IP 192.168.1.100 blocked due to suspicious activity
"""


@pytest.fixture
def temp_log_file(sample_log_content):
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(sample_log_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def large_log_file():
    """Create a large log file for performance testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        # Generate ~1MB of log data
        for i in range(10000):
            f.write(f"2024-01-15 10:30:{i%60:02d} INFO [TestService] Processing request {i}\n")
            if i % 100 == 0:
                f.write(f"2024-01-15 10:30:{i%60:02d} ERROR [TestService] Error processing request {i}: Connection timeout\n")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini API client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.text = "Mocked analysis result"
    mock_client.generate_content.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_groq_client():
    """Mock Groq API client."""
    mock_client = AsyncMock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Mocked orchestration result"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_tavily_client():
    """Mock Tavily search client."""
    mock_client = Mock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Test Documentation",
                "url": "https://example.com/docs",
                "content": "Test documentation content"
            }
        ]
    }
    return mock_client


@pytest.fixture
def sample_state_data():
    """Sample state data for testing."""
    return {
        "messages": [],
        "log_content": "Sample log content",
        "analysis_result": None,
        "issues": [],
        "suggestions": [],
        "documentation_references": [],
        "user_input": None,
        "validation_result": None,
        "iteration_count": 0,
        "max_iterations": 5,
        "analysis_complete": False,
        "requires_user_input": False,
        "tool_calls": [],
        "error_message": None
    }


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result for testing."""
    return {
        "summary": "Database connection issues detected",
        "issues": [
            {
                "severity": "high",
                "category": "connectivity",
                "description": "Database connection timeouts",
                "affected_components": ["DatabaseConnection"],
                "first_occurrence": "2024-01-15 10:30:15",
                "frequency": 3
            }
        ],
        "suggestions": [
            {
                "priority": "high",
                "category": "configuration",
                "description": "Increase database connection timeout",
                "implementation": "Update connection timeout from 30s to 60s",
                "estimated_impact": "Should resolve timeout issues"
            }
        ],
        "documentation_references": [
            {
                "title": "Database Configuration Guide",
                "url": "https://docs.example.com/database-config",
                "relevance": "Connection timeout configuration"
            }
        ]
    }


@pytest.fixture
def mock_configuration():
    """Mock configuration for testing."""
    from src.log_analyzer_agent.configuration import Configuration
    
    config = Configuration()
    config.primary_model = "gemini-2.5-flash"
    config.orchestration_model = "kimi-k2"
    config.max_iterations = 5
    config.enable_streaming = False
    config.enable_memory = False
    config.enable_ui_mode = False
    config.chunk_size = 1000
    config.max_chunk_overlap = 100
    
    return config


@pytest.fixture
def mock_runnable_config():
    """Mock runnable config for LangGraph."""
    return {
        "configurable": {
            "primary_model": "gemini-2.5-flash",
            "orchestration_model": "kimi-k2",
            "max_iterations": 5,
            "enable_streaming": False,
            "enable_memory": False,
            "enable_ui_mode": False
        }
    }


class MockLLMResponse:
    """Mock LLM response for testing."""
    
    def __init__(self, content: str):
        self.content = content
        self.text = content


@pytest.fixture
def mock_llm_responses():
    """Mock LLM responses for different scenarios."""
    return {
        "analysis": MockLLMResponse("""
        {
            "summary": "Database connection issues detected",
            "issues": [
                {
                    "severity": "high",
                    "category": "connectivity", 
                    "description": "Database connection timeouts",
                    "affected_components": ["DatabaseConnection"],
                    "first_occurrence": "2024-01-15 10:30:15",
                    "frequency": 3
                }
            ],
            "suggestions": [
                {
                    "priority": "high",
                    "category": "configuration",
                    "description": "Increase database connection timeout",
                    "implementation": "Update connection timeout from 30s to 60s",
                    "estimated_impact": "Should resolve timeout issues"
                }
            ]
        }
        """),
        "validation": MockLLMResponse("""
        {
            "is_valid": true,
            "completeness_score": 0.9,
            "accuracy_score": 0.85,
            "feedback": "Analysis is comprehensive and accurate"
        }
        """),
        "tool_call": MockLLMResponse("""
        I need to search for documentation about database connection timeouts.
        
        <tool_call>
        search_documentation("database connection timeout configuration")
        </tool_call>
        """)
    }


# Async fixtures for testing async functions
@pytest.fixture
async def async_mock_state():
    """Async mock state for testing."""
    from src.log_analyzer_agent.state import State
    
    state = State()
    state.log_content = "Sample log content"
    state.messages = []
    return state


# Performance testing fixtures
@pytest.fixture
def performance_metrics():
    """Performance metrics tracking for tests."""
    import time
    import psutil
    import threading
    
    class PerformanceTracker:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.start_memory = None
            self.end_memory = None
            self.peak_memory = None
            self._monitoring = False
            self._monitor_thread = None
        
        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = self.start_memory
            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_memory)
            self._monitor_thread.start()
        
        def stop(self):
            self.end_time = time.time()
            self.end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            self._monitoring = False
            if self._monitor_thread:
                self._monitor_thread.join()
        
        def _monitor_memory(self):
            while self._monitoring:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                self.peak_memory = max(self.peak_memory, current_memory)
                time.sleep(0.1)
        
        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
        
        @property
        def memory_usage(self):
            if self.start_memory and self.end_memory:
                return self.end_memory - self.start_memory
            return None
    
    return PerformanceTracker()


# Database fixtures (for future database tests)
@pytest.fixture
def mock_database():
    """Mock database for testing."""
    class MockDB:
        def __init__(self):
            self.data = {}
        
        async def get(self, key):
            return self.data.get(key)
        
        async def set(self, key, value):
            self.data[key] = value
        
        async def delete(self, key):
            if key in self.data:
                del self.data[key]
        
        async def clear(self):
            self.data.clear()
    
    return MockDB()


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Automatically cleanup temporary files after each test."""
    temp_files = []
    
    def track_temp_file(filepath):
        temp_files.append(filepath)
    
    yield track_temp_file
    
    # Cleanup
    for filepath in temp_files:
        if os.path.exists(filepath):
            try:
                os.unlink(filepath)
            except OSError:
                pass  # File might already be deleted