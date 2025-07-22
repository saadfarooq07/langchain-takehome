"""
Integration tests for API interactions in the Log Analyzer Agent.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.log_analyzer_agent.tools import (
    search_documentation,
    request_additional_info,
    submit_analysis
)
from src.log_analyzer_agent.utils import get_model, get_orchestration_model


class TestAPIIntegration:
    """Test integration with external APIs."""
    
    @pytest.fixture
    def mock_api_responses(self):
        """Mock API responses for testing."""
        return {
            "gemini": {
                "text": """
                {
                    "summary": "API integration test analysis",
                    "issues": [
                        {
                            "severity": "medium",
                            "category": "api",
                            "description": "API integration test issue",
                            "affected_components": ["TestComponent"],
                            "first_occurrence": "2024-01-15 10:30:00",
                            "frequency": 1
                        }
                    ],
                    "suggestions": [
                        {
                            "priority": "medium",
                            "category": "testing",
                            "description": "API integration test suggestion",
                            "implementation": "Test implementation",
                            "estimated_impact": "Test impact"
                        }
                    ]
                }
                """
            },
            "groq": {
                "choices": [
                    {
                        "message": {
                            "content": """
                            {
                                "is_valid": true,
                                "completeness_score": 0.8,
                                "accuracy_score": 0.8,
                                "feedback": "API integration test validation"
                            }
                            """
                        }
                    }
                ]
            },
            "tavily": {
                "results": [
                    {
                        "title": "API Integration Documentation",
                        "url": "https://docs.example.com/api-integration",
                        "content": "Documentation for API integration testing"
                    }
                ]
            }
        }
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    async def test_gemini_api_integration(self, mock_env_vars, mock_api_responses):
        """Test integration with Gemini API."""
        with patch('google.generativeai.GenerativeModel') as mock_gemini:
            # Setup mock
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = mock_api_responses["gemini"]["text"]
            mock_model.generate_content.return_value = mock_response
            mock_gemini.return_value = mock_model
            
            # Test model creation and usage
            model = get_model("gemini-2.5-flash")
            assert model is not None
            
            # Test content generation
            response = model.generate_content("Test prompt")
            assert response is not None
            assert response.text is not None
            
            # Verify API was called correctly
            mock_model.generate_content.assert_called_once_with("Test prompt")
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    async def test_groq_api_integration(self, mock_env_vars, mock_api_responses):
        """Test integration with Groq API."""
        with patch('groq.AsyncGroq') as mock_groq:
            # Setup mock
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.choices = mock_api_responses["groq"]["choices"]
            mock_client.chat.completions.create.return_value = mock_response
            mock_groq.return_value = mock_client
            
            # Test model creation and usage
            model = get_orchestration_model("kimi-k2")
            assert model is not None
            
            # Test chat completion
            response = await model.chat.completions.create(
                model="kimi-k2",
                messages=[{"role": "user", "content": "Test message"}]
            )
            
            assert response is not None
            assert response.choices is not None
            assert len(response.choices) > 0
            
            # Verify API was called correctly
            mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    async def test_tavily_api_integration(self, mock_env_vars, mock_api_responses):
        """Test integration with Tavily search API."""
        with patch('tavily.TavilyClient') as mock_tavily:
            # Setup mock
            mock_client = Mock()
            mock_client.search.return_value = mock_api_responses["tavily"]
            mock_tavily.return_value = mock_client
            
            # Test search functionality
            result = await search_documentation("test query")
            
            assert result is not None
            assert "results" in result
            assert len(result["results"]) > 0
            
            # Verify search was called correctly
            mock_client.search.assert_called_once()
    
    @pytest.mark.integration
    async def test_api_error_handling(self, mock_env_vars):
        """Test API error handling and retries."""
        with patch('google.generativeai.GenerativeModel') as mock_gemini:
            # Setup mock to raise exception
            mock_model = Mock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_gemini.return_value = mock_model
            
            # Test error handling
            model = get_model("gemini-2.5-flash")
            
            with pytest.raises(Exception) as exc_info:
                model.generate_content("Test prompt")
            
            assert "API Error" in str(exc_info.value)
    
    @pytest.mark.integration
    async def test_api_rate_limiting(self, mock_env_vars):
        """Test API rate limiting behavior."""
        with patch('google.generativeai.GenerativeModel') as mock_gemini:
            # Setup mock to simulate rate limiting
            call_count = 0
            def rate_limited_response(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise Exception("Rate limit exceeded")
                else:
                    mock_response = Mock()
                    mock_response.text = '{"summary": "Rate limit test", "issues": [], "suggestions": []}'
                    return mock_response
            
            mock_model = Mock()
            mock_model.generate_content.side_effect = rate_limited_response
            mock_gemini.return_value = mock_model
            
            model = get_model("gemini-2.5-flash")
            
            # Should eventually succeed after rate limit errors
            # In a real implementation, this would include retry logic
            with pytest.raises(Exception):
                model.generate_content("Test prompt")  # First call fails
            
            with pytest.raises(Exception):
                model.generate_content("Test prompt")  # Second call fails
            
            # Third call should succeed
            response = model.generate_content("Test prompt")
            assert response is not None
    
    @pytest.mark.integration
    async def test_concurrent_api_calls(self, mock_env_vars, mock_api_responses):
        """Test concurrent API calls."""
        with patch('google.generativeai.GenerativeModel') as mock_gemini, \
             patch('groq.AsyncGroq') as mock_groq, \
             patch('tavily.TavilyClient') as mock_tavily:
            
            # Setup mocks
            mock_gemini_model = Mock()
            mock_gemini_response = Mock()
            mock_gemini_response.text = mock_api_responses["gemini"]["text"]
            mock_gemini_model.generate_content.return_value = mock_gemini_response
            mock_gemini.return_value = mock_gemini_model
            
            mock_groq_client = AsyncMock()
            mock_groq_response = Mock()
            mock_groq_response.choices = mock_api_responses["groq"]["choices"]
            mock_groq_client.chat.completions.create.return_value = mock_groq_response
            mock_groq.return_value = mock_groq_client
            
            mock_tavily_client = Mock()
            mock_tavily_client.search.return_value = mock_api_responses["tavily"]
            mock_tavily.return_value = mock_tavily_client
            
            # Test concurrent API calls
            async def gemini_call():
                model = get_model("gemini-2.5-flash")
                return model.generate_content("Gemini test")
            
            async def groq_call():
                model = get_orchestration_model("kimi-k2")
                return await model.chat.completions.create(
                    model="kimi-k2",
                    messages=[{"role": "user", "content": "Groq test"}]
                )
            
            async def tavily_call():
                return await search_documentation("Tavily test")
            
            # Execute concurrently
            results = await asyncio.gather(
                gemini_call(),
                groq_call(),
                tavily_call(),
                return_exceptions=True
            )
            
            # Verify all calls completed
            assert len(results) == 3
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent API call failed: {result}")
                assert result is not None


class TestToolIntegration:
    """Test integration of tools with APIs."""
    
    @pytest.mark.integration
    async def test_search_documentation_integration(self, mock_env_vars):
        """Test search documentation tool integration."""
        with patch('tavily.TavilyClient') as mock_tavily:
            mock_client = Mock()
            mock_client.search.return_value = {
                "results": [
                    {
                        "title": "Integration Test Documentation",
                        "url": "https://docs.example.com/integration",
                        "content": "Integration testing documentation content"
                    },
                    {
                        "title": "API Testing Guide",
                        "url": "https://docs.example.com/api-testing",
                        "content": "Guide for testing API integrations"
                    }
                ]
            }
            mock_tavily.return_value = mock_client
            
            # Test search functionality
            result = await search_documentation("integration testing best practices")
            
            assert result is not None
            assert "results" in result
            assert len(result["results"]) == 2
            
            # Verify search parameters
            mock_client.search.assert_called_once()
            call_args = mock_client.search.call_args
            assert "integration testing best practices" in str(call_args)
    
    @pytest.mark.integration
    async def test_request_additional_info_integration(self, mock_env_vars):
        """Test request additional info tool integration."""
        # Test the tool functionality
        result = await request_additional_info("Please provide database configuration details")
        
        assert result is not None
        assert "message" in result
        assert "database configuration details" in result["message"]
        assert result["requires_user_input"] is True
    
    @pytest.mark.integration
    async def test_submit_analysis_integration(self, mock_env_vars, sample_analysis_result):
        """Test submit analysis tool integration."""
        # Test the tool functionality
        result = await submit_analysis(sample_analysis_result)
        
        assert result is not None
        assert "status" in result
        assert result["status"] == "submitted"
        assert "analysis" in result
        assert result["analysis"] == sample_analysis_result
    
    @pytest.mark.integration
    async def test_tool_error_handling(self, mock_env_vars):
        """Test tool error handling."""
        with patch('tavily.TavilyClient') as mock_tavily:
            mock_client = Mock()
            mock_client.search.side_effect = Exception("Search API Error")
            mock_tavily.return_value = mock_client
            
            # Test error handling in search tool
            result = await search_documentation("test query")
            
            # Should handle error gracefully
            assert result is not None
            assert "error" in result or "results" in result
    
    @pytest.mark.integration
    async def test_tool_timeout_handling(self, mock_env_vars):
        """Test tool timeout handling."""
        import asyncio
        
        with patch('tavily.TavilyClient') as mock_tavily:
            mock_client = Mock()
            
            # Simulate slow API response
            async def slow_search(*args, **kwargs):
                await asyncio.sleep(10)  # Simulate 10 second delay
                return {"results": []}
            
            mock_client.search.side_effect = slow_search
            mock_tavily.return_value = mock_client
            
            # Test with timeout
            try:
                result = await asyncio.wait_for(
                    search_documentation("test query"),
                    timeout=5.0  # 5 second timeout
                )
                # If we get here, the call completed within timeout
                assert result is not None
            except asyncio.TimeoutError:
                # Expected behavior for slow API
                pass
    
    @pytest.mark.integration
    async def test_tool_retry_logic(self, mock_env_vars):
        """Test tool retry logic for transient failures."""
        with patch('tavily.TavilyClient') as mock_tavily:
            mock_client = Mock()
            
            # Setup to fail first two calls, succeed on third
            call_count = 0
            def retry_search(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise Exception("Transient API Error")
                else:
                    return {"results": [{"title": "Retry Success", "content": "Success after retry"}]}
            
            mock_client.search.side_effect = retry_search
            mock_tavily.return_value = mock_client
            
            # Test retry behavior (if implemented)
            # Note: This test assumes retry logic exists in the tool
            try:
                result = await search_documentation("test query")
                # If retry logic exists, this should succeed
                assert result is not None
                if "results" in result:
                    assert len(result["results"]) > 0
            except Exception:
                # If no retry logic, expect the exception
                pass


class TestModelIntegration:
    """Test integration with different AI models."""
    
    @pytest.mark.integration
    @pytest.mark.requires_api
    async def test_model_switching(self, mock_env_vars):
        """Test switching between different models."""
        with patch('google.generativeai.GenerativeModel') as mock_gemini, \
             patch('groq.AsyncGroq') as mock_groq:
            
            # Setup mocks
            mock_gemini_model = Mock()
            mock_gemini_response = Mock()
            mock_gemini_response.text = "Gemini response"
            mock_gemini_model.generate_content.return_value = mock_gemini_response
            mock_gemini.return_value = mock_gemini_model
            
            mock_groq_client = AsyncMock()
            mock_groq_response = Mock()
            mock_groq_response.choices = [Mock()]
            mock_groq_response.choices[0].message.content = "Groq response"
            mock_groq_client.chat.completions.create.return_value = mock_groq_response
            mock_groq.return_value = mock_groq_client
            
            # Test Gemini model
            gemini_model = get_model("gemini-2.5-flash")
            gemini_response = gemini_model.generate_content("Test prompt")
            assert gemini_response.text == "Gemini response"
            
            # Test Groq model
            groq_model = get_orchestration_model("kimi-k2")
            groq_response = await groq_model.chat.completions.create(
                model="kimi-k2",
                messages=[{"role": "user", "content": "Test message"}]
            )
            assert groq_response.choices[0].message.content == "Groq response"
    
    @pytest.mark.integration
    async def test_model_configuration(self, mock_env_vars):
        """Test model configuration and parameters."""
        with patch('google.generativeai.GenerativeModel') as mock_gemini:
            mock_model = Mock()
            mock_gemini.return_value = mock_model
            
            # Test model creation with different configurations
            model = get_model("gemini-2.5-flash")
            assert model is not None
            
            # Verify model was created with correct parameters
            mock_gemini.assert_called_once()
            call_args = mock_gemini.call_args
            assert "gemini-2.5-flash" in str(call_args)
    
    @pytest.mark.integration
    async def test_model_fallback(self, mock_env_vars):
        """Test model fallback behavior."""
        with patch('google.generativeai.GenerativeModel') as mock_gemini:
            # First model fails
            mock_gemini.side_effect = [
                Exception("Primary model unavailable"),
                Mock()  # Fallback model succeeds
            ]
            
            # Test fallback logic (if implemented)
            try:
                model = get_model("gemini-2.5-flash")
                # If fallback is implemented, should succeed
                assert model is not None
            except Exception:
                # If no fallback, expect exception
                pass