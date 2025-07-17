"""Minimal graph configuration for evaluation."""

from typing import List
from ..core.interfaces import GraphConfiguration, Evaluator, SystemType
from ..evaluators.analysis_quality import AnalysisQualityEvaluator
from ..evaluators.response_time import ResponseTimeEvaluator
from ..evaluators.issue_detection import IssueDetectionEvaluator


class MinimalGraphConfiguration(GraphConfiguration):
    """Minimal graph configuration for lightweight evaluation."""
    
    def __init__(self):
        """Initialize the minimal configuration."""
        self.evaluators = [
            AnalysisQualityEvaluator(),
            ResponseTimeEvaluator(timeout_threshold=60.0),
            IssueDetectionEvaluator()
        ]
    
    def get_name(self) -> str:
        """Get the name of the graph configuration."""
        return "Minimal"
    
    async def create_graph(self):
        """Create and return the minimal graph instance."""
        # Import here to avoid circular imports
        from src.log_analyzer_agent.graph import create_minimal_graph
        return create_minimal_graph()
    
    def get_evaluators(self) -> List[Evaluator]:
        """Get the evaluators applicable to this configuration."""
        return self.evaluators
    
    def get_description(self) -> str:
        """Get a description of this configuration."""
        return "Minimal graph configuration for fast, lightweight log analysis evaluation"
    
    def supports_memory(self) -> bool:
        """Check if this configuration supports memory features."""
        return False