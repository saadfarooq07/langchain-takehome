# AGENTS.md - Coding Agent Guidelines

## Build/Test Commands
```bash
pip install -e .                                    # Install package in editable mode (REQUIRED)
python main.py                                      # Run CLI mode
langgraph dev                                       # Run development server with Studio UI
python loghub/loghub_evaluation_dataset/example_evaluation.py  # Run evaluation tests
```

## Code Style Guidelines
- **Imports**: Use relative imports within package (e.g., `from .state import State`)
- **Type Hints**: Always use type hints for function parameters and returns
- **Docstrings**: Use triple quotes for all functions/classes with clear descriptions
- **Async/Await**: Use async functions for all node implementations
- **State Management**: All data flows through `State` class with proper reducers
- **Error Handling**: Validate inputs early, return structured errors in state
- **File Structure**: Keep nodes in `src/log_analyzer_agent/nodes/`, tools in `tools.py`
- **Configuration**: Use `Configuration.from_runnable_config(config)` for settings
- **LangGraph**: Module paths in langgraph.json (e.g., `log_analyzer_agent.graph:graph`)
- **Environment**: All API keys required: GEMINI_API_KEY, GROQ_API_KEY, TAVILY_API_KEY