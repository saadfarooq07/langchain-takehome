# Log Analyzer Agent - Comprehensive Test Suite

This directory contains a comprehensive test suite for the Log Analyzer Agent with full coverage of all components and scenarios.

## 🧪 Test Structure

```
tests/
├── unit/                   # Unit tests for individual components
│   ├── test_nodes.py              # Node implementations
│   ├── test_graph.py              # Graph workflows
│   ├── test_state.py              # State management
│   ├── test_tools.py              # Tool functions
│   ├── test_configuration.py      # Configuration handling
│   ├── test_utils.py              # Utility functions
│   ├── test_validation.py         # Validation models
│   ├── test_cache.py              # Caching functionality
│   └── test_enhanced_components.py # Enhanced/improved components
├── integration/            # Integration tests
│   ├── test_graph_workflows.py    # Complete graph workflows
│   └── test_api_integration.py    # API integrations
├── functional/             # Functional tests
│   └── test_log_analysis_scenarios.py # Real-world scenarios
├── e2e/                    # End-to-end tests
│   └── test_complete_workflows.py # Full system tests
├── performance/            # Performance tests
│   └── test_load_performance.py   # Load and performance tests
├── fixtures/               # Test data and fixtures
│   ├── log_samples/               # Sample log files
│   └── test_data/                 # Test data files
├── archive/                # Archived old test files
├── conftest.py            # Pytest configuration and fixtures
├── test_config.py         # Test configuration utilities
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites

1. **Install the package in editable mode:**
   ```bash
   pip install -e .
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   export GEMINI_API_KEY="your_gemini_key"
   export GROQ_API_KEY="your_groq_key"
   export TAVILY_API_KEY="your_tavily_key"
   ```

3. **Install test dependencies:**
   ```bash
   pip install pytest pytest-asyncio pytest-cov pytest-html pytest-xdist psutil
   ```

### Running Tests

#### Using the Comprehensive Test Runner (Recommended)

```bash
# Run quick tests (unit + integration, no slow tests)
./run_comprehensive_tests.py --suite quick

# Run all unit tests with coverage
./run_comprehensive_tests.py --suite unit --coverage

# Run integration tests
./run_comprehensive_tests.py --suite integration

# Run functional tests
./run_comprehensive_tests.py --suite functional

# Run end-to-end tests
./run_comprehensive_tests.py --suite e2e

# Run performance tests
./run_comprehensive_tests.py --suite performance

# Run all tests with coverage and report
./run_comprehensive_tests.py --suite all --coverage --report

# Run with linting checks
./run_comprehensive_tests.py --suite quick --lint

# Verbose output
./run_comprehensive_tests.py --suite unit --verbose
```

#### Using pytest directly

```bash
# Run all tests
pytest tests/

# Run specific test suites
pytest tests/unit/                    # Unit tests
pytest tests/integration/             # Integration tests
pytest tests/functional/              # Functional tests
pytest tests/e2e/                     # End-to-end tests
pytest tests/performance/             # Performance tests

# Run with markers
pytest tests/ -m unit                 # Only unit tests
pytest tests/ -m "not slow"           # Exclude slow tests
pytest tests/ -m "performance"        # Only performance tests
pytest tests/ -m "requires_api"       # Only tests requiring API keys

# Run with coverage
pytest tests/ --cov=src/log_analyzer_agent --cov-report=html

# Run specific test files
pytest tests/unit/test_nodes.py -v
pytest tests/integration/test_graph_workflows.py -v

# Run specific test methods
pytest tests/unit/test_nodes.py::TestAnalysisNode::test_analyze_logs_basic -v
```

## 📊 Test Categories

### Unit Tests (`tests/unit/`)
- **Coverage**: Individual components, functions, and classes
- **Speed**: Fast (< 30 seconds total)
- **Dependencies**: Mocked external APIs
- **Purpose**: Verify component behavior in isolation

**Key test files:**
- `test_nodes.py`: All node implementations (analysis, validation, user input)
- `test_graph.py`: Graph creation, routing, and execution logic
- `test_state.py`: State management and reducers
- `test_tools.py`: Tool functions (search, request info, submit analysis)
- `test_enhanced_components.py`: Improved implementation components

### Integration Tests (`tests/integration/`)
- **Coverage**: Component interactions and workflows
- **Speed**: Medium (1-5 minutes)
- **Dependencies**: Mocked APIs with realistic responses
- **Purpose**: Verify components work together correctly

**Key scenarios:**
- Complete graph workflow execution
- API integration patterns
- Error handling and recovery
- Tool call execution
- State transitions

### Functional Tests (`tests/functional/`)
- **Coverage**: Real-world log analysis scenarios
- **Speed**: Medium (2-10 minutes)
- **Dependencies**: Mocked APIs with scenario-specific responses
- **Purpose**: Verify system handles realistic use cases

**Scenarios covered:**
- Database connection issues
- Security incidents (brute force, SQL injection)
- Performance problems (memory leaks, high CPU)
- Cascading failures
- Complex multi-issue scenarios

### End-to-End Tests (`tests/e2e/`)
- **Coverage**: Complete system workflows with real data
- **Speed**: Slow (5-20 minutes)
- **Dependencies**: Can use real APIs or comprehensive mocks
- **Purpose**: Verify entire system works as expected

**Test scenarios:**
- Real LogHub dataset processing
- Multiple log type handling
- Error recovery workflows
- Concurrent processing
- Resource limit handling

### Performance Tests (`tests/performance/`)
- **Coverage**: System performance and scalability
- **Speed**: Very slow (10-30 minutes)
- **Dependencies**: Mocked APIs for consistent timing
- **Purpose**: Verify performance characteristics

**Benchmarks:**
- Small log processing (1MB): < 30s, < 200MB memory
- Medium log processing (10MB): < 60s, < 500MB memory
- Large log processing (50MB): < 180s, < 1GB memory
- Concurrent processing efficiency
- Memory usage under load
- Throughput benchmarks

## 🏷️ Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.functional`: Functional tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.performance`: Performance tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.requires_api`: Tests requiring API keys
- `@pytest.mark.requires_db`: Tests requiring database

## 🔧 Test Configuration

### Environment Variables

**Required for API tests:**
- `GEMINI_API_KEY`: Google Gemini API key
- `GROQ_API_KEY`: Groq API key
- `TAVILY_API_KEY`: Tavily search API key

**Optional:**
- `OPENAI_API_KEY`: OpenAI API key
- `USE_IMPROVED_LOG_ANALYZER`: Enable improved implementation
- `LOG_LEVEL`: Logging level for tests

### Test Data

Test data is organized in `tests/fixtures/`:
- `log_samples/`: Sample log files for different scenarios
- `test_data/`: Additional test data files

### Performance Thresholds

Performance tests use these thresholds:
- **Small logs (1MB)**: 30s max, 200MB memory
- **Medium logs (10MB)**: 60s max, 500MB memory  
- **Large logs (50MB)**: 180s max, 1GB memory

## 📈 Coverage Goals

- **Unit tests**: > 90% line coverage
- **Integration tests**: > 80% workflow coverage
- **Functional tests**: > 95% scenario coverage
- **E2E tests**: 100% critical path coverage

## 🐛 Debugging Tests

### Running Individual Tests
```bash
# Run with verbose output and no capture
pytest tests/unit/test_nodes.py::TestAnalysisNode::test_analyze_logs_basic -v -s

# Run with pdb debugger
pytest tests/unit/test_nodes.py::TestAnalysisNode::test_analyze_logs_basic --pdb

# Run with custom markers
pytest tests/ -m "unit and not slow" -v
```

### Common Issues

1. **Import Errors**: Ensure package is installed with `pip install -e .`
2. **API Key Errors**: Set required environment variables
3. **Timeout Errors**: Increase timeout for slow tests
4. **Memory Errors**: Run performance tests on machines with sufficient RAM

### Test Logs
```bash
# Run with detailed logging
pytest tests/ --log-cli-level=DEBUG

# Capture stdout/stderr
pytest tests/ -s --capture=no
```

## 🔄 Continuous Integration

### GitHub Actions Integration
```yaml
# Example CI configuration
- name: Run Tests
  run: |
    pip install -e .
    ./run_comprehensive_tests.py --suite quick --coverage --report
    
- name: Upload Coverage
  uses: codecov/codecov-action@v1
  with:
    file: ./coverage.xml
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📋 Test Reports

### Coverage Reports
```bash
# Generate HTML coverage report
pytest tests/ --cov=src/log_analyzer_agent --cov-report=html
# Open htmlcov/index.html

# Generate XML coverage report
pytest tests/ --cov=src/log_analyzer_agent --cov-report=xml
```

### Test Reports
```bash
# Generate HTML test report
pytest tests/ --html=test-report.html --self-contained-html

# Generate JUnit XML report
pytest tests/ --junitxml=test-results.xml
```

## 🚀 Best Practices

### Writing New Tests

1. **Follow naming conventions**: `test_<functionality>.py`
2. **Use descriptive test names**: `test_analyze_logs_with_database_errors`
3. **Group related tests in classes**: `class TestDatabaseScenarios`
4. **Use appropriate markers**: `@pytest.mark.functional`
5. **Mock external dependencies**: Use `@patch` for API calls
6. **Include docstrings**: Explain what the test verifies
7. **Use fixtures**: Reuse common setup code
8. **Assert meaningfully**: Check specific conditions, not just "not None"

### Test Organization

1. **One concept per test**: Don't test multiple unrelated things
2. **Arrange-Act-Assert**: Clear test structure
3. **Independent tests**: Tests should not depend on each other
4. **Cleanup resources**: Use fixtures with cleanup
5. **Parameterize similar tests**: Use `@pytest.mark.parametrize`

### Performance Testing

1. **Use realistic data sizes**: Test with actual log file sizes
2. **Monitor resource usage**: Track memory and CPU
3. **Set reasonable thresholds**: Based on production requirements
4. **Test concurrency**: Verify thread safety
5. **Profile bottlenecks**: Use performance metrics

## 🔍 Troubleshooting

### Common Test Failures

1. **Module import errors**: 
   ```bash
   pip install -e .
   ```

2. **API timeout errors**:
   - Check network connectivity
   - Verify API keys are valid
   - Increase timeout values

3. **Memory errors in performance tests**:
   - Run on machine with more RAM
   - Reduce test data sizes
   - Check for memory leaks

4. **Async test issues**:
   - Ensure `pytest-asyncio` is installed
   - Use `@pytest.mark.asyncio` decorator
   - Check event loop handling

### Getting Help

1. **Check test logs**: Run with `-v` and `--tb=long`
2. **Review fixtures**: Ensure test data is correct
3. **Verify environment**: Check API keys and dependencies
4. **Run subset**: Isolate failing tests
5. **Check documentation**: Review component docs

## 📚 Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py documentation](https://coverage.readthedocs.io/)
- [LangGraph testing guide](https://langchain-ai.github.io/langgraph/)

---

**Happy Testing! 🧪✨**