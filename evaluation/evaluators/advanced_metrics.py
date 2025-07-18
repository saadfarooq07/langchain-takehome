"""Advanced evaluation metrics for comprehensive agent assessment.

This module provides sophisticated metrics beyond basic accuracy,
including semantic similarity, response time analysis, and more.
"""

import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from langsmith.schemas import Example, Run
from langsmith.evaluation import run_evaluator
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ..core.interfaces import Evaluator, EvaluationMetric, EvaluationResult, SystemType


class SemanticSimilarityEvaluator(Evaluator):
    """Evaluates semantic similarity between generated and expected outputs."""
    
    def __init__(self, embeddings_model: Optional[Embeddings] = None, threshold: float = 0.8):
        """Initialize the semantic similarity evaluator.
        
        Args:
            embeddings_model: Model to use for embeddings
            threshold: Similarity threshold for passing
        """
        self.embeddings = embeddings_model or GoogleGenerativeAIEmbeddings(
            model="models/embedding-001"
        )
        self.threshold = threshold
    
    def get_name(self) -> str:
        return "SemanticSimilarity"
    
    def applies_to(self, system_type: SystemType) -> bool:
        return True
    
    def get_description(self) -> str:
        return "Evaluates semantic similarity between actual and expected analysis"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate semantic similarity of the analysis."""
        actual_analysis = outputs.get("analysis_result", {})
        expected_analysis = reference.get("analysis_result", {})
        
        # Extract text representations
        actual_text = self._extract_text(actual_analysis)
        expected_text = self._extract_text(expected_analysis)
        
        if not actual_text or not expected_text:
            return EvaluationMetric(
                key="semantic_similarity",
                value=0.0,
                score=0.0,
                comment="Missing text for comparison",
                result=EvaluationResult.FAILED
            )
        
        # Calculate embeddings
        try:
            actual_embedding = await self.embeddings.aembed_query(actual_text)
            expected_embedding = await self.embeddings.aembed_query(expected_text)
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(actual_embedding, expected_embedding)
            
            # Determine result
            if similarity >= self.threshold:
                result = EvaluationResult.PASSED
            elif similarity >= self.threshold * 0.7:
                result = EvaluationResult.PARTIAL
            else:
                result = EvaluationResult.FAILED
            
            return EvaluationMetric(
                key="semantic_similarity",
                value=similarity,
                score=similarity,
                comment=f"Semantic similarity: {similarity:.3f} (threshold: {self.threshold})",
                result=result
            )
            
        except Exception as e:
            return EvaluationMetric(
                key="semantic_similarity",
                value=0.0,
                score=0.0,
                comment=f"Error calculating similarity: {str(e)}",
                result=EvaluationResult.FAILED
            )
    
    def _extract_text(self, analysis: Dict[str, Any]) -> str:
        """Extract text representation from analysis."""
        parts = []
        
        # Extract issues
        if "issues" in analysis:
            for issue in analysis["issues"]:
                parts.append(f"Issue: {issue.get('description', '')} - Severity: {issue.get('severity', '')}")
        
        # Extract suggestions
        if "suggestions" in analysis:
            for suggestion in analysis["suggestions"]:
                parts.append(f"Suggestion: {suggestion}")
        
        # Extract summary
        if "summary" in analysis:
            parts.append(f"Summary: {analysis['summary']}")
        
        return " ".join(parts)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class ResponseTimeEvaluator(Evaluator):
    """Evaluates response time and performance characteristics."""
    
    def __init__(self, 
                 p50_threshold: float = 2.0,
                 p95_threshold: float = 5.0,
                 p99_threshold: float = 10.0):
        """Initialize response time evaluator.
        
        Args:
            p50_threshold: 50th percentile threshold in seconds
            p95_threshold: 95th percentile threshold in seconds
            p99_threshold: 99th percentile threshold in seconds
        """
        self.p50_threshold = p50_threshold
        self.p95_threshold = p95_threshold
        self.p99_threshold = p99_threshold
        self.response_times = []
    
    def get_name(self) -> str:
        return "ResponseTime"
    
    def applies_to(self, system_type: SystemType) -> bool:
        return True
    
    def get_description(self) -> str:
        return "Evaluates response time performance"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate response time performance."""
        # Extract response time
        response_time = outputs.get("response_time", 0.0)
        
        if response_time <= 0:
            # Try to calculate from timestamps
            start_time = outputs.get("start_time")
            end_time = outputs.get("end_time")
            
            if start_time and end_time:
                response_time = end_time - start_time
        
        # Store for percentile calculations
        self.response_times.append(response_time)
        
        # Calculate score based on thresholds
        if response_time <= self.p50_threshold:
            score = 1.0
            performance = "Excellent"
        elif response_time <= self.p95_threshold:
            score = 0.8
            performance = "Good"
        elif response_time <= self.p99_threshold:
            score = 0.6
            performance = "Acceptable"
        else:
            score = 0.3
            performance = "Poor"
        
        # Calculate percentiles if we have enough data
        percentiles_info = ""
        if len(self.response_times) >= 10:
            p50 = np.percentile(self.response_times, 50)
            p95 = np.percentile(self.response_times, 95)
            p99 = np.percentile(self.response_times, 99)
            percentiles_info = f" | P50: {p50:.2f}s, P95: {p95:.2f}s, P99: {p99:.2f}s"
        
        return EvaluationMetric(
            key="response_time",
            value=response_time,
            score=score,
            comment=f"{performance} response time: {response_time:.2f}s{percentiles_info}",
            result=EvaluationResult.PASSED if score >= 0.6 else EvaluationResult.FAILED
        )


class DocumentationRelevanceEvaluator(Evaluator):
    """Evaluates the relevance and quality of documentation references."""
    
    def __init__(self):
        """Initialize documentation relevance evaluator."""
        self.trusted_sources = {
            "official_docs": 1.0,
            "github": 0.8,
            "stackoverflow": 0.7,
            "forum": 0.6,
            "blog": 0.5,
            "other": 0.3
        }
    
    def get_name(self) -> str:
        return "DocumentationRelevance"
    
    def applies_to(self, system_type: SystemType) -> bool:
        return True
    
    def get_description(self) -> str:
        return "Evaluates relevance and quality of documentation references"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate documentation relevance."""
        analysis_result = outputs.get("analysis_result", {})
        doc_refs = analysis_result.get("documentation_references", [])
        
        if not doc_refs:
            # Check if documentation was needed
            issues = analysis_result.get("issues", [])
            if issues:
                return EvaluationMetric(
                    key="documentation_relevance",
                    value=0,
                    score=0.0,
                    comment="No documentation provided for identified issues",
                    result=EvaluationResult.FAILED
                )
            else:
                return EvaluationMetric(
                    key="documentation_relevance",
                    value=0,
                    score=1.0,
                    comment="No documentation needed - no issues found",
                    result=EvaluationResult.PASSED
                )
        
        # Evaluate documentation quality
        total_score = 0.0
        source_counts = defaultdict(int)
        
        for ref in doc_refs:
            source_type = ref.get("source_type", "other")
            source_counts[source_type] += 1
            
            # Calculate relevance score
            base_score = self.trusted_sources.get(source_type, 0.3)
            
            # Adjust based on relevance indicators
            if ref.get("relevance_score", 0) > 0:
                base_score *= ref["relevance_score"]
            
            total_score += base_score
        
        # Calculate average score
        avg_score = total_score / len(doc_refs) if doc_refs else 0
        
        # Bonus for diversity of sources
        diversity_bonus = min(0.2, len(source_counts) * 0.05)
        final_score = min(1.0, avg_score + diversity_bonus)
        
        # Create comment
        source_summary = ", ".join(f"{k}: {v}" for k, v in source_counts.items())
        comment = f"Found {len(doc_refs)} references ({source_summary}). "
        
        if final_score >= 0.8:
            comment += "High quality documentation"
            result = EvaluationResult.PASSED
        elif final_score >= 0.6:
            comment += "Adequate documentation"
            result = EvaluationResult.PARTIAL
        else:
            comment += "Low quality or irrelevant documentation"
            result = EvaluationResult.FAILED
        
        return EvaluationMetric(
            key="documentation_relevance",
            value=len(doc_refs),
            score=final_score,
            comment=comment,
            result=result
        )


class MemoryEffectivenessEvaluator(Evaluator):
    """Evaluates how effectively memory features improve analysis."""
    
    def get_name(self) -> str:
        return "MemoryEffectiveness"
    
    def applies_to(self, system_type: SystemType) -> bool:
        return True
    
    def get_description(self) -> str:
        return "Evaluates effectiveness of memory-based improvements"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate memory effectiveness."""
        # Check if memory was used
        memory_used = outputs.get("memory_search_count", 0) > 0
        similar_issues = outputs.get("similar_issues", [])
        
        if not memory_used:
            return EvaluationMetric(
                key="memory_effectiveness",
                value=0,
                score=0.5,
                comment="Memory features not utilized",
                result=EvaluationResult.PARTIAL
            )
        
        # Evaluate memory impact
        score = 0.0
        benefits = []
        
        # Check if similar issues were found
        if similar_issues:
            score += 0.3
            benefits.append(f"Found {len(similar_issues)} similar issues")
            
            # Check if solutions from memory were used
            analysis_result = outputs.get("analysis_result", {})
            suggestions = analysis_result.get("suggestions", [])
            
            memory_solutions = []
            for issue in similar_issues:
                memory_solutions.extend(issue.get("solutions", []))
            
            if memory_solutions and suggestions:
                # Check overlap
                overlap = sum(1 for sug in suggestions if any(
                    mem_sol in sug for mem_sol in memory_solutions
                ))
                if overlap > 0:
                    score += 0.4
                    benefits.append(f"Reused {overlap} solutions from memory")
        
        # Check response time improvement
        if "performance_metrics" in outputs:
            metrics = outputs["performance_metrics"]
            if metrics.get("memory_cache_hit", False):
                score += 0.3
                benefits.append("Cache hit improved response time")
        
        # Determine result
        if score >= 0.7:
            result = EvaluationResult.PASSED
            assessment = "Highly effective"
        elif score >= 0.4:
            result = EvaluationResult.PARTIAL
            assessment = "Moderately effective"
        else:
            result = EvaluationResult.FAILED
            assessment = "Minimally effective"
        
        comment = f"{assessment} memory usage. "
        if benefits:
            comment += " | ".join(benefits)
        else:
            comment += "No clear benefits from memory usage"
        
        return EvaluationMetric(
            key="memory_effectiveness",
            value=len(similar_issues),
            score=score,
            comment=comment,
            result=result
        )


# LangSmith-compatible evaluator functions
@run_evaluator
def evaluate_semantic_similarity(run: Run, example: Example) -> Dict[str, Any]:
    """LangSmith-compatible semantic similarity evaluator."""
    evaluator = SemanticSimilarityEvaluator()
    
    outputs = {
        "analysis_result": run.outputs.get("analysis_result", {}) if run.outputs else {}
    }
    
    reference = {
        "analysis_result": example.outputs.get("analysis_result", {})
    }
    
    import asyncio
    metric = asyncio.run(evaluator.evaluate(outputs, reference))
    
    return {
        "key": metric.key,
        "score": metric.score,
        "comment": metric.comment
    }


@run_evaluator
def evaluate_response_time(run: Run, example: Example) -> Dict[str, Any]:
    """LangSmith-compatible response time evaluator."""
    # Calculate response time from run
    response_time = 0.0
    
    if hasattr(run, 'start_time') and hasattr(run, 'end_time'):
        response_time = (run.end_time - run.start_time).total_seconds()
    elif hasattr(run, 'latency'):
        response_time = run.latency / 1000.0  # Convert ms to seconds
    
    return {
        "key": "response_time",
        "score": 1.0 if response_time < 2.0 else 0.5 if response_time < 5.0 else 0.0,
        "value": response_time,
        "comment": f"Response time: {response_time:.2f}s"
    }


@run_evaluator
def evaluate_documentation_relevance(run: Run, example: Example) -> Dict[str, Any]:
    """LangSmith-compatible documentation relevance evaluator."""
    evaluator = DocumentationRelevanceEvaluator()
    
    outputs = {
        "analysis_result": run.outputs.get("analysis_result", {}) if run.outputs else {}
    }
    
    reference = {}
    
    import asyncio
    metric = asyncio.run(evaluator.evaluate(outputs, reference))
    
    return {
        "key": metric.key,
        "score": metric.score,
        "value": metric.value,
        "comment": metric.comment
    }


@run_evaluator
def evaluate_memory_effectiveness(run: Run, example: Example) -> Dict[str, Any]:
    """LangSmith-compatible memory effectiveness evaluator."""
    evaluator = MemoryEffectivenessEvaluator()
    
    outputs = run.outputs if run.outputs else {}
    reference = {}
    
    import asyncio
    metric = asyncio.run(evaluator.evaluate(outputs, reference))
    
    return {
        "key": metric.key,
        "score": metric.score,
        "value": metric.value,
        "comment": metric.comment
    }