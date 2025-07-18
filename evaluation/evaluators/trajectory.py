"""Trajectory evaluator for analyzing agent execution paths.

This evaluator assesses the quality of the agent's decision-making process
by analyzing the sequence of actions taken during log analysis.
"""

from typing import Dict, Any, List, Optional, Tuple
from langsmith.schemas import Example, Run
from langsmith.evaluation import run_evaluator

from ..core.interfaces import Evaluator, EvaluationMetric, EvaluationResult, SystemType


class TrajectoryEvaluator(Evaluator):
    """Evaluates the quality of agent trajectories during log analysis."""
    
    def __init__(self, 
                 optimal_trajectories: Optional[Dict[str, List[str]]] = None,
                 penalize_redundant_actions: bool = True,
                 reward_efficient_paths: bool = True):
        """Initialize the trajectory evaluator.
        
        Args:
            optimal_trajectories: Known optimal action sequences for different scenarios
            penalize_redundant_actions: Whether to penalize repeated/unnecessary actions
            reward_efficient_paths: Whether to reward shorter paths that achieve the goal
        """
        self.optimal_trajectories = optimal_trajectories or self._get_default_trajectories()
        self.penalize_redundant_actions = penalize_redundant_actions
        self.reward_efficient_paths = reward_efficient_paths
    
    def _get_default_trajectories(self) -> Dict[str, List[str]]:
        """Get default optimal trajectories for common scenarios."""
        return {
            "simple_error": ["analyze_logs", "submit_analysis"],
            "needs_documentation": ["analyze_logs", "search_documentation", "analyze_logs", "submit_analysis"],
            "needs_user_input": ["analyze_logs", "request_additional_info", "handle_user_input", "analyze_logs", "submit_analysis"],
            "complex_analysis": ["analyze_logs", "search_documentation", "analyze_logs", "validate_analysis"],
            "no_issues": ["analyze_logs", "submit_analysis"]
        }
    
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        return "Trajectory"
    
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        return True  # Trajectory evaluation applies to all systems
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return "Evaluates the efficiency and correctness of agent execution trajectories"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the trajectory of agent execution.
        
        Args:
            outputs: Analysis outputs including execution trace
            reference: Reference data including expected trajectory
            
        Returns:
            EvaluationMetric with trajectory score
        """
        # Extract trajectory from outputs
        actual_trajectory = self._extract_trajectory(outputs)
        
        # Determine scenario type
        scenario_type = self._identify_scenario(reference)
        
        # Get expected trajectory
        expected_trajectory = reference.get("expected_trajectory") or \
                            self.optimal_trajectories.get(scenario_type, [])
        
        # Calculate trajectory metrics
        efficiency_score = self._calculate_efficiency(actual_trajectory, expected_trajectory)
        correctness_score = self._calculate_correctness(actual_trajectory, expected_trajectory)
        redundancy_penalty = self._calculate_redundancy_penalty(actual_trajectory)
        
        # Calculate overall score
        overall_score = (
            0.4 * efficiency_score +
            0.4 * correctness_score +
            0.2 * (1.0 - redundancy_penalty)
        )
        
        # Determine result
        if overall_score >= 0.8:
            result = EvaluationResult.PASSED
        elif overall_score >= 0.6:
            result = EvaluationResult.PARTIAL
        else:
            result = EvaluationResult.FAILED
        
        comment = self._create_comment(
            actual_trajectory, 
            expected_trajectory,
            efficiency_score,
            correctness_score,
            redundancy_penalty
        )
        
        return EvaluationMetric(
            key="trajectory",
            value=len(actual_trajectory),
            score=overall_score,
            comment=comment,
            result=result
        )
    
    def _extract_trajectory(self, outputs: Dict[str, Any]) -> List[str]:
        """Extract the execution trajectory from outputs."""
        # Look for trajectory in different possible locations
        if "trajectory" in outputs:
            return outputs["trajectory"]
        
        if "execution_trace" in outputs:
            return outputs["execution_trace"]
        
        # Try to reconstruct from messages or events
        if "messages" in outputs:
            trajectory = []
            for msg in outputs["messages"]:
                if isinstance(msg, dict) and "node" in msg:
                    trajectory.append(msg["node"])
            return trajectory
        
        # Default empty trajectory
        return []
    
    def _identify_scenario(self, reference: Dict[str, Any]) -> str:
        """Identify the scenario type from reference data."""
        log_content = reference.get("log_content", "").lower()
        expected_issues = reference.get("issues", [])
        
        # Check for different scenario types
        if not expected_issues:
            return "no_issues"
        
        if any(keyword in log_content for keyword in ["complex", "multiple", "cascading"]):
            return "complex_analysis"
        
        if "documentation" in str(reference):
            return "needs_documentation"
        
        if "user_input" in str(reference) or "additional_info" in str(reference):
            return "needs_user_input"
        
        return "simple_error"
    
    def _calculate_efficiency(self, actual: List[str], expected: List[str]) -> float:
        """Calculate efficiency score based on path length."""
        if not actual:
            return 0.0
        
        if not expected:
            # No expected trajectory, use heuristic
            # Penalize very long trajectories
            if len(actual) <= 3:
                return 1.0
            elif len(actual) <= 5:
                return 0.8
            elif len(actual) <= 7:
                return 0.6
            else:
                return max(0.3, 1.0 - (len(actual) - 7) * 0.1)
        
        # Compare lengths
        length_ratio = len(expected) / len(actual) if len(actual) > 0 else 0
        return min(1.0, length_ratio)
    
    def _calculate_correctness(self, actual: List[str], expected: List[str]) -> float:
        """Calculate correctness score based on action sequence matching."""
        if not actual or not expected:
            return 0.5  # Neutral score if no comparison possible
        
        # Check if key actions are present
        key_actions = self._extract_key_actions(expected)
        found_actions = sum(1 for action in key_actions if action in actual)
        
        if not key_actions:
            return 1.0
        
        action_coverage = found_actions / len(key_actions)
        
        # Check order preservation for key actions
        order_score = self._calculate_order_preservation(actual, key_actions)
        
        return 0.6 * action_coverage + 0.4 * order_score
    
    def _extract_key_actions(self, trajectory: List[str]) -> List[str]:
        """Extract key actions that must be present."""
        key_actions = []
        
        for action in trajectory:
            # These are critical actions that should always be present
            if action in ["analyze_logs", "submit_analysis", "validate_analysis"]:
                key_actions.append(action)
            # Tool usage is important
            elif action in ["search_documentation", "request_additional_info"]:
                key_actions.append(action)
        
        return key_actions
    
    def _calculate_order_preservation(self, actual: List[str], key_actions: List[str]) -> float:
        """Calculate how well the order of key actions is preserved."""
        if not key_actions:
            return 1.0
        
        # Find positions of key actions in actual trajectory
        positions = []
        for action in key_actions:
            if action in actual:
                positions.append(actual.index(action))
            else:
                positions.append(float('inf'))
        
        # Check if positions are in increasing order
        ordered_count = sum(1 for i in range(len(positions) - 1) 
                          if positions[i] < positions[i + 1] and positions[i] != float('inf'))
        
        max_possible = len(key_actions) - 1
        return ordered_count / max_possible if max_possible > 0 else 1.0
    
    def _calculate_redundancy_penalty(self, trajectory: List[str]) -> float:
        """Calculate penalty for redundant actions."""
        if not self.penalize_redundant_actions or len(trajectory) <= 1:
            return 0.0
        
        # Count repeated consecutive actions
        redundant_count = 0
        for i in range(1, len(trajectory)):
            if trajectory[i] == trajectory[i-1]:
                redundant_count += 1
        
        # Count excessive loops
        action_counts = {}
        for action in trajectory:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Penalize actions repeated more than necessary
        excessive_repeats = sum(max(0, count - 2) for count in action_counts.values())
        
        total_penalty = (redundant_count + excessive_repeats) / len(trajectory)
        return min(1.0, total_penalty)
    
    def _create_comment(self, actual: List[str], expected: List[str], 
                       efficiency: float, correctness: float, redundancy: float) -> str:
        """Create a detailed comment about the trajectory evaluation."""
        comments = []
        
        # Trajectory length comparison
        comments.append(f"Trajectory length: {len(actual)} steps")
        if expected:
            comments.append(f"Expected: {len(expected)} steps")
        
        # Scores
        comments.append(f"Efficiency: {efficiency:.2f}")
        comments.append(f"Correctness: {correctness:.2f}")
        
        if redundancy > 0:
            comments.append(f"Redundancy penalty: {redundancy:.2f}")
        
        # Performance assessment
        overall = (0.4 * efficiency + 0.4 * correctness + 0.2 * (1.0 - redundancy))
        if overall >= 0.8:
            performance = "Excellent"
        elif overall >= 0.6:
            performance = "Good"
        elif overall >= 0.4:
            performance = "Fair"
        else:
            performance = "Poor"
        
        # Specific feedback
        if redundancy > 0.3:
            comments.append("Consider reducing redundant actions")
        
        if efficiency < 0.6:
            comments.append("Path could be more efficient")
        
        if correctness < 0.6:
            comments.append("Missing key actions or incorrect ordering")
        
        return f"{performance} trajectory. {' | '.join(comments)}"


@run_evaluator
def evaluate_trajectory(run: Run, example: Example) -> Dict[str, Any]:
    """LangSmith-compatible trajectory evaluator function."""
    evaluator = TrajectoryEvaluator()
    
    # Extract trajectory from run
    trajectory = []
    
    # Try to get trajectory from run outputs
    if hasattr(run, 'outputs') and run.outputs:
        if 'trajectory' in run.outputs:
            trajectory = run.outputs['trajectory']
        elif 'execution_trace' in run.outputs:
            trajectory = run.outputs['execution_trace']
    
    # If not in outputs, try to reconstruct from events
    if not trajectory and hasattr(run, 'events'):
        for event in run.events:
            if event.get('event') == 'on_chain_start':
                trajectory.append(event.get('name', 'unknown'))
    
    # Create outputs dict for evaluator
    outputs = {
        'trajectory': trajectory,
        'analysis_result': run.outputs.get('analysis_result', {}) if run.outputs else {}
    }
    
    # Create reference dict
    reference = {
        'log_content': example.inputs.get('log_content', ''),
        'expected_trajectory': example.outputs.get('expected_trajectory', []),
        'issues': example.outputs.get('analysis_result', {}).get('issues', [])
    }
    
    # Run evaluation
    import asyncio
    metric = asyncio.run(evaluator.evaluate(outputs, reference))
    
    return {
        'key': metric.key,
        'score': metric.score,
        'comment': metric.comment
    }


@run_evaluator  
def evaluate_tool_usage(run: Run, example: Example) -> Dict[str, Any]:
    """Evaluate whether tools were used appropriately."""
    tool_calls = []
    
    # Extract tool calls from run
    if hasattr(run, 'outputs') and run.outputs:
        messages = run.outputs.get('messages', [])
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                tool_calls.extend(msg.tool_calls)
    
    # Check if documentation search was needed
    log_content = example.inputs.get('log_content', '').lower()
    needs_doc_search = any(keyword in log_content for keyword in 
                          ['unknown', 'unfamiliar', 'documentation', 'reference'])
    
    # Check if user input was needed
    needs_user_input = example.outputs.get('needs_user_input', False)
    
    # Evaluate tool usage
    score = 1.0
    comments = []
    
    # Check documentation search
    used_doc_search = any(tc.get('name') == 'search_documentation' for tc in tool_calls)
    if needs_doc_search and not used_doc_search:
        score -= 0.3
        comments.append("Missing documentation search")
    elif not needs_doc_search and used_doc_search:
        score -= 0.1
        comments.append("Unnecessary documentation search")
    
    # Check user input request
    requested_input = any(tc.get('name') == 'request_additional_info' for tc in tool_calls)
    if needs_user_input and not requested_input:
        score -= 0.3
        comments.append("Should have requested user input")
    elif not needs_user_input and requested_input:
        score -= 0.1
        comments.append("Unnecessary user input request")
    
    # Check for submit_analysis
    submitted = any(tc.get('name') == 'submit_analysis' for tc in tool_calls)
    if not submitted:
        score -= 0.3
        comments.append("Did not submit analysis")
    
    return {
        'key': 'tool_usage',
        'score': max(0, score),
        'comment': ' | '.join(comments) if comments else 'Appropriate tool usage'
    }