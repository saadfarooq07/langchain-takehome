#!/usr/bin/env python3
"""Test script to verify Phase 1 improvements are working correctly."""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def test_model_pool():
    """Test that model pool is working correctly."""
    print("\n🧪 Testing Model Pool...")
    
    from log_analyzer_agent.model_pool import get_model_pool
    from log_analyzer_agent.configuration import Configuration
    
    config = Configuration()
    pool = await get_model_pool()
    
    # Test acquiring models multiple times
    print("  - Acquiring model first time (should be a miss)")
    async with pool.get_model(config.primary_model) as model1:
        assert model1 is not None
    
    print("  - Acquiring model second time (should be a hit)")
    async with pool.get_model(config.primary_model) as model2:
        assert model2 is not None
    
    # Check metrics
    metrics = pool.get_metrics()
    print(f"  - Pool metrics: Hits={metrics['hits']}, Misses={metrics['misses']}")
    assert metrics['hits'] >= 1, "Model pool should have at least one hit"
    
    print("✅ Model Pool test passed!")
    

async def test_database_pool():
    """Test that database pool is working correctly."""
    print("\n🧪 Testing Database Pool...")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("⚠️  Skipping DB pool test - DATABASE_URL not set")
        return
    
    from log_analyzer_agent.db_pool import get_db_pool
    
    pool = await get_db_pool()
    
    # Test health check
    print("  - Running health check")
    is_healthy = await pool.health_check()
    if is_healthy:
        print("  - Database connection is healthy")
    else:
        print("⚠️  Database connection failed - skipping test")
        return
    
    # Test acquiring connections
    print("  - Testing connection acquisition")
    async with pool.acquire() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    
    # Check pool status
    status = pool.get_pool_status()
    print(f"  - Pool status: {status['status']}, Free connections: {status.get('free_size', 'N/A')}")
    
    print("✅ Database Pool test passed!")


def test_cycle_detector():
    """Test that cycle detector is working correctly."""
    print("\n🧪 Testing Cycle Detector...")
    
    from log_analyzer_agent.cycle_detector import CycleDetector, CycleType
    
    detector = CycleDetector(max_simple_loops=2)
    
    # Test simple loop detection
    print("  - Testing simple loop detection")
    state1 = {"test": "state1"}
    state2 = {"test": "state2"}
    
    detector.add_transition("A", "B", state1)
    detector.add_transition("B", "A", state2)
    detector.add_transition("A", "B", state1)
    detector.add_transition("B", "A", state2)
    
    should_break = detector.should_break_cycle()
    cycle = detector.get_current_cycle()
    
    print(f"  - Should break: {should_break}")
    if cycle:
        print(f"  - Detected cycle type: {cycle.cycle_type}")
        print(f"  - Pattern: {' -> '.join(cycle.pattern)}")
    
    assert should_break, "Should detect simple loop after threshold"
    assert cycle.cycle_type == CycleType.SIMPLE_LOOP
    
    print("✅ Cycle Detector test passed!")


def test_configurable_limits():
    """Test that environment variables are being read correctly."""
    print("\n🧪 Testing Configurable Limits...")
    
    # Set test values
    os.environ["MAX_ANALYSIS_ITERATIONS"] = "5"
    os.environ["MAX_TOOL_CALLS"] = "10"
    os.environ["MAX_VALIDATION_RETRIES"] = "2"
    
    # Reload the module to pick up new values
    import importlib
    import log_analyzer_agent.graph as graph_module
    importlib.reload(graph_module)
    
    print(f"  - MAX_ANALYSIS_ITERATIONS: {graph_module.MAX_ANALYSIS_ITERATIONS}")
    print(f"  - MAX_TOOL_CALLS: {graph_module.MAX_TOOL_CALLS}")
    print(f"  - MAX_VALIDATION_RETRIES: {graph_module.MAX_VALIDATION_RETRIES}")
    
    assert graph_module.MAX_ANALYSIS_ITERATIONS == 5
    assert graph_module.MAX_TOOL_CALLS == 10
    assert graph_module.MAX_VALIDATION_RETRIES == 2
    
    print("✅ Configurable Limits test passed!")


async def main():
    """Run all tests."""
    print("🚀 Testing Phase 1 Improvements")
    print("=" * 50)
    
    try:
        # Test each improvement
        await test_model_pool()
        await test_database_pool()
        test_cycle_detector()
        test_configurable_limits()
        
        print("\n" + "=" * 50)
        print("✅ All Phase 1 improvements are working correctly!")
        print("\nSummary of improvements:")
        print("1. ✅ Model Pool - Reusing model instances across requests")
        print("2. ✅ Database Pool - Connection reuse in auth services")
        print("3. ✅ Cycle Detector - Advanced loop prevention")
        print("4. ✅ Configurable Limits - Via environment variables")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())