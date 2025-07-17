"""Core interfaces and abstractions for the evaluation framework."""

from .interfaces import (
    SystemType,
    EvaluationResult,
    EvaluationMetric,
    LogEntry,
    DatasetProvider,
    Evaluator,
    GraphConfiguration
)

__all__ = [
    "SystemType",
    "EvaluationResult", 
    "EvaluationMetric",
    "LogEntry",
    "DatasetProvider",
    "Evaluator",
    "GraphConfiguration"
]