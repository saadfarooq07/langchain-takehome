"""
Unit tests for all node implementations in the Log Analyzer Agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from src.log_analyzer_agent.nodes.analysis import analyze_logs
from src.log_analyzer_agent.nodes.validation import validate_analysis
from src.log_analyzer_agent.nodes.user_input import handle_user_input
from src.log_analyzer_agent.nodes.enhanced_analysis import enhanced_analyze_logs
from src.log_analyzer_agent.state import State
from src.log_analyzer_agent.configuration import Configuration


class TestAnalysisNode:
    """Test the main analysis node."""
    
    @pytest.fixture
    def mock_state(self, sample_log_content):
        """Create a mock state for testing."""
        state = State()
        state.log_content = sample_log_content
        state.messages = []
        state.iteration_count = 0
        return state
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "configurable": {
                "primary_model": "gemini-2.5-flash",
                "max_iterations": 5
            }
        }
    
    @pytest.mark.asyncio
    async def test_analyze_logs_basic(self, mock_state, mock_config, mock_gemini_client):
        """Test basic log analysis functionality."""
        with patch('src.log_analyzer_agent.nodes.analysis.init_model_async') as mock_init_model:
            mock_init_model.return_value = mock_gemini_client
            mock_gemini_client.generate_content.return_value.text = """
            {
                "summary": "Database connection issues detected",
                "issues": [
                    {
                        "severity": "high",
                        "category": "connectivity",
                        "description": "Database connection timeouts",
                        "affected_components": ["DatabaseConnection"],
                        "first_occurrence": "2024-01-15 10:30:15",
                        "frequency": 3
                    }
                ],
                "suggestions": [
                    {
                        "priority": "high",
                        "category": "configuration",
                        "description": "Increase database connection timeout",
                        "implementation": "Update connection timeout from 30s to 60s",
                        "estimated_impact": "Should resolve timeout issues"
                    }
                ]
            }
            """
            
            result = await analyze_logs(mock_state, config=mock_config)
            
            assert result is not None
            assert "analysis_result" in result
            assert result["iteration_count"] == 1
            mock_gemini_client.generate_content.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_logs_with_tool_calls(self, mock_state, mock_config, mock_gemini_client):
        """Test analysis with tool calls."""
        with patch('src.log_analyzer_agent.nodes.analysis.init_model_async') as mock_init_model:
            mock_init_model.return_value = mock_gemini_client
            mock_gemini_client.generate_content.return_value.text = """
            I need to search for more information about database timeouts.
            
            <tool_call>
            search_documentation("database connection timeout troubleshooting")
            </tool_call>
            """
            
            result = await analyze_logs(mock_state, config=mock_config)
            
            assert result is not None
            assert len(result["tool_calls"]) > 0
            assert "search_documentation" in result["tool_calls"][0]["name"]
    
    @pytest.mark.asyncio
    async def test_analyze_logs_error_handling(self, mock_state, mock_config):
        """Test error handling in analysis node."""
        with patch('src.log_analyzer_agent.nodes.analysis.init_model_async') as mock_init_model:
            mock_init_model.side_effect = Exception("API Error")
            
            result = await analyze_logs(mock_state, config=mock_config)
            
            assert result is not None
            assert "error_message" in result
            assert "API Error" in result["error_message"]
    
    @pytest.mark.asyncio
    async def test_analyze_logs_max_iterations(self, mock_state, mock_config, mock_gemini_client):
        """Test max iterations limit."""
        mock_state.iteration_count = 5  # At max iterations
        
        result = await analyze_logs(mock_state, config=mock_config)
        
        assert result is not None
        assert "error_message" in result
        assert "maximum iterations" in result["error_message"].lower()


class TestValidationNode:
    """Test the validation node."""
    
    @pytest.fixture
    def mock_state_with_analysis(self, sample_analysis_result):
        """Create a mock state with analysis result."""
        state = State()
        state.analysis_result = sample_analysis_result
        state.messages = []
        return state
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "configurable": {
                "orchestration_model": "kimi-k2"
            }
        }
    
    @pytest.mark.asyncio
    async def test_validate_analysis_valid(self, mock_state_with_analysis, mock_config, mock_groq_client):
        """Test validation of valid analysis."""
        with patch('src.log_analyzer_agent.nodes.validation.init_model_async') as mock_init_model:
            mock_init_model.return_value = mock_groq_client
            mock_groq_client.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.9,
                "accuracy_score": 0.85,
                "feedback": "Analysis is comprehensive and accurate"
            }
            """
            
            result = await validate_analysis(state, config=mock_config)
            
            assert result is not None
            assert result["validation_result"]["is_valid"] is True
            assert result["analysis_complete"] is True
    
    @pytest.mark.asyncio
    async def test_validate_analysis_invalid(self, mock_state_with_analysis, mock_config, mock_groq_client):
        """Test validation of invalid analysis."""
        with patch('src.log_analyzer_agent.nodes.validation.init_model_async') as mock_init_model:
            mock_init_model.return_value = mock_groq_client
            mock_groq_client.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": false,
                "completeness_score": 0.4,
                "accuracy_score": 0.3,
                "feedback": "Analysis lacks detail and has inaccuracies"
            }
            """
            
            result = await validate_analysis(state, config=mock_config)
            
            assert result is not None
            assert result["validation_result"]["is_valid"] is False
            assert result["analysis_complete"] is False
    
    @pytest.mark.asyncio
    async def test_validate_analysis_no_result(self, mock_config):
        """Test validation with no analysis result."""
        state = State()
        state.analysis_result = None
        
        result = await validate_analysis(state, config=mock_config)
        
        assert result is not None
        assert "error_message" in result
        assert "no analysis result" in result["error_message"].lower()


class TestUserInputNode:
    """Test the user input handling node."""
    
    @pytest.fixture
    def mock_state_needs_input(self):
        """Create a mock state that needs user input."""
        state = State()
        state.requires_user_input = True
        state.messages = []
        return state
    
    @pytest.mark.asyncio
    async def test_handle_user_input_basic(self, mock_state_needs_input, mock_runnable_config):
        """Test basic user input handling."""
        mock_state_needs_input.user_input = "Please provide more details about the database configuration."
        
        result = await handle_user_input(state, config=mock_runnable_config)
        
        assert result is not None
        assert result["requires_user_input"] is False
        assert len(result["messages"]) > 0
    
    @pytest.mark.asyncio
    async def test_handle_user_input_no_input_needed(self, mock_runnable_config):
        """Test when no user input is needed."""
        state = State()
        state.requires_user_input = False
        
        result = await handle_user_input(state, config=mock_runnable_config)
        
        assert result is not None
        assert result["requires_user_input"] is False
    
    @pytest.mark.asyncio
    async def test_handle_user_input_with_context(self, mock_state_needs_input, mock_runnable_config):
        """Test user input handling with context."""
        mock_state_needs_input.user_input = "The database is PostgreSQL 13 running on AWS RDS."
        mock_state_needs_input.analysis_result = {"summary": "Database issues detected"}
        
        result = await handle_user_input(state, config=mock_runnable_config)
        
        assert result is not None
        assert result["requires_user_input"] is False
        assert any("PostgreSQL" in str(msg) for msg in result["messages"])


class TestEnhancedAnalysisNode:
    """Test the enhanced analysis node from improved implementation."""
    
    @pytest.fixture
    def mock_unified_state(self, sample_log_content):
        """Create a mock unified state for testing."""
        from src.log_analyzer_agent.core.unified_state import UnifiedState
        
        state = UnifiedState()
        state.log_content = sample_log_content
        state.messages = []
        state.iteration_count = 0
        return state
    
    @pytest.mark.asyncio
    async def test_enhanced_analyze_logs_streaming(self, mock_unified_state, mock_runnable_config):
        """Test enhanced analysis with streaming enabled."""
        mock_unified_state.enable_streaming = True
        mock_unified_state.log_content = "x" * 15000000  # 15MB log
        
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.init_model_async') as mock_init_model:
            mock_model = Mock()
            mock_model.generate_content.return_value.text = '{"summary": "Large log analyzed", "issues": [], "suggestions": []}'
            mock_init_model.return_value = mock_model
            
            result = await enhanced_analyze_logs(mock_unified_state, mock_runnable_config)
            
            assert result is not None
            assert "analysis_result" in result
    
    @pytest.mark.asyncio
    async def test_enhanced_analyze_logs_circuit_breaker(self, mock_unified_state, mock_runnable_config):
        """Test enhanced analysis with circuit breaker."""
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.init_model_async') as mock_init_model:
            # Simulate repeated failures to trigger circuit breaker
            mock_init_model.side_effect = Exception("API Error")
            
            result = await enhanced_analyze_logs(mock_unified_state, mock_runnable_config)
            
            assert result is not None
            assert "error_message" in result
    
    @pytest.mark.asyncio
    async def test_enhanced_analyze_logs_basic(self, mock_unified_state, mock_runnable_config):
        """Test enhanced analysis basic functionality."""
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.init_model_async') as mock_init_model:
            mock_model = Mock()
            mock_model.generate_content.return_value.text = '{"summary": "Test", "issues": [], "suggestions": []}'
            mock_init_model.return_value = mock_model
            
            result = await enhanced_analyze_logs(mock_unified_state, config=mock_runnable_config)
            
            assert result is not None


class TestNodeIntegration:
    """Test integration between different nodes."""
    
    @pytest.mark.asyncio
    async def test_analysis_to_validation_flow(self, sample_log_content, mock_runnable_config):
        """Test the flow from analysis to validation."""
        # Setup initial state
        state = State()
        state.log_content = sample_log_content
        state.messages = []
        state.iteration_count = 0
        
        # Mock the analysis
        with patch('src.log_analyzer_agent.nodes.analysis.init_model_async') as mock_analysis_model:
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Test analysis",
                "issues": [{"severity": "high", "description": "Test issue"}],
                "suggestions": [{"priority": "high", "description": "Test suggestion"}]
            }
            """
            
            # Run analysis
            analysis_result = await analyze_logs(state, mock_runnable_config)
            
            # Update state with analysis result
            state.analysis_result = analysis_result["analysis_result"]
            
            # Mock the validation
            with patch('src.log_analyzer_agent.nodes.validation.init_model_async') as mock_validation_model:
                mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
                {
                    "is_valid": true,
                    "completeness_score": 0.9,
                    "accuracy_score": 0.85,
                    "feedback": "Good analysis"
                }
                """
                
                # Run validation
                validation_result = await validate_analysis(state, config=mock_config)
                
                assert validation_result is not None
                assert validation_result["analysis_complete"] is True
                assert validation_result["validation_result"]["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_node_error_propagation(self, sample_log_content, mock_runnable_config):
        """Test error propagation between nodes."""
        state = State()
        state.log_content = sample_log_content
        state.messages = []
        
        # Simulate error in analysis
        with patch('src.log_analyzer_agent.nodes.analysis.init_model_async') as mock_model:
            mock_model.side_effect = Exception("Network error")
            
            result = await analyze_logs(state, mock_runnable_config)
            
            assert result is not None
            assert "error_message" in result
            assert "Network error" in result["error_message"]
            
            # Verify error state can be handled by validation
            state.error_message = result["error_message"]
            validation_result = await validate_analysis(state, config=mock_config)
            
            assert validation_result is not None
            assert "error_message" in validation_result


# Performance tests for nodes
class TestNodePerformance:
    """Performance tests for node operations."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_analysis_node_performance(self, large_log_file, mock_runnable_config, performance_metrics):
        """Test analysis node performance with large logs."""
        with open(large_log_file, 'r') as f:
            large_log_content = f.read()
        
        state = State()
        state.log_content = large_log_content
        state.messages = []
        
        with patch('src.log_analyzer_agent.nodes.analysis.init_model_async') as mock_model:
            mock_model.return_value.generate_content.return_value.text = '{"summary": "Large log", "issues": [], "suggestions": []}'
            
            performance_metrics.start()
            result = await analyze_logs(state, mock_runnable_config)
            performance_metrics.stop()
            
            assert result is not None
            assert performance_metrics.duration < 30.0  # Should complete within 30 seconds
            assert performance_metrics.memory_usage < 500  # Should use less than 500MB additional memory
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_node_execution(self, sample_log_content, mock_runnable_config):
        """Test concurrent execution of multiple nodes."""
        import asyncio
        
        # Create multiple states
        states = []
        for i in range(5):
            state = State()
            state.log_content = f"{sample_log_content}\nBatch {i}"
            state.messages = []
            states.append(state)
        
        with patch('src.log_analyzer_agent.nodes.analysis.init_model_async') as mock_model:
            mock_model.return_value.generate_content.return_value.text = '{"summary": "Concurrent test", "issues": [], "suggestions": []}'
            
            # Run analyses concurrently
            tasks = [analyze_logs(state, mock_runnable_config) for state in states]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            assert all(result is not None for result in results)
            assert all("analysis_result" in result for result in results)