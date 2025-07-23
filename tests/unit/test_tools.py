"""Unit tests for tools module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.log_analyzer_agent.tools import (
    CommandSuggestionEngine,
    search_documentation,
    request_additional_info,
    submit_analysis,
    _categorize_source
)
from src.log_analyzer_agent.state import CoreWorkingState


class TestCommandSuggestionEngine:
    """Test the command suggestion engine."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = CommandSuggestionEngine()
    
    def test_memory_issue_commands(self):
        """Test commands suggested for memory issues."""
        issues = [{
            "type": "memory",
            "description": "Out of memory error detected"
        }]
        
        suggestions = self.engine.suggest_commands({}, issues)
        
        # Should include memory-related commands
        commands = [s["command"] for s in suggestions]
        assert "free -h" in commands
        assert "ps aux --sort=-%mem | head -20" in commands
        assert "dmesg | grep -i memory" in commands
    
    def test_disk_issue_commands(self):
        """Test commands suggested for disk issues."""
        issues = [{
            "type": "storage",
            "description": "Disk space critically low"
        }]
        
        suggestions = self.engine.suggest_commands({}, issues)
        
        commands = [s["command"] for s in suggestions]
        assert "df -h" in commands
        assert "du -sh /* 2>/dev/null | sort -h" in commands
        assert "lsblk" in commands
    
    def test_network_issue_commands(self):
        """Test commands suggested for network issues."""
        issues = [{
            "type": "network",
            "description": "Connection timeout to database server"
        }]
        
        suggestions = self.engine.suggest_commands({}, issues)
        
        commands = [s["command"] for s in suggestions]
        assert "netstat -tuln" in commands
        assert "ss -s" in commands
        assert "ip addr show" in commands
    
    def test_process_issue_commands(self):
        """Test commands suggested for process issues."""
        issues = [{
            "type": "service",
            "description": "Service crashed unexpectedly"
        }]
        
        suggestions = self.engine.suggest_commands({}, issues)
        
        commands = [s["command"] for s in suggestions]
        assert "systemctl status" in commands
        assert "journalctl -xe --since '1 hour ago'" in commands
        assert any("ps aux" in cmd for cmd in commands)
    
    def test_permission_issue_commands(self):
        """Test commands suggested for permission issues."""
        issues = [{
            "type": "security",
            "description": "Permission denied when accessing log file"
        }]
        
        suggestions = self.engine.suggest_commands({}, issues)
        
        commands = [s["command"] for s in suggestions]
        assert "ls -la <path>" in commands
        assert "id" in commands
        assert "sudo -l" in commands
    
    def test_multiple_issues(self):
        """Test handling multiple issues."""
        issues = [
            {"type": "memory", "description": "High memory usage"},
            {"type": "disk", "description": "Disk full"}
        ]
        
        suggestions = self.engine.suggest_commands({}, issues)
        
        commands = [s["command"] for s in suggestions]
        # Should have commands for both issues
        assert "free -h" in commands
        assert "df -h" in commands
        
        # Should not have duplicates
        assert len(commands) == len(set(commands))
    
    def test_no_specific_issue(self):
        """Test default commands when no specific issue matches."""
        issues = [{"type": "unknown", "description": "General error"}]
        
        suggestions = self.engine.suggest_commands({}, issues)
        
        commands = [s["command"] for s in suggestions]
        # Should get general diagnostic commands
        assert "uname -a" in commands
        assert "uptime" in commands
        assert "tail -50 /var/log/syslog" in commands
    
    def test_command_descriptions(self):
        """Test that all suggestions have descriptions."""
        issues = [{"type": "memory", "description": "OOM"}]
        
        suggestions = self.engine.suggest_commands({}, issues)
        
        for suggestion in suggestions:
            assert "command" in suggestion
            assert "description" in suggestion
            assert len(suggestion["description"]) > 0


class TestSearchDocumentation:
    """Test the search_documentation tool."""
    
    @pytest.mark.asyncio
    @patch("src.log_analyzer_agent.tools.TavilySearch")
    async def test_successful_search(self, mock_tavily):
        """Test successful documentation search."""
        # Mock Tavily response
        mock_search = AsyncMock()
        mock_search.ainvoke.return_value = {
            "results": [
                {
                    "title": "Fix Database Connection Error",
                    "url": "https://docs.example.com/db-fix",
                    "snippet": "To fix connection refused error...",
                    "score": 0.95
                }
            ]
        }
        mock_tavily.return_value = mock_search
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.return_value = {"configurable": {"max_search_results": 5}}
        
        result = await search_documentation(
            "database connection refused error postgresql",
            config=mock_config
        )
        
        assert result is not None
        assert len(result) == 1
        assert result[0]["title"] == "Fix Database Connection Error"
        assert result[0]["evidence_type"] == "documentation"
        assert result[0]["relevance_score"] == 0.95
        assert result[0]["source_type"] == "official_docs"
    
    @pytest.mark.asyncio
    @patch("src.log_analyzer_agent.tools.TavilySearch")
    async def test_search_error_handling(self, mock_tavily):
        """Test error handling in search."""
        mock_search = AsyncMock()
        mock_search.ainvoke.side_effect = Exception("API error")
        mock_tavily.return_value = mock_search
        
        mock_config = MagicMock()
        
        result = await search_documentation("test query", config=mock_config)
        
        # Should return empty list on error
        assert result == []
    
    @pytest.mark.asyncio
    @patch("src.log_analyzer_agent.tools.TavilySearch")
    async def test_search_categorization(self, mock_tavily):
        """Test source categorization."""
        mock_search = AsyncMock()
        mock_search.ainvoke.return_value = {
            "results": [
                {"url": "https://github.com/org/repo", "title": "t1", "snippet": "s1"},
                {"url": "https://stackoverflow.com/questions/123", "title": "t2", "snippet": "s2"},
                {"url": "https://docs.python.org/3/", "title": "t3", "snippet": "s3"},
                {"url": "https://forum.example.com/", "title": "t4", "snippet": "s4"},
                {"url": "https://medium.com/article", "title": "t5", "snippet": "s5"},
                {"url": "https://example.com/", "title": "t6", "snippet": "s6"}
            ]
        }
        mock_tavily.return_value = mock_search
        
        mock_config = MagicMock()
        
        result = await search_documentation("test", config=mock_config)
        
        assert len(result) == 6
        assert result[0]["source_type"] == "github"
        assert result[1]["source_type"] == "stackoverflow"
        assert result[2]["source_type"] == "official_docs"
        assert result[3]["source_type"] == "forum"
        assert result[4]["source_type"] == "blog"
        assert result[5]["source_type"] == "other"


class TestCategorizeSource:
    """Test the source categorization function."""
    
    def test_github_categorization(self):
        """Test GitHub URL categorization."""
        assert _categorize_source("https://github.com/langchain/langchain") == "github"
        assert _categorize_source("https://GITHUB.COM/org/repo") == "github"
    
    def test_stackoverflow_categorization(self):
        """Test StackOverflow categorization."""
        assert _categorize_source("https://stackoverflow.com/questions/123") == "stackoverflow"
    
    def test_docs_categorization(self):
        """Test documentation site categorization."""
        assert _categorize_source("https://docs.python.org") == "official_docs"
        assert _categorize_source("https://documentation.example.com") == "official_docs"
        assert _categorize_source("https://wiki.archlinux.org") == "official_docs"
    
    def test_forum_categorization(self):
        """Test forum categorization."""
        assert _categorize_source("https://forum.example.com") == "forum"
        assert _categorize_source("https://discuss.python.org") == "forum"
        assert _categorize_source("https://community.ubuntu.com") == "forum"
    
    def test_blog_categorization(self):
        """Test blog categorization."""
        assert _categorize_source("https://blog.example.com") == "blog"
        assert _categorize_source("https://medium.com/@user/article") == "blog"
        assert _categorize_source("https://dev.to/article") == "blog"
    
    def test_other_categorization(self):
        """Test default categorization."""
        assert _categorize_source("https://example.com") == "other"
        assert _categorize_source("https://random-site.org") == "other"


class TestRequestAdditionalInfo:
    """Test the request_additional_info tool."""
    
    @pytest.mark.asyncio
    async def test_request_info_sets_flag(self):
        """Test that requesting info sets the needs_user_input flag."""
        state = CoreWorkingState(
            messages=[],
            log_content="test"
        )
        
        request = {
            "question": "What version of PostgreSQL?",
            "reason": "Need to check version-specific issues",
            "how_to_retrieve": "Run: psql --version"
        }
        
        result = await request_additional_info(request, state=state)
        
        assert state.needs_user_input is True
        assert "Request for additional information" in result
        assert "What version of PostgreSQL?" in result
        assert "Need to check version-specific issues" in result
    
    @pytest.mark.asyncio
    async def test_request_info_formats_response(self):
        """Test response formatting."""
        state = CoreWorkingState(messages=[], log_content="test", message_count=0)
        
        request = {
            "question": "Test question",
            "reason": "Test reason"
        }
        
        result = await request_additional_info(request, state=state)
        
        assert "Test question" in result
        assert "Test reason" in result


class TestSubmitAnalysis:
    """Test the submit_analysis tool."""
    
    @pytest.mark.asyncio
    async def test_submit_basic_analysis(self):
        """Test submitting basic analysis."""
        state = CoreWorkingState(
            messages=[],
            log_content="test",
            message_count=0
        )
        
        analysis = {
            "issues": [
                {"description": "Database connection failed", "severity": "high"}
            ],
            "explanations": ["Connection refused typically means..."],
            "suggestions": ["Check if database is running"],
            "documentation_references": ["https://docs.example.com"]
        }
        
        result = await submit_analysis(analysis, state=state)
        
        assert state.analysis_result == analysis
        assert "Analysis completed and submitted successfully" in result
    
    @pytest.mark.asyncio
    async def test_submit_analysis_generates_commands(self):
        """Test that submit_analysis generates diagnostic commands if missing."""
        state = CoreWorkingState(
            messages=[],
            log_content="test",
            message_count=0
        )
        
        analysis = {
            "issues": [
                {"description": "Out of memory error", "severity": "critical"}
            ]
        }
        
        result = await submit_analysis(analysis, state=state)
        
        # Should have generated diagnostic commands
        assert "diagnostic_commands" in state.analysis_result
        assert len(state.analysis_result["diagnostic_commands"]) > 0
        
        # Should include memory-related commands
        commands = [cmd["command"] for cmd in state.analysis_result["diagnostic_commands"]]
        assert "free -h" in commands
    
    @pytest.mark.asyncio
    async def test_submit_analysis_preserves_existing_commands(self):
        """Test that existing diagnostic commands are preserved."""
        state = CoreWorkingState(
            messages=[],
            log_content="test",
            message_count=0
        )
        
        existing_commands = [
            {"command": "custom-command", "description": "Custom diagnostic"}
        ]
        
        analysis = {
            "issues": [{"description": "Test issue", "severity": "low"}],
            "diagnostic_commands": existing_commands
        }
        
        result = await submit_analysis(analysis, state=state)
        
        # Should preserve the existing commands
        assert state.analysis_result["diagnostic_commands"] == existing_commands


if __name__ == "__main__":
    pytest.main([__file__, "-v"])