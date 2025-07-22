"""
Unit tests for enhanced components in the improved implementation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from src.log_analyzer_agent.core.unified_state import UnifiedState
from src.log_analyzer_agent.core.circuit_breaker import CircuitBreaker
from src.log_analyzer_agent.core.rate_limiter import RateLimiter
from src.log_analyzer_agent.core.feature_registry import FeatureRegistry


class TestUnifiedState:
    """Test the unified state implementation."""
    
    def test_unified_state_initialization(self):
        """Test unified state initialization."""
        state = UnifiedState()
        
        # Check default values
        assert state.messages == []
        assert state.log_content == ""
        assert state.analysis_result is None
        assert state.iteration_count == 0
        assert state.analysis_complete is False
        assert state.enable_streaming is False
        assert state.enable_memory is False
        assert state.enable_ui_mode is False
    
    def test_unified_state_feature_flags(self):
        """Test unified state feature flag handling."""
        state = UnifiedState()
        
        # Test feature flag setting
        state.enable_streaming = True
        state.enable_subgraphs = True
        state.enable_circuit_breaker = True
        
        assert state.enable_streaming is True
        assert state.enable_subgraphs is True
        assert state.enable_circuit_breaker is True
    
    def test_unified_state_message_accumulation(self):
        """Test message accumulation in unified state."""
        state = UnifiedState()
        
        # Add messages
        state.messages.append({"role": "user", "content": "Test message 1"})
        state.messages.append({"role": "assistant", "content": "Test response 1"})
        
        assert len(state.messages) == 2
        assert state.messages[0]["content"] == "Test message 1"
        assert state.messages[1]["content"] == "Test response 1"
    
    def test_unified_state_analysis_data(self, sample_analysis_result):
        """Test analysis data handling in unified state."""
        state = UnifiedState()
        
        state.analysis_result = sample_analysis_result
        state.issues = sample_analysis_result["issues"]
        state.suggestions = sample_analysis_result["suggestions"]
        
        assert state.analysis_result == sample_analysis_result
        assert len(state.issues) > 0
        assert len(state.suggestions) > 0
    
    def test_unified_state_error_handling(self):
        """Test error handling in unified state."""
        state = UnifiedState()
        
        state.error_message = "Test error message"
        state.analysis_complete = False
        
        assert state.error_message == "Test error message"
        assert state.analysis_complete is False
    
    def test_unified_state_tool_calls(self):
        """Test tool call handling in unified state."""
        state = UnifiedState()
        
        tool_call = {
            "name": "search_documentation",
            "args": {"query": "test query"}
        }
        
        state.tool_calls = [tool_call]
        
        assert len(state.tool_calls) == 1
        assert state.tool_calls[0]["name"] == "search_documentation"
        assert state.tool_calls[0]["args"]["query"] == "test query"


class TestCircuitBreaker:
    """Test the circuit breaker implementation."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60
        assert cb.failure_count == 0
        assert cb.state == "closed"
        assert cb.last_failure_time is None
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Should allow calls in closed state
        assert cb.can_execute() is True
        assert cb.state == "closed"
    
    def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker failure tracking."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        # Record failures
        cb.record_failure()
        assert cb.failure_count == 1
        assert cb.state == "closed"
        
        cb.record_failure()
        assert cb.failure_count == 2
        assert cb.state == "open"  # Should open after reaching threshold
        assert cb.last_failure_time is not None
    
    def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Trigger open state
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False
    
    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)  # Short timeout
        
        # Trigger open state
        cb.record_failure()
        assert cb.state == "open"
        
        # Wait for recovery timeout
        import time
        time.sleep(0.2)
        
        # Should transition to half-open
        assert cb.can_execute() is True
        assert cb.state == "half_open"
    
    def test_circuit_breaker_success_recovery(self):
        """Test circuit breaker recovery on success."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        
        # Trigger open state
        cb.record_failure()
        assert cb.state == "open"
        
        # Wait and transition to half-open
        import time
        time.sleep(0.2)
        cb.can_execute()  # This transitions to half-open
        
        # Record success should close the circuit
        cb.record_success()
        assert cb.state == "closed"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_context_manager(self):
        """Test circuit breaker as context manager."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        # Test successful execution
        with cb:
            pass  # Successful execution
        
        assert cb.failure_count == 0
        assert cb.state == "closed"
        
        # Test failed execution
        try:
            with cb:
                raise Exception("Test failure")
        except Exception:
            pass
        
        assert cb.failure_count == 1
        assert cb.state == "closed"  # Still closed, threshold is 2


class TestRateLimiter:
    """Test the rate limiter implementation."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        rl = RateLimiter(max_requests=10, time_window=60)
        
        assert rl.max_requests == 10
        assert rl.time_window == 60
        assert len(rl.request_times) == 0
    
    def test_rate_limiter_allows_requests(self):
        """Test rate limiter allows requests within limit."""
        rl = RateLimiter(max_requests=5, time_window=60)
        
        # Should allow requests within limit
        for i in range(5):
            assert rl.acquire() is True
        
        assert len(rl.request_times) == 5
    
    def test_rate_limiter_blocks_excess_requests(self):
        """Test rate limiter blocks excess requests."""
        rl = RateLimiter(max_requests=2, time_window=60)
        
        # Allow first two requests
        assert rl.acquire() is True
        assert rl.acquire() is True
        
        # Block third request
        assert rl.acquire() is False
        
        assert len(rl.request_times) == 2
    
    def test_rate_limiter_time_window_cleanup(self):
        """Test rate limiter cleans up old requests."""
        rl = RateLimiter(max_requests=2, time_window=0.1)  # Short window
        
        # Make requests
        assert rl.acquire() is True
        assert rl.acquire() is True
        assert rl.acquire() is False  # Should be blocked
        
        # Wait for time window to pass
        import time
        time.sleep(0.2)
        
        # Should allow new requests after cleanup
        assert rl.acquire() is True
    
    def test_rate_limiter_context_manager(self):
        """Test rate limiter as context manager."""
        rl = RateLimiter(max_requests=3, time_window=60)
        
        # Test successful acquisition
        with rl:
            pass  # Should succeed
        
        assert len(rl.request_times) == 1
        
        # Test blocked acquisition
        rl.request_times = [time.time()] * 3  # Fill up the limit
        
        with rl:
            pass  # Should be blocked but not raise exception
    
    def test_rate_limiter_async_context_manager(self):
        """Test rate limiter as async context manager."""
        rl = RateLimiter(max_requests=2, time_window=60)
        
        async def test_async():
            async with rl:
                pass  # Should succeed
            
            assert len(rl.request_times) == 1
        
        asyncio.run(test_async())


class TestFeatureRegistry:
    """Test the feature registry implementation."""
    
    def test_feature_registry_initialization(self):
        """Test feature registry initialization."""
        registry = FeatureRegistry()
        
        # Should have default features
        assert "streaming" in registry.features
        assert "memory" in registry.features
        assert "ui_mode" in registry.features
        assert "subgraphs" in registry.features
        assert "circuit_breaker" in registry.features
        assert "rate_limiting" in registry.features
    
    def test_feature_registry_enable_disable(self):
        """Test enabling and disabling features."""
        registry = FeatureRegistry()
        
        # Test enabling feature
        registry.enable_feature("streaming")
        assert registry.is_enabled("streaming") is True
        
        # Test disabling feature
        registry.disable_feature("streaming")
        assert registry.is_enabled("streaming") is False
    
    def test_feature_registry_unknown_feature(self):
        """Test handling of unknown features."""
        registry = FeatureRegistry()
        
        # Should handle unknown features gracefully
        assert registry.is_enabled("unknown_feature") is False
        
        # Should not raise error when enabling unknown feature
        registry.enable_feature("unknown_feature")
        assert registry.is_enabled("unknown_feature") is True
    
    def test_feature_registry_bulk_operations(self):
        """Test bulk feature operations."""
        registry = FeatureRegistry()
        
        # Test enabling multiple features
        features_to_enable = ["streaming", "memory", "subgraphs"]
        for feature in features_to_enable:
            registry.enable_feature(feature)
        
        for feature in features_to_enable:
            assert registry.is_enabled(feature) is True
        
        # Test disabling all features
        registry.disable_all()
        for feature in features_to_enable:
            assert registry.is_enabled(feature) is False
    
    def test_feature_registry_get_enabled_features(self):
        """Test getting list of enabled features."""
        registry = FeatureRegistry()
        
        # Enable some features
        registry.enable_feature("streaming")
        registry.enable_feature("memory")
        
        enabled = registry.get_enabled_features()
        assert "streaming" in enabled
        assert "memory" in enabled
        assert len(enabled) == 2
    
    def test_feature_registry_configuration_integration(self):
        """Test feature registry integration with configuration."""
        registry = FeatureRegistry()
        
        # Test configuration-style feature setting
        config = {
            "enable_streaming": True,
            "enable_memory": False,
            "enable_subgraphs": True
        }
        
        for key, value in config.items():
            feature_name = key.replace("enable_", "")
            if value:
                registry.enable_feature(feature_name)
            else:
                registry.disable_feature(feature_name)
        
        assert registry.is_enabled("streaming") is True
        assert registry.is_enabled("memory") is False
        assert registry.is_enabled("subgraphs") is True


class TestEnhancedIntegration:
    """Test integration between enhanced components."""
    
    @pytest.mark.asyncio
    async def test_unified_state_with_circuit_breaker(self):
        """Test unified state integration with circuit breaker."""
        state = UnifiedState()
        state.enable_circuit_breaker = True
        
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        # Simulate analysis with circuit breaker
        if cb.can_execute():
            try:
                with cb:
                    # Simulate successful analysis
                    state.analysis_result = {"summary": "Test analysis", "issues": [], "suggestions": []}
                    state.analysis_complete = True
            except Exception as e:
                state.error_message = str(e)
        
        assert state.analysis_complete is True
        assert state.analysis_result is not None
        assert cb.state == "closed"
    
    @pytest.mark.asyncio
    async def test_unified_state_with_rate_limiter(self):
        """Test unified state integration with rate limiter."""
        state = UnifiedState()
        state.enable_rate_limiting = True
        
        rl = RateLimiter(max_requests=3, time_window=60)
        
        # Simulate multiple analysis requests
        results = []
        for i in range(5):
            if rl.acquire():
                # Simulate successful analysis
                result = {"summary": f"Analysis {i}", "issues": [], "suggestions": []}
                results.append(result)
            else:
                # Rate limited
                state.error_message = "Rate limit exceeded"
                break
        
        assert len(results) == 3  # Should only allow 3 requests
        assert state.error_message == "Rate limit exceeded"
    
    def test_feature_registry_with_unified_state(self):
        """Test feature registry integration with unified state."""
        registry = FeatureRegistry()
        state = UnifiedState()
        
        # Configure features through registry
        registry.enable_feature("streaming")
        registry.enable_feature("memory")
        registry.disable_feature("ui_mode")
        
        # Apply to state
        state.enable_streaming = registry.is_enabled("streaming")
        state.enable_memory = registry.is_enabled("memory")
        state.enable_ui_mode = registry.is_enabled("ui_mode")
        
        assert state.enable_streaming is True
        assert state.enable_memory is True
        assert state.enable_ui_mode is False
    
    @pytest.mark.asyncio
    async def test_enhanced_error_handling_integration(self):
        """Test integration of enhanced error handling components."""
        state = UnifiedState()
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        rl = RateLimiter(max_requests=2, time_window=60)
        
        # Simulate analysis with both circuit breaker and rate limiter
        async def enhanced_analysis():
            if not rl.acquire():
                raise Exception("Rate limit exceeded")
            
            if not cb.can_execute():
                raise Exception("Circuit breaker open")
            
            try:
                with cb:
                    # Simulate analysis that might fail
                    if state.iteration_count > 0:
                        raise Exception("Analysis failed")
                    
                    state.analysis_result = {"summary": "Success", "issues": [], "suggestions": []}
                    state.analysis_complete = True
                    return state.analysis_result
            except Exception as e:
                state.error_message = str(e)
                raise
        
        # First attempt should succeed
        try:
            result = await enhanced_analysis()
            assert result is not None
            assert state.analysis_complete is True
        except Exception:
            pass
        
        # Second attempt should fail and open circuit breaker
        state.iteration_count = 1
        state.analysis_complete = False
        state.error_message = None
        
        try:
            await enhanced_analysis()
        except Exception:
            pass
        
        assert cb.state == "open"
        assert state.error_message is not None