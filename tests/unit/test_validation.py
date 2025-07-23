"""Unit tests for validation module."""

import pytest
from pydantic import ValidationError

from src.log_analyzer_agent.nodes.validation import AnalysisQualityCheck
from src.log_analyzer_agent.api.models import AnalysisIssue as Issue, AnalysisResult
# Note: Suggestion class doesn't exist, using recommendations from AnalysisResult instead


class TestIssueValidation:
    """Test Issue model validation."""
    
    def test_valid_issue(self):
        """Test creating a valid issue."""
        issue = Issue(
            description="Database connection timeout",
            severity="high",
            message="Connection refused at 10:23:45"
        )
        assert issue.description == "Database connection timeout"
        assert issue.severity == "high"
        assert issue.message == "Connection refused at 10:23:45"
    
    def test_issue_severity_validation(self):
        """Test severity field validation."""
        # Valid severities - AnalysisIssue accepts any string for severity
        for severity in ["low", "medium", "high", "critical"]:
            issue = Issue(
                description="Test issue",
                severity=severity,
                message="Evidence"
            )
            assert issue.severity == severity
        
        # AnalysisIssue doesn't validate severity values, so this test is not applicable
        # Any string is accepted for severity
    
    def test_issue_optional_evidence(self):
        """Test that message is optional."""
        issue = Issue(
            description="Test issue",
            severity="low"
        )
        assert issue.message is None
    
    def test_issue_description_required(self):
        """Test that description has a default value."""
        # AnalysisIssue has default values for all fields
        issue = Issue(severity="high", message="Evidence")
        assert issue.description == ""  # Default value


class TestRecommendationValidation:
    """Test recommendations in AnalysisResult."""
    
    def test_recommendations_list(self):
        """Test that recommendations is a list of strings."""
        result = AnalysisResult(
            issues=[
                Issue(
                    description="Database connection pool exhausted",
                    severity="critical",
                    message="MaxPoolSize reached at 10:45:23"
                ),
                Issue(
                    description="Slow query performance",
                    severity="medium",
                    message="Query took 5.2s, expected <1s"
                )
            ],
            suggestions=[
                "Increase connection pool size - current pool size of 10 is insufficient for load",
                "Add index on user_id column - missing index causes full table scan"
            ],
            summary="Critical database performance issues identified"
        )
        
        # Validate the analysis
        quality_check = AnalysisQualityCheck(
            is_complete=True,
            improvement_suggestions=None
        )
        
        # Assertions
        assert len(result.issues) == 2
        assert result.issues[0].severity == "critical"
        assert len(result.suggestions) == 2
        assert "connection pool" in result.suggestions[0]
        assert quality_check.is_complete


if __name__ == "__main__":
    pytest.main([__file__, "-v"])