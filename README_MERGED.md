# Merged Log Analyzer Agent - Usage Guide

This guide explains how to use the merged log analyzer agent that combines the original functionality with the v2 lightweight enhancements.

## Running with LangGraph Dev

The `langgraph.json` configuration now supports multiple graph modes:

```bash
# Start the development server (opens browser automatically)
langgraph dev

# Start without opening browser
langgraph dev --no-browser

# Start on a different port
langgraph dev --port 8080
```

### Available Graphs in LangGraph Studio

When you run `langgraph dev`, you'll see three graph options:

1. **log_analyzer** - Original full-featured graph with all capabilities
2. **log_analyzer_minimal** - Lightweight graph for fast processing
3. **log_analyzer_interactive** - Medium-weight graph with user interaction support

## CLI Usage

### Legacy Mode (Default)
```bash
# Run with default test log
python main.py

# Run API server (requires FastAPI dependencies)
python main.py --mode api
```

### V2 Lightweight Modes
```bash
# Minimal mode - fastest, no interactive features
python main.py --use-v2 --mode minimal --log-file example.log

# Interactive mode - supports user input requests
python main.py --use-v2 --mode interactive --log-file example.log

# Memory mode - full features with database support
python main.py --use-v2 --mode memory --log-file example.log

# Run v2 demo
python main.py --use-v2
```

## Architecture Overview

### Legacy System
- Full state with all features always enabled
- Single graph configuration
- Higher memory overhead

### V2 System
- Progressive enhancement based on needs
- Three graph configurations:
  - **Minimal**: Core analysis only
  - **Interactive**: + user input handling
  - **Memory**: + database persistence
- Optimized performance for simple use cases

### Compatibility
- All existing code continues to work
- Import either legacy or v2 components:
  ```python
  # Legacy imports
  from src.log_analyzer_agent import graph, State
  
  # V2 imports
  from src.log_analyzer_agent import GraphFactory, CoreState
  ```

## API Server (Optional)

The API server is now optional and only runs when explicitly requested:

```bash
# Start API server
python main.py --mode api

# API endpoints:
# - POST /analyze - Analyze logs
# - GET /health - Health check
# - Full docs at http://localhost:8000/docs
```

## Environment Variables

Required for all modes:
- `GEMINI_API_KEY` - Google AI API key
- `GROQ_API_KEY` - Groq API key for orchestration
- `TAVILY_API_KEY` - Tavily API key for documentation search

Optional for memory mode:
- `DATABASE_URL` - PostgreSQL connection string

## Testing Different Modes

1. **Performance Comparison**:
   ```bash
   python main_v2.py --mode benchmark
   ```

2. **Specific Log File**:
   ```bash
   # Legacy
   python main.py --log-file /path/to/log.txt
   
   # V2 minimal
   python main.py --use-v2 --mode minimal --log-file /path/to/log.txt
   ```

3. **With Docker** (for memory mode):
   ```bash
   docker-compose up -d
   python main.py --use-v2 --mode memory --log-file example.log
   ```

## Key Benefits

1. **Backward Compatibility**: All existing code works unchanged
2. **Performance**: Minimal mode is significantly faster for simple analyses
3. **Flexibility**: Choose the right mode for your use case
4. **Optional Features**: API and database are not required for basic usage
5. **Development**: Use `langgraph dev` to visualize and debug all graph modes