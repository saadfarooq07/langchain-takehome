"""Full graph configuration for evaluation."""

from typing import List
from ..core.interfaces import GraphConfiguration, Evaluator, SystemType
from ..evaluators.analysis_quality import AnalysisQualityEvaluator
from ..evaluators.response_time import ResponseTimeEvaluator, ThroughputEvaluator
from ..evaluators.issue_detection import IssueDetectionEvaluator
from ..evaluators.documentation_relevance import DocumentationRelevanceEvaluator
from ..evaluators.memory_efficiency import MemoryEfficiencyEvaluator


class FullGraphConfiguration(GraphConfiguration):
    """Full graph configuration for comprehensive evaluation."""
    
    def __init__(self):
        """Initialize the full configuration."""
        self.evaluators = [
            AnalysisQualityEvaluator(),
            ResponseTimeEvaluator(),
            ThroughputEvaluator(),
            IssueDetectionEvaluator(),
            DocumentationRelevanceEvaluator(),
            MemoryEfficiencyEvaluator()
        ]
    
    def get_name(self) -> str:
        """Get the name of the graph configuration."""
        return "Full"
    
    async def create_graph(self):
        """Create and return the full graph instance."""
        # Import here to avoid circular imports
        from src.log_analyzer_agent.graph import create_full_graph
        return create_full_graph()
    
    def get_evaluators(self) -> List[Evaluator]:
        """Get the evaluators applicable to this configuration."""
        return self.evaluators
    
    def get_description(self) -> str:
        """Get a description of this configuration."""
        return "Full graph configuration with all features enabled for comprehensive evaluation"
    
    def supports_memory(self) -> bool:
        """Check if this configuration supports memory features."""
        return True