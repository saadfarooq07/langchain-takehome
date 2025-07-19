"""Log Analyzer Agent

A LangGraph-based agent that analyzes logs, provides insights, and suggests
solutions with documentation references.

This agent can:
- Analyze logs from various systems and applications
- Identify issues, errors, and anomalies
- Provide explanations and suggested solutions
- Reference relevant documentation
- Request additional information when needed

Version 2.0 adds:
- Lightweight core state with progressive enhancement
- Optional memory and interactive features
- Improved performance for simple use cases
"""

# Main imports
from .graph import (
    create_minimal_graph as graph,
)  # Default graph for backward compatibility
from .state import (
    CoreState as State,  # Alias for backward compatibility
    InputState,
    OutputState,
    CoreState,
    InteractiveState,
    MemoryState,
    create_state_class,
)
from .configuration import Configuration
from .graph_factory import GraphFactory, get_graph, create_improved_analyzer
from .state_compat import StateAdapter

# Conditionally import improved components
import os
if os.getenv("USE_IMPROVED_LOG_ANALYZER", "false").lower() == "true":
    try:
        from .core import (
            UnifiedState,
            LogAnalysisInput,
            LogAnalysisOutput,
            create_improved_graph,
            CircuitBreaker,
            ExecutionController,
            APIManager,
            ResourceManager,
            ErrorRecoveryManager,
        )
        IMPROVED_AVAILABLE = True
    except ImportError:
        IMPROVED_AVAILABLE = False
else:
    IMPROVED_AVAILABLE = False

__all__ = [
    "graph",
    "State",
    "InputState",
    "OutputState",
    "Configuration",
    "GraphFactory",
    "get_graph",
    "create_improved_analyzer",
    "CoreState",
    "InteractiveState",
    "MemoryState",
    "create_state_class",
    "StateAdapter",
]

# Add improved components to exports if available
if IMPROVED_AVAILABLE:
    __all__.extend([
        "UnifiedState",
        "LogAnalysisInput",
        "LogAnalysisOutput",
        "create_improved_graph",
        "CircuitBreaker",
        "ExecutionController",
        "APIManager",
        "ResourceManager",
        "ErrorRecoveryManager",
    ])

# Version info
__version__ = "2.1.0"  # Bumped for improved implementation
