# Log Analyzer Agent

A LangGraph-based agent that analyzes logs, identifies issues, suggests solutions, and references relevant documentation.

## Features

- **Comprehensive Log Analysis**: Analyzes logs from various systems and applications
- **Multiple Operation Modes**:
  - **Minimal**: Lightweight core for fast basic analysis
  - **Interactive**: Supports user interaction for additional information
  - **Memory**: Full-featured with database persistence and context retention
- **Environment Context**: Configurable with software and runtime environment details
- **Documentation References**: Provides links to relevant documentation
- **Dual Model Architecture**:
  - Gemini 2.5 Flash: Primary model for analyzing large log files
  - Kimi K2: Orchestration model for managing agent tasks

## Setup

### Prerequisites

- Python 3.9 or higher
- API keys for Gemini, Groq, and Tavily
- PostgreSQL (only for Memory mode)

### Quick Start

1. **Clone and install dependencies**
   ```bash
   git clone <repository-url>
   cd log-analyzer-agent
   pip install -r requirements.txt
   ```

2. **Create a `.env` file based on `.env.example` with your API keys**
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   TAVILY_API_KEY=your_tavily_api_key_here
   ```

3. **Run the agent in your preferred mode**
   ```bash
   # Minimal mode - fastest, no interactive features
   python main.py --mode minimal --log-file example.log
   
   # Interactive mode - supports user input requests
   python main.py --mode interactive --log-file example.log
   
   # Memory mode - full features with database support (requires PostgreSQL)
   python main.py --mode memory --log-file example.log
   
   # Run interactive demo
   python main.py
   ```

For more detailed setup instructions including Docker configuration, see [Setup Guide](./setup.md).

## Usage

For complete usage instructions including code examples and API information, see [Usage Guide](./usage.md).

## Project Structure

```
src/
├── log_analyzer_agent/      # Main agent code
│   ├── core/                # Core functionality
│   ├── features/            # Optional features 
│   ├── nodes/               # Graph nodes
│   ├── services/            # External services
│   ├── api/                 # API components
│   └── utils/               # Utility functions
├── evaluation/              # Evaluation framework
└── examples/                # Example usage
```

## Architecture

For detailed information about the architecture including graph modes, state management, and core components, see [Architecture Guide](./architecture.md).

## Extending the Agent

For instructions on customizing and extending the agent with new tools or features, see [Extension Guide](./extending.md).

## Troubleshooting

For common issues and solutions, see [Troubleshooting Guide](./troubleshooting.md).

## License

MIT License