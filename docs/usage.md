# Usage Guide

This guide covers the various ways to use the Log Analyzer Agent, from command-line interface to programmatic usage and API interactions.

## Command Line Usage

The agent can be run directly from the command line with different modes:

```bash
# Minimal mode - fastest, no interactive features
python main.py --mode minimal --log-file path/to/logfile.log

# Interactive mode - supports user input requests
python main.py --mode interactive --log-file path/to/logfile.log

# Memory mode - full features with database support
python main.py --mode memory --log-file path/to/logfile.log --user-id demo_user --app-name myapp

# Run interactive demo (prompts for input)
python main.py
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `--mode` | Operation mode: minimal, interactive, memory, or api |
| `--log-file` | Path to log file for analysis |
| `--user-id` | User ID for Memory mode (default: demo_user) |
| `--app-name` | Application name for Memory mode (default: demo_app) |
| `--verbose` | Enable verbose output |
| `--config` | Path to configuration JSON file |

## Programmatic Usage

### Basic Integration

```python
from src.log_analyzer_agent import GraphFactory

# Create a graph with your preferred mode
graph = GraphFactory.create_graph(mode="interactive")

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
result = graph.invoke(input_state)
print(result["analysis_result"])
```

### Advanced Configuration

```python
# Custom configuration
config = {
    "configurable": {
        "primary_model": "gemini:gemini-2.5-flash",  # Model for log analysis
        "orchestrator_model": "kimi:k2",             # Model for agent orchestration
        "streaming": True,                           # Enable streaming responses
        "max_tokens": 8192                           # Maximum tokens for analysis
    }
}

# Run with configuration
result = graph.invoke(input_state, config)
```

### Streaming Output

```python
from src.log_analyzer_agent.streaming import StreamingLogAnalyzer

# Create streaming analyzer
analyzer = StreamingLogAnalyzer()

# Define callbacks
def on_token(token):
    print(token, end="", flush=True)

def on_tool_start(tool, inputs):
    print(f"\n[Tool started: {tool}]")

def on_tool_end(tool, output):
    print(f"\n[Tool completed: {tool}]")

def on_complete(result):
    print("\n\nAnalysis complete!")

# Run with streaming
analyzer.stream_with_callback(
    log_content=log_content,
    on_token=on_token,
    on_tool_start=on_tool_start,
    on_tool_end=on_tool_end,
    on_complete=on_complete
)
```

## Using with LangGraph Dev

The agent integrates with LangGraph Dev for visual inspection and debugging:

```bash
# Start LangGraph Dev server
langgraph dev
```

Then access the UI at `http://localhost:8000` and select one of the available graphs:
- log_analyzer_minimal
- log_analyzer_interactive
- log_analyzer_memory

This provides a visual interface to see:
- Graph structure and execution flow
- Messages between nodes
- Tool calls and responses
- State at each step

## API Usage

When running in API mode, the agent provides a RESTful interface:

```bash
# Start the API server
python main.py --mode api
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze` | POST | Analyze log content |
| `/api/v1/history` | GET | Get analysis history |
| `/api/v1/memory/search` | POST | Search memory for similar issues |
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login user |

### Example API Requests

#### Analyze Logs

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "log_content": "2023-08-15T14:25:12.345Z ERROR [app.main] Failed to connect to database: Connection refused",
    "environment_details": {
      "software": "MyApp v1.2.3",
      "database": "PostgreSQL 14.5"
    }
  }'
```

#### Search Memory (requires auth)

```bash
curl -X POST http://localhost:8000/api/v1/memory/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "application_name": "myapp",
    "query": "database connection"
  }'
```

## Example Scenarios

### Analyzing Application Logs

```python
from src.log_analyzer_agent import GraphFactory

# Load log file
with open("app_logs.txt", "r") as f:
    log_content = f.read()

# Create environment context
env_details = {
    "software": "MyApp v1.2.3",
    "framework": "Django 4.1",
    "database": "PostgreSQL 14.5",
    "runtime": "Python 3.9 on Ubuntu 22.04"
}

# Create graph
graph = GraphFactory.create_graph(mode="interactive")

# Run analysis
result = graph.invoke({
    "log_content": log_content,
    "environment_details": env_details
})

# Process results
analysis = result["analysis_result"]
print(f"Issues found: {len(analysis['issues'])}")
for issue in analysis["issues"]:
    print(f"- {issue['severity'].upper()}: {issue['description']}")
    print(f"  Suggestion: {issue['suggestion']}")
```

### Using Memory to Track Recurring Issues

```python
from src.log_analyzer_agent import GraphFactory

# Create memory-enabled graph
graph = GraphFactory.create_graph(mode="memory")

# Run analysis with user and app context
result = graph.invoke({
    "log_content": log_content,
    "environment_details": env_details,
    "user_id": "user123",
    "application_name": "production-api"
})

# Access memory information
if "memory_matches" in result:
    print("Similar past issues:")
    for match in result["memory_matches"]:
        print(f"- {match['timestamp']}: {match['issue_type']}")
        print(f"  Solution: {match['solution']}")
```