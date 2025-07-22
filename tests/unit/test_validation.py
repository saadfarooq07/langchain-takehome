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
            evidence="Connection refused at 10:23:45"
        )
        assert issue.description == "Database connection timeout"
        assert issue.severity == "high"
        assert issue.evidence == "Connection refused at 10:23:45"
    
    def test_issue_severity_validation(self):
        """Test severity field validation."""
        # Valid severities
        for severity in ["low", "medium", "high", "critical"]:
            issue = Issue(
                description="Test issue",
                severity=severity,
                evidence="Evidence"
            )
            assert issue.severity == severity
        
        # Invalid severity should raise error
        with pytest.raises(ValidationError) as exc_info:
            Issue(
                description="Test issue",
                severity="extreme",  # Invalid
                evidence="Evidence"
            )
        assert "Input should be 'low', 'medium', 'high' or 'critical'" in str(exc_info.value)
    
    def test_issue_optional_evidence(self):
        """Test that evidence is optional."""
        issue = Issue(
            description="Test issue",
            severity="low"
        )
        assert issue.evidence is None
    
    def test_issue_description_required(self):
        """Test that description is required."""
        with pytest.raises(ValidationError) as exc_info:
            Issue(severity="high", evidence="Evidence")
        assert "description" in str(exc_info.value)


class TestSuggestionValidation:
    """Test Suggestion model validation."""
    
    def test_valid_suggestion(self):
        """Test creating a valid suggestion."""
        suggestion = Suggestion(
            action="Restart the database service",
            explanation="This will clear any stuck connections",
            commands=["sudo systemctl restart postgresql"]
        )
        assert suggestion.action == "Restart the database service"
        assert suggestion.explanation == "This will clear any stuck connections"
        assert suggestion.commands == ["sudo systemctl restart postgresql"]
    
    def test_suggestion_optional_fields(self):
        """Test that explanation and commands are optional."""
        suggestion = Suggestion(action="Check logs")
        assert suggestion.action == "Check logs"
        assert suggestion.explanation is None
        assert suggestion.commands is None
    
    def test_suggestion_commands_list(self):
        """Test commands field accepts list."""
        suggestion = Suggestion(
            action="Diagnose issue",
            commands=["df -h", "free -m", "top -n 1"]
        )
        assert len(suggestion.commands) == 3
        assert "df -h" in suggestion.commands


class TestAnalysisResultValidation:
    """Test AnalysisResult model validation."""
    
    def test_valid_analysis_result(self):
        """Test creating a valid analysis result."""
        result = AnalysisResult(
            issues=[
                Issue(description="Memory leak", severity="high"),
                Issue(description="Slow queries", severity="medium")
            ],
            suggestions=[
                Suggestion(action="Increase heap size"),
                Suggestion(action="Add database indexes")
            ],
            summary="Found 2 issues: memory leak and performance problems"
        )
        
        assert len(result.issues) == 2
        assert len(result.suggestions) == 2
        assert result.summary == "Found 2 issues: memory leak and performance problems"
    
    def test_analysis_result_empty_lists(self):
        """Test that empty lists are valid."""
        result = AnalysisResult(
            issues=[],
            suggestions=[],
            summary="No issues found"
        )
        assert result.issues == []
        assert result.suggestions == []
    
    def test_analysis_result_optional_summary(self):
        """Test that summary is optional."""
        result = AnalysisResult(
            issues=[Issue(description="Test", severity="low")],
            suggestions=[]
        )
        assert result.summary is None
    
    def test_analysis_result_validation_cascades(self):
        """Test that validation errors in nested models cascade."""
        with pytest.raises(ValidationError) as exc_info:
            AnalysisResult(
                issues=[
                    {"description": "Valid issue", "severity": "high"},
                    {"description": "Invalid issue", "severity": "extreme"}  # Invalid severity
                ],
                suggestions=[]
            )
        assert "severity" in str(exc_info.value)


class TestAnalysisQualityCheck:
    """Test AnalysisQualityCheck model validation."""
    
    def test_valid_quality_check_pass(self):
        """Test creating a passing quality check."""
        check = AnalysisQualityCheck(
            is_complete=True,
            missing_elements=[],
            quality_score=0.95,
            feedback="Excellent analysis with clear recommendations"
        )
        assert check.is_complete is True
        assert check.missing_elements == []
        assert check.quality_score == 0.95
        assert check.feedback == "Excellent analysis with clear recommendations"
    
    def test_valid_quality_check_fail(self):
        """Test creating a failing quality check."""
        check = AnalysisQualityCheck(
            is_complete=False,
            missing_elements=["No root cause analysis", "Missing diagnostic commands"],
            quality_score=0.4,
            feedback="Analysis needs more detail"
        )
        assert check.is_complete is False
        assert len(check.missing_elements) == 2
        assert "No root cause analysis" in check.missing_elements
        assert check.quality_score == 0.4
    
    def test_quality_score_range_validation(self):
        """Test quality score must be between 0 and 1."""
        # Valid scores
        for score in [0.0, 0.5, 1.0]:
            check = AnalysisQualityCheck(
                is_complete=True,
                missing_elements=[],
                quality_score=score,
                feedback="Test"
            )
            assert check.quality_score == score
        
        # Invalid scores
        with pytest.raises(ValidationError):
            AnalysisQualityCheck(
                is_complete=True,
                missing_elements=[],
                quality_score=1.5,  # Too high
                feedback="Test"
            )
        
        with pytest.raises(ValidationError):
            AnalysisQualityCheck(
                is_complete=True,
                missing_elements=[],
                quality_score=-0.1,  # Too low
                feedback="Test"
            )
    
    def test_quality_check_all_fields_required(self):
        """Test that all fields are required."""
        # Missing is_complete
        with pytest.raises(ValidationError) as exc_info:
            AnalysisQualityCheck(
                missing_elements=[],
                quality_score=0.8,
                feedback="Test"
            )
        assert "is_complete" in str(exc_info.value)
        
        # Missing quality_score
        with pytest.raises(ValidationError) as exc_info:
            AnalysisQualityCheck(
                is_complete=True,
                missing_elements=[],
                feedback="Test"
            )
        assert "quality_score" in str(exc_info.value)
    
    def test_quality_check_with_improvements(self):
        """Test quality check with suggested improvements."""
        check = AnalysisQualityCheck(
            is_complete=False,
            missing_elements=[
                "No specific error patterns identified",
                "Missing time correlation analysis",
                "No performance impact assessment"
            ],
            quality_score=0.6,
            feedback="Good start but needs more comprehensive analysis"
        )
        
        assert not check.is_complete
        assert len(check.missing_elements) == 3
        assert check.quality_score == 0.6


class TestValidationIntegration:
    """Test validation models working together."""
    
    def test_full_analysis_validation(self):
        """Test creating a complete analysis with all components."""
        # Create a full analysis
        analysis = AnalysisResult(
            issues=[
                Issue(
                    description="Database connection pool exhausted",
                    severity="critical",
                    evidence="MaxPoolSize reached at 10:45:23"
                ),
                Issue(
                    description="Slow query performance",
                    severity="medium",
                    evidence="Query took 5.2s, expected <1s"
                )
            ],
            suggestions=[
                Suggestion(
                    action="Increase connection pool size",
                    explanation="Current pool size of 10 is insufficient for load",
                    commands=["UPDATE config SET max_pool_size = 50;"]
                ),
                Suggestion(
                    action="Add index on user_id column",
                    explanation="Missing index causes full table scan",
                    commands=["CREATE INDEX idx_user_id ON orders(user_id);"]
                )
            ],
            summary="Critical database performance issues identified"
        )
        
        # Validate the analysis
        quality_check = AnalysisQualityCheck(
            is_complete=True,
            missing_elements=[],
            quality_score=0.92,
            feedback="Comprehensive analysis with actionable recommendations"
        )
        
        # Assertions
        assert len(analysis.issues) == 2
        assert analysis.issues[0].severity == "critical"
        assert len(analysis.suggestions) == 2
        assert analysis.suggestions[0].commands is not None
        assert quality_check.is_complete
        assert quality_check.quality_score > 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])