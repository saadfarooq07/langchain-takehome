"""Memory-enabled graph configuration for evaluation."""

from typing import List
from ..core.interfaces import GraphConfiguration, Evaluator, SystemType
from ..evaluators.analysis_quality import AnalysisQualityEvaluator
from ..evaluators.response_time import ResponseTimeEvaluator, ThroughputEvaluator
from ..evaluators.issue_detection import IssueDetectionEvaluator
from ..evaluators.documentation_relevance import DocumentationRelevanceEvaluator
from ..evaluators.memory_efficiency import MemoryEfficiencyEvaluator, MemoryScalabilityEvaluator


class MemoryGraphConfiguration(GraphConfiguration):
    """Memory-enabled graph configuration for evaluation."""
    
    def __init__(self):
        """Initialize the memory configuration."""
        self.evaluators = [
            AnalysisQualityEvaluator(),
            ResponseTimeEvaluator(timeout_threshold=90.0),  # Allow more time for memory features
            ThroughputEvaluator(),
            IssueDetectionEvaluator(),
            DocumentationRelevanceEvaluator(),
            MemoryEfficiencyEvaluator(),
            MemoryScalabilityEvaluator()
        ]
    
    def get_name(self) -> str:
        """Get the name of the graph configuration."""
        return "Memory"
    
    async def create_graph(self):
        """Create and return the memory-enabled graph instance."""
        # Import here to avoid circular imports
        from src.log_analyzer_agent.graph import create_graph_with_memory
        return create_graph_with_memory()
    
    def get_evaluators(self) -> List[Evaluator]:
        """Get the evaluators applicable to this configuration."""
        return self.evaluators
    
    def get_description(self) -> str:
        """Get a description of this configuration."""
        return "Memory-enabled graph configuration with persistence and context features"
    
    def supports_memory(self) -> bool:
        """Check if this configuration supports memory features."""
        return True