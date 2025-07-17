"""Core interfaces and abstractions for the evaluation framework."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class SystemType(Enum):
    """Enumeration of system types for log analysis."""
    DISTRIBUTED = "distributed"
    SUPERCOMPUTER = "supercomputer"
    SERVER = "server"
    OS = "os"
    APPLICATION = "application"
    MOBILE = "mobile"
    STANDALONE = "standalone"

class EvaluationResult(Enum):
    """Enumeration of evaluation results."""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"

@dataclass
class EvaluationMetric:
    """Container for evaluation metric results."""
    key: str
    value: float
    score: float
    comment: str = ""
    result: EvaluationResult = EvaluationResult.PASSED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LangSmith compatibility."""
        return {
            "key": self.key,
            "value": self.value,
            "score": self.score,
            "comment": self.comment
        }

@dataclass
class LogEntry:
    """Container for log entry data."""
    content: str
    system_type: SystemType
    dataset: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_length(self) -> int:
        """Get the length of the log content."""
        return len(self.content)
    
    def has_timestamp(self) -> bool:
        """Check if log entry has a timestamp."""
        import re
        # Simple regex for common timestamp patterns
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}:\d{2}:\d{2}',  # HH:MM:SS
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO format
        ]
        
        for pattern in timestamp_patterns:
            if re.search(pattern, self.content):
                return True
        return False

class DatasetProvider(ABC):
    """Abstract base class for dataset providers."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the dataset provider."""
        pass
    
    @abstractmethod
    def load_samples(self, limit: Optional[int] = None) -> List[LogEntry]:
        """Load log samples from the dataset."""
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata about the dataset."""
        pass
    
    def get_system_types(self) -> List[SystemType]:
        """Get the system types supported by this provider."""
        return [SystemType.APPLICATION]  # Default implementation

class Evaluator(ABC):
    """Abstract base class for evaluators."""
    
    @abstractmethod
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the outputs against the reference."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        pass
    
    @abstractmethod
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        pass
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return f"Evaluator: {self.get_name()}"

class GraphConfiguration(ABC):
    """Abstract base class for graph configurations."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the graph configuration."""
        pass
    
    @abstractmethod
    async def create_graph(self):
        """Create and return the graph instance."""
        pass
    
    @abstractmethod
    def get_evaluators(self) -> List[Evaluator]:
        """Get the evaluators applicable to this configuration."""
        pass
    
    def get_description(self) -> str:
        """Get a description of this configuration."""
        return f"Graph configuration: {self.get_name()}"
    
    def supports_memory(self) -> bool:
        """Check if this configuration supports memory features."""
        return False

class BenchmarkProvider(ABC):
    """Abstract base class for benchmark providers."""
    
    @abstractmethod
    async def run_benchmark(self, graph, dataset_provider: DatasetProvider) -> Dict[str, Any]:
        """Run benchmark against the given graph and dataset."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the benchmark provider."""
        pass