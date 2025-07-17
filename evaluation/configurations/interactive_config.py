"""Interactive graph configuration for evaluation."""

from typing import List
from ..core.interfaces import GraphConfiguration, Evaluator, SystemType
from ..evaluators.analysis_quality import AnalysisQualityEvaluator
from ..evaluators.response_time import ResponseTimeEvaluator
from ..evaluators.issue_detection import IssueDetectionEvaluator
from ..evaluators.documentation_relevance import DocumentationRelevanceEvaluator
from ..evaluators.memory_efficiency import MemoryEfficiencyEvaluator


class InteractiveGraphConfiguration(GraphConfiguration):
    """Interactive graph configuration for evaluation."""
    
    def __init__(self):
        """Initialize the interactive configuration."""
        self.evaluators = [
            AnalysisQualityEvaluator(),
            ResponseTimeEvaluator(timeout_threshold=75.0),  # Allow more time for interactive features
            IssueDetectionEvaluator(),
            DocumentationRelevanceEvaluator(),
            MemoryEfficiencyEvaluator()
        ]
    
    def get_name(self) -> str:
        """Get the name of the graph configuration."""
        return "Interactive"
    
    async def create_graph(self):
        """Create and return the interactive graph instance."""
        # Import here to avoid circular imports
        from src.log_analyzer_agent.graph import create_interactive_graph
        return create_interactive_graph()
    
    def get_evaluators(self) -> List[Evaluator]:
        """Get the evaluators applicable to this configuration."""
        return self.evaluators
    
    def get_description(self) -> str:
        """Get a description of this configuration."""
        return "Interactive graph configuration with user interaction support"
    
    def supports_memory(self) -> bool:
        """Check if this configuration supports memory features."""
        return False