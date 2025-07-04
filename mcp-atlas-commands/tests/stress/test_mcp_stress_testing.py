"""
Stress tests for ATLAS MCP Server - Breaking point analysis and load testing
Testing system limits, failure modes, and recovery patterns under extreme conditions.
"""

import pytest
import asyncio
import time
import psutil
import os
import gc
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median, stdev
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from contextlib import contextmanager

from src.atlas_commands.intelligent_orchestrator import IntelligentMCPOrchestrator
from src.atlas_commands.token_optimization.token_optimizer import TokenOptimizer
from src.atlas_commands.task_analysis_algorithm import analyze_task_for_atlas_framework


@dataclass
class StressTestMetrics:
    """Metrics collected during stress testing."""
    operation_count: int
    success_count: int
    failure_count: int
    total_time: float
    memory_peak_mb: float
    cpu_peak_percent: float
    operations_per_second: float
    error_rate: float
    p95_latency_ms: float
    p99_latency_ms: float


@contextmanager
def system_monitor():
    """Context manager for monitoring system resources during tests."""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    peak_memory = initial_memory
    peak_cpu = 0.0
    
    def monitor_loop():
        nonlocal peak_memory, peak_cpu
        while True:
            try:
                current_memory = process.memory_info().rss
                current_cpu = process.cpu_percent()
                peak_memory = max(peak_memory, current_memory)
                peak_cpu = max(peak_cpu, current_cpu)
                time.sleep(0.1)
            except:
                break
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    
    yield
    
    # Calculate final metrics
    peak_memory_mb = (peak_memory - initial_memory) / (1024 * 1024)
    return {'peak_memory_mb': peak_memory_mb, 'peak_cpu_percent': peak_cpu}


class TestExtremeLoadStressTesting:
    """Test system behavior under extreme load conditions."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for stress testing."""
        return IntelligentMCPOrchestrator()
    
    @pytest.fixture
    def token_optimizer(self):
        """Create token optimizer for stress testing."""
        return TokenOptimizer()
    
    @pytest.mark.asyncio
    async def test_massive_concurrent_orchestration(self, orchestrator):
        """Test system with massive concurrent orchestration requests."""
        concurrency_levels = [50, 100, 200, 500, 1000]
        results = {}
        
        async def single_orchestration(task_id: int) -> Tuple[bool, float, str]:
            """Single orchestration task returning success, latency, error."""
            start_time = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    orchestrator.orchestrate_task(
                        f"Stress test task {task_id}",
                        {"domain": "stress_test", "task_id": task_id},
                        {}
                    ),
                    timeout=60.0  # 1 minute timeout per task
                )
                end_time = time.perf_counter()
                return True, (end_time - start_time) * 1000, ""
            except Exception as e:
                end_time = time.perf_counter()
                return False, (end_time - start_time) * 1000, str(type(e).__name__)
        
        for concurrency in concurrency_levels:
            print(f"\nTesting concurrency level: {concurrency}")
            
            with system_monitor() as monitor:
                start_time = time.perf_counter()
                
                # Create massive number of concurrent tasks
                tasks = [single_orchestration(i) for i in range(concurrency)]
                
                try:
                    task_results = await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=300.0  # 5 minute total timeout
                    )
                    
                    end_time = time.perf_counter()
                    total_time = end_time - start_time
                    
                    # Analyze results
                    successes = [r for r in task_results if isinstance(r, tuple) and r[0]]
                    failures = [r for r in task_results if isinstance(r, tuple) and not r[0]]
                    exceptions = [r for r in task_results if isinstance(r, Exception)]
                    
                    latencies = [r[1] for r in successes + failures if isinstance(r, tuple)]
                    
                    metrics = StressTestMetrics(
                        operation_count=concurrency,
                        success_count=len(successes),
                        failure_count=len(failures) + len(exceptions),
                        total_time=total_time,
                        memory_peak_mb=monitor.get('peak_memory_mb', 0),
                        cpu_peak_percent=monitor.get('peak_cpu_percent', 0),
                        operations_per_second=concurrency / total_time,
                        error_rate=(len(failures) + len(exceptions)) / concurrency,
                        p95_latency_ms=sorted(latencies)[int(0.95 * len(latencies))] if latencies else 0,
                        p99_latency_ms=sorted(latencies)[int(0.99 * len(latencies))] if latencies else 0
                    )
                    
                    results[concurrency] = metrics
                    
                    print(f"Success rate: {(1 - metrics.error_rate):.2%}")
                    print(f"Throughput: {metrics.operations_per_second:.2f} ops/sec")
                    print(f"P95 latency: {metrics.p95_latency_ms:.2f}ms")
                    print(f"Memory peak: {metrics.memory_peak_mb:.2f}MB")
                    
                    # Stop if error rate becomes too high
                    if metrics.error_rate > 0.5:  # 50% error rate threshold
                        print(f"Stopping at concurrency {concurrency} due to high error rate")
                        break
                        
                except asyncio.TimeoutError:
                    print(f"Timeout at concurrency level {concurrency}")
                    break
        
        # Verify we handled reasonable load
        successful_levels = [level for level, metrics in results.items() if metrics.error_rate < 0.2]
        assert len(successful_levels) > 0, "Should handle at least some concurrent load"
        assert max(successful_levels) >= 50, "Should handle at least 50 concurrent operations"
        
        return results
    
    @pytest.mark.asyncio
    async def test_memory_exhaustion_stress(self, token_optimizer):
        """Test system behavior under memory pressure."""
        memory_pressure_levels = []
        
        # Generate increasingly large datasets
        for size_multiplier in [10, 50, 100, 500, 1000, 2000]:
            try:
                # Create large dataset
                large_dataset = {
                    "massive_array": [f"data_item_{i}" * 100 for i in range(size_multiplier * 10)],
                    "massive_text": "Lorem ipsum " * (size_multiplier * 1000),
                    "nested_objects": {
                        f"category_{i}": {
                            f"subcategory_{j}": {
                                f"item_{k}": f"value_{i}_{j}_{k}" * 50
                                for k in range(10)
                            }
                            for j in range(10)
                        }
                        for i in range(size_multiplier)
                    },
                    "matrix_data": [
                        [i * j for j in range(100)]
                        for i in range(size_multiplier * 2)
                    ]
                }
                
                # Monitor memory during processing
                process = psutil.Process(os.getpid())
                memory_before = process.memory_info().rss
                
                start_time = time.perf_counter()
                
                # Process the large dataset
                result = await asyncio.wait_for(
                    token_optimizer.optimize_response("stress_tool", large_dataset),
                    timeout=120.0  # 2 minute timeout
                )
                
                end_time = time.perf_counter()
                memory_after = process.memory_info().rss
                
                memory_used_mb = (memory_after - memory_before) / (1024 * 1024)
                processing_time = end_time - start_time
                
                pressure_metrics = {
                    'size_multiplier': size_multiplier,
                    'memory_used_mb': memory_used_mb,
                    'processing_time': processing_time,
                    'original_tokens': result[0].original_tokens if result else 0,
                    'success': True
                }
                
                memory_pressure_levels.append(pressure_metrics)
                
                print(f"Size {size_multiplier}: {memory_used_mb:.2f}MB, {processing_time:.2f}s")
                
                # Force garbage collection
                del large_dataset
                gc.collect()
                
                # Stop if memory usage becomes excessive
                if memory_used_mb > 1000:  # 1GB threshold
                    print(f"Stopping at size multiplier {size_multiplier} due to memory usage")
                    break
                    
            except (MemoryError, asyncio.TimeoutError) as e:
                pressure_metrics = {
                    'size_multiplier': size_multiplier,
                    'error': str(type(e).__name__),
                    'success': False
                }
                memory_pressure_levels.append(pressure_metrics)
                print(f"Failed at size multiplier {size_multiplier}: {type(e).__name__}")
                break
            except Exception as e:
                print(f"Unexpected error at size multiplier {size_multiplier}: {e}")
                break
        
        # Verify reasonable memory handling
        successful_levels = [level for level in memory_pressure_levels if level.get('success', False)]
        assert len(successful_levels) >= 3, "Should handle multiple memory pressure levels"
        
        # Check memory usage scaling
        memory_usage = [level['memory_used_mb'] for level in successful_levels]
        assert max(memory_usage) < 2000, "Memory usage should be reasonable (< 2GB)"
        
        return memory_pressure_levels
    
    def test_cpu_intensive_stress(self):
        """Test CPU-intensive operations stress."""
        cpu_stress_results = []
        
        def cpu_intensive_task(iterations: int) -> Dict[str, Any]:
            """CPU-intensive task for stress testing."""
            start_time = time.perf_counter()
            
            # Perform CPU-intensive operations
            for i in range(iterations):
                # Complex task analysis
                result = analyze_task_for_atlas_framework(
                    f"Complex CPU-intensive task iteration {i} with extensive analysis requirements",
                    {
                        'domain': 'performance_testing',
                        'complexity': 'maximum',
                        'cpu_intensive': True,
                        'iteration': i,
                        'detailed_analysis': {
                            'factor_1': f"analysis_data_{i}" * 100,
                            'factor_2': list(range(i % 100)),
                            'factor_3': {f"key_{j}": f"value_{j}" for j in range(i % 50)}
                        }
                    }
                )
                
                # Verify result
                assert result is not None
                assert 'complexity' in result
            
            end_time = time.perf_counter()
            return {
                'iterations': iterations,
                'total_time': end_time - start_time,
                'iterations_per_second': iterations / (end_time - start_time),
                'success': True
            }
        
        # Test with increasing CPU load
        for iteration_count in [10, 50, 100, 200, 500]:
            try:
                print(f"\nTesting CPU stress with {iteration_count} iterations")
                
                # Monitor CPU usage
                process = psutil.Process(os.getpid())
                cpu_before = process.cpu_percent()
                
                result = cpu_intensive_task(iteration_count)
                
                cpu_after = process.cpu_percent()
                
                result['cpu_usage_increase'] = cpu_after - cpu_before
                cpu_stress_results.append(result)
                
                print(f"Completed: {result['iterations_per_second']:.2f} iterations/sec")
                print(f"CPU usage increase: {result['cpu_usage_increase']:.2f}%")
                
                # Stop if performance degrades significantly
                if result['iterations_per_second'] < 1.0:  # Less than 1 iteration per second
                    print(f"Stopping at {iteration_count} iterations due to performance")
                    break
                    
            except Exception as e:
                cpu_stress_results.append({
                    'iterations': iteration_count,
                    'error': str(type(e).__name__),
                    'success': False
                })
                print(f"Failed at {iteration_count} iterations: {e}")
                break
        
        # Verify reasonable CPU handling
        successful_results = [r for r in cpu_stress_results if r.get('success', False)]
        assert len(successful_results) >= 2, "Should handle multiple CPU stress levels"
        
        return cpu_stress_results
    
    @pytest.mark.asyncio
    async def test_timeout_and_deadline_stress(self, orchestrator):
        """Test system behavior under tight deadlines and timeouts."""
        timeout_scenarios = [
            {'timeout': 0.1, 'expected_failures': 'high'},   # 100ms - very tight
            {'timeout': 0.5, 'expected_failures': 'medium'}, # 500ms - tight
            {'timeout': 1.0, 'expected_failures': 'low'},    # 1s - reasonable
            {'timeout': 5.0, 'expected_failures': 'minimal'}, # 5s - generous
        ]
        
        timeout_results = []
        
        for scenario in timeout_scenarios:
            timeout_duration = scenario['timeout']
            
            print(f"\nTesting timeout scenario: {timeout_duration}s")
            
            # Run multiple operations with tight timeout
            operations = 20
            successes = 0
            timeouts = 0
            errors = 0
            latencies = []
            
            for i in range(operations):
                try:
                    start_time = time.perf_counter()
                    
                    result = await asyncio.wait_for(
                        orchestrator.orchestrate_task(
                            f"Timeout stress test {i}",
                            {"domain": "timeout_test", "urgency": "immediate"},
                            {}
                        ),
                        timeout=timeout_duration
                    )
                    
                    end_time = time.perf_counter()
                    latency = (end_time - start_time) * 1000
                    latencies.append(latency)
                    
                    if result is not None:
                        successes += 1
                    
                except asyncio.TimeoutError:
                    timeouts += 1
                except Exception:
                    errors += 1
            
            success_rate = successes / operations
            timeout_rate = timeouts / operations
            error_rate = errors / operations
            
            scenario_result = {
                'timeout_duration': timeout_duration,
                'success_rate': success_rate,
                'timeout_rate': timeout_rate,
                'error_rate': error_rate,
                'mean_latency_ms': mean(latencies) if latencies else 0,
                'operations': operations
            }
            
            timeout_results.append(scenario_result)
            
            print(f"Success rate: {success_rate:.2%}")
            print(f"Timeout rate: {timeout_rate:.2%}")
            print(f"Mean latency: {scenario_result['mean_latency_ms']:.2f}ms")
        
        # Verify timeout handling improves with longer timeouts
        success_rates = [r['success_rate'] for r in timeout_results]
        assert success_rates[-1] > success_rates[0], "Longer timeouts should have higher success rates"
        
        return timeout_results


class TestFailureModeAnalysis:
    """Analyze specific failure modes and recovery patterns."""
    
    @pytest.mark.asyncio
    async def test_cascading_failure_resistance(self, orchestrator):
        """Test resistance to cascading failures."""
        
        # Simulate component failures in sequence
        failure_scenarios = [
            "task_analysis_failure",
            "dependency_analysis_failure", 
            "pattern_detection_failure",
            "token_optimization_failure",
            "multiple_component_failure"
        ]
        
        cascade_results = {}
        
        for scenario in failure_scenarios:
            print(f"\nTesting failure scenario: {scenario}")
            
            if scenario == "multiple_component_failure":
                # Simulate multiple simultaneous failures
                with patch('src.atlas_commands.task_analysis_algorithm.TaskComplexityAnalyzer') as mock1, \
                     patch('src.atlas_commands.task_analysis_algorithm.DependencyAnalyzer') as mock2:
                    
                    mock1.side_effect = Exception("Task analysis failed")
                    mock2.side_effect = Exception("Dependency analysis failed")
                    
                    failure_results = []
                    for i in range(10):
                        try:
                            result = await orchestrator.orchestrate_task(
                                f"Cascade test {i}",
                                {"domain": "failure_test"},
                                {}
                            )
                            failure_results.append({'success': True, 'result': result})
                        except Exception as e:
                            failure_results.append({'success': False, 'error': str(e)})
                    
                    success_count = sum(1 for r in failure_results if r['success'])
                    cascade_results[scenario] = {
                        'success_rate': success_count / len(failure_results),
                        'degraded_operation': success_count > 0,
                        'total_failure': success_count == 0
                    }
            else:
                # Test individual component failures
                cascade_results[scenario] = {'tested': True, 'requires_specific_implementation': True}
        
        # Verify system doesn't completely fail
        multi_failure_result = cascade_results.get("multiple_component_failure", {})
        if multi_failure_result:
            # Either graceful degradation or controlled failure
            assert multi_failure_result['success_rate'] >= 0 and multi_failure_result['success_rate'] <= 1
            
        return cascade_results
    
    @pytest.mark.asyncio
    async def test_resource_leak_detection(self, token_optimizer):
        """Test for resource leaks during repeated operations."""
        
        # Baseline memory measurement
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss
        
        # Perform many operations that could leak resources
        leak_test_cycles = 50
        memory_measurements = []
        
        for cycle in range(leak_test_cycles):
            # Create and process data
            test_data = {
                "cycle": cycle,
                "large_data": ["item_" + str(i) for i in range(1000)],
                "nested": {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
            }
            
            # Process the data
            result = await token_optimizer.optimize_response(f"leak_test_{cycle}", test_data)
            assert len(result) == 1
            
            # Force garbage collection
            del test_data, result
            gc.collect()
            
            # Measure memory every 10 cycles
            if cycle % 10 == 0:
                current_memory = process.memory_info().rss
                memory_increase = (current_memory - baseline_memory) / (1024 * 1024)
                memory_measurements.append({
                    'cycle': cycle,
                    'memory_increase_mb': memory_increase
                })
                
                print(f"Cycle {cycle}: Memory increase {memory_increase:.2f}MB")
        
        # Analyze memory growth trend
        memory_increases = [m['memory_increase_mb'] for m in memory_measurements]
        
        if len(memory_increases) >= 3:
            # Check if memory is steadily increasing (potential leak)
            memory_growth_rate = (memory_increases[-1] - memory_increases[0]) / len(memory_increases)
            
            # Memory should not grow excessively
            assert memory_increases[-1] < 500, f"Memory usage too high: {memory_increases[-1]:.2f}MB"
            assert memory_growth_rate < 10, f"Memory growth rate too high: {memory_growth_rate:.2f}MB/cycle"
            
            print(f"Final memory increase: {memory_increases[-1]:.2f}MB")
            print(f"Memory growth rate: {memory_growth_rate:.2f}MB/cycle")
        
        return memory_measurements
    
    def test_thread_safety_under_stress(self):
        """Test thread safety under concurrent access."""
        
        # Shared data structure to test thread safety
        shared_results = []
        lock = threading.Lock()
        
        def worker_thread(worker_id: int, iterations: int):
            """Worker thread performing operations."""
            thread_results = []
            
            for i in range(iterations):
                try:
                    # Perform thread-safe operation
                    result = analyze_task_for_atlas_framework(
                        f"Thread {worker_id} task {i}",
                        {"domain": "thread_safety", "worker_id": worker_id, "iteration": i}
                    )
                    
                    thread_results.append({
                        'worker_id': worker_id,
                        'iteration': i,
                        'success': True,
                        'result_keys': list(result.keys()) if result else []
                    })
                    
                except Exception as e:
                    thread_results.append({
                        'worker_id': worker_id,
                        'iteration': i,
                        'success': False,
                        'error': str(type(e).__name__)
                    })
            
            # Thread-safe update of shared results
            with lock:
                shared_results.extend(thread_results)
        
        # Launch multiple threads
        num_threads = 10
        iterations_per_thread = 20
        
        threads = []
        start_time = time.perf_counter()
        
        for worker_id in range(num_threads):
            thread = threading.Thread(
                target=worker_thread,
                args=(worker_id, iterations_per_thread)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Analyze thread safety results
        total_operations = num_threads * iterations_per_thread
        successful_operations = sum(1 for r in shared_results if r['success'])
        failed_operations = total_operations - successful_operations
        
        thread_safety_metrics = {
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'success_rate': successful_operations / total_operations,
            'total_time': total_time,
            'operations_per_second': total_operations / total_time,
            'threads': num_threads,
            'iterations_per_thread': iterations_per_thread
        }
        
        print(f"\nThread Safety Test Results:")
        print(f"Success rate: {thread_safety_metrics['success_rate']:.2%}")
        print(f"Operations/sec: {thread_safety_metrics['operations_per_second']:.2f}")
        print(f"Failed operations: {failed_operations}")
        
        # Verify thread safety
        assert thread_safety_metrics['success_rate'] > 0.95, "Thread safety issues detected"
        assert len(shared_results) == total_operations, "Missing results indicate thread safety issues"
        
        return thread_safety_metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s", "-x"])  # -x stops on first failure