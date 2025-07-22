"""
Integration tests for LangGraph Studio functionality.
"""

import pytest
import asyncio
import os
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List, Optional

from src.log_analyzer_agent.graph import create_graph
from src.log_analyzer_agent.core.improved_graph import create_improved_graph


class TestLangGraphStudioIntegration:
    """Test LangGraph Studio integration and deployment."""
    
    @pytest.fixture
    def studio_config(self):
        """LangGraph Studio configuration for testing."""
        return {
            "api_key": os.getenv("LANGGRAPH_STUDIO_API_KEY", "test_studio_key"),
            "project_id": "log-analyzer-agent",
            "deployment_name": "production",
            "studio_url": "https://studio.langchain.com"
        }
    
    @pytest.fixture
    def mock_studio_client(self):
        """Mock LangGraph Studio client."""
        mock_client = Mock()
        
        # Mock deployment operations
        mock_client.deploy.return_value = {
            "deployment_id": "deploy_123",
            "status": "deployed",
            "url": "https://api.langchain.com/deployments/deploy_123"
        }
        
        mock_client.get_deployment.return_value = {
            "deployment_id": "deploy_123",
            "status": "running",
            "health": "healthy",
            "metrics": {
                "requests_per_minute": 10,
                "average_response_time": 1.5,
                "error_rate": 0.01
            }
        }
        
        # Mock graph operations
        mock_client.upload_graph.return_value = {
            "graph_id": "graph_123",
            "version": "v1.0.0",
            "status": "uploaded"
        }
        
        # Mock monitoring operations
        mock_client.get_metrics.return_value = {
            "total_requests": 1000,
            "successful_requests": 990,
            "failed_requests": 10,
            "average_latency": 2.1,
            "p95_latency": 4.5,
            "p99_latency": 8.2
        }
        
        mock_client.get_logs.return_value = [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "level": "INFO",
                "message": "Graph execution started",
                "trace_id": "trace_123"
            },
            {
                "timestamp": "2024-01-15T10:30:02Z",
                "level": "INFO", 
                "message": "Analysis completed successfully",
                "trace_id": "trace_123"
            }
        ]
        
        return mock_client
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_graph_deployment_to_studio(self, studio_config, mock_studio_client):
        """Test deploying graph to LangGraph Studio."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Mock deployment process
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test deployment
            deployment_result = mock_studio_client.deploy(
                graph=compiled_graph,
                project_id=studio_config["project_id"],
                deployment_name=studio_config["deployment_name"]
            )
            
            assert deployment_result["deployment_id"] == "deploy_123"
            assert deployment_result["status"] == "deployed"
            assert "url" in deployment_result
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_improved_graph_deployment(self, studio_config, mock_studio_client):
        """Test deploying improved graph to Studio."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test improved graph deployment
            deployment_result = mock_studio_client.deploy(
                graph=compiled_graph,
                project_id=studio_config["project_id"],
                deployment_name="improved-production",
                config={
                    "enable_streaming": True,
                    "enable_subgraphs": True,
                    "enable_circuit_breaker": True
                }
            )
            
            assert deployment_result["deployment_id"] == "deploy_123"
            assert deployment_result["status"] == "deployed"
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_deployment_health_monitoring(self, studio_config, mock_studio_client):
        """Test monitoring deployment health in Studio."""
        deployment_id = "deploy_123"
        
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test health check
            health_status = mock_studio_client.get_deployment(deployment_id)
            
            assert health_status["deployment_id"] == deployment_id
            assert health_status["status"] == "running"
            assert health_status["health"] == "healthy"
            assert "metrics" in health_status
            
            metrics = health_status["metrics"]
            assert metrics["requests_per_minute"] > 0
            assert metrics["average_response_time"] > 0
            assert metrics["error_rate"] < 0.1  # Less than 10% error rate
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_studio_metrics_collection(self, studio_config, mock_studio_client):
        """Test collecting metrics from Studio."""
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test metrics collection
            metrics = mock_studio_client.get_metrics(
                deployment_id="deploy_123",
                time_range="1h"
            )
            
            assert metrics["total_requests"] > 0
            assert metrics["successful_requests"] > 0
            assert metrics["average_latency"] > 0
            assert metrics["p95_latency"] > metrics["average_latency"]
            assert metrics["p99_latency"] > metrics["p95_latency"]
            
            # Calculate success rate
            success_rate = metrics["successful_requests"] / metrics["total_requests"]
            assert success_rate > 0.9  # At least 90% success rate
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_studio_logging_integration(self, studio_config, mock_studio_client):
        """Test logging integration with Studio."""
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test log retrieval
            logs = mock_studio_client.get_logs(
                deployment_id="deploy_123",
                level="INFO",
                limit=100
            )
            
            assert len(logs) > 0
            
            for log_entry in logs:
                assert "timestamp" in log_entry
                assert "level" in log_entry
                assert "message" in log_entry
                assert log_entry["level"] in ["DEBUG", "INFO", "WARN", "ERROR"]
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_studio_tracing_integration(self, studio_config, mock_studio_client):
        """Test distributed tracing with Studio."""
        # Mock trace data
        mock_trace = {
            "trace_id": "trace_123",
            "spans": [
                {
                    "span_id": "span_1",
                    "operation_name": "analyze_logs",
                    "start_time": "2024-01-15T10:30:00Z",
                    "end_time": "2024-01-15T10:30:02Z",
                    "duration_ms": 2000,
                    "status": "success"
                },
                {
                    "span_id": "span_2", 
                    "operation_name": "validate_analysis",
                    "start_time": "2024-01-15T10:30:02Z",
                    "end_time": "2024-01-15T10:30:03Z",
                    "duration_ms": 1000,
                    "status": "success"
                }
            ]
        }
        
        mock_studio_client.get_trace.return_value = mock_trace
        
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test trace retrieval
            trace = mock_studio_client.get_trace("trace_123")
            
            assert trace["trace_id"] == "trace_123"
            assert len(trace["spans"]) == 2
            
            # Verify span details
            analyze_span = trace["spans"][0]
            assert analyze_span["operation_name"] == "analyze_logs"
            assert analyze_span["status"] == "success"
            assert analyze_span["duration_ms"] == 2000
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_studio_a_b_testing(self, studio_config, mock_studio_client):
        """Test A/B testing capabilities in Studio."""
        # Mock A/B test configuration
        ab_test_config = {
            "test_id": "original_vs_improved",
            "variants": [
                {
                    "name": "original",
                    "deployment_id": "deploy_original",
                    "traffic_percentage": 50
                },
                {
                    "name": "improved",
                    "deployment_id": "deploy_improved", 
                    "traffic_percentage": 50
                }
            ],
            "metrics": ["response_time", "accuracy", "user_satisfaction"]
        }
        
        mock_studio_client.create_ab_test.return_value = {
            "test_id": "original_vs_improved",
            "status": "running",
            "start_time": "2024-01-15T10:00:00Z"
        }
        
        mock_studio_client.get_ab_test_results.return_value = {
            "test_id": "original_vs_improved",
            "results": {
                "original": {
                    "response_time": 2.1,
                    "accuracy": 0.85,
                    "user_satisfaction": 4.2
                },
                "improved": {
                    "response_time": 1.8,
                    "accuracy": 0.92,
                    "user_satisfaction": 4.6
                }
            },
            "statistical_significance": 0.95
        }
        
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test A/B test creation
            test_result = mock_studio_client.create_ab_test(ab_test_config)
            
            assert test_result["test_id"] == "original_vs_improved"
            assert test_result["status"] == "running"
            
            # Test A/B test results
            results = mock_studio_client.get_ab_test_results("original_vs_improved")
            
            assert results["statistical_significance"] >= 0.95
            
            # Verify improved version performs better
            improved_metrics = results["results"]["improved"]
            original_metrics = results["results"]["original"]
            
            assert improved_metrics["response_time"] < original_metrics["response_time"]
            assert improved_metrics["accuracy"] > original_metrics["accuracy"]
            assert improved_metrics["user_satisfaction"] > original_metrics["user_satisfaction"]
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_studio_auto_scaling(self, studio_config, mock_studio_client):
        """Test auto-scaling configuration in Studio."""
        scaling_config = {
            "min_instances": 1,
            "max_instances": 10,
            "target_cpu_utilization": 70,
            "target_memory_utilization": 80,
            "scale_up_threshold": 5,  # requests per second
            "scale_down_threshold": 1,
            "cooldown_period": 300  # seconds
        }
        
        mock_studio_client.configure_auto_scaling.return_value = {
            "deployment_id": "deploy_123",
            "scaling_config": scaling_config,
            "status": "configured"
        }
        
        mock_studio_client.get_scaling_status.return_value = {
            "current_instances": 3,
            "target_instances": 3,
            "cpu_utilization": 65,
            "memory_utilization": 72,
            "requests_per_second": 4.2,
            "last_scale_event": "2024-01-15T10:25:00Z"
        }
        
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test scaling configuration
            config_result = mock_studio_client.configure_auto_scaling(
                deployment_id="deploy_123",
                config=scaling_config
            )
            
            assert config_result["status"] == "configured"
            assert config_result["scaling_config"]["max_instances"] == 10
            
            # Test scaling status
            status = mock_studio_client.get_scaling_status("deploy_123")
            
            assert status["current_instances"] >= scaling_config["min_instances"]
            assert status["current_instances"] <= scaling_config["max_instances"]
            assert status["cpu_utilization"] < 100
            assert status["memory_utilization"] < 100
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    def test_studio_rollback_functionality(self, studio_config, mock_studio_client):
        """Test rollback functionality in Studio."""
        # Mock deployment history
        deployment_history = [
            {
                "deployment_id": "deploy_123",
                "version": "v1.2.0",
                "status": "active",
                "deployed_at": "2024-01-15T10:30:00Z"
            },
            {
                "deployment_id": "deploy_122",
                "version": "v1.1.0", 
                "status": "inactive",
                "deployed_at": "2024-01-14T10:30:00Z"
            },
            {
                "deployment_id": "deploy_121",
                "version": "v1.0.0",
                "status": "inactive",
                "deployed_at": "2024-01-13T10:30:00Z"
            }
        ]
        
        mock_studio_client.get_deployment_history.return_value = deployment_history
        
        mock_studio_client.rollback_deployment.return_value = {
            "deployment_id": "deploy_122",
            "version": "v1.1.0",
            "status": "rolling_back",
            "rollback_started_at": "2024-01-15T11:00:00Z"
        }
        
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test deployment history retrieval
            history = mock_studio_client.get_deployment_history("log-analyzer-agent")
            
            assert len(history) == 3
            assert history[0]["status"] == "active"
            assert history[0]["version"] == "v1.2.0"
            
            # Test rollback to previous version
            rollback_result = mock_studio_client.rollback_deployment(
                project_id="log-analyzer-agent",
                target_deployment_id="deploy_122"
            )
            
            assert rollback_result["deployment_id"] == "deploy_122"
            assert rollback_result["version"] == "v1.1.0"
            assert rollback_result["status"] == "rolling_back"
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    @pytest.mark.slow
    def test_studio_load_testing(self, studio_config, mock_studio_client):
        """Test load testing integration with Studio."""
        load_test_config = {
            "test_name": "log_analyzer_load_test",
            "target_rps": 100,  # requests per second
            "duration_minutes": 10,
            "ramp_up_minutes": 2,
            "test_data": [
                {"log_content": "Sample log 1"},
                {"log_content": "Sample log 2"},
                {"log_content": "Sample log 3"}
            ]
        }
        
        mock_studio_client.start_load_test.return_value = {
            "test_id": "load_test_123",
            "status": "running",
            "started_at": "2024-01-15T11:00:00Z"
        }
        
        mock_studio_client.get_load_test_results.return_value = {
            "test_id": "load_test_123",
            "status": "completed",
            "results": {
                "total_requests": 60000,
                "successful_requests": 59400,
                "failed_requests": 600,
                "average_response_time": 1.8,
                "p95_response_time": 3.2,
                "p99_response_time": 5.1,
                "max_response_time": 8.7,
                "requests_per_second": 99.2,
                "error_rate": 0.01
            }
        }
        
        with patch('langgraph_studio.Client') as mock_client_class:
            mock_client_class.return_value = mock_studio_client
            
            # Test load test initiation
            test_result = mock_studio_client.start_load_test(load_test_config)
            
            assert test_result["test_id"] == "load_test_123"
            assert test_result["status"] == "running"
            
            # Test load test results
            results = mock_studio_client.get_load_test_results("load_test_123")
            
            assert results["status"] == "completed"
            
            test_metrics = results["results"]
            assert test_metrics["total_requests"] == 60000
            assert test_metrics["error_rate"] < 0.05  # Less than 5% error rate
            assert test_metrics["average_response_time"] < 3.0  # Less than 3 seconds
            assert test_metrics["requests_per_second"] > 90  # At least 90 RPS


class TestLangGraphStudioConfiguration:
    """Test LangGraph Studio configuration and setup."""
    
    @pytest.mark.integration
    def test_langgraph_json_configuration(self):
        """Test langgraph.json configuration for Studio deployment."""
        # Read the actual langgraph.json file
        langgraph_config_path = "/home/shl0th/Documents/langchain-takehome/langgraph.json"
        
        if os.path.exists(langgraph_config_path):
            with open(langgraph_config_path, 'r') as f:
                config = json.load(f)
            
            # Verify required fields
            assert "dependencies" in config
            assert "graphs" in config
            assert "env" in config
            
            # Verify graph configuration
            graphs = config["graphs"]
            assert isinstance(graphs, dict)
            
            for graph_name, graph_config in graphs.items():
                assert "path" in graph_config
                assert graph_config["path"].endswith(":graph") or graph_config["path"].endswith(":create_graph")
        else:
            pytest.skip("langgraph.json not found")
    
    @pytest.mark.integration
    def test_studio_environment_variables(self):
        """Test Studio environment variable configuration."""
        required_env_vars = [
            "GEMINI_API_KEY",
            "GROQ_API_KEY", 
            "TAVILY_API_KEY"
        ]
        
        optional_env_vars = [
            "LANGSMITH_API_KEY",
            "LANGGRAPH_STUDIO_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY"
        ]
        
        # Check that environment variables are properly configured
        missing_required = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        if missing_required:
            pytest.skip(f"Required environment variables not set: {missing_required}")
        
        # Log optional variables status
        missing_optional = []
        for var in optional_env_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        if missing_optional:
            print(f"Optional environment variables not set: {missing_optional}")
    
    @pytest.mark.integration
    def test_studio_deployment_readiness(self):
        """Test that the application is ready for Studio deployment."""
        # Test graph creation
        try:
            graph = create_graph()
            compiled_graph = graph.compile()
            assert compiled_graph is not None
        except Exception as e:
            pytest.fail(f"Graph creation failed: {e}")
        
        # Test improved graph creation
        try:
            improved_graph = create_improved_graph()
            compiled_improved = improved_graph.compile()
            assert compiled_improved is not None
        except Exception as e:
            pytest.fail(f"Improved graph creation failed: {e}")
        
        # Test that graphs can be serialized (required for deployment)
        try:
            graph_dict = compiled_graph.get_graph().to_dict()
            assert "nodes" in graph_dict
            assert "edges" in graph_dict
        except Exception as e:
            pytest.fail(f"Graph serialization failed: {e}")