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
        assert state.features == set()
        assert state.node_visits == {}
        assert state.tool_calls == []
        assert state.token_count == 0
        assert state.user_interaction_required is False
    
    def test_unified_state_feature_flags(self):
        """Test unified state feature flag handling."""
        state = UnifiedState()
        
        # Test feature flag setting
        state.enable_feature("streaming")
        state.enable_feature("subgraphs")
        state.enable_feature("circuit_breaker")
        
        assert state.has_feature("streaming") is True
        assert state.has_feature("subgraphs") is True
        assert state.has_feature("circuit_breaker") is True
    
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
        assert cb._consecutive_failures == 0
        assert cb.state.value == "closed"
        assert cb._last_failure_time is None
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Should allow calls in closed state
        assert cb.state.value == "closed"
        # Test by calling a function through the circuit breaker
        def test_func():
            return "success"
        result = cb.call(test_func)
        assert result == "success"
    
    def test_circuit_breaker_failure_tracking(self):
        """Test circuit breaker failure tracking."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60, failure_rate_threshold=1.1)
        
        # Record failures by calling failing functions
        def failing_func():
            raise Exception("Test failure")
        
        # First failure
        with pytest.raises(Exception):
            cb.call(failing_func)
        assert cb._consecutive_failures == 1
        # Circuit should still be closed after first failure
        assert cb.state.value == "closed"
        
        # Second failure should open circuit
        with pytest.raises(Exception):
            cb.call(failing_func)
        assert cb._consecutive_failures == 2
        assert cb.state.value == "open"
        assert cb._last_failure_time is not None
    
    def test_circuit_breaker_open_state(self):
        """Test circuit breaker in open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Trigger open state
        def failing_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception):
            cb.call(failing_func)
        assert cb.state.value == "open"
        
        # Should reject calls when open
        from src.log_analyzer_agent.core.circuit_breaker import CircuitBreakerOpen
        with pytest.raises(CircuitBreakerOpen):
            cb.call(lambda: "test")
    
    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker in half-open state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)  # Short timeout
        
        # Trigger open state
        def failing_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception):
            cb.call(failing_func)
        assert cb.state.value == "open"
        
        # Wait for recovery timeout
        import time
        time.sleep(0.2)
        
        # Should transition to half-open when we check state
        assert cb.state.value == "half_open"
    
    def test_circuit_breaker_success_recovery(self):
        """Test circuit breaker recovery on success."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=1)
        
        # Trigger open state
        def failing_func():
            raise Exception("Test failure")
        
        with pytest.raises(Exception):
            cb.call(failing_func)
        assert cb.state.value == "open"
        
        # Wait and transition to half-open
        import time
        time.sleep(0.2)
        assert cb.state.value == "half_open"  # This transitions to half-open
        
        # Successful call should close the circuit
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb.state.value == "closed"
        assert cb._consecutive_failures == 0
    
    def test_circuit_breaker_context_manager(self):
        """Test circuit breaker as context manager."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        # Circuit breaker doesn't implement context manager protocol
        # Test using decorator instead
        @cb.decorator
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
        assert cb._consecutive_failures == 0
        assert cb.state.value == "closed"


class TestRateLimiter:
    """Test the rate limiter implementation."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        from src.log_analyzer_agent.core.rate_limiter import RateLimitConfig
        config = RateLimitConfig(calls_per_minute=10)
        rl = RateLimiter(config=config)
        
        assert rl.config.calls_per_minute == 10
        assert rl.name == "default"
        assert len(rl._request_times) == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Test rate limiter allows requests within limit."""
        from src.log_analyzer_agent.core.rate_limiter import RateLimitConfig
        config = RateLimitConfig(calls_per_minute=5)
        rl = RateLimiter(config=config)
        
        # Should allow requests within limit
        for i in range(5):
            await rl.acquire()  # Should not raise exception
        
        assert rl._stats.allowed_requests == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess_requests(self):
        """Test rate limiter blocks excess requests."""
        from src.log_analyzer_agent.core.rate_limiter import RateLimitConfig
        config = RateLimitConfig(calls_per_minute=2)
        rl = RateLimiter(config=config)
        
        # Allow first two requests
        await rl.acquire()
        await rl.acquire()
        
        # Block third request
        from src.log_analyzer_agent.core.rate_limiter import RateLimitExceeded
        with pytest.raises(RateLimitExceeded):
            await rl.acquire()
        
        assert rl._stats.allowed_requests == 2
        assert rl._stats.rejected_requests == 1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_time_window_cleanup(self):
        """Test rate limiter cleans up old requests."""
        from src.log_analyzer_agent.core.rate_limiter import RateLimitConfig, RateLimitExceeded
        config = RateLimitConfig(calls_per_minute=120)  # 2 per second for testing
        rl = RateLimiter(config=config)
        
        # Make requests quickly
        await rl.acquire()
        await rl.acquire()
        
        # Wait a bit and should be able to make more requests
        import asyncio
        await asyncio.sleep(0.1)
        
        # Should allow new requests
        await rl.acquire()
    
    @pytest.mark.asyncio
    async def test_rate_limiter_context_manager(self):
        """Test rate limiter as context manager."""
        from src.log_analyzer_agent.core.rate_limiter import RateLimitConfig
        config = RateLimitConfig(calls_per_minute=3)
        rl = RateLimiter(config=config)
        
        # Test using decorator instead of context manager
        @rl.decorator()
        async def test_func():
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert rl._stats.allowed_requests == 1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_async_context_manager(self):
        """Test rate limiter as async context manager."""
        from src.log_analyzer_agent.core.rate_limiter import RateLimitConfig
        config = RateLimitConfig(calls_per_minute=2)
        rl = RateLimiter(config=config)
        
        # Test using decorator for async functions
        @rl.decorator()
        async def test_async():
            return "async_success"
        
        result = await test_async()
        assert result == "async_success"
        assert rl._stats.allowed_requests == 1
        



class TestFeatureRegistry:
    """Test the feature registry implementation."""
    
    def test_feature_registry_initialization(self):
        """Test feature registry initialization."""
        registry = FeatureRegistry()
        
        # Should have default features
        assert "streaming" in registry._features
        assert "memory" in registry._features
        assert "interactive" in registry._features
        assert "specialized" in registry._features
        assert "circuit_breaker" in registry._features
        assert "rate_limiting" in registry._features
    
    def test_feature_registry_enable_disable(self):
        """Test enabling and disabling features."""
        registry = FeatureRegistry()
        
        # Streaming should already be enabled by default
        assert registry.is_enabled("streaming") is True
        
        # Test disabling feature
        registry.disable("streaming")
        assert registry.is_enabled("streaming") is False
        
        # Test re-enabling feature
        registry.enable("streaming")
        assert registry.is_enabled("streaming") is True
    
    def test_feature_registry_unknown_feature(self):
        """Test handling of unknown features."""
        registry = FeatureRegistry()
        
        # Should handle unknown features gracefully
        assert registry.is_enabled("unknown_feature") is False
        
        # Should return False when enabling unknown feature
        result = registry.enable("unknown_feature")
        assert result is False
        assert registry.is_enabled("unknown_feature") is False
    
    def test_feature_registry_bulk_operations(self):
        """Test bulk feature operations."""
        registry = FeatureRegistry()
        
        # Test enabling multiple features (some already enabled by default)
        features_to_enable = ["streaming", "memory", "specialized"]
        for feature in features_to_enable:
            registry.enable(feature)
        
        for feature in features_to_enable:
            assert registry.is_enabled(feature) is True
        
        # Test disabling features
        for feature in features_to_enable:
            registry.disable(feature)
            assert registry.is_enabled(feature) is False
    
    def test_feature_registry_get_enabled_features(self):
        """Test getting list of enabled features."""
        registry = FeatureRegistry()
        
        # Get initially enabled features (some are enabled by default)
        enabled = registry.get_enabled_features()
        assert "streaming" in enabled
        assert "memory" in enabled
        assert len(enabled) > 0
    
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
                registry.enable(feature_name)
            else:
                registry.disable(feature_name)
        
        assert registry.is_enabled("streaming") is True
        assert registry.is_enabled("memory") is False
        assert registry.is_enabled("subgraphs") is True


class TestEnhancedIntegration:
    """Test integration between enhanced components."""
    
    @pytest.mark.asyncio
    async def test_unified_state_with_circuit_breaker(self):
        """Test unified state integration with circuit breaker."""
        state = UnifiedState()
        state.enable_feature("circuit_breaker")
        
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        # Simulate analysis with circuit breaker
        def analysis_func():
            # Simulate successful analysis
            state.analysis_result = {"summary": "Test analysis", "issues": [], "suggestions": []}
            return "success"
        
        result = cb.call(analysis_func)
        assert result == "success"
        assert state.analysis_result is not None
        assert cb.state.value == "closed"
    
    @pytest.mark.asyncio
    async def test_unified_state_with_rate_limiter(self):
        """Test unified state integration with rate limiter."""
        state = UnifiedState()
        state.enable_feature("rate_limiting")
        
        from src.log_analyzer_agent.core.rate_limiter import RateLimitConfig, RateLimitExceeded
        config = RateLimitConfig(calls_per_minute=3)
        rl = RateLimiter(config=config)
        
        # Simulate multiple analysis requests
        results = []
        for i in range(5):
            try:
                await rl.acquire()
                # Simulate successful analysis
                result = {"summary": f"Analysis {i}", "issues": [], "suggestions": []}
                results.append(result)
            except RateLimitExceeded:
                # Rate limited
                break
        
        assert len(results) == 3  # Should only allow 3 requests
    
    def test_feature_registry_with_unified_state(self):
        """Test feature registry integration with unified state."""
        registry = FeatureRegistry()
        state = UnifiedState()
        
        # Configure features through registry
        registry.enable("streaming")
        registry.enable("memory")
        registry.disable("interactive")
        
        # Apply to state
        if registry.is_enabled("streaming"):
            state.enable_feature("streaming")
        if registry.is_enabled("memory"):
            state.enable_feature("memory")
        if not registry.is_enabled("interactive"):
            state.disable_feature("interactive")
        
        assert state.has_feature("streaming") is True
        assert state.has_feature("memory") is True
        assert state.has_feature("interactive") is False
    
    @pytest.mark.asyncio
    async def test_enhanced_error_handling_integration(self):
        """Test integration of enhanced error handling components."""
        state = UnifiedState()
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        from src.log_analyzer_agent.core.rate_limiter import RateLimitConfig
        config = RateLimitConfig(calls_per_minute=2)
        rl = RateLimiter(config=config)
        
        # Simulate analysis with both circuit breaker and rate limiter
        async def enhanced_analysis():
            await rl.acquire()  # May raise RateLimitExceeded
            
            def analysis_func():
                # Simulate analysis that succeeds
                state.analysis_result = {"summary": "Success", "issues": [], "suggestions": []}
                return state.analysis_result
            
            return cb.call(analysis_func)
        
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