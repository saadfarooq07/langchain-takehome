"""Response time evaluator for log analysis performance."""

import time
from typing import Dict, Any, Optional
from ..core.interfaces import Evaluator, EvaluationMetric, EvaluationResult, SystemType


class ResponseTimeEvaluator(Evaluator):
    """Evaluates response time performance of log analysis."""
    
    def __init__(self, 
                 target_times: Optional[Dict[SystemType, float]] = None,
                 timeout_threshold: float = 120.0):
        """Initialize the evaluator.
        
        Args:
            target_times: Target response times per system type (in seconds)
            timeout_threshold: Maximum acceptable response time (in seconds)
        """
        self.target_times = target_times or {
            SystemType.DISTRIBUTED: 30.0,
            SystemType.SUPERCOMPUTER: 60.0,
            SystemType.SERVER: 20.0,
            SystemType.OS: 15.0,
            SystemType.APPLICATION: 10.0,
            SystemType.MOBILE: 10.0,
            SystemType.STANDALONE: 10.0
        }
        self.timeout_threshold = timeout_threshold
    
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        return "ResponseTime"
    
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        return True  # Response time evaluation applies to all system types
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return "Evaluates the response time performance of log analysis"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the response time performance.
        
        Args:
            outputs: Analysis outputs from the system
            reference: Reference data including system type and log characteristics
            
        Returns:
            EvaluationMetric with response time score
        """
        # Extract response time
        response_time = outputs.get("response_time", 0.0)
        
        # If response time is not provided, try to extract from timestamps
        if response_time == 0.0:
            start_time = outputs.get("start_time", 0.0)
            end_time = outputs.get("end_time", 0.0)
            if start_time and end_time:
                response_time = end_time - start_time
        
        # Extract system type
        system_type_str = reference.get("system_type", "application")
        try:
            system_type = SystemType(system_type_str)
        except ValueError:
            system_type = SystemType.APPLICATION
        
        # Get target time for this system type
        target_time = self.target_times.get(system_type, 10.0)
        
        # Calculate score based on response time
        score = self._calculate_response_time_score(response_time, target_time)
        
        # Determine result
        if response_time > self.timeout_threshold:
            result = EvaluationResult.FAILED
        elif score >= 0.8:
            result = EvaluationResult.PASSED
        elif score >= 0.6:
            result = EvaluationResult.PARTIAL
        else:
            result = EvaluationResult.FAILED
        
        # Create comment
        comment = self._create_response_time_comment(response_time, target_time, score)
        
        return EvaluationMetric(
            key="response_time",
            value=response_time,
            score=score,
            comment=comment,
            result=result
        )
    
    def _calculate_response_time_score(self, actual_time: float, target_time: float) -> float:
        """Calculate response time score based on actual vs target time.
        
        Args:
            actual_time: Actual response time in seconds
            target_time: Target response time in seconds
            
        Returns:
            Score between 0 and 1
        """
        if actual_time <= 0:
            return 0.0
        
        # Perfect score if under target time
        if actual_time <= target_time:
            return 1.0
        
        # Gradual degradation after target time
        # Score = 1 - (excess_time / target_time)
        excess_time = actual_time - target_time
        degradation = excess_time / target_time
        
        # Cap the degradation so score doesn't go below 0
        score = max(0.0, 1.0 - degradation)
        
        # Additional penalty for very slow responses
        if actual_time > self.timeout_threshold:
            score = 0.0
        
        return score
    
    def _create_response_time_comment(self, actual_time: float, target_time: float, score: float) -> str:
        """Create a comment about response time performance."""
        if actual_time > self.timeout_threshold:
            return f"Response time exceeded timeout threshold: {actual_time:.2f}s > {self.timeout_threshold:.2f}s"
        
        if actual_time <= target_time:
            return f"Excellent response time: {actual_time:.2f}s (target: {target_time:.2f}s)"
        
        excess_time = actual_time - target_time
        percentage_over = (excess_time / target_time) * 100
        
        if score >= 0.8:
            return f"Good response time: {actual_time:.2f}s ({percentage_over:.1f}% over target)"
        elif score >= 0.6:
            return f"Acceptable response time: {actual_time:.2f}s ({percentage_over:.1f}% over target)"
        else:
            return f"Poor response time: {actual_time:.2f}s ({percentage_over:.1f}% over target)"


class ThroughputEvaluator(Evaluator):
    """Evaluates throughput performance of log analysis."""
    
    def __init__(self, 
                 target_throughput: Optional[Dict[SystemType, float]] = None):
        """Initialize the evaluator.
        
        Args:
            target_throughput: Target throughput per system type (logs per second)
        """
        self.target_throughput = target_throughput or {
            SystemType.DISTRIBUTED: 100.0,
            SystemType.SUPERCOMPUTER: 50.0,
            SystemType.SERVER: 200.0,
            SystemType.OS: 300.0,
            SystemType.APPLICATION: 500.0,
            SystemType.MOBILE: 500.0,
            SystemType.STANDALONE: 500.0
        }
    
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        return "Throughput"
    
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        return True  # Throughput evaluation applies to all system types
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return "Evaluates the throughput performance of log analysis (logs processed per second)"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the throughput performance.
        
        Args:
            outputs: Analysis outputs from the system
            reference: Reference data including system type and log characteristics
            
        Returns:
            EvaluationMetric with throughput score
        """
        # Extract throughput
        throughput = outputs.get("throughput", 0.0)
        
        # If throughput is not provided, calculate from response time and log count
        if throughput == 0.0:
            response_time = outputs.get("response_time", 0.0)
            log_count = reference.get("log_count", 1)
            
            if response_time > 0:
                throughput = log_count / response_time
        
        # Extract system type
        system_type_str = reference.get("system_type", "application")
        try:
            system_type = SystemType(system_type_str)
        except ValueError:
            system_type = SystemType.APPLICATION
        
        # Get target throughput for this system type
        target_throughput = self.target_throughput.get(system_type, 500.0)
        
        # Calculate score based on throughput
        score = self._calculate_throughput_score(throughput, target_throughput)
        
        # Determine result
        if score >= 0.8:
            result = EvaluationResult.PASSED
        elif score >= 0.6:
            result = EvaluationResult.PARTIAL
        else:
            result = EvaluationResult.FAILED
        
        # Create comment
        comment = self._create_throughput_comment(throughput, target_throughput, score)
        
        return EvaluationMetric(
            key="throughput",
            value=throughput,
            score=score,
            comment=comment,
            result=result
        )
    
    def _calculate_throughput_score(self, actual_throughput: float, target_throughput: float) -> float:
        """Calculate throughput score based on actual vs target throughput.
        
        Args:
            actual_throughput: Actual throughput in logs per second
            target_throughput: Target throughput in logs per second
            
        Returns:
            Score between 0 and 1
        """
        if actual_throughput <= 0:
            return 0.0
        
        # Score based on ratio to target
        ratio = actual_throughput / target_throughput
        
        # Cap score at 1.0 (no extra credit for exceeding target)
        score = min(1.0, ratio)
        
        return score
    
    def _create_throughput_comment(self, actual_throughput: float, target_throughput: float, score: float) -> str:
        """Create a comment about throughput performance."""
        if actual_throughput >= target_throughput:
            return f"Excellent throughput: {actual_throughput:.2f} logs/s (target: {target_throughput:.2f} logs/s)"
        
        percentage_of_target = (actual_throughput / target_throughput) * 100
        
        if score >= 0.8:
            return f"Good throughput: {actual_throughput:.2f} logs/s ({percentage_of_target:.1f}% of target)"
        elif score >= 0.6:
            return f"Acceptable throughput: {actual_throughput:.2f} logs/s ({percentage_of_target:.1f}% of target)"
        else:
            return f"Poor throughput: {actual_throughput:.2f} logs/s ({percentage_of_target:.1f}% of target)"