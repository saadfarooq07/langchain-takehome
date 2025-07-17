"""Analysis quality evaluator for log analysis outputs."""

import json
import re
from typing import Dict, Any, List, Optional
from ..core.interfaces import Evaluator, EvaluationMetric, EvaluationResult, SystemType


class AnalysisQualityEvaluator(Evaluator):
    """Evaluates the quality of log analysis outputs."""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """Initialize the evaluator.
        
        Args:
            weights: Custom weights for different quality aspects
        """
        self.weights = weights or {
            "completeness": 0.3,
            "accuracy": 0.3,
            "clarity": 0.2,
            "actionability": 0.2
        }
    
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        return "AnalysisQuality"
    
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        return True  # Quality evaluation applies to all system types
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return "Evaluates the overall quality of log analysis including completeness, accuracy, clarity, and actionability"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the analysis quality against reference data.
        
        Args:
            outputs: Analysis outputs from the system
            reference: Reference data for comparison
            
        Returns:
            EvaluationMetric with quality score
        """
        # Extract analysis result
        analysis_result = outputs.get("analysis_result", {})
        
        # Calculate individual quality scores
        completeness_score = self._evaluate_completeness(analysis_result, reference)
        accuracy_score = self._evaluate_accuracy(analysis_result, reference)
        clarity_score = self._evaluate_clarity(analysis_result)
        actionability_score = self._evaluate_actionability(analysis_result)
        
        # Calculate weighted overall score
        overall_score = (
            completeness_score * self.weights["completeness"] +
            accuracy_score * self.weights["accuracy"] +
            clarity_score * self.weights["clarity"] +
            actionability_score * self.weights["actionability"]
        )
        
        # Create detailed comment
        comment = self._create_quality_comment(
            completeness_score, accuracy_score, clarity_score, actionability_score
        )
        
        # Determine result based on score
        if overall_score >= 0.8:
            result = EvaluationResult.PASSED
        elif overall_score >= 0.6:
            result = EvaluationResult.PARTIAL
        else:
            result = EvaluationResult.FAILED
        
        return EvaluationMetric(
            key="analysis_quality",
            value=overall_score,
            score=overall_score,
            comment=comment,
            result=result
        )
    
    def _evaluate_completeness(self, analysis_result: Dict[str, Any], reference: Dict[str, Any]) -> float:
        """Evaluate completeness of the analysis."""
        required_fields = ["summary", "issues", "recommendations"]
        present_fields = sum(1 for field in required_fields if field in analysis_result and analysis_result[field])
        
        completeness_score = present_fields / len(required_fields)
        
        # Check if issues are properly identified
        if "issues" in analysis_result:
            issues = analysis_result["issues"]
            if isinstance(issues, list) and len(issues) > 0:
                # Bonus for having detailed issues
                has_detailed_issues = any(
                    isinstance(issue, dict) and "description" in issue and "severity" in issue
                    for issue in issues
                )
                if has_detailed_issues:
                    completeness_score = min(1.0, completeness_score + 0.1)
        
        return completeness_score
    
    def _evaluate_accuracy(self, analysis_result: Dict[str, Any], reference: Dict[str, Any]) -> float:
        """Evaluate accuracy of the analysis."""
        # If we have reference issues, compare against them
        if "issues" in reference:
            reference_issues = reference["issues"]
            detected_issues = analysis_result.get("issues", [])
            
            if not reference_issues:
                # No reference issues - penalize false positives
                return 0.8 if not detected_issues else 0.6
            
            # Calculate precision and recall
            precision = self._calculate_issue_precision(detected_issues, reference_issues)
            recall = self._calculate_issue_recall(detected_issues, reference_issues)
            
            # F1 score as accuracy measure
            if precision + recall > 0:
                accuracy = 2 * precision * recall / (precision + recall)
            else:
                accuracy = 0.0
            
            return accuracy
        
        # Without reference, use heuristic evaluation
        return self._heuristic_accuracy_evaluation(analysis_result)
    
    def _evaluate_clarity(self, analysis_result: Dict[str, Any]) -> float:
        """Evaluate clarity and readability of the analysis."""
        clarity_score = 0.0
        
        # Check summary clarity
        summary = analysis_result.get("summary", "")
        if summary:
            clarity_score += 0.3 * self._evaluate_text_clarity(summary)
        
        # Check issues clarity
        issues = analysis_result.get("issues", [])
        if issues:
            issue_clarity = sum(
                self._evaluate_text_clarity(issue.get("description", ""))
                for issue in issues
                if isinstance(issue, dict) and "description" in issue
            )
            if len(issues) > 0:
                clarity_score += 0.4 * (issue_clarity / len(issues))
        
        # Check recommendations clarity
        recommendations = analysis_result.get("recommendations", [])
        if recommendations:
            rec_clarity = sum(
                self._evaluate_text_clarity(rec.get("description", "") if isinstance(rec, dict) else str(rec))
                for rec in recommendations
            )
            if len(recommendations) > 0:
                clarity_score += 0.3 * (rec_clarity / len(recommendations))
        
        return min(1.0, clarity_score)
    
    def _evaluate_actionability(self, analysis_result: Dict[str, Any]) -> float:
        """Evaluate actionability of recommendations."""
        recommendations = analysis_result.get("recommendations", [])
        
        if not recommendations:
            return 0.0
        
        actionability_score = 0.0
        
        for rec in recommendations:
            if isinstance(rec, dict):
                # Check for specific fields that indicate actionability
                action_indicators = [
                    "commands" in rec,
                    "steps" in rec,
                    "command" in rec,
                    "action" in rec,
                    "fix" in rec
                ]
                
                # Check for specific action words in description
                description = rec.get("description", "")
                action_words = ["run", "execute", "check", "install", "configure", "restart", "update"]
                has_action_words = any(word in description.lower() for word in action_words)
                
                if any(action_indicators) or has_action_words:
                    actionability_score += 1.0
                else:
                    actionability_score += 0.5
            else:
                # String recommendation - check for action words
                description = str(rec)
                action_words = ["run", "execute", "check", "install", "configure", "restart", "update"]
                has_action_words = any(word in description.lower() for word in action_words)
                actionability_score += 0.8 if has_action_words else 0.3
        
        return min(1.0, actionability_score / len(recommendations))
    
    def _evaluate_text_clarity(self, text: str) -> float:
        """Evaluate clarity of a text passage."""
        if not text:
            return 0.0
        
        clarity_score = 0.5  # Base score
        
        # Check length (not too short, not too long)
        if 20 <= len(text) <= 200:
            clarity_score += 0.2
        
        # Check for technical terms without explanation
        technical_terms = ["error", "exception", "timeout", "memory", "cpu", "disk", "network"]
        has_technical_terms = any(term in text.lower() for term in technical_terms)
        if has_technical_terms:
            clarity_score += 0.1
        
        # Check for specific details (numbers, paths, etc.)
        has_specifics = bool(re.search(r'[0-9]+|/[a-zA-Z0-9_/]+|[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+', text))
        if has_specifics:
            clarity_score += 0.2
        
        return min(1.0, clarity_score)
    
    def _calculate_issue_precision(self, detected_issues: List[Dict], reference_issues: List[Dict]) -> float:
        """Calculate precision of issue detection."""
        if not detected_issues:
            return 0.0
        
        # Simple matching based on keywords
        matched_issues = 0
        for detected in detected_issues:
            detected_text = str(detected).lower()
            for reference in reference_issues:
                reference_text = str(reference).lower()
                # Simple keyword matching
                if self._issues_match(detected_text, reference_text):
                    matched_issues += 1
                    break
        
        return matched_issues / len(detected_issues)
    
    def _calculate_issue_recall(self, detected_issues: List[Dict], reference_issues: List[Dict]) -> float:
        """Calculate recall of issue detection."""
        if not reference_issues:
            return 1.0
        
        # Simple matching based on keywords
        matched_issues = 0
        for reference in reference_issues:
            reference_text = str(reference).lower()
            for detected in detected_issues:
                detected_text = str(detected).lower()
                # Simple keyword matching
                if self._issues_match(detected_text, reference_text):
                    matched_issues += 1
                    break
        
        return matched_issues / len(reference_issues)
    
    def _issues_match(self, text1: str, text2: str) -> bool:
        """Check if two issue descriptions match."""
        # Extract keywords from both texts
        keywords1 = set(re.findall(r'\b\w+\b', text1.lower()))
        keywords2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        # Remove common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords1 -= common_words
        keywords2 -= common_words
        
        # Check for significant overlap
        if len(keywords1) == 0 or len(keywords2) == 0:
            return False
        
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2
        
        # Jaccard similarity
        similarity = len(intersection) / len(union)
        return similarity > 0.3
    
    def _heuristic_accuracy_evaluation(self, analysis_result: Dict[str, Any]) -> float:
        """Evaluate accuracy using heuristics when no reference is available."""
        accuracy_score = 0.5  # Base score
        
        # Check for reasonable issue types
        issues = analysis_result.get("issues", [])
        if issues:
            reasonable_types = ["error", "warning", "timeout", "memory", "disk", "network", "performance"]
            has_reasonable_types = any(
                any(issue_type in str(issue).lower() for issue_type in reasonable_types)
                for issue in issues
            )
            if has_reasonable_types:
                accuracy_score += 0.2
        
        # Check for consistent severity levels
        if issues:
            severities = [issue.get("severity", "").lower() for issue in issues if isinstance(issue, dict)]
            valid_severities = ["low", "medium", "high", "critical", "info", "warning", "error"]
            has_valid_severities = all(sev in valid_severities for sev in severities if sev)
            if has_valid_severities:
                accuracy_score += 0.2
        
        # Check for logical consistency
        summary = analysis_result.get("summary", "")
        if summary and issues:
            # Summary should mention issues
            summary_lower = summary.lower()
            issue_mentioned = any(
                any(keyword in summary_lower for keyword in ["error", "issue", "problem", "warning"])
                for issue in issues
            )
            if issue_mentioned:
                accuracy_score += 0.1
        
        return min(1.0, accuracy_score)
    
    def _create_quality_comment(self, completeness: float, accuracy: float, clarity: float, actionability: float) -> str:
        """Create a detailed comment about the analysis quality."""
        comments = []
        
        if completeness >= 0.8:
            comments.append("Analysis is complete with all required sections")
        elif completeness >= 0.6:
            comments.append("Analysis is mostly complete but missing some sections")
        else:
            comments.append("Analysis is incomplete - missing key sections")
        
        if accuracy >= 0.8:
            comments.append("High accuracy in issue detection")
        elif accuracy >= 0.6:
            comments.append("Moderate accuracy in issue detection")
        else:
            comments.append("Low accuracy in issue detection")
        
        if clarity >= 0.8:
            comments.append("Clear and well-structured presentation")
        elif clarity >= 0.6:
            comments.append("Reasonably clear presentation")
        else:
            comments.append("Unclear or poorly structured presentation")
        
        if actionability >= 0.8:
            comments.append("Highly actionable recommendations")
        elif actionability >= 0.6:
            comments.append("Moderately actionable recommendations")
        else:
            comments.append("Recommendations lack actionability")
        
        overall_score = (completeness + accuracy + clarity + actionability) / 4
        
        return f"Overall quality: {overall_score:.2f}. {' | '.join(comments)}"