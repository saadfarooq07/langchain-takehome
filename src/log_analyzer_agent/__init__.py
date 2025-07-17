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
from .graph import create_minimal_graph as graph  # Default graph for backward compatibility
from .state import (
    CoreState as State,  # Alias for backward compatibility
    InputState, 
    OutputState,
    CoreState,
    InteractiveState, 
    MemoryState,
    create_state_class
)
from .configuration import Configuration
from .graph_factory import GraphFactory, get_graph
from .state_compat import StateAdapter

__all__ = [
    "graph", 
    "State", 
    "InputState", 
    "OutputState", 
    "Configuration",
    "GraphFactory",
    "get_graph",
    "CoreState",
    "InteractiveState",
    "MemoryState",
    "create_state_class",
    "StateAdapter"
]

# Version info
__version__ = "2.0.0"