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
# CLI mode
python main.py

# LangGraph development server (for visualization/debugging)
langgraph dev
# Opens at http://127.0.0.1:2024 with Studio UI at https://smith.langchain.com/studio/
```

### Common Development Tasks
```bash
# No formal test suite exists - use the evaluation dataset for testing
python loghub/loghub_evaluation_dataset/example_evaluation.py

# No linting configuration found - consider adding when needed
```

## Architecture Overview

The agent follows a state machine pattern using LangGraph:

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

## Important Configuration

### langgraph.json
- Must use module path format: `"log_analyzer_agent.graph:graph"`
- NOT file path format (will cause import errors)

### Package Structure
- The package must be installed in editable mode (`pip install -e .`) for imports to work
- `src/__init__.py` must exist to make src a proper package
- All imports in the package use relative imports (e.g., `from .state import State`)

## Key Files to Understand

1. **`src/log_analyzer_agent/graph.py`**: Main workflow definition and routing logic
2. **`src/log_analyzer_agent/state.py`**: State definitions with reducer functions
3. **`src/log_analyzer_agent/nodes/analysis.py`**: Core log analysis implementation
4. **`src/log_analyzer_agent/prompts.py`**: All prompt templates
5. **`src/log_analyzer_agent/configuration.py`**: Model and parameter configuration

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