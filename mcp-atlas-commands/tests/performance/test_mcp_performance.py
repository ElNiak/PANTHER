"""
Performance tests for ATLAS MCP Server - Load Testing and Benchmarking
Testing performance characteristics, concurrent operations, and scalability.
"""

import pytest
import asyncio
import time
import psutil
import os
from concurrent.futures import ThreadPoolExecutor
from statistics import mean, median, stdev
from typing import List, Dict, Any

from src.atlas_commands.intelligent_orchestrator import IntelligentMCPOrchestrator
from src.atlas_commands.token_optimization.token_optimizer import TokenOptimizer
from src.atlas_commands.task_analysis_algorithm import analyze_task_for_atlas_framework


class TestMCPPerformanceBenchmarks:
    """Comprehensive performance testing for MCP components."""
    
    @pytest.fixture
    def performance_context(self):
        """Setup performance testing context."""
        return {
            'test_start_time': time.time(),
            'process': psutil.Process(os.getpid()),
            'baseline_memory': psutil.Process(os.getpid()).memory_info().rss,
            'baseline_cpu': psutil.cpu_percent()
        }
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for performance testing."""
        return IntelligentMCPOrchestrator()
    
    @pytest.fixture
    def token_optimizer(self):
        """Create token optimizer for performance testing."""
        return TokenOptimizer()
    
    @pytest.mark.asyncio
    async def test_orchestration_latency_benchmark(self, orchestrator, performance_context):
        """Benchmark orchestration latency across different task complexities."""
        test_tasks = [
            ("Simple task - fix typo", {"complexity": "trivial"}),
            ("Moderate task - add API endpoint", {"complexity": "moderate"}),
            ("Complex task - refactor architecture", {"complexity": "complex"}),
            ("Very complex task - migrate to microservices", {"complexity": "very_complex"})
        ]
        
        latency_results = {}
        
        for task_desc, context in test_tasks:
            # Warm-up run
            await orchestrator.orchestrate_task(task_desc, context, {})
            
            # Benchmark runs
            latencies = []
            for _ in range(10):
                start_time = time.perf_counter()
                result = await orchestrator.orchestrate_task(task_desc, context, {})
                end_time = time.perf_counter()
                
                latency = (end_time - start_time) * 1000  # Convert to milliseconds
                latencies.append(latency)
                
                # Verify result structure
                assert result is not None
                assert hasattr(result, 'estimated_efficiency_gain')
            
            latency_results[context["complexity"]] = {
                'mean': mean(latencies),
                'median': median(latencies),
                'std_dev': stdev(latencies) if len(latencies) > 1 else 0,
                'min': min(latencies),
                'max': max(latencies),
                'p95': sorted(latencies)[int(0.95 * len(latencies))],
                'p99': sorted(latencies)[int(0.99 * len(latencies))]
            }
        
        # Performance assertions
        assert latency_results['trivial']['mean'] < 100  # < 100ms for trivial tasks
        assert latency_results['moderate']['mean'] < 300  # < 300ms for moderate tasks
        assert latency_results['complex']['mean'] < 1000  # < 1s for complex tasks
        
        # Log performance results
        print("\n=== Orchestration Latency Benchmark Results ===")
        for complexity, metrics in latency_results.items():
            print(f"{complexity.upper()}:")
            print(f"  Mean: {metrics['mean']:.2f}ms")
            print(f"  P95:  {metrics['p95']:.2f}ms")
            print(f"  P99:  {metrics['p99']:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_token_optimization_throughput(self, token_optimizer, performance_context):
        """Benchmark token optimization throughput."""
        # Generate test data of varying sizes
        test_datasets = [
            ("Small JSON", {"small": "data" * 10}),
            ("Medium JSON", {"medium": "data" * 100, "array": list(range(50))}),
            ("Large JSON", {"large": "data" * 1000, "big_array": list(range(500))}),
            ("Very Large JSON", {
                "very_large": "data" * 5000,
                "huge_array": [{"id": i, "data": f"item_{i}"} for i in range(1000)]
            })
        ]
        
        throughput_results = {}
        
        for dataset_name, data in test_datasets:
            # Warm-up
            await token_optimizer.optimize_response("benchmark_tool", data)
            
            # Throughput test
            start_time = time.perf_counter()
            operations = 100
            
            for _ in range(operations):
                result = await token_optimizer.optimize_response("benchmark_tool", data)
                assert len(result) == 1
                assert result[0].original_tokens > 0
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            ops_per_second = operations / total_time
            
            throughput_results[dataset_name] = {
                'operations': operations,
                'total_time': total_time,
                'ops_per_second': ops_per_second,
                'avg_latency_ms': (total_time / operations) * 1000
            }
        
        # Performance assertions
        assert throughput_results['Small JSON']['ops_per_second'] > 500  # > 500 ops/sec
        assert throughput_results['Medium JSON']['ops_per_second'] > 100  # > 100 ops/sec
        
        print("\n=== Token Optimization Throughput Results ===")
        for dataset, metrics in throughput_results.items():
            print(f"{dataset}:")
            print(f"  Throughput: {metrics['ops_per_second']:.2f} ops/sec")
            print(f"  Avg Latency: {metrics['avg_latency_ms']:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_concurrent_orchestration_load(self, orchestrator, performance_context):
        """Test concurrent orchestration under load."""
        concurrency_levels = [1, 5, 10, 20]
        load_test_results = {}
        
        async def orchestration_task(task_id: int):
            """Single orchestration task for load testing."""
            start_time = time.perf_counter()
            result = await orchestrator.orchestrate_task(
                f"Load test task {task_id}",
                {"domain": "load_test", "task_id": task_id},
                {}
            )
            end_time = time.perf_counter()
            return {
                'task_id': task_id,
                'latency': (end_time - start_time) * 1000,
                'success': result is not None
            }
        
        for concurrency in concurrency_levels:
            start_time = time.perf_counter()
            
            # Create concurrent tasks
            tasks = [orchestration_task(i) for i in range(concurrency)]
            results = await asyncio.gather(*tasks)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # Analyze results
            latencies = [r['latency'] for r in results]
            success_rate = sum(1 for r in results if r['success']) / len(results)
            
            load_test_results[concurrency] = {
                'total_time': total_time,
                'success_rate': success_rate,
                'throughput': concurrency / total_time,
                'mean_latency': mean(latencies),
                'p95_latency': sorted(latencies)[int(0.95 * len(latencies))],
                'p99_latency': sorted(latencies)[int(0.99 * len(latencies))]
            }
        
        # Performance assertions
        for concurrency, metrics in load_test_results.items():
            assert metrics['success_rate'] >= 0.95  # 95% success rate
            assert metrics['mean_latency'] < 5000  # < 5s mean latency
        
        print("\n=== Concurrent Load Test Results ===")
        for concurrency, metrics in load_test_results.items():
            print(f"Concurrency Level {concurrency}:")
            print(f"  Success Rate: {metrics['success_rate']:.2%}")
            print(f"  Throughput: {metrics['throughput']:.2f} tasks/sec")
            print(f"  Mean Latency: {metrics['mean_latency']:.2f}ms")
            print(f"  P95 Latency: {metrics['p95_latency']:.2f}ms")
    
    def test_memory_usage_analysis(self, performance_context):
        """Analyze memory usage patterns during operations."""
        process = performance_context['process']
        baseline_memory = performance_context['baseline_memory']
        
        memory_snapshots = []
        
        # Perform memory-intensive operations
        for i in range(10):
            # Create multiple components
            orchestrator = IntelligentMCPOrchestrator()
            optimizer = TokenOptimizer()
            
            # Record memory usage
            current_memory = process.memory_info().rss
            memory_increase = current_memory - baseline_memory
            memory_snapshots.append({
                'iteration': i,
                'memory_rss': current_memory,
                'memory_increase': memory_increase,
                'memory_increase_mb': memory_increase / (1024 * 1024)
            })
            
            # Perform some operations
            result = analyze_task_for_atlas_framework(
                f"Memory test task {i}",
                {"domain": "memory_test"}
            )
            assert result is not None
        
        # Analyze memory growth
        memory_increases = [s['memory_increase_mb'] for s in memory_snapshots]
        final_memory_increase = memory_increases[-1]
        memory_growth_rate = (memory_increases[-1] - memory_increases[0]) / len(memory_increases)
        
        # Memory assertions
        assert final_memory_increase < 500  # < 500MB total increase
        assert memory_growth_rate < 10  # < 10MB growth per operation
        
        print("\n=== Memory Usage Analysis ===")
        print(f"Final Memory Increase: {final_memory_increase:.2f}MB")
        print(f"Memory Growth Rate: {memory_growth_rate:.2f}MB/operation")
        print(f"Peak Memory: {max(memory_increases):.2f}MB")
    
    @pytest.mark.asyncio
    async def test_stress_testing_limits(self, orchestrator, token_optimizer):
        """Stress test to find system limits."""
        stress_results = {}
        
        # Test 1: Maximum concurrent orchestrations
        max_concurrent = 0
        for concurrency in [10, 25, 50, 100, 200]:
            try:
                start_time = time.perf_counter()
                
                tasks = [
                    orchestrator.orchestrate_task(
                        f"Stress test {i}",
                        {"stress_level": concurrency},
                        {}
                    ) for i in range(concurrency)
                ]
                
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=30.0  # 30 second timeout
                )
                
                end_time = time.perf_counter()
                
                success_count = sum(1 for r in results if not isinstance(r, Exception))
                success_rate = success_count / len(results)
                
                if success_rate >= 0.90:  # 90% success threshold
                    max_concurrent = concurrency
                    stress_results[f'concurrent_{concurrency}'] = {
                        'success_rate': success_rate,
                        'total_time': end_time - start_time,
                        'passed': True
                    }
                else:
                    stress_results[f'concurrent_{concurrency}'] = {
                        'success_rate': success_rate,
                        'total_time': end_time - start_time,
                        'passed': False
                    }
                    break
                    
            except asyncio.TimeoutError:
                stress_results[f'concurrent_{concurrency}'] = {
                    'success_rate': 0.0,
                    'timeout': True,
                    'passed': False
                }
                break
        
        # Test 2: Large data optimization stress
        large_data_limit = 0
        for size_multiplier in [10, 50, 100, 500, 1000]:
            try:
                large_data = {
                    "massive_array": [f"item_{i}" for i in range(size_multiplier * 100)],
                    "massive_text": "data " * (size_multiplier * 1000),
                    "nested_structure": {
                        f"level_{i}": {f"sub_{j}": f"value_{i}_{j}" for j in range(100)}
                        for i in range(size_multiplier)
                    }
                }
                
                start_time = time.perf_counter()
                result = await asyncio.wait_for(
                    token_optimizer.optimize_response("stress_tool", large_data),
                    timeout=10.0
                )
                end_time = time.perf_counter()
                
                assert len(result) == 1
                assert result[0].original_tokens > 0
                
                large_data_limit = size_multiplier
                stress_results[f'data_size_{size_multiplier}'] = {
                    'optimization_time': end_time - start_time,
                    'original_tokens': result[0].original_tokens,
                    'optimized_tokens': result[0].optimized_tokens,
                    'passed': True
                }
                
            except (asyncio.TimeoutError, MemoryError, Exception) as e:
                stress_results[f'data_size_{size_multiplier}'] = {
                    'error': str(type(e).__name__),
                    'passed': False
                }
                break
        
        print("\n=== Stress Test Results ===")
        print(f"Maximum Concurrent Operations: {max_concurrent}")
        print(f"Maximum Data Size Multiplier: {large_data_limit}")
        
        # Ensure we found reasonable limits
        assert max_concurrent >= 25  # Should handle at least 25 concurrent operations
        assert large_data_limit >= 50  # Should handle reasonably large data


class TestMCPScalabilityPatterns:
    """Test scalability patterns and optimization strategies."""
    
    @pytest.mark.asyncio
    async def test_caching_performance_impact(self):
        """Test performance impact of caching mechanisms."""
        from src.atlas_commands.coordination.caching_strategy import CachingStrategy
        
        cache_strategy = CachingStrategy()
        
        # Test without caching
        start_time = time.perf_counter()
        for i in range(50):
            result = analyze_task_for_atlas_framework(
                "Repeated analysis task",
                {"iteration": i, "caching": False}
            )
            assert result is not None
        no_cache_time = time.perf_counter() - start_time
        
        # Test with caching
        start_time = time.perf_counter()
        for i in range(50):
            cache_key = "repeated_analysis_task"
            cached_result = cache_strategy.get(cache_key)
            
            if cached_result is None:
                result = analyze_task_for_atlas_framework(
                    "Repeated analysis task",
                    {"iteration": i, "caching": True}
                )
                cache_strategy.set(cache_key, result)
            else:
                result = cached_result
                
            assert result is not None
        cached_time = time.perf_counter() - start_time
        
        # Caching should provide significant speedup
        speedup_ratio = no_cache_time / cached_time
        assert speedup_ratio > 2.0  # At least 2x speedup
        
        print(f"\nCaching Performance:")
        print(f"Without cache: {no_cache_time:.3f}s")
        print(f"With cache: {cached_time:.3f}s")
        print(f"Speedup: {speedup_ratio:.2f}x")
    
    @pytest.mark.asyncio
    async def test_batch_processing_efficiency(self, token_optimizer):
        """Test batch processing vs individual processing efficiency."""
        test_data_items = [
            {"batch_item": i, "data": f"test_data_{i}" * 100}
            for i in range(20)
        ]
        
        # Individual processing
        start_time = time.perf_counter()
        individual_results = []
        for item in test_data_items:
            result = await token_optimizer.optimize_response("individual_tool", item)
            individual_results.extend(result)
        individual_time = time.perf_counter() - start_time
        
        # Batch processing (simulated)
        start_time = time.perf_counter()
        batch_data = {"batch_items": test_data_items}
        batch_results = await token_optimizer.optimize_response("batch_tool", batch_data)
        batch_time = time.perf_counter() - start_time
        
        # Batch processing should be more efficient
        efficiency_ratio = individual_time / batch_time
        
        print(f"\nBatch Processing Efficiency:")
        print(f"Individual processing: {individual_time:.3f}s")
        print(f"Batch processing: {batch_time:.3f}s")
        print(f"Efficiency ratio: {efficiency_ratio:.2f}x")
        
        assert efficiency_ratio > 1.5  # Batch should be at least 1.5x faster
    
    def test_resource_pool_management(self):
        """Test resource pool management for scalability."""
        from src.atlas_commands.coordination.resource_pool import ResourcePool
        
        # Create resource pool
        pool = ResourcePool(max_size=10, resource_type="orchestrator")
        
        # Test resource acquisition and release
        acquired_resources = []
        
        # Acquire resources up to limit
        for i in range(10):
            resource = pool.acquire()
            assert resource is not None
            acquired_resources.append(resource)
        
        # Should not be able to acquire more than max
        try:
            extra_resource = pool.acquire(timeout=0.1)
            assert False, "Should not be able to acquire beyond pool limit"
        except TimeoutError:
            pass  # Expected
        
        # Release resources
        for resource in acquired_resources:
            pool.release(resource)
        
        # Should be able to acquire again
        new_resource = pool.acquire()
        assert new_resource is not None
        pool.release(new_resource)
        
        print(f"Resource pool management test passed")


@pytest.fixture(scope="module")  
def event_loop():
    """Create event loop for module-level async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])  # -s to show print statements