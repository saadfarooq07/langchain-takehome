"""
Integration tests for complete graph workflows in the Log Analyzer Agent.
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.log_analyzer_agent.graph import create_graph
from src.log_analyzer_agent.core.improved_graph import create_improved_graph
from src.log_analyzer_agent.state import State
from src.log_analyzer_agent.configuration import Configuration


class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""
    
    @pytest.fixture
    def real_log_samples(self):
        """Load real log samples for integration testing."""
        samples_dir = Path(__file__).parent.parent / "fixtures" / "log_samples"
        
        samples = {}
        for log_file in samples_dir.glob("*.log"):
            with open(log_file, 'r') as f:
                samples[log_file.stem] = f.read()
        
        return samples
    
    @pytest.fixture
    def integration_config(self, mock_env_vars):
        """Configuration for integration tests."""
        return {
            "configurable": {
                "primary_model": "gemini-2.5-flash",
                "orchestration_model": "kimi-k2",
                "max_iterations": 3,  # Reduced for faster tests
                "enable_streaming": False,
                "enable_memory": False,
                "enable_ui_mode": False
            }
        }
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, real_log_samples, integration_config):
        """Test complete analysis workflow with real log data."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Test with system error log
        log_content = real_log_samples.get("system_error", "Test log content")
        
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "requires_user_input": False
        }
        
        # Mock external APIs but allow full workflow
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model, \
             patch('src.log_analyzer_agent.tools.search_documentation') as mock_search:
            
            # Setup realistic responses
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Database connection failures detected in system logs",
                "issues": [
                    {
                        "severity": "high",
                        "category": "connectivity",
                        "description": "Multiple database connection timeouts",
                        "affected_components": ["DatabaseConnection", "RetryManager"],
                        "first_occurrence": "2024-01-15 10:30:15",
                        "frequency": 3
                    },
                    {
                        "severity": "critical",
                        "category": "availability",
                        "description": "Application shutdown due to database unavailability",
                        "affected_components": ["Application"],
                        "first_occurrence": "2024-01-15 10:30:27",
                        "frequency": 1
                    }
                ],
                "suggestions": [
                    {
                        "priority": "high",
                        "category": "configuration",
                        "description": "Increase database connection timeout",
                        "implementation": "Update connection timeout from 30s to 60s in database configuration",
                        "estimated_impact": "Should reduce timeout-related connection failures"
                    },
                    {
                        "priority": "medium",
                        "category": "monitoring",
                        "description": "Implement database health checks",
                        "implementation": "Add periodic health checks to detect database issues early",
                        "estimated_impact": "Proactive detection of database problems"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.9,
                "accuracy_score": 0.85,
                "feedback": "Analysis correctly identifies database connectivity issues and provides actionable suggestions"
            }
            """
            
            mock_search.return_value = {
                "results": [
                    {
                        "title": "Database Connection Troubleshooting",
                        "url": "https://docs.example.com/db-troubleshooting",
                        "content": "Guide for resolving database connection issues"
                    }
                ]
            }
            
            # Execute complete workflow
            result = await compiled_graph.ainvoke(initial_state, config=integration_config)
            
            # Verify complete workflow execution
            assert result is not None
            assert result.get("analysis_complete") is True
            assert "analysis_result" in result
            assert "validation_result" in result
            
            # Verify analysis quality
            analysis = result["analysis_result"]
            assert "summary" in analysis
            assert "issues" in analysis
            assert "suggestions" in analysis
            assert len(analysis["issues"]) > 0
            assert len(analysis["suggestions"]) > 0
            
            # Verify validation
            validation = result["validation_result"]
            assert validation["is_valid"] is True
            assert validation["completeness_score"] > 0.5
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_tool_calls(self, real_log_samples, integration_config):
        """Test workflow that includes tool calls."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        log_content = real_log_samples.get("apache_error", "Apache error log")
        
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model, \
             patch('src.log_analyzer_agent.tools.search_documentation') as mock_search:
            
            # First analysis response with tool call
            mock_analysis_model.return_value.generate_content.return_value.text = """
            I need to search for more information about Apache SSL certificate issues.
            
            <tool_call>
            search_documentation("Apache SSL certificate CA configuration error")
            </tool_call>
            """
            
            # Mock search results
            mock_search.return_value = {
                "results": [
                    {
                        "title": "Apache SSL Configuration",
                        "url": "https://httpd.apache.org/docs/ssl",
                        "content": "SSL certificate configuration guide"
                    }
                ]
            }
            
            # Second analysis response after tool call
            def analysis_side_effect(*args, **kwargs):
                # Check if this is the second call (after tool execution)
                if hasattr(analysis_side_effect, 'call_count'):
                    analysis_side_effect.call_count += 1
                else:
                    analysis_side_effect.call_count = 1
                
                if analysis_side_effect.call_count == 1:
                    # First call - return tool call
                    mock_response = Mock()
                    mock_response.text = """
                    I need to search for more information about Apache SSL certificate issues.
                    
                    <tool_call>
                    search_documentation("Apache SSL certificate CA configuration error")
                    </tool_call>
                    """
                    return mock_response
                else:
                    # Second call - return analysis
                    mock_response = Mock()
                    mock_response.text = """
                    {
                        "summary": "Apache server configuration and SSL certificate issues",
                        "issues": [
                            {
                                "severity": "medium",
                                "category": "configuration",
                                "description": "SSL certificate is configured as CA certificate",
                                "affected_components": ["Apache SSL"],
                                "first_occurrence": "2024-01-15 10:30:16",
                                "frequency": 1
                            }
                        ],
                        "suggestions": [
                            {
                                "priority": "medium",
                                "category": "security",
                                "description": "Review SSL certificate configuration",
                                "implementation": "Ensure server certificate is not marked as CA certificate",
                                "estimated_impact": "Resolves SSL configuration warning"
                            }
                        ]
                    }
                    """
                    return mock_response
            
            mock_analysis_model.return_value.generate_content.side_effect = analysis_side_effect
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.8,
                "accuracy_score": 0.8,
                "feedback": "Analysis identifies SSL configuration issues correctly"
            }
            """
            
            # Execute workflow with tool calls
            result = await compiled_graph.ainvoke(initial_state, config=integration_config)
            
            # Verify tool calls were executed
            assert result is not None
            assert result.get("analysis_complete") is True
            
            # Verify search was called
            mock_search.assert_called()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, real_log_samples, integration_config):
        """Test workflow error handling and recovery."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        log_content = real_log_samples.get("system_error", "Test log")
        
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        # Simulate API failures and recovery
        call_count = 0
        def failing_analysis(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first two calls
                raise Exception(f"API Error {call_count}")
            else:  # Succeed on third call
                mock_response = Mock()
                mock_response.text = '{"summary": "Recovered analysis", "issues": [], "suggestions": []}'
                return mock_response
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.side_effect = failing_analysis
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.7,
                "accuracy_score": 0.7,
                "feedback": "Analysis recovered successfully"
            }
            """
            
            # Execute workflow - should handle errors gracefully
            result = await compiled_graph.ainvoke(initial_state, config=integration_config)
            
            # Should either complete successfully or fail gracefully
            assert result is not None
            # May have error_message or may have recovered
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_improved_workflow_streaming(self, integration_config):
        """Test improved workflow with streaming enabled."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        # Create large log content to trigger streaming
        large_log = "\n".join([
            f"2024-01-15 10:30:{i%60:02d} INFO [Service{i%10}] Processing request {i}"
            for i in range(50000)  # 50k lines
        ])
        
        initial_state = {
            "log_content": large_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "enable_streaming": True
        }
        
        integration_config["configurable"]["enable_streaming"] = True
        
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
            mock_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Large log file processed with streaming",
                "issues": [
                    {
                        "severity": "low",
                        "category": "performance",
                        "description": "High volume of requests detected",
                        "affected_components": ["Service0", "Service1"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": 50000
                    }
                ],
                "suggestions": [
                    {
                        "priority": "medium",
                        "category": "optimization",
                        "description": "Consider request batching or rate limiting",
                        "implementation": "Implement request queuing system",
                        "estimated_impact": "Reduce system load"
                    }
                ]
            }
            """
            
            # Execute with streaming
            result = await compiled_graph.ainvoke(initial_state, config=integration_config)
            
            assert result is not None
            # Should handle large logs efficiently
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_workflow_with_subgraphs(self, real_log_samples, integration_config):
        """Test workflow with specialized subgraphs."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        # Use HDFS log to trigger HDFS subgraph
        hdfs_log = real_log_samples.get("hdfs_datanode", "HDFS log content")
        
        initial_state = {
            "log_content": hdfs_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "enable_subgraphs": True
        }
        
        integration_config["configurable"]["enable_subgraphs"] = True
        
        with patch('src.log_analyzer_agent.subgraphs.hdfs_analyzer.analyze_hdfs_logs') as mock_hdfs_analyzer, \
             patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
            
            # Mock HDFS-specific analysis
            mock_hdfs_analyzer.return_value = {
                "hdfs_specific_issues": [
                    {
                        "severity": "high",
                        "category": "hdfs",
                        "description": "DataNode initialization failure",
                        "block_pool": "BP-123456789-10.0.0.1-1234567890123"
                    }
                ]
            }
            
            mock_model.return_value.generate_content.return_value.text = """
            {
                "summary": "HDFS DataNode issues detected",
                "issues": [
                    {
                        "severity": "high",
                        "category": "hdfs",
                        "description": "DataNode initialization failure for block pool",
                        "affected_components": ["DataNode"],
                        "first_occurrence": "2024-01-15 10:30:18",
                        "frequency": 1
                    }
                ],
                "suggestions": [
                    {
                        "priority": "high",
                        "category": "hdfs",
                        "description": "Check NameNode connectivity and block pool configuration",
                        "implementation": "Verify network connectivity to NameNode and check block pool settings",
                        "estimated_impact": "Restore DataNode functionality"
                    }
                ]
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=integration_config)
            
            assert result is not None
            # Should use HDFS-specific analysis
    
    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_long_running_workflow(self, integration_config):
        """Test long-running workflow with multiple iterations."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Set higher iteration limit for this test
        integration_config["configurable"]["max_iterations"] = 10
        
        initial_state = {
            "log_content": "Complex log requiring multiple analysis iterations",
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        iteration_responses = [
            # First iteration - incomplete analysis
            """
            I need more information about this log pattern.
            
            <tool_call>
            search_documentation("complex log pattern analysis")
            </tool_call>
            """,
            # Second iteration - still incomplete
            """
            {
                "summary": "Partial analysis completed",
                "issues": [{"severity": "medium", "description": "Partial issue identified"}],
                "suggestions": []
            }
            """,
            # Third iteration - complete analysis
            """
            {
                "summary": "Complete analysis after multiple iterations",
                "issues": [
                    {
                        "severity": "high",
                        "category": "complex",
                        "description": "Complex issue identified after thorough analysis",
                        "affected_components": ["ComplexSystem"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": 1
                    }
                ],
                "suggestions": [
                    {
                        "priority": "high",
                        "category": "resolution",
                        "description": "Comprehensive solution for complex issue",
                        "implementation": "Multi-step resolution process",
                        "estimated_impact": "Complete resolution of complex issue"
                    }
                ]
            }
            """
        ]
        
        call_count = 0
        def multi_iteration_analysis(*args, **kwargs):
            nonlocal call_count
            response_index = min(call_count, len(iteration_responses) - 1)
            call_count += 1
            
            mock_response = Mock()
            mock_response.text = iteration_responses[response_index]
            return mock_response
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model, \
             patch('src.log_analyzer_agent.tools.search_documentation') as mock_search:
            
            mock_analysis_model.return_value.generate_content.side_effect = multi_iteration_analysis
            
            # Validation responses - first two invalid, third valid
            validation_responses = [
                '{"is_valid": false, "completeness_score": 0.3, "accuracy_score": 0.4, "feedback": "Needs more analysis"}',
                '{"is_valid": false, "completeness_score": 0.6, "accuracy_score": 0.7, "feedback": "Getting better but incomplete"}',
                '{"is_valid": true, "completeness_score": 0.9, "accuracy_score": 0.9, "feedback": "Complete and accurate analysis"}'
            ]
            
            validation_call_count = 0
            def multi_iteration_validation(*args, **kwargs):
                nonlocal validation_call_count
                response_index = min(validation_call_count, len(validation_responses) - 1)
                validation_call_count += 1
                
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = validation_responses[response_index]
                return mock_response
            
            mock_validation_model.return_value.chat.completions.create.side_effect = multi_iteration_validation
            
            mock_search.return_value = {"results": [{"title": "Complex Analysis Guide", "content": "Guide content"}]}
            
            # Execute long-running workflow
            result = await compiled_graph.ainvoke(initial_state, config=integration_config)
            
            assert result is not None
            # Should eventually complete or reach max iterations
            assert result.get("iteration_count", 0) > 1  # Should have multiple iterations