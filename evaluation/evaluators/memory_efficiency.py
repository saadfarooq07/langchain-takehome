"""Memory efficiency evaluator for log analysis performance."""

import sys
import psutil
from typing import Dict, Any, Optional
from ..core.interfaces import Evaluator, EvaluationMetric, EvaluationResult, SystemType


class MemoryEfficiencyEvaluator(Evaluator):
    """Evaluates memory efficiency of log analysis."""
    
    def __init__(self, 
                 memory_thresholds: Optional[Dict[SystemType, float]] = None,
                 baseline_memory: Optional[float] = None):
        """Initialize the evaluator.
        
        Args:
            memory_thresholds: Memory usage thresholds per system type (MB)
            baseline_memory: Baseline memory usage for comparison (MB)
        """
        self.memory_thresholds = memory_thresholds or {
            SystemType.DISTRIBUTED: 1024.0,    # 1GB
            SystemType.SUPERCOMPUTER: 2048.0,  # 2GB
            SystemType.SERVER: 512.0,          # 512MB
            SystemType.OS: 256.0,              # 256MB
            SystemType.APPLICATION: 128.0,     # 128MB
            SystemType.MOBILE: 64.0,           # 64MB
            SystemType.STANDALONE: 128.0       # 128MB
        }
        
        self.baseline_memory = baseline_memory or 50.0  # 50MB baseline
    
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        return "MemoryEfficiency"
    
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        return True  # Memory efficiency applies to all system types
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return "Evaluates memory efficiency and usage patterns during log analysis"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the memory efficiency.
        
        Args:
            outputs: Analysis outputs from the system
            reference: Reference data including system type and log characteristics
            
        Returns:
            EvaluationMetric with memory efficiency score
        """
        # Extract memory usage metrics
        memory_usage = self._extract_memory_usage(outputs)
        
        # Extract system type
        system_type_str = reference.get("system_type", "application")
        try:
            system_type = SystemType(system_type_str)
        except ValueError:
            system_type = SystemType.APPLICATION
        
        # Get threshold for this system type
        threshold = self.memory_thresholds.get(system_type, 128.0)
        
        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score(memory_usage, threshold)
        
        # Evaluate memory patterns
        pattern_score = self._evaluate_memory_patterns(outputs)
        
        # Combined score
        overall_score = 0.7 * efficiency_score + 0.3 * pattern_score
        
        # Determine result
        if overall_score >= 0.8:
            result = EvaluationResult.PASSED
        elif overall_score >= 0.6:
            result = EvaluationResult.PARTIAL
        else:
            result = EvaluationResult.FAILED
        
        # Create comment
        comment = self._create_memory_comment(memory_usage, threshold, efficiency_score, pattern_score)
        
        return EvaluationMetric(
            key="memory_efficiency",
            value=memory_usage.get("peak_memory", 0.0),
            score=overall_score,
            comment=comment,
            result=result
        )
    
    def _extract_memory_usage(self, outputs: Dict[str, Any]) -> Dict[str, float]:
        """Extract memory usage metrics from outputs."""
        memory_usage = {}
        
        # Try to get memory metrics directly
        if "memory_usage" in outputs:
            memory_data = outputs["memory_usage"]
            if isinstance(memory_data, dict):
                memory_usage.update(memory_data)
            else:
                memory_usage["peak_memory"] = float(memory_data)
        
        # Try to get from performance metrics
        if "performance_metrics" in outputs:
            perf_metrics = outputs["performance_metrics"]
            if isinstance(perf_metrics, dict):
                memory_usage.update({
                    k: v for k, v in perf_metrics.items() 
                    if "memory" in k.lower()
                })
        
        # If no memory data available, try to estimate from current process
        if not memory_usage:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_usage = {
                    "peak_memory": memory_info.rss / 1024 / 1024,  # Convert to MB
                    "current_memory": memory_info.rss / 1024 / 1024
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Fallback to basic estimate
                memory_usage = {"peak_memory": 100.0, "current_memory": 100.0}
        
        return memory_usage
    
    def _calculate_efficiency_score(self, memory_usage: Dict[str, float], threshold: float) -> float:
        """Calculate efficiency score based on memory usage."""
        peak_memory = memory_usage.get("peak_memory", 0.0)
        
        if peak_memory <= 0:
            return 0.0
        
        # Perfect score if under baseline
        if peak_memory <= self.baseline_memory:
            return 1.0
        
        # Good score if under threshold
        if peak_memory <= threshold:
            # Linear degradation from baseline to threshold
            excess = peak_memory - self.baseline_memory
            max_excess = threshold - self.baseline_memory
            degradation = excess / max_excess * 0.2  # 20% degradation at threshold
            return 1.0 - degradation
        
        # Poor score if over threshold
        excess = peak_memory - threshold
        penalty = min(0.7, excess / threshold)  # Cap penalty at 70%
        return max(0.0, 0.8 - penalty)
    
    def _evaluate_memory_patterns(self, outputs: Dict[str, Any]) -> float:
        """Evaluate memory usage patterns."""
        pattern_score = 0.5  # Base score
        
        memory_usage = self._extract_memory_usage(outputs)
        
        # Check for memory growth patterns
        if "memory_samples" in outputs:
            samples = outputs["memory_samples"]
            if isinstance(samples, list) and len(samples) > 1:
                # Check for memory leaks (consistently increasing)
                increases = 0
                for i in range(1, len(samples)):
                    if samples[i] > samples[i-1]:
                        increases += 1
                
                leak_ratio = increases / (len(samples) - 1)
                if leak_ratio < 0.3:  # Low increase ratio is good
                    pattern_score += 0.3
                elif leak_ratio < 0.6:
                    pattern_score += 0.1
                else:
                    pattern_score -= 0.2  # Penalize potential leaks
        
        # Check for memory spikes
        peak_memory = memory_usage.get("peak_memory", 0.0)
        avg_memory = memory_usage.get("avg_memory", peak_memory)
        
        if avg_memory > 0:
            spike_ratio = peak_memory / avg_memory
            if spike_ratio < 1.5:  # Low spike ratio is good
                pattern_score += 0.2
            elif spike_ratio > 3.0:  # High spike ratio is bad
                pattern_score -= 0.2
        
        return min(1.0, max(0.0, pattern_score))
    
    def _create_memory_comment(self, memory_usage: Dict[str, float], threshold: float, 
                             efficiency_score: float, pattern_score: float) -> str:
        """Create a comment about memory efficiency."""
        comments = []
        
        peak_memory = memory_usage.get("peak_memory", 0.0)
        comments.append(f"Peak Memory: {peak_memory:.1f}MB")
        comments.append(f"Threshold: {threshold:.1f}MB")
        
        # Memory efficiency assessment
        if peak_memory <= self.baseline_memory:
            efficiency_desc = "Excellent - under baseline"
        elif peak_memory <= threshold:
            efficiency_desc = "Good - under threshold"
        elif peak_memory <= threshold * 1.5:
            efficiency_desc = "Fair - moderately over threshold"
        else:
            efficiency_desc = "Poor - significantly over threshold"
        
        comments.append(f"Efficiency: {efficiency_desc}")
        
        # Pattern assessment
        if pattern_score >= 0.8:
            pattern_desc = "Excellent patterns"
        elif pattern_score >= 0.6:
            pattern_desc = "Good patterns"
        elif pattern_score >= 0.4:
            pattern_desc = "Fair patterns"
        else:
            pattern_desc = "Poor patterns"
        
        comments.append(f"Patterns: {pattern_desc}")
        
        return " | ".join(comments)


class MemoryScalabilityEvaluator(Evaluator):
    """Evaluates memory scalability with different log sizes."""
    
    def __init__(self, 
                 scalability_thresholds: Optional[Dict[str, float]] = None):
        """Initialize the evaluator.
        
        Args:
            scalability_thresholds: Thresholds for memory scalability assessment
        """
        self.scalability_thresholds = scalability_thresholds or {
            "linear_coefficient": 2.0,      # MB per MB of log data
            "constant_overhead": 50.0,      # MB base overhead
            "max_acceptable_ratio": 5.0     # Max memory to log size ratio
        }
    
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        return "MemoryScalability"
    
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        return True  # Memory scalability applies to all system types
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return "Evaluates how memory usage scales with log size"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the memory scalability.
        
        Args:
            outputs: Analysis outputs from the system
            reference: Reference data including log size
            
        Returns:
            EvaluationMetric with memory scalability score
        """
        # Extract memory usage and log size
        memory_usage = outputs.get("memory_usage", {})
        if isinstance(memory_usage, (int, float)):
            peak_memory = float(memory_usage)
        else:
            peak_memory = memory_usage.get("peak_memory", 0.0)
        
        # Get log size
        log_size = self._estimate_log_size(reference)
        
        if log_size <= 0 or peak_memory <= 0:
            return EvaluationMetric(
                key="memory_scalability",
                value=0.0,
                score=0.0,
                comment="Insufficient data for scalability evaluation",
                result=EvaluationResult.SKIPPED
            )
        
        # Calculate memory to log size ratio
        memory_ratio = peak_memory / log_size
        
        # Calculate scalability score
        scalability_score = self._calculate_scalability_score(memory_ratio, log_size)
        
        # Determine result
        if scalability_score >= 0.8:
            result = EvaluationResult.PASSED
        elif scalability_score >= 0.6:
            result = EvaluationResult.PARTIAL
        else:
            result = EvaluationResult.FAILED
        
        # Create comment
        comment = self._create_scalability_comment(peak_memory, log_size, memory_ratio, scalability_score)
        
        return EvaluationMetric(
            key="memory_scalability",
            value=memory_ratio,
            score=scalability_score,
            comment=comment,
            result=result
        )
    
    def _estimate_log_size(self, reference: Dict[str, Any]) -> float:
        """Estimate log size in MB."""
        # Try to get log size directly
        if "log_size" in reference:
            return float(reference["log_size"])
        
        # Try to estimate from log content
        log_content = reference.get("log_content", "")
        if log_content:
            # Estimate size in MB
            size_bytes = len(log_content.encode('utf-8'))
            return size_bytes / (1024 * 1024)
        
        # Try to get from metadata
        metadata = reference.get("metadata", {})
        if "size" in metadata:
            return float(metadata["size"])
        
        # Default estimate
        return 1.0
    
    def _calculate_scalability_score(self, memory_ratio: float, log_size: float) -> float:
        """Calculate scalability score based on memory ratio and log size."""
        max_ratio = self.scalability_thresholds["max_acceptable_ratio"]
        linear_coeff = self.scalability_thresholds["linear_coefficient"]
        
        # Perfect score if ratio is reasonable
        if memory_ratio <= linear_coeff:
            return 1.0
        
        # Good score if under max acceptable ratio
        if memory_ratio <= max_ratio:
            # Linear degradation
            excess = memory_ratio - linear_coeff
            max_excess = max_ratio - linear_coeff
            degradation = (excess / max_excess) * 0.5  # 50% degradation at max
            return 1.0 - degradation
        
        # Poor score if over max acceptable ratio
        excess = memory_ratio - max_ratio
        penalty = min(0.7, excess / max_ratio)  # Cap penalty at 70%
        return max(0.0, 0.5 - penalty)
    
    def _create_scalability_comment(self, peak_memory: float, log_size: float, 
                                  memory_ratio: float, scalability_score: float) -> str:
        """Create a comment about memory scalability."""
        comments = []
        
        comments.append(f"Peak Memory: {peak_memory:.1f}MB")
        comments.append(f"Log Size: {log_size:.1f}MB")
        comments.append(f"Memory Ratio: {memory_ratio:.2f}x")
        
        # Scalability assessment
        max_ratio = self.scalability_thresholds["max_acceptable_ratio"]
        linear_coeff = self.scalability_thresholds["linear_coefficient"]
        
        if memory_ratio <= linear_coeff:
            scalability_desc = "Excellent scalability"
        elif memory_ratio <= max_ratio:
            scalability_desc = "Good scalability"
        elif memory_ratio <= max_ratio * 1.5:
            scalability_desc = "Fair scalability"
        else:
            scalability_desc = "Poor scalability"
        
        comments.append(scalability_desc)
        
        return " | ".join(comments)