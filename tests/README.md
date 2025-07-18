# Log Analyzer Agent Tests

This directory contains the test suite for the Log Analyzer Agent.

## Test Structure

```
tests/
├── unit/               # Unit tests for individual components
│   ├── test_state.py          # State management tests
│   ├── test_utils.py          # Utility function tests
│   ├── test_tools.py          # Tool function tests
│   ├── test_validation.py     # Validation model tests
│   └── test_configuration.py  # Configuration tests
├── integration/        # Integration tests (future)
└── e2e/               # End-to-end tests (future)
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements.txt
```

### Run All Unit Tests

```bash
# Using pytest directly
pytest tests/unit -v

# Using the test runner script
python run_unit_tests.py

# Run with coverage
pytest tests/unit --cov=src/log_analyzer_agent --cov-report=html
```

### Run Specific Test Files

```bash
# Test state management
pytest tests/unit/test_state.py -v

# Test utils
pytest tests/unit/test_utils.py -v

# Test tools
pytest tests/unit/test_tools.py -v
```

### Run Specific Test Classes or Methods

```bash
# Run specific test class
pytest tests/unit/test_state.py::TestCoreState -v

# Run specific test method
pytest tests/unit/test_state.py::TestCoreState::test_core_state_initialization -v
```

## Test Coverage

The unit tests cover:

1. **State Management** (`test_state.py`)
   - Core, Interactive, and Memory state initialization
   - State feature detection
   - State factory functions

2. **Utilities** (`test_utils.py`)
   - Environment context formatting
   - Log preprocessing and pattern detection
   - Model initialization and configuration

3. **Tools** (`test_tools.py`)
   - Command suggestion engine
   - Documentation search
   - Request additional info
   - Analysis submission

4. **Validation** (`test_validation.py`)
   - Pydantic model validation
   - Issue, Suggestion, and AnalysisResult models
   - Analysis quality checks

5. **Configuration** (`test_configuration.py`)
   - Default configuration values
   - Configuration from runnable config
   - Feature flag combinations

## Writing New Tests

When adding new tests:

1. Follow the existing naming convention: `test_<module>.py`
2. Group related tests in classes
3. Use descriptive test method names that explain what is being tested
4. Include docstrings for test classes and methods
5. Use pytest fixtures for common setup
6. Mock external dependencies (APIs, databases, etc.)

### Example Test Structure

```python
import pytest
from unittest.mock import Mock, patch

class TestNewFeature:
    """Test the new feature functionality."""
    
    @pytest.fixture
    def setup(self):
        """Common setup for tests."""
        return {"test_data": "value"}
    
    def test_feature_basic(self, setup):
        """Test basic functionality."""
        # Arrange
        data = setup["test_data"]
        
        # Act
        result = function_under_test(data)
        
        # Assert
        assert result == expected_value
    
    @patch("module.external_api")
    def test_feature_with_mock(self, mock_api):
        """Test with mocked external dependency."""
        mock_api.return_value = {"mocked": "response"}
        
        result = function_that_calls_api()
        
        assert result["mocked"] == "response"
        mock_api.assert_called_once()
```

## Continuous Integration

Tests should be run:
- Before committing changes
- In pull request checks
- As part of the deployment pipeline

## Known Issues

1. Some tests require environment variables (API keys) to be set
2. Async tests require `pytest-asyncio` to be installed
3. Integration tests with external services should be mocked in unit tests

## Future Improvements

1. Add integration tests for the full graph workflow
2. Add performance benchmarks
3. Implement property-based testing for complex inputs
4. Add mutation testing to verify test quality
5. Create fixtures for common test data (log samples, state objects)