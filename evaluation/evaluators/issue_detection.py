"""Issue detection evaluator for log analysis accuracy."""

import re
from typing import Dict, Any, List, Set, Optional
from ..core.interfaces import Evaluator, EvaluationMetric, EvaluationResult, SystemType


class IssueDetectionEvaluator(Evaluator):
    """Evaluates accuracy of issue detection in log analysis."""
    
    def __init__(self, 
                 issue_keywords: Optional[Dict[str, List[str]]] = None,
                 severity_weights: Optional[Dict[str, float]] = None):
        """Initialize the evaluator.
        
        Args:
            issue_keywords: Keywords that indicate different types of issues
            severity_weights: Weights for different severity levels
        """
        self.issue_keywords = issue_keywords or {
            "error": ["error", "exception", "failed", "failure", "fatal", "critical"],
            "warning": ["warning", "warn", "deprecated", "timeout", "retry"],
            "performance": ["slow", "timeout", "memory", "cpu", "disk", "latency", "performance"],
            "security": ["unauthorized", "permission", "access", "security", "authentication", "ssl", "tls"],
            "network": ["connection", "network", "socket", "tcp", "udp", "dns", "http", "https"],
            "database": ["database", "sql", "query", "transaction", "deadlock", "lock", "table"]
        }
        
        self.severity_weights = severity_weights or {
            "critical": 1.0,
            "high": 0.8,
            "medium": 0.6,
            "low": 0.4,
            "info": 0.2
        }
    
    def get_name(self) -> str:
        """Get the name of the evaluator."""
        return "IssueDetection"
    
    def applies_to(self, system_type: SystemType) -> bool:
        """Check if this evaluator applies to the given system type."""
        return True  # Issue detection applies to all system types
    
    def get_description(self) -> str:
        """Get a description of what this evaluator measures."""
        return "Evaluates the accuracy of issue detection and classification in log analysis"
    
    async def evaluate(self, outputs: Dict[str, Any], reference: Dict[str, Any]) -> EvaluationMetric:
        """Evaluate the issue detection accuracy.
        
        Args:
            outputs: Analysis outputs from the system
            reference: Reference data including expected issues and log content
            
        Returns:
            EvaluationMetric with issue detection score
        """
        # Extract detected issues
        analysis_result = outputs.get("analysis_result", {})
        detected_issues = analysis_result.get("issues", [])
        
        # Extract reference issues if available
        reference_issues = reference.get("issues", [])
        
        # Extract log content for analysis
        log_content = reference.get("log_content", "")
        
        # Calculate scores
        if reference_issues:
            # Use reference issues for comparison
            precision = self._calculate_precision(detected_issues, reference_issues)
            recall = self._calculate_recall(detected_issues, reference_issues)
            f1_score = self._calculate_f1_score(precision, recall)
            
            # Evaluate severity accuracy
            severity_accuracy = self._evaluate_severity_accuracy(detected_issues, reference_issues)
            
            # Combined score
            overall_score = 0.6 * f1_score + 0.4 * severity_accuracy
            
            comment = self._create_reference_comment(precision, recall, f1_score, severity_accuracy)
        else:
            # Use heuristic evaluation based on log content
            detection_score = self._heuristic_detection_evaluation(detected_issues, log_content)
            classification_score = self._evaluate_issue_classification(detected_issues)
            
            overall_score = 0.7 * detection_score + 0.3 * classification_score
            
            comment = self._create_heuristic_comment(detection_score, classification_score, detected_issues)
        
        # Determine result
        if overall_score >= 0.8:
            result = EvaluationResult.PASSED
        elif overall_score >= 0.6:
            result = EvaluationResult.PARTIAL
        else:
            result = EvaluationResult.FAILED
        
        return EvaluationMetric(
            key="issue_detection",
            value=len(detected_issues),
            score=overall_score,
            comment=comment,
            result=result
        )
    
    def _calculate_precision(self, detected: List[Dict], reference: List[Dict]) -> float:
        """Calculate precision of issue detection."""
        if not detected:
            return 0.0
        
        true_positives = 0
        
        for detected_issue in detected:
            if self._find_matching_issue(detected_issue, reference):
                true_positives += 1
        
        return true_positives / len(detected)
    
    def _calculate_recall(self, detected: List[Dict], reference: List[Dict]) -> float:
        """Calculate recall of issue detection."""
        if not reference:
            return 1.0
        
        true_positives = 0
        
        for reference_issue in reference:
            if self._find_matching_issue(reference_issue, detected):
                true_positives += 1
        
        return true_positives / len(reference)
    
    def _calculate_f1_score(self, precision: float, recall: float) -> float:
        """Calculate F1 score from precision and recall."""
        if precision + recall == 0:
            return 0.0
        
        return 2 * precision * recall / (precision + recall)
    
    def _find_matching_issue(self, issue: Dict, issue_list: List[Dict]) -> bool:
        """Find if an issue matches any issue in the list."""
        issue_text = self._extract_issue_text(issue).lower()
        issue_keywords = self._extract_keywords(issue_text)
        
        for candidate in issue_list:
            candidate_text = self._extract_issue_text(candidate).lower()
            candidate_keywords = self._extract_keywords(candidate_text)
            
            # Check for keyword overlap
            overlap = len(issue_keywords & candidate_keywords)
            total_keywords = len(issue_keywords | candidate_keywords)
            
            if total_keywords > 0:
                similarity = overlap / total_keywords
                if similarity > 0.3:  # Threshold for matching
                    return True
        
        return False
    
    def _extract_issue_text(self, issue: Dict) -> str:
        """Extract text from an issue for comparison."""
        if isinstance(issue, dict):
            parts = []
            if "description" in issue:
                parts.append(issue["description"])
            if "type" in issue:
                parts.append(issue["type"])
            if "message" in issue:
                parts.append(issue["message"])
            return " ".join(parts)
        
        return str(issue)
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract keywords from text."""
        # Remove punctuation and split
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Remove common words
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "was", "are", "were"}
        keywords = set(words) - stopwords
        
        return keywords
    
    def _evaluate_severity_accuracy(self, detected: List[Dict], reference: List[Dict]) -> float:
        """Evaluate accuracy of severity classification."""
        if not detected or not reference:
            return 0.0
        
        correct_severities = 0
        total_matched = 0
        
        for detected_issue in detected:
            matching_ref = self._find_matching_reference_issue(detected_issue, reference)
            if matching_ref:
                total_matched += 1
                detected_severity = detected_issue.get("severity", "").lower()
                reference_severity = matching_ref.get("severity", "").lower()
                
                if detected_severity == reference_severity:
                    correct_severities += 1
                elif self._similar_severity(detected_severity, reference_severity):
                    correct_severities += 0.5
        
        return correct_severities / total_matched if total_matched > 0 else 0.0
    
    def _find_matching_reference_issue(self, issue: Dict, reference: List[Dict]) -> Optional[Dict]:
        """Find the best matching reference issue."""
        issue_text = self._extract_issue_text(issue).lower()
        issue_keywords = self._extract_keywords(issue_text)
        
        best_match = None
        best_similarity = 0
        
        for candidate in reference:
            candidate_text = self._extract_issue_text(candidate).lower()
            candidate_keywords = self._extract_keywords(candidate_text)
            
            overlap = len(issue_keywords & candidate_keywords)
            total_keywords = len(issue_keywords | candidate_keywords)
            
            if total_keywords > 0:
                similarity = overlap / total_keywords
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = candidate
        
        return best_match if best_similarity > 0.3 else None
    
    def _similar_severity(self, severity1: str, severity2: str) -> bool:
        """Check if two severities are similar."""
        severity_groups = [
            {"critical", "high", "fatal", "error"},
            {"medium", "warning", "warn"},
            {"low", "info", "notice"}
        ]
        
        for group in severity_groups:
            if severity1 in group and severity2 in group:
                return True
        
        return False
    
    def _heuristic_detection_evaluation(self, detected_issues: List[Dict], log_content: str) -> float:
        """Evaluate issue detection using heuristics when no reference is available."""
        if not log_content:
            return 0.5  # Default score
        
        # Analyze log content for potential issues
        potential_issues = self._analyze_log_content(log_content)
        
        if not potential_issues:
            # No issues in log - penalize false positives
            return 0.8 if not detected_issues else 0.4
        
        # Check if detected issues align with potential issues
        detection_score = 0.0
        
        for detected_issue in detected_issues:
            issue_text = self._extract_issue_text(detected_issue).lower()
            
            # Check if detected issue matches potential issues
            matches_potential = False
            for potential_type, indicators in potential_issues.items():
                if any(indicator in issue_text for indicator in indicators):
                    matches_potential = True
                    break
            
            if matches_potential:
                detection_score += 1.0
            else:
                detection_score += 0.2  # Penalty for false positive
        
        # Normalize by number of potential issues
        if len(potential_issues) > 0:
            detection_score /= max(len(detected_issues), len(potential_issues))
        
        return min(1.0, detection_score)
    
    def _analyze_log_content(self, log_content: str) -> Dict[str, List[str]]:
        """Analyze log content to identify potential issues."""
        log_lower = log_content.lower()
        potential_issues = {}
        
        for issue_type, keywords in self.issue_keywords.items():
            found_indicators = []
            for keyword in keywords:
                if keyword in log_lower:
                    found_indicators.append(keyword)
            
            if found_indicators:
                potential_issues[issue_type] = found_indicators
        
        return potential_issues
    
    def _evaluate_issue_classification(self, detected_issues: List[Dict]) -> float:
        """Evaluate the classification quality of detected issues."""
        if not detected_issues:
            return 0.0
        
        classification_score = 0.0
        
        for issue in detected_issues:
            score = 0.0
            
            # Check for proper structure
            if isinstance(issue, dict):
                score += 0.2
                
                # Check for required fields
                if "type" in issue or "category" in issue:
                    score += 0.3
                
                if "severity" in issue:
                    severity = issue["severity"].lower()
                    if severity in self.severity_weights:
                        score += 0.2
                
                if "description" in issue:
                    description = issue["description"]
                    if len(description) > 10:  # Meaningful description
                        score += 0.3
            
            classification_score += score
        
        return classification_score / len(detected_issues)
    
    def _create_reference_comment(self, precision: float, recall: float, f1_score: float, severity_accuracy: float) -> str:
        """Create comment for reference-based evaluation."""
        comments = []
        
        comments.append(f"Precision: {precision:.3f}")
        comments.append(f"Recall: {recall:.3f}")
        comments.append(f"F1-Score: {f1_score:.3f}")
        comments.append(f"Severity Accuracy: {severity_accuracy:.3f}")
        
        if f1_score >= 0.8:
            performance = "Excellent"
        elif f1_score >= 0.6:
            performance = "Good"
        elif f1_score >= 0.4:
            performance = "Fair"
        else:
            performance = "Poor"
        
        return f"{performance} issue detection performance. {' | '.join(comments)}"
    
    def _create_heuristic_comment(self, detection_score: float, classification_score: float, detected_issues: List[Dict]) -> str:
        """Create comment for heuristic evaluation."""
        comments = []
        
        comments.append(f"Detection Score: {detection_score:.3f}")
        comments.append(f"Classification Score: {classification_score:.3f}")
        comments.append(f"Issues Found: {len(detected_issues)}")
        
        if detection_score >= 0.8:
            performance = "Excellent"
        elif detection_score >= 0.6:
            performance = "Good"
        elif detection_score >= 0.4:
            performance = "Fair"
        else:
            performance = "Poor"
        
        return f"{performance} heuristic issue detection. {' | '.join(comments)}"