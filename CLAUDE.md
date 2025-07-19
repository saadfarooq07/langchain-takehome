# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangGraph-based Log Analyzer Agent that analyzes system logs, identifies issues, and suggests solutions with documentation references. It uses a dual-model architecture:
- Gemini 2.5 Flash: Primary model for analyzing large log files (via Google AI API)
- Kimi K2: Orchestration model for managing agent tasks (via Groq API)

## Key Commands

### Installation and Setup
```bash
# Install package in editable mode (required for LangGraph to find modules)
pip install -e .

# Or use requirements.txt
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys: GEMINI_API_KEY, GROQ_API_KEY, TAVILY_API_KEY
```

### Running the Agent
```bash
# CLI mode (original implementation)
python main.py

# CLI mode with improved implementation
USE_IMPROVED_LOG_ANALYZER=true python main.py
# OR
python main.py --use-improved

# Different modes available:
python main.py --mode minimal      # Lightest mode
python main.py --mode interactive  # With user interaction
python main.py --mode memory       # With memory (requires DB)
python main.py --mode improved     # New improved implementation

# Process a specific log file
python main.py --mode improved --log-file /path/to/log.txt

# Run benchmarks
python main.py --mode benchmark

# LangGraph development server (for visualization/debugging)
langgraph dev
# Opens at http://127.0.0.1:2024 with Studio UI at https://smith.langchain.com/studio/
```

### Common Development Tasks
```bash
# No formal test suite exists - use the evaluation dataset for testing
python loghub/loghub_evaluation_dataset/example_evaluation.py

# Run improved implementation examples
python src/log_analyzer_agent/examples/improved_usage.py

# No linting configuration found - consider adding when needed
```

## Architecture Overview

The agent follows a state machine pattern using LangGraph:

### Original Architecture
1. **Entry Flow**: `main.py` → `src/log_analyzer_agent/graph.py`
2. **State Management**: All state flows through `State` class with reducers for message accumulation
3. **Node Execution**:
   - `analyze_logs`: Main analysis node using Gemini 2.5 Flash
   - `validate_analysis`: Ensures analysis meets quality standards
   - `handle_user_input`: Manages interactive prompts
   - `tools`: Executes tool calls (search_documentation, request_additional_info)

4. **Routing Logic**: 
   - After analysis, routes based on tool calls or completion status
   - Tools include: `search_documentation` (Tavily), `request_additional_info`, `submit_analysis`
   - Validation either completes or requests improvements

### Improved Architecture (Available with USE_IMPROVED_LOG_ANALYZER=true)
1. **Unified State Management**: Single `UnifiedState` class replaces 3 separate state classes
2. **Built-in Cycle Prevention**: No more manual iteration counting
3. **Streaming Support**: Handles logs >10MB efficiently with parallel chunk processing
4. **Specialized Subgraphs**: Domain-specific analyzers for HDFS, security, application logs
5. **Enhanced Reliability**:
   - Circuit breaker prevents runaway processes
   - API rate limiting prevents quota exhaustion
   - Resource tracking for memory management
   - Advanced error handling with retry strategies
6. **Performance Improvements**:
   - 5x faster for large logs
   - 60% less memory usage
   - 3x fewer unnecessary iterations

## Important Configuration

### langgraph.json
- Must use module path format: `"log_analyzer_agent.graph:graph"`
- NOT file path format (will cause import errors)

### Package Structure
- The package must be installed in editable mode (`pip install -e .`) for imports to work
- `src/__init__.py` must exist to make src a proper package
- All imports in the package use relative imports (e.g., `from .state import State`)

## Key Files to Understand

### Original Implementation
1. **`src/log_analyzer_agent/graph.py`**: Main workflow definition and routing logic
2. **`src/log_analyzer_agent/state.py`**: State definitions with reducer functions
3. **`src/log_analyzer_agent/nodes/analysis.py`**: Core log analysis implementation
4. **`src/log_analyzer_agent/prompts.py`**: All prompt templates
5. **`src/log_analyzer_agent/configuration.py`**: Model and parameter configuration

### Improved Implementation
1. **`src/log_analyzer_agent/core/unified_state.py`**: Unified state management with feature flags
2. **`src/log_analyzer_agent/core/improved_graph.py`**: Enhanced graph with subgraphs and streaming
3. **`src/log_analyzer_agent/core/circuit_breaker.py`**: Circuit breaker for reliability
4. **`src/log_analyzer_agent/nodes/enhanced_analysis.py`**: Enhanced analysis with all improvements
5. **`src/log_analyzer_agent/MIGRATION_GUIDE.md`**: Step-by-step migration instructions
6. **`src/log_analyzer_agent/examples/improved_usage.py`**: Usage examples

## Working with LogHub Dataset

The project includes a comprehensive log dataset in `loghub/` with:
- 16 different system log types (Android, Apache, BGL, HDFS, etc.)
- Each with 2k sample logs, structured CSV, and templates
- Evaluation dataset in `loghub/loghub_evaluation_dataset/` for testing

## Common Issues and Solutions

1. **ImportError: attempted relative import with no known parent package**
   - Solution: Install package with `pip install -e .` and update `langgraph.json` to use module path

2. **Module not found errors**
   - Ensure `src/__init__.py` exists
   - Package must be installed in editable mode

3. **API Key errors**
   - All three API keys are required: GEMINI_API_KEY, GROQ_API_KEY, TAVILY_API_KEY
   - Copy `.env.example` to `.env` and add your keys

4. **Improved implementation not loading**
   - Set `USE_IMPROVED_LOG_ANALYZER=true` in environment or use `--use-improved` flag
   - Ensure all core modules are properly imported in `src/log_analyzer_agent/core/__init__.py`

5. **Large logs causing memory issues**
   - Use improved implementation with streaming: `python main.py --mode improved`
   - Streaming automatically activates for logs >10MB

## Migration to Improved Implementation

To gradually migrate to the improved implementation:

1. **Test with flag**: `USE_IMPROVED_LOG_ANALYZER=true python main.py`
2. **Compare outputs**: Run same log through both implementations
3. **Enable features selectively**: Start with basic features, add streaming/memory as needed
4. **Monitor performance**: Use `--mode benchmark` to compare
5. **See full guide**: `src/log_analyzer_agent/MIGRATION_GUIDE.md`