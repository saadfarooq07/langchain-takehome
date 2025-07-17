"""
Comprehensive evaluation suite for log-analyzer LangGraph agent.

This package provides a complete evaluation framework with:
- LogHub dataset integration
- Custom test cases
- Multiple evaluators
- Performance benchmarking
- Clean OOP design
"""

from .engine.evaluation_engine import EvaluationEngine
from .core.interfaces import SystemType, EvaluationResult
from .providers.dataset_providers import LogHubDatasetProvider, CustomDatasetProvider
from .configurations.graph_configs import GraphConfigurationFactory

__version__ = "1.0.0"
__all__ = [
    "EvaluationEngine",
    "SystemType", 
    "EvaluationResult",
    "LogHubDatasetProvider",
    "CustomDatasetProvider", 
    "GraphConfigurationFactory"
]