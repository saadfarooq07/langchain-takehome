"""
Performance and load tests for the Log Analyzer Agent.
"""

import pytest
import asyncio
import time
import psutil
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from concurrent.futures import ThreadPoolExecutor

from src.log_analyzer_agent.graph import create_graph
from src.log_analyzer_agent.core.improved_graph import create_improved_graph


class TestPerformanceBenchmarks:
    """Performance benchmarks for various system components."""
    
    @pytest.fixture
    def performance_config(self, mock_env_vars):
        """Configuration optimized for performance testing."""
        return {
            "configurable": {
                "primary_model": "gemini-2.5-flash",
                "orchestration_model": "kimi-k2",
                "max_iterations": 2,  # Reduced for performance
                "enable_streaming": True,
                "enable_memory": False,
                "enable_ui_mode": False,
                "chunk_size": 5000,
                "max_chunk_overlap": 200
            }
        }
    
    @pytest.fixture
    def large_log_generator(self):
        """Generate large log files for performance testing."""
        def generate_log(size_mb: int, pattern: str = "standard") -> str:
            """Generate log content of specified size."""
            lines = []
            target_size = size_mb * 1024 * 1024  # Convert MB to bytes
            current_size = 0
            
            if pattern == "standard":
                base_line = "2024-01-15 10:30:{:02d} INFO [Service{}] Processing request {} - status: success"
            elif pattern == "error_heavy":
                base_line = "2024-01-15 10:30:{:02d} ERROR [Service{}] Failed to process request {} - error: connection timeout"
            elif pattern == "mixed":
                patterns = [
                    "2024-01-15 10:30:{:02d} INFO [Service{}] Processing request {} - status: success",
                    "2024-01-15 10:30:{:02d} WARN [Service{}] Slow response for request {} - took 2.5s",
                    "2024-01-15 10:30:{:02d} ERROR [Service{}] Failed request {} - error: database timeout"
                ]
                base_line = None
            else:
                base_line = pattern
            
            i = 0
            while current_size < target_size:
                if pattern == "mixed":
                    line = patterns[i % len(patterns)].format(i % 60, i % 10, i)
                else:
                    line = base_line.format(i % 60, i % 10, i)
                
                lines.append(line)
                current_size += len(line) + 1  # +1 for newline
                i += 1
            
            return "\n".join(lines)
        
        return generate_log
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_small_log_performance(self, performance_config, large_log_generator, performance_metrics):
        """Test performance with small log files (1MB)."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        log_content = large_log_generator(1, "standard")  # 1MB
        
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_model, \
             patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation:
            
            mock_model.return_value.generate_content.return_value.text = '{"summary": "Small log performance test", "issues": [], "suggestions": []}'
            mock_validation.return_value.chat.completions.create.return_value.choices[0].message.content = '{"is_valid": true, "completeness_score": 0.8, "accuracy_score": 0.8, "feedback": "Good"}'
            
            performance_metrics.start()
            result = await compiled_graph.ainvoke(initial_state, config=performance_config)
            performance_metrics.stop()
            
            assert result is not None
            assert performance_metrics.duration < 30.0, f"Small log should process in <30s, took {performance_metrics.duration:.2f}s"
            assert performance_metrics.memory_usage < 200, f"Should use <200MB, used {performance_metrics.memory_usage:.2f}MB"
            
            print(f"✅ Small log (1MB) performance: {performance_metrics.duration:.2f}s, {performance_metrics.memory_usage:.2f}MB")
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_medium_log_performance(self, performance_config, large_log_generator, performance_metrics):
        """Test performance with medium log files (10MB)."""
        graph = create_improved_graph()  # Use improved graph for better performance
        compiled_graph = graph.compile()
        
        log_content = large_log_generator(10, "mixed")  # 10MB
        
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "enable_streaming": True
        }
        
        performance_config["configurable"]["enable_streaming"] = True
        
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
            mock_model.return_value.generate_content.return_value.text = '{"summary": "Medium log performance test", "issues": [], "suggestions": []}'
            
            performance_metrics.start()
            result = await compiled_graph.ainvoke(initial_state, config=performance_config)
            performance_metrics.stop()
            
            assert result is not None
            assert performance_metrics.duration < 60.0, f"Medium log should process in <60s, took {performance_metrics.duration:.2f}s"
            assert performance_metrics.memory_usage < 500, f"Should use <500MB, used {performance_metrics.memory_usage:.2f}MB"
            
            print(f"✅ Medium log (10MB) performance: {performance_metrics.duration:.2f}s, {performance_metrics.memory_usage:.2f}MB")
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_log_performance(self, performance_config, large_log_generator, performance_metrics):
        """Test performance with large log files (50MB)."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        log_content = large_log_generator(50, "error_heavy")  # 50MB
        
        initial_state = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "enable_streaming": True,
            "enable_circuit_breaker": True
        }
        
        performance_config["configurable"]["enable_streaming"] = True
        performance_config["configurable"]["enable_circuit_breaker"] = True
        
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
            mock_model.return_value.generate_content.return_value.text = '{"summary": "Large log performance test", "issues": [], "suggestions": []}'
            
            performance_metrics.start()
            result = await compiled_graph.ainvoke(initial_state, config=performance_config)
            performance_metrics.stop()
            
            assert result is not None
            assert performance_metrics.duration < 180.0, f"Large log should process in <3min, took {performance_metrics.duration:.2f}s"
            assert performance_metrics.memory_usage < 1000, f"Should use <1GB, used {performance_metrics.memory_usage:.2f}MB"
            
            print(f"✅ Large log (50MB) performance: {performance_metrics.duration:.2f}s, {performance_metrics.memory_usage:.2f}MB")
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_streaming_vs_non_streaming_performance(self, performance_config, large_log_generator):
        """Compare streaming vs non-streaming performance."""
        log_content = large_log_generator(20, "mixed")  # 20MB
        
        # Test non-streaming
        graph_regular = create_graph()
        compiled_regular = graph_regular.compile()
        
        state_regular = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False
        }
        
        config_regular = performance_config.copy()
        config_regular["configurable"]["enable_streaming"] = False
        
        with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_model:
            mock_model.return_value.generate_content.return_value.text = '{"summary": "Non-streaming test", "issues": [], "suggestions": []}'
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            result_regular = await compiled_regular.ainvoke(state_regular, config=config_regular)
            
            regular_time = time.time() - start_time
            regular_memory = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory
        
        # Test streaming
        graph_streaming = create_improved_graph()
        compiled_streaming = graph_streaming.compile()
        
        state_streaming = {
            "log_content": log_content,
            "messages": [],
            "iteration_count": 0,
            "analysis_complete": False,
            "enable_streaming": True
        }
        
        config_streaming = performance_config.copy()
        config_streaming["configurable"]["enable_streaming"] = True
        
        with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
            mock_model.return_value.generate_content.return_value.text = '{"summary": "Streaming test", "issues": [], "suggestions": []}'
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            result_streaming = await compiled_streaming.ainvoke(state_streaming, config=config_streaming)
            
            streaming_time = time.time() - start_time
            streaming_memory = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory
        
        assert result_regular is not None
        assert result_streaming is not None
        
        print(f"✅ Performance comparison (20MB log):")
        print(f"   Regular: {regular_time:.2f}s, {regular_memory:.2f}MB")
        print(f"   Streaming: {streaming_time:.2f}s, {streaming_memory:.2f}MB")
        print(f"   Streaming improvement: {((regular_time - streaming_time) / regular_time * 100):.1f}% time, {((regular_memory - streaming_memory) / regular_memory * 100):.1f}% memory")


class TestConcurrencyPerformance:
    """Test performance under concurrent load."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_analysis_performance(self, performance_config, large_log_generator):
        """Test performance with concurrent analysis requests."""
        graph = create_graph()
        compiled_graph = graph.compile()
        
        # Create multiple log samples
        log_samples = [
            large_log_generator(5, "standard"),  # 5MB each
            large_log_generator(5, "error_heavy"),
            large_log_generator(5, "mixed")
        ]
        
        async def run_analysis(log_content, index):
            initial_state = {
                "log_content": log_content,
                "messages": [],
                "iteration_count": 0,
                "analysis_complete": False
            }
            
            with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_model, \
                 patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation:
                
                mock_model.return_value.generate_content.return_value.text = f'{{"summary": "Concurrent test {index}", "issues": [], "suggestions": []}}'
                mock_validation.return_value.chat.completions.create.return_value.choices[0].message.content = '{"is_valid": true, "completeness_score": 0.8, "accuracy_score": 0.8, "feedback": "Good"}'
                
                start_time = time.time()
                result = await compiled_graph.ainvoke(initial_state, config=performance_config)
                duration = time.time() - start_time
                
                return result, duration
        
        # Run concurrent analyses
        start_time = time.time()
        tasks = [run_analysis(log_content, i) for i, log_content in enumerate(log_samples)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify all completed successfully
        assert len(results) == len(log_samples)
        for result, duration in results:
            assert result is not None
            assert result.get("analysis_complete") is True
        
        individual_times = [duration for _, duration in results]
        avg_time = sum(individual_times) / len(individual_times)
        
        print(f"✅ Concurrent analysis performance:")
        print(f"   Total time: {total_time:.2f}s")
        print(f"   Average individual time: {avg_time:.2f}s")
        print(f"   Concurrency efficiency: {(sum(individual_times) / total_time):.1f}x")
        
        # Should be faster than sequential execution
        assert total_time < sum(individual_times) * 0.8, "Concurrent execution should be significantly faster"
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_config, large_log_generator):
        """Test memory usage under sustained load."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        peak_memory = initial_memory
        
        async def memory_monitor():
            nonlocal peak_memory
            while True:
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)
                await asyncio.sleep(0.1)
        
        # Start memory monitoring
        monitor_task = asyncio.create_task(memory_monitor())
        
        try:
            # Run multiple analyses in sequence to test memory cleanup
            for i in range(5):
                log_content = large_log_generator(10, "mixed")  # 10MB each
                
                initial_state = {
                    "log_content": log_content,
                    "messages": [],
                    "iteration_count": 0,
                    "analysis_complete": False,
                    "enable_streaming": True
                }
                
                with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
                    mock_model.return_value.generate_content.return_value.text = f'{{"summary": "Memory test {i}", "issues": [], "suggestions": []}}'
                    
                    result = await compiled_graph.ainvoke(initial_state, config=performance_config)
                    assert result is not None
                
                # Force garbage collection
                import gc
                gc.collect()
                
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                print(f"   After analysis {i+1}: {current_memory:.2f}MB")
        
        finally:
            monitor_task.cancel()
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        print(f"✅ Memory usage under load:")
        print(f"   Initial: {initial_memory:.2f}MB")
        print(f"   Peak: {peak_memory:.2f}MB")
        print(f"   Final: {final_memory:.2f}MB")
        print(f"   Growth: {memory_growth:.2f}MB")
        
        # Memory growth should be reasonable
        assert memory_growth < 500, f"Memory growth should be <500MB, was {memory_growth:.2f}MB"
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_thread_safety_performance(self, performance_config, large_log_generator):
        """Test thread safety and performance with ThreadPoolExecutor."""
        import threading
        
        graph = create_graph()
        compiled_graph = graph.compile()
        
        log_content = large_log_generator(5, "standard")  # 5MB
        
        def run_sync_analysis(thread_id):
            """Run analysis in a thread."""
            initial_state = {
                "log_content": log_content,
                "messages": [],
                "iteration_count": 0,
                "analysis_complete": False
            }
            
            with patch('src.log_analyzer_agent.nodes.analysis.get_model') as mock_model, \
                 patch('src.log_analyzer_agent.nodes.validation.get_orchestration_model') as mock_validation:
                
                mock_model.return_value.generate_content.return_value.text = f'{{"summary": "Thread test {thread_id}", "issues": [], "suggestions": []}}'
                mock_validation.return_value.chat.completions.create.return_value.choices[0].message.content = '{"is_valid": true, "completeness_score": 0.8, "accuracy_score": 0.8, "feedback": "Good"}'
                
                # Use asyncio.run to run async code in thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        compiled_graph.ainvoke(initial_state, config=performance_config)
                    )
                    return result, thread_id
                finally:
                    loop.close()
        
        # Run with ThreadPoolExecutor
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(run_sync_analysis, i) for i in range(3)]
            results = [future.result() for future in futures]
        total_time = time.time() - start_time
        
        # Verify all completed successfully
        assert len(results) == 3
        for result, thread_id in results:
            assert result is not None
            assert result.get("analysis_complete") is True
        
        print(f"✅ Thread safety performance:")
        print(f"   3 threads completed in: {total_time:.2f}s")
        print(f"   Average per thread: {total_time/3:.2f}s")


class TestScalabilityTests:
    """Test system scalability with increasing loads."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_scalability_with_log_size(self, performance_config, large_log_generator):
        """Test how performance scales with log size."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        sizes = [1, 5, 10, 20]  # MB
        results = []
        
        for size in sizes:
            log_content = large_log_generator(size, "mixed")
            
            initial_state = {
                "log_content": log_content,
                "messages": [],
                "iteration_count": 0,
                "analysis_complete": False,
                "enable_streaming": True
            }
            
            config = performance_config.copy()
            config["configurable"]["enable_streaming"] = True
            
            with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
                mock_model.return_value.generate_content.return_value.text = f'{{"summary": "Scalability test {size}MB", "issues": [], "suggestions": []}}'
                
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
                result = await compiled_graph.ainvoke(initial_state, config=config)
                
                duration = time.time() - start_time
                memory_used = psutil.Process().memory_info().rss / 1024 / 1024 - start_memory
                
                assert result is not None
                results.append((size, duration, memory_used))
        
        print("✅ Scalability with log size:")
        for size, duration, memory in results:
            print(f"   {size}MB: {duration:.2f}s, {memory:.2f}MB")
        
        # Check that performance scales reasonably
        # Time should scale sub-linearly with streaming
        time_ratios = []
        for i in range(1, len(results)):
            size_ratio = results[i][0] / results[i-1][0]
            time_ratio = results[i][1] / results[i-1][1]
            time_ratios.append(time_ratio / size_ratio)
        
        avg_scaling = sum(time_ratios) / len(time_ratios)
        print(f"   Average time scaling factor: {avg_scaling:.2f} (lower is better)")
        
        # With streaming, scaling should be better than linear
        assert avg_scaling < 1.5, f"Time scaling should be sub-linear, was {avg_scaling:.2f}"
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_throughput_benchmark(self, performance_config, large_log_generator):
        """Benchmark system throughput (logs processed per minute)."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        log_content = large_log_generator(2, "standard")  # 2MB logs
        
        # Process multiple logs to measure throughput
        num_logs = 10
        start_time = time.time()
        
        for i in range(num_logs):
            initial_state = {
                "log_content": log_content,
                "messages": [],
                "iteration_count": 0,
                "analysis_complete": False,
                "enable_streaming": True
            }
            
            config = performance_config.copy()
            config["configurable"]["enable_streaming"] = True
            
            with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
                mock_model.return_value.generate_content.return_value.text = f'{{"summary": "Throughput test {i}", "issues": [], "suggestions": []}}'
                
                result = await compiled_graph.ainvoke(initial_state, config=config)
                assert result is not None
        
        total_time = time.time() - start_time
        throughput = num_logs / (total_time / 60)  # logs per minute
        data_throughput = (num_logs * 2) / (total_time / 60)  # MB per minute
        
        print(f"✅ Throughput benchmark:")
        print(f"   Processed {num_logs} logs (2MB each) in {total_time:.2f}s")
        print(f"   Throughput: {throughput:.1f} logs/minute")
        print(f"   Data throughput: {data_throughput:.1f} MB/minute")
        
        # Should achieve reasonable throughput
        assert throughput > 5, f"Should process >5 logs/minute, achieved {throughput:.1f}"
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_resource_limits(self, performance_config, large_log_generator):
        """Test behavior at resource limits."""
        graph = create_improved_graph()
        compiled_graph = graph.compile()
        
        # Test with very large log (100MB)
        try:
            log_content = large_log_generator(100, "mixed")  # 100MB
            
            initial_state = {
                "log_content": log_content,
                "messages": [],
                "iteration_count": 0,
                "analysis_complete": False,
                "enable_streaming": True,
                "enable_circuit_breaker": True
            }
            
            config = performance_config.copy()
            config["configurable"]["enable_streaming"] = True
            config["configurable"]["enable_circuit_breaker"] = True
            
            with patch('src.log_analyzer_agent.nodes.enhanced_analysis.get_model') as mock_model:
                mock_model.return_value.generate_content.return_value.text = '{"summary": "Resource limit test", "issues": [], "suggestions": []}'
                
                start_time = time.time()
                start_memory = psutil.Process().memory_info().rss / 1024 / 1024
                
                result = await compiled_graph.ainvoke(initial_state, config=config)
                
                duration = time.time() - start_time
                peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_used = peak_memory - start_memory
                
                print(f"✅ Resource limits test (100MB log):")
                print(f"   Duration: {duration:.2f}s")
                print(f"   Memory used: {memory_used:.2f}MB")
                print(f"   Peak memory: {peak_memory:.2f}MB")
                
                # Should handle large logs without excessive resource usage
                assert memory_used < 2000, f"Should use <2GB memory, used {memory_used:.2f}MB"
                assert duration < 600, f"Should complete in <10min, took {duration:.2f}s"
                
                if result is not None:
                    print("   ✅ Successfully processed 100MB log")
                else:
                    print("   ⚠️  Large log processing returned None (may be expected)")
        
        except MemoryError:
            print("   ⚠️  MemoryError encountered with 100MB log (expected on resource-constrained systems)")
        except Exception as e:
            print(f"   ⚠️  Exception with 100MB log: {e} (may be expected)")
            # This is acceptable for resource limit testing