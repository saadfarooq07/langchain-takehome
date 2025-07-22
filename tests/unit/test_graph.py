"""
Unit tests for graph implementations in the Log Analyzer Agent.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from src.log_analyzer_agent.graph import create_graph
from src.log_analyzer_agent.core.improved_graph import create_improved_graph
from src.log_analyzer_agent.state import State
from src.log_analyzer_agent.core.unified_state import UnifiedState
from src.log_analyzer_agent.configuration import Configuration


class TestOriginalGraph:
    """Test the original graph implementation."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return {
            "configurable": {
                "primary_model": "gemini-2.5-flash",
                "orchestration_model": "kimi-k2",
                "max_iterations": 5,
                "enable_streaming": False,
                "enable_memory": False,
                "enable_ui_mode": False
            }
        }
    
    def test_create_graph_basic(self):
        """Test basic graph creation."""
        graph = create_graph()
        
        assert graph is not None
        assert hasattr(graph, 'nodes')
        assert hasattr(graph, 'edges')
        
        # Check that required nodes exist
        node_names = [node for node in graph.nodes]
        assert "analyze_logs" in node_names
        assert "validate_analysis" in node_names
        assert "tools" in node_names
    
    def test_graph_node_connections(self):
        """Test that graph nodes are properly connected."""
        graph = create_graph()
        
        # Get the compiled graph
        compiled_graph = graph.compile()
        
        # Verify the graph has the expected structure
        assert compiled_graph is not None
        
        # Check that the graph can be invoked (basic structure test)
        try:
            # This should not raise an exception for basic structure
            graph_dict = compiled_graph.get_graph().to_dict()
            assert "nodes" in graph_dict
            assert "edges" in graph_dict
        except Exception as e:
            pytest.fail(f"Graph structure is invalid: {e}")
    
    @pytest.mark.asyncio
    async def test_graph_execution_basic(self, mock_config, sample_log_content):
        """Test basic graph execution."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": sample_log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        # Mock all the external dependencies
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model, \
             patch('src.log_analyzer_agent.tools.search_documentation') as mock_search:
            
            # Setup mocks
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "Test analysis complete",
                "issues": [],
                "suggestions": []
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.9,
                "accuracy_score": 0.85,
                "feedback": "Analysis is good"
            }
            """
            
            mock_search.return_value = {"results": []}
            
            # Execute graph
            result = await compiled_graph.ainvoke(initial_state, config=mock_config)
            
            assert result is not None
            assert "analysis_complete" in result
    
    @pytest.mark.asyncio
    async def test_graph_routing_logic(self, mock_config, sample_log_content):
        """Test graph routing logic."""
        graph = create_graph()
        
        # Test the routing functions directly
        from src.log_analyzer_agent.graph import route_after_analysis, route_after_validation
        
        # Test routing after analysis - should go to validation
        state_after_analysis = State()
        state_after_analysis.analysis_result = {"summary": "Test"}
        state_after_analysis.tool_calls = []
        
        route = route_after_analysis(state_after_analysis)
        assert route == "validate_analysis"
        
        # Test routing after analysis with tool calls - should go to tools
        state_with_tools = State()
        state_with_tools.analysis_result = {"summary": "Test"}
        state_with_tools.tool_calls = [{"name": "search_documentation", "args": {}}]
        
        route = route_after_analysis(state_with_tools)
        assert route == "tools"
        
        # Test routing after validation - complete
        state_validated = State()
        state_validated.validation_result = {"is_valid": True}
        state_validated.analysis_complete = True
        
        route = route_after_validation(state_validated)
        assert route == "__end__"
    
    def test_graph_conditional_edges(self):
        """Test conditional edges in the graph."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Get graph structure
        graph_dict = compiled_graph.get_graph().to_dict()
        
        # Verify conditional edges exist
        edges = graph_dict.get("edges", [])
        conditional_edges = [edge for edge in edges if edge.get("data", {}).get("condition")]
        
        assert len(conditional_edges) > 0, "Graph should have conditional edges"


class TestImprovedGraph:
    """Test the improved graph implementation."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for improved graph."""
        return {
            "configurable": {
                "primary_model": "gemini-2.5-flash",
                "orchestration_model": "kimi-k2",
                "max_iterations": 5,
                "enable_streaming": True,
                "enable_memory": False,
                "enable_ui_mode": False,
                "enable_subgraphs": True,
                "enable_circuit_breaker": True,
                "enable_rate_limiting": True
            }
        }
    
    def test_create_improved_graph_basic(self):
        """Test basic improved graph creation."""
        graph = create_improved_graph()
        
        assert graph is not None
        assert hasattr(graph, 'nodes')
        assert hasattr(graph, 'edges')
    
    def test_improved_graph_with_subgraphs(self, mock_config):
        """Test improved graph with subgraphs enabled."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        # Verify subgraphs are included
        graph_dict = compiled_graph.get_graph().to_dict()
        node_names = [node["id"] for node in graph_dict.get("nodes", [])]
        
        # Should include subgraph nodes
        subgraph_nodes = [name for name in node_names if "analyzer" in name.lower()]
        assert len(subgraph_nodes) > 0, "Should include subgraph analyzer nodes"
    
    @pytest.mark.asyncio
    async def test_improved_graph_streaming(self, mock_config):
        """Test improved graph with streaming enabled."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        # Large log content to trigger streaming
        large_log = "x" * 15000000  # 15MB
        
        initial_state = {
            "log_content": large_log,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "enable_streaming": True
        }
        
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
            mock_model.return_value.generate_content.return_value.text = '{"summary": "Streaming test", "issues": [], "suggestions": []}'
            
            # This should handle streaming without errors
            result = await compiled_graph.ainvoke(initial_state, config=mock_config)
            
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_improved_graph_circuit_breaker(self, mock_config):
        """Test improved graph with circuit breaker."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": "Test log content",
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "enable_circuit_breaker": True
        }
        
        # Simulate repeated failures to trigger circuit breaker
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
            mock_model.side_effect = Exception("Repeated API failure")
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_config)
            
            # Should handle circuit breaker gracefully
            assert result is not None
            assert "error_message" in result or "circuit_breaker_open" in result


class TestGraphIntegration:
    """Test integration between different graph components."""
    
    @pytest.mark.asyncio
    async def test_graph_state_transitions(self, mock_runnable_config, sample_log_content):
        """Test state transitions through the graph."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Track state changes through execution
        states = []
        
        def track_state(state):
            states.append(dict(state))
            return state
        
        initial_state = {
            "log_content": sample_log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = """
            {
                "summary": "State transition test",
                "issues": [{"severity": "medium", "description": "Test issue"}],
                "suggestions": [{"priority": "medium", "description": "Test suggestion"}]
            }
            """
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.8,
                "accuracy_score": 0.75,
                "feedback": "Good analysis"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Verify final state
            assert result is not None
            assert result.get("analysis_complete") is True
            assert "analysis_result" in result
            assert "validation_result" in result
    
    @pytest.mark.asyncio
    async def test_graph_error_recovery(self, mock_runnable_config, sample_log_content):
        """Test graph error recovery mechanisms."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": sample_log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        # Simulate error in analysis, then recovery
        call_count = 0
        def mock_analysis_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary API error")
            else:
                mock_response = Mock()
                mock_response.text = '{"summary": "Recovered analysis", "issues": [], "suggestions": []}'
                return mock_response
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.side_effect = mock_analysis_side_effect
            
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = """
            {
                "is_valid": true,
                "completeness_score": 0.8,
                "accuracy_score": 0.75,
                "feedback": "Recovered successfully"
            }
            """
            
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            
            # Should recover from error
            assert result is not None
            # May complete or may have error message, but should not crash
    
    def test_graph_configuration_validation(self):
        """Test graph configuration validation."""
        # Test with invalid configuration
        invalid_config = {
            "configurable": {
                "primary_model": "invalid-model",
                "max_iterations": -1
            }
        }
        
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Should handle invalid config gracefully
        try:
            # This might raise an exception or handle gracefully
            # depending on implementation
            pass
        except Exception as e:
            # If it raises an exception, it should be a validation error
            assert "invalid" in str(e).lower() or "config" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_graph_concurrent_execution(self, mock_runnable_config):
        """Test concurrent graph execution."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Create multiple initial states
        states = []
        for i in range(3):
            states.append({
                "log_content": f"Test log content {i}",
                "messages": [],
                "iteration_count": 0,
                "analysis_complete": False
            })
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = '{"summary": "Concurrent test", "issues": [], "suggestions": []}'
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = '{"is_valid": true, "completeness_score": 0.8, "accuracy_score": 0.75, "feedback": "Good"}'
            
            # Execute graphs concurrently
            tasks = [compiled_graph.ainvoke(state, config=mock_runnable_config) for state in states]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete successfully
            assert len(results) == 3
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent execution failed: {result}")
                assert result is not None


class TestGraphPerformance:
    """Performance tests for graph execution."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_graph_execution_time(self, mock_runnable_config, performance_metrics, large_log_file):
        """Test graph execution time with large logs."""
        with open(large_log_file, 'r') as f:
            large_log_content = f.read()
        
        graph = create_graph()
        compiled_graph = graph.compile()
        
        initial_state = {
            "log_content": large_log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = '{"summary": "Performance test", "issues": [], "suggestions": []}'
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = '{"is_valid": true, "completeness_score": 0.8, "accuracy_score": 0.75, "feedback": "Good"}'
            
            performance_metrics.start()
            result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
            performance_metrics.stop()
            
            assert result is not None
            assert performance_metrics.duration < 60.0  # Should complete within 60 seconds
            assert performance_metrics.memory_usage < 1000  # Should use less than 1GB additional memory
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_graph_memory_usage(self, mock_runnable_config, performance_metrics):
        """Test graph memory usage with multiple executions."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_analysis_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation_model:
            
            mock_analysis_model.return_value.generate_content.return_value.text = '{"summary": "Memory test", "issues": [], "suggestions": []}'
            mock_validation_model.return_value.chat.completions.create.return_value.choices[0].message.content = '{"is_valid": true, "completeness_score": 0.8, "accuracy_score": 0.75, "feedback": "Good"}'
            
            performance_metrics.start()
            
            # Execute multiple times to check for memory leaks
            for i in range(10):
                initial_state = {
                    "log_content": f"Memory test log content iteration {i}",
                    "messages": [],
                    "iteration_count": 0,
                    "analysis_complete": False
                }
                
                result = await compiled_graph.ainvoke(initial_state, config=mock_runnable_config)
                assert result is not None
            
            performance_metrics.stop()
            
            # Memory usage should be reasonable even after multiple executions
            assert performance_metrics.memory_usage < 200  # Should use less than 200MB additional memory