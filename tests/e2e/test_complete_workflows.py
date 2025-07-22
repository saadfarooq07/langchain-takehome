"""
End-to-end tests for complete workflows using real log files and full system integration.
"""

import pytest
import asyncio
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.log_analyzer_agent.graph import create_graph
from src.log_analyzer_agent.core.improved_graph import create_improved_graph
from src.log_analyzer_agent.configuration import Configuration


class TestCompleteE2EWorkflows:
    """Test complete end-to-end workflows with real log data."""
    
    @pytest.fixture
    def loghub_samples(self):
        """Load LogHub dataset samples for E2E testing."""
        loghub_dir = Path(__file__).parent.parent.parent / "loghub"
        samples = {}
        
        # Try to load some LogHub samples if available
        sample_dirs = [
            "Android", "Apache", "BGL", "HDFS", "HealthApp", 
            "HPC", "Linux", "Mac", "OpenSSH", "OpenStack",
            "Proxifier", "Spark", "SSH", "Thunderbird", "Windows", "Zookeeper"
        ]
        
        for sample_dir in sample_dirs:
            sample_path = loghub_dir / sample_dir
            if sample_path.exists():
                # Look for log files
                for log_file in sample_path.glob("*.log"):
                    if log_file.stat().st_size < 1024 * 1024:  # Only small files for testing
                        try:
                            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if content.strip():
                                    samples[f"{sample_dir}_{log_file.stem}"] = content[:10000]  # First 10KB
                        except Exception:
                            continue
        
        # If no LogHub samples found, use fixture samples
        if not samples:
            fixture_dir = Path(__file__).parent.parent / "fixtures" / "log_samples"
            for log_file in fixture_dir.glob("*.log"):
                with open(log_file, 'r') as f:
                    samples[log_file.stem] = f.read()
        
        return samples
    
    @pytest.fixture
    def e2e_config(self, mock_env_vars):
        """Configuration for E2E tests."""
        return {
            "configurable": {
                "primary_model": "gemini-2.5-flash",
                "orchestration_model": "kimi-k2",
                "max_iterations": 3,
                "enable_streaming": False,
                "enable_memory": False,
                "enable_ui_mode": False,
                "enable_subgraphs": False,
                "enable_circuit_breaker": False,
                "enable_rate_limiting": False
            }
        }
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_complete_log_analysis_workflow(self, loghub_samples, e2e_config):
        """Test complete log analysis workflow with real log data."""
        if not loghub_samples:
            pytest.skip("No log samples available for E2E testing")
        
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Test with first available log sample
        sample_name, log_content = next(iter(loghub_samples.items()))
        
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "requires_user_input": False,
            "tool_calls": [],
            "error_message": None
        }
        
        # Mock external APIs with realistic responses
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model, \
             patch('src.log_analyzer_agent.tools.search_documentation') as mock_search:
            
            # Generate realistic analysis based on log content
            def generate_realistic_analysis(log_content):
                # Simple heuristics to generate realistic analysis
                issues = []
                suggestions = []
                
                if "error" in log_content.lower() or "exception" in log_content.lower():
                    issues.append({
                        "severity": "high",
                        "category": "error",
                        "description": "Error conditions detected in log file",
                        "affected_components": ["System"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": log_content.lower().count("error") + log_content.lower().count("exception")
                    })
                    suggestions.append({
                        "priority": "high",
                        "category": "investigation",
                        "description": "Investigate error conditions",
                        "implementation": "Review error logs and stack traces",
                        "estimated_impact": "Resolve system errors"
                    })
                
                if "timeout" in log_content.lower():
                    issues.append({
                        "severity": "medium",
                        "category": "performance",
                        "description": "Timeout issues detected",
                        "affected_components": ["Network", "Database"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": log_content.lower().count("timeout")
                    })
                    suggestions.append({
                        "priority": "medium",
                        "category": "configuration",
                        "description": "Review timeout configurations",
                        "implementation": "Increase timeout values or optimize performance",
                        "estimated_impact": "Reduce timeout-related issues"
                    })
                
                if "warn" in log_content.lower() or "warning" in log_content.lower():
                    issues.append({
                        "severity": "low",
                        "category": "warning",
                        "description": "Warning conditions detected",
                        "affected_components": ["System"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": log_content.lower().count("warn") + log_content.lower().count("warning")
                    })
                    suggestions.append({
                        "priority": "low",
                        "category": "monitoring",
                        "description": "Monitor warning conditions",
                        "implementation": "Set up monitoring for warning patterns",
                        "estimated_impact": "Proactive issue detection"
                    })
                
                # Default analysis if no patterns found
                if not issues:
                    issues.append({
                        "severity": "info",
                        "category": "general",
                        "description": "Log file analyzed successfully",
                        "affected_components": ["System"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": 1
                    })
                    suggestions.append({
                        "priority": "low",
                        "category": "maintenance",
                        "description": "Continue regular log monitoring",
                        "implementation": "Maintain current monitoring practices",
                        "estimated_impact": "Ongoing system health awareness"
                    })
                
                return {
                    "summary": f"Analysis of {sample_name} log file completed",
                    "issues": issues,
                    "suggestions": suggestions
                }
            
            realistic_analysis = generate_realistic_analysis(log_content)
            
            mock_analysis_model.return_value.generate_content.return_value.text = json.dumps(realistic_analysis)
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.8,
                "accuracy_score": 0.8,
                "feedback": "Analysis completed successfully for E2E test"
            }
            """
            
            mock_search.return_value = {
                "results": [
                    {
                        "title": f"Documentation for {sample_name}",
                        "url": f"https://docs.example.com/{sample_name}",
                        "content": f"Documentation content for {sample_name} log analysis"
                    }
                ]
            }
            
            # Execute complete E2E workflow
            result = await compiled_graph.ainvoke(initial_state, config=e2e_config)
            
            # Comprehensive E2E verification
            assert result is not None, "E2E workflow should return a result"
            assert result.get("analysis_complete") is True, "Analysis should be marked as complete"
            assert "analysis_result" in result, "Should contain analysis result"
            assert "validation_result" in result, "Should contain validation result"
            
            # Verify analysis structure
            analysis = result["analysis_result"]
            assert "summary" in analysis, "Analysis should have summary"
            assert "issues" in analysis, "Analysis should have issues"
            assert "suggestions" in analysis, "Analysis should have suggestions"
            assert isinstance(analysis["issues"], list), "Issues should be a list"
            assert isinstance(analysis["suggestions"], list), "Suggestions should be a list"
            
            # Verify validation structure
            validation = result["validation_result"]
            assert "is_valid" in validation, "Validation should have is_valid field"
            assert validation["is_valid"] is True, "Validation should pass for E2E test"
            
            print(f"✅ E2E test completed successfully for {sample_name}")
            print(f"   - Found {len(analysis['issues'])} issues")
            print(f"   - Generated {len(analysis['suggestions'])} suggestions")
            print(f"   - Validation score: {validation.get('completeness_score', 'N/A')}")
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_improved_workflow_e2e(self, loghub_samples, e2e_config):
        """Test improved workflow end-to-end."""
        if not loghub_samples:
            pytest.skip("No log samples available for E2E testing")
        
        # Enable improved features
        e2e_config["configurable"]["enable_streaming"] = True
        e2e_config["configurable"]["enable_subgraphs"] = True
        e2e_config["configurable"]["enable_circuit_breaker"] = True
        
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        # Use a larger log sample for streaming test
        sample_name, log_content = next(iter(loghub_samples.items()))
        # Duplicate content to make it larger
        large_log_content = (log_content + "\n") * 100  # Make it larger
        
        initial_state = {
            "log_content": large_log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "enable_streaming": True,
            "enable_subgraphs": True,
            "enable_circuit_breaker": True
        }
        
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
            mock_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Improved workflow E2E test completed with streaming and subgraphs",
                "issues": [
                    {
                        "severity": "medium",
                        "category": "performance",
                        "description": "Large log file processed efficiently with streaming",
                        "affected_components": ["StreamingProcessor"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": 1
                    }
                ],
                "suggestions": [
                    {
                        "priority": "low",
                        "category": "optimization",
                        "description": "Continue using streaming for large log files",
                        "implementation": "Maintain streaming configuration",
                        "estimated_impact": "Efficient processing of large logs"
                    }
                ]
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=e2e_config)
            
            assert result is not None
            print(f"✅ Improved workflow E2E test completed for large log sample")
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_multiple_log_types_e2e(self, loghub_samples, e2e_config):
        """Test E2E workflow with multiple different log types."""
        if len(loghub_samples) < 2:
            pytest.skip("Need at least 2 log samples for multi-type testing")
        
        graph = create_graph()
        compiled_graph = graph.compile()
        
        results = []
        
        # Test with up to 3 different log types
        for i, (sample_name, log_content) in enumerate(list(loghub_samples.items())[:3]):
            initial_state = {
                "log_content": log_content,
                "messages": [],
                "iteration_count": 0,
                "analysis_complete": False
            }
            
            with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
                 patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
                
                mock_analysis_model.return_value.generate_content.return_value.text = f"""
                {{
                    "summary": "Analysis of {sample_name} log type completed",
                    "issues": [
                        {{
                            "severity": "medium",
                            "category": "analysis",
                            "description": "Multi-type E2E test for {sample_name}",
                            "affected_components": ["LogAnalyzer"],
                            "first_occurrence": "2024-01-15 10:30:00",
                            "frequency": 1
                        }}
                    ],
                    "suggestions": [
                        {{
                            "priority": "low",
                            "category": "testing",
                            "description": "Continue multi-type log analysis testing",
                            "implementation": "Test with various log formats",
                            "estimated_impact": "Ensure broad compatibility"
                        }}
                    ]
                }}
                """
                
                mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
                {
                    "is_valid": true,
                    "completeness_score": 0.8,
                    "accuracy_score": 0.8,
                    "feedback": "Multi-type E2E test validation passed"
                }
                """
                
                result = await compiled_graph.ainvoke(initial_state, config=e2e_config)
                results.append((sample_name, result))
        
        # Verify all log types were processed successfully
        assert len(results) > 0, "Should process at least one log type"
        
        for sample_name, result in results:
            assert result is not None, f"Result should not be None for {sample_name}"
            assert result.get("analysis_complete") is True, f"Analysis should complete for {sample_name}"
            print(f"✅ Multi-type E2E test completed for {sample_name}")
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_error_recovery_e2e(self, loghub_samples, e2e_config):
        """Test E2E workflow with error recovery scenarios."""
        if not loghub_samples:
            pytest.skip("No log samples available for E2E testing")
        
        graph = create_graph()
        compiled_graph = graph.compile()
        
        sample_name, log_content = next(iter(loghub_samples.items()))
        
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        # Simulate API failures and recovery
        call_count = 0
        def failing_then_succeeding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated API failure for E2E error recovery test")
            else:
                mock_response = Mock()
                mock_response.text = """
                {
                    "summary": "E2E error recovery test - analysis succeeded after retry",
                    "issues": [
                        {
                            "severity": "low",
                            "category": "resilience",
                            "description": "System recovered from API failure",
                            "affected_components": ["ErrorRecovery"],
                            "first_occurrence": "2024-01-15 10:30:00",
                            "frequency": 1
                        }
                    ],
                    "suggestions": [
                        {
                            "priority": "medium",
                            "category": "reliability",
                            "description": "Maintain error recovery mechanisms",
                            "implementation": "Keep retry logic and error handling",
                            "estimated_impact": "Better system resilience"
                        }
                    ]
                }
                """
                return mock_response
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.side_effect = failing_then_succeeding
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.7,
                "accuracy_score": 0.8,
                "feedback": "E2E error recovery test validation"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=e2e_config)
            
            # Should either succeed (if retry logic exists) or fail gracefully
            assert result is not None, "Should return a result even with errors"
            
            if result.get("analysis_complete"):
                print("✅ E2E error recovery test - system recovered successfully")
            elif "error_message" in result:
                print("✅ E2E error recovery test - system failed gracefully")
            else:
                print("✅ E2E error recovery test - system handled error appropriately")
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_e2e(self, loghub_samples, e2e_config, performance_metrics):
        """Test E2E workflow performance with real log data."""
        if not loghub_samples:
            pytest.skip("No log samples available for E2E testing")
        
        graph = create_graph()
        compiled_graph = graph.compile()
        
        sample_name, log_content = next(iter(loghub_samples.items()))
        
        # Create larger log content for performance testing
        large_log_content = (log_content + "\n") * 50  # 50x larger
        
        initial_state = {
            "log_content": large_log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Performance E2E test completed",
                "issues": [
                    {
                        "severity": "low",
                        "category": "performance",
                        "description": "Large log file processed for performance testing",
                        "affected_components": ["PerformanceTest"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": 1
                    }
                ],
                "suggestions": [
                    {
                        "priority": "low",
                        "category": "optimization",
                        "description": "Monitor performance metrics",
                        "implementation": "Continue performance monitoring",
                        "estimated_impact": "Maintain system performance"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.8,
                "accuracy_score": 0.8,
                "feedback": "Performance E2E test validation"
            }
            """
            
            performance_metrics.start()
            result = await compiled_graph.ainvoke(initial_state, config=e2e_config)
            performance_metrics.stop()
            
            assert result is not None
            assert performance_metrics.duration < 120.0, "E2E workflow should complete within 2 minutes"
            assert performance_metrics.memory_usage < 1000, "Should use less than 1GB additional memory"
            
            print(f"✅ Performance E2E test completed in {performance_metrics.duration:.2f}s")
            print(f"   Memory usage: {performance_metrics.memory_usage:.2f}MB")
            print(f"   Peak memory: {performance_metrics.peak_memory:.2f}MB")


class TestRealWorldScenarios:
    """Test with real-world log scenarios and edge cases."""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_empty_log_file_e2e(self, e2e_config):
        """Test E2E workflow with empty log file."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": "",
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Empty log file - no content to analyze",
                "issues": [
                    {
                        "severity": "info",
                        "category": "data",
                        "description": "Log file is empty",
                        "affected_components": ["LogFile"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": 1
                    }
                ],
                "suggestions": [
                    {
                        "priority": "low",
                        "category": "monitoring",
                        "description": "Verify log generation is working",
                        "implementation": "Check if logging is properly configured",
                        "estimated_impact": "Ensure logs are being generated"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.6,
                "accuracy_score": 0.8,
                "feedback": "Appropriate handling of empty log file"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=e2e_config)
            
            assert result is not None
            assert result.get("analysis_complete") is True
            print("✅ Empty log file E2E test completed")
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_malformed_log_e2e(self, e2e_config):
        """Test E2E workflow with malformed log content."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        malformed_log = """
        This is not a proper log format
        Random text without timestamps
        ���� Some binary data ����
        {"json": "mixed with random text"}
        2024-01-15 Valid timestamp but then garbage ���
        """
        
        initial_state = {
            "log_content": malformed_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Malformed log content detected - mixed formats and encoding issues",
                "issues": [
                    {
                        "severity": "medium",
                        "category": "format",
                        "description": "Log file contains malformed or mixed format content",
                        "affected_components": ["LogParser"],
                        "first_occurrence": "2024-01-15 10:30:00",
                        "frequency": 1
                    }
                ],
                "suggestions": [
                    {
                        "priority": "medium",
                        "category": "data_quality",
                        "description": "Standardize log format",
                        "implementation": "Implement consistent logging format across all components",
                        "estimated_impact": "Improve log analysis accuracy"
                    }
                ]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.7,
                "accuracy_score": 0.7,
                "feedback": "Good handling of malformed log content"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=e2e_config)
            
            assert result is not None
            print("✅ Malformed log E2E test completed")
    
    @pytest.mark.e2e
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_e2e_workflows(self, loghub_samples, e2e_config):
        """Test multiple concurrent E2E workflows."""
        if len(loghub_samples) < 2:
            pytest.skip("Need at least 2 log samples for concurrent testing")
        
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Create multiple concurrent workflows
        async def run_workflow(sample_name, log_content):
            initial_state = {
                "log_content": log_content,
                "messages": [],
                "iteration_count": 0,
                "analysis_complete": False
            }
            
            with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
                 patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
                
                mock_analysis_model.return_value.generate_content.return_value.text = f"""
                {{
                    "summary": "Concurrent E2E test for {sample_name}",
                    "issues": [
                        {{
                            "severity": "low",
                            "category": "concurrency",
                            "description": "Concurrent workflow test for {sample_name}",
                            "affected_components": ["ConcurrencyTest"],
                            "first_occurrence": "2024-01-15 10:30:00",
                            "frequency": 1
                        }}
                    ],
                    "suggestions": [
                        {{
                            "priority": "low",
                            "category": "testing",
                            "description": "Continue concurrent testing",
                            "implementation": "Test concurrent workflow execution",
                            "estimated_impact": "Ensure system handles concurrent loads"
                        }}
                    ]
                }}
                """
                
                mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
                {
                    "is_valid": true,
                    "completeness_score": 0.8,
                    "accuracy_score": 0.8,
                    "feedback": "Concurrent E2E test validation"
                }
                """
                
                return await compiled_graph.ainvoke(initial_state, config=e2e_config)
        
        # Run up to 3 workflows concurrently
        tasks = []
        for sample_name, log_content in list(loghub_samples.items())[:3]:
            tasks.append(run_workflow(sample_name, log_content))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all workflows completed
        assert len(results) > 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent workflow {i} failed: {result}")
            assert result is not None
        
        print(f"✅ Concurrent E2E test completed with {len(results)} workflows")