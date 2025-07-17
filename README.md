# Log Analyzer Agent

A LangGraph-based agent that helps analyze logs, identify issues, suggest solutions, and reference relevant documentation.

## Features

- **Broad Log Analysis**: Analyzes logs from various systems and applications
- **Environment Context**: Can be configured with software and runtime environment details
- **Interactive**: Prompts user for additional information when needed
- **Documentation References**: Provides links to relevant documentation
- **Dual Model Architecture**:
  - Gemini 2.5 Flash: Primary model for analyzing large log files (via Gemini API)
  - Kimi K2: Orchestration model for managing agent tasks (via Groq API)

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file based on `.env.example` with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

## Usage

### Running the agent

```python
python main.py
```

### Using the agent in your code

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
        "primary_model": "gemini:2.5-flash",
        "orchestrator_model": "kimi:k2"
    }
}

# Get results
result = graph.invoke(input_state, config)
print(result["analysis_result"])
```

### LangGraph Server Integration

This agent can be run with the LangGraph development server to visualize and debug the agent execution through a GUI:

```
langgraph server start
```

Then open your browser to `http://localhost:8000`.

## Project Structure

- `src/log_analyzer_agent/`: Main agent code
  - `graph.py`: LangGraph state machine definition
  - `state.py`: State definitions
  - `tools.py`: Tools available to the agent
  - `configuration.py`: Configuration options
  - `prompts.py`: Prompt templates
  - `utils.py`: Utility functions
- `main.py`: Entry point script

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

Then register it in `graph.py`:

```python
# In the graph definition
model = raw_model.bind_tools(
    [search_documentation, request_additional_info, submit_analysis, my_new_tool], 
    tool_choice="any"
)
```

### Customizing Prompts

Modify the prompt templates in `src/log_analyzer_agent/prompts.py` to adjust agent behavior.

## License

MIT