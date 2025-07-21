# AGENTS.md - Coding Agent Guidelines

## Build/Test Commands
```bash
pip install -e .                                    # Install package in editable mode (REQUIRED)
python main.py                                      # Run CLI mode
python main.py --mode improved                      # Run improved implementation
langgraph dev                                       # Run development server with Studio UI
python -m pytest tests/unit/test_utils.py -v       # Run single unit test
python run_unit_tests.py                            # Run all unit tests
python run_tests.py                                 # Run comprehensive test suite
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
- **Testing**: No formal linting setup; use pytest for tests; mock external API calls
- **Naming**: Use snake_case for functions/variables, PascalCase for classes