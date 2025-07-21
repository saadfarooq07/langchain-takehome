# Log Analyzer Agent

![Docker Build](https://github.com/YOUR_USERNAME/langchain-takehome/actions/workflows/langgraph-docker-build.yml/badge.svg)
![Deploy Verification](https://github.com/YOUR_USERNAME/langchain-takehome/actions/workflows/langgraph-deploy.yml/badge.svg)
![Tests](https://github.com/YOUR_USERNAME/langchain-takehome/actions/workflows/test-suite.yml/badge.svg)

A LangGraph-based agent that helps analyze logs, identify issues, suggest solutions, and reference relevant documentation.

## Features

- **Smart Log Analysis**: Identifies errors, warnings, and patterns with actionable recommendations
- **Automatic Streaming**: Handles large logs (>10MB) with memory-efficient chunk processing
- **Specialized Analyzers**: Domain-specific analysis for:
  - HDFS/Hadoop logs (block corruption, replication, namenode/datanode issues)
  - Security logs (authentication failures, intrusion attempts, threats)
  - Application logs (HTTP errors, exceptions, performance issues)
- **High Reliability**: 
  - Circuit breaker prevents cascading failures
  - Rate limiting protects API quotas
  - Automatic retries with exponential backoff
- **Dual Model Architecture**:
  - Gemini 2.5 Flash: Primary model for analyzing large log files (via Google AI API)
  - Kimi K2: Orchestration model for managing agent tasks (via Groq API)
- **Performance Optimizations**:
  - Result caching for repeated analyses
  - Parallel chunk processing for large files
  - 5x faster than single-pass analysis
- **Interactive Mode**: Requests clarification when needed
- **Documentation Search**: Integrates with Tavily for up-to-date solutions
- **OAuth Authentication**: Sign in with Google for seamless access

## Prerequisites

- Python 3.11+
- API Keys:
  - Google AI API key (for Gemini 2.5 Flash)
  - Groq API key (for Kimi K2)
  - Tavily API key (for documentation search)
  - (Optional) LangChain API key for LangSmith tracing

## Setup

### Option 1: Quick Setup

1. Clone this repository
2. Install the package in editable mode:
   ```bash
   pip install -e .
   ```
3. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
4. Add your API keys to `.env`:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   LANGCHAIN_API_KEY=your_langchain_api_key_here  # Optional
   ```

### Option 2: Docker Setup

```bash
docker-compose up
```

## Usage

### Quick Start

```bash
# Start the backend API server
uv run main.py

# In another terminal, start the frontend
cd frontend
bun run start
```

That's it! The API runs on http://localhost:8000 and the frontend on http://localhost:3000

### API Documentation

Once the server is running, visit http://localhost:8000/docs for interactive API documentation.

### Testing the Setup

Run the test script to verify everything is working:

```bash
python test_setup.py
```

### Using in Your Code

```python
from src.log_analyzer_agent import graph, InputState

# Prepare your log content
log_content = """
2023-08-15T14:25:12.345Z ERROR [app.main] Failed to connect to database: Connection refused
2023-08-15T14:25:14.123Z FATAL [app.main] Application startup failed: Database connection error
"""

# Optional environment details
environment_details = {
    "software": "MyApp v1.2.3",
    "database": "PostgreSQL 14.5",
    "runtime": "Python 3.9 on Ubuntu 22.04"
}

# Create input state
input_state = {
    "log_content": log_content,
    "environment_details": environment_details
}

# Run the graph
config = {
    "configurable": {
        "primary_model": "gemini:gemini-2.5-flash",
        "orchestrator_model": "kimi:k2"
    }
}

# Get results
result = graph.invoke(input_state, config)
print(result["analysis_result"])
```

## Project Structure

```
.
├── src/log_analyzer_agent/     # Main agent code
│   ├── api/                    # API endpoints
│   ├── nodes/                  # Graph nodes
│   │   ├── analysis.py         # Log analysis node
│   │   ├── user_input.py       # User interaction node
│   │   └── validation.py       # Validation node
│   ├── services/               # Service layer
│   ├── graph.py                # LangGraph state machine
│   ├── state.py                # State definitions
│   ├── tools.py                # Agent tools
│   ├── configuration.py        # Configuration
│   ├── prompts.py              # Prompt templates
│   └── utils.py                # Utilities
├── evaluation/                 # Evaluation framework
│   ├── benchmark/              # Benchmarking tools
│   ├── configurations/         # Test configurations
│   ├── evaluators/             # Custom evaluators
│   └── scripts/                # Evaluation scripts
├── tests/                      # Unit tests
├── docs/                       # Documentation
├── frontend/                   # Web UI (React)
└── main.py                     # CLI entry point
```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_system.py
```

### Running Evaluations

```bash
# Run evaluation with LangSmith
python evaluation/scripts/evaluate_simple.py

# Run demo evaluation (no API calls)
python evaluation/scripts/evaluate_simple_demo.py
```

### Code Style

- Use type hints for all function parameters and returns
- Follow relative imports within the package
- Add docstrings to all functions and classes
- Use async/await for node implementations

## Extending the Agent

### Adding New Tools

Add new tools in `src/log_analyzer_agent/tools.py`:

```python
@tool
async def my_new_tool(
    params: Dict[str, Any],
    *,
    state: Annotated[State, InjectedState],
) -> str:
    """Description of what this tool does.
    
    Args:
        params: Parameters for the tool
        
    Returns:
        Tool result
    """
    # Tool implementation
    return "Result"
```

### Customizing Prompts

Modify the prompt templates in `src/log_analyzer_agent/prompts.py` to adjust agent behavior.

## CI/CD

This project uses GitHub Actions for continuous integration and deployment verification:

- **Docker Build**: Automatically builds and tests Docker images on every push
- **Deploy Verification**: Validates LangGraph configuration and deployment readiness
- **Test Suite**: Runs unit and integration tests across Python 3.9, 3.10, and 3.11

### Setting up GitHub Actions

1. Add the following secrets to your repository (Settings → Secrets → Actions):
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - `TAVILY_API_KEY`
   - `LANGCHAIN_API_KEY` (optional, for deployment)

2. Push to trigger workflows:
   ```bash
   git add .github/workflows/
   git commit -m "Add GitHub Actions workflows"
   git push
   ```

3. Monitor workflow runs in the Actions tab of your repository

### Manual Workflow Triggers

- **Verify Secrets**: Run manually to check if all secrets are configured correctly
  ```bash
  gh workflow run verify-secrets.yml
  ```

## Troubleshooting

### Common Issues

1. **ImportError: attempted relative import with no known parent package**
   - Solution: Install package with `pip install -e .`

2. **Module not found errors**
   - Ensure `src/__init__.py` exists
   - Package must be installed in editable mode

3. **API Key errors**
   - All three API keys are required: GEMINI_API_KEY, GROQ_API_KEY, TAVILY_API_KEY
   - Copy `.env.example` to `.env` and add your keys

4. **GitHub Actions failures**
   - Check the Actions tab for detailed logs
   - Run the verify-secrets workflow to ensure all secrets are set
   - Review `.github/workflows/README.md` for troubleshooting tips

## License

MIT