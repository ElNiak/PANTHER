"""
Performance and benchmark testing for PANTHER network environments.

This module provides comprehensive performance testing including:
- Scalability testing with large service counts
- Concurrency performance under load
- Memory usage profiling and leak detection
- Latency and throughput benchmarks
- Resource utilization optimization
- Performance regression detection

Benchmarks are designed to:
1. Establish performance baselines
2. Detect performance regressions
3. Identify optimization opportunities
4. Validate performance under stress
5. Profile resource usage patterns
"""

import asyncio
import cProfile
import gc
import pstats
import random
import statistics
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from unittest.mock import Mock, patch

import psutil
import pytest

# PANTHER imports
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)

# ========== PERFORMANCE MEASUREMENT UTILITIES ==========


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""

    operation_name: str
    duration_ms: float
    memory_usage_mb: float
    cpu_percent: float
    throughput_ops_per_sec: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_rate: float
    resource_efficiency: float


class PerformanceProfiler:
    """Advanced performance profiler for network environment operations."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.latency_samples = []
        self.error_count = 0
        self.total_operations = 0

    def __enter__(self):
        """Start performance measurement."""
        # Start memory tracing
        tracemalloc.start()

        # Record baseline metrics
        self.start_time = time.perf_counter()
        self.start_memory = psutil.virtual_memory().used

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End performance measurement and calculate metrics."""
        self.end_time = time.perf_counter()
        self.end_memory = psutil.virtual_memory().used

        # Stop memory tracing
        tracemalloc.stop()

        return False

    def record_operation(self, duration_ms: float, success: bool = True):
        """Record an individual operation result."""
        self.latency_samples.append(duration_ms)
        self.total_operations += 1
        if not success:
            self.error_count += 1

    def get_metrics(self) -> PerformanceMetrics:
        """Calculate and return performance metrics."""
        total_duration = (self.end_time - self.start_time) * 1000  # Convert to ms
        memory_delta = (self.end_memory - self.start_memory) / (
            1024 * 1024
        )  # Convert to MB

        # Calculate latency percentiles
        if self.latency_samples:
            sorted_latencies = sorted(self.latency_samples)
            p50 = statistics.median(sorted_latencies)
            p95 = (
                sorted_latencies[int(0.95 * len(sorted_latencies))]
                if len(sorted_latencies) > 1
                else sorted_latencies[0]
            )
            p99 = (
                sorted_latencies[int(0.99 * len(sorted_latencies))]
                if len(sorted_latencies) > 1
                else sorted_latencies[0]
            )
        else:
            p50 = p95 = p99 = 0

        # Calculate throughput
        throughput = (
            self.total_operations / (total_duration / 1000) if total_duration > 0 else 0
        )

        # Calculate error rate
        error_rate = (
            self.error_count / self.total_operations if self.total_operations > 0 else 0
        )

        # Calculate resource efficiency (operations per MB per second)
        resource_efficiency = (
            throughput / max(memory_delta, 1) if memory_delta > 0 else throughput
        )

        return PerformanceMetrics(
            operation_name=self.operation_name,
            duration_ms=total_duration,
            memory_usage_mb=memory_delta,
            cpu_percent=psutil.cpu_percent(),
            throughput_ops_per_sec=throughput,
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            latency_p99_ms=p99,
            error_rate=error_rate,
            resource_efficiency=resource_efficiency,
        )


class LoadGenerator:
    """Generate realistic load patterns for performance testing."""

    def __init__(self, target_rps: float = 10.0, duration_seconds: float = 10.0):
        self.target_rps = target_rps
        self.duration_seconds = duration_seconds
        self.results = []

    def constant_load(self, operation_func: Callable, *args, **kwargs):
        """Generate constant load at target RPS."""
        interval = 1.0 / self.target_rps
        start_time = time.time()
        operation_count = 0

        while time.time() - start_time < self.duration_seconds:
            op_start = time.perf_counter()

            try:
                result = operation_func(*args, **kwargs)
                success = True
            except Exception as e:
                result = str(e)
                success = False

            op_duration = (time.perf_counter() - op_start) * 1000

            self.results.append(
                {
                    "duration_ms": op_duration,
                    "success": success,
                    "result": result,
                    "timestamp": time.time(),
                }
            )

            operation_count += 1

            # Sleep to maintain target RPS
            elapsed = time.time() - start_time
            expected_time = operation_count * interval
            if expected_time > elapsed:
                time.sleep(expected_time - elapsed)

        return self.results

    def burst_load(
        self, operation_func: Callable, burst_size: int = 10, *args, **kwargs
    ):
        """Generate burst load patterns."""
        results = []

        for burst in range(int(self.duration_seconds)):
            burst_results = []
            burst_start = time.perf_counter()

            # Execute burst
            for i in range(burst_size):
                op_start = time.perf_counter()

                try:
                    result = operation_func(*args, **kwargs)
                    success = True
                except Exception as e:
                    result = str(e)
                    success = False

                op_duration = (time.perf_counter() - op_start) * 1000
                burst_results.append(
                    {
                        "duration_ms": op_duration,
                        "success": success,
                        "result": result,
                        "burst": burst,
                        "operation": i,
                    }
                )

            results.extend(burst_results)

            # Wait until next burst
            burst_duration = time.perf_counter() - burst_start
            if burst_duration < 1.0:
                time.sleep(1.0 - burst_duration)

        return results


@contextmanager
def performance_baseline(
    operation_name: str, max_duration_ms: float = 1000.0, max_memory_mb: float = 100.0
):
    """Context manager to enforce performance baselines."""
    profiler = PerformanceProfiler(operation_name)

    with profiler:
        yield profiler

    metrics = profiler.get_metrics()

    # Check performance baselines
    if metrics.duration_ms > max_duration_ms:
        pytest.fail(
            f"Performance baseline exceeded: {metrics.duration_ms:.2f}ms > {max_duration_ms}ms"
        )

    if metrics.memory_usage_mb > max_memory_mb:
        pytest.fail(
            f"Memory baseline exceeded: {metrics.memory_usage_mb:.2f}MB > {max_memory_mb}MB"
        )


# ========== SCALABILITY TESTS ==========


@pytest.mark.performance
class TestScalabilityPerformance:
    """Test scalability performance with increasing loads."""

    def test_service_count_scaling_performance(self):
        """Test performance scaling with increasing service counts."""

        class ScalabilityTestEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.services = {}
                self.performance_stats = {}

            def add_services_batch(self, count: int, batch_size: int = 10):
                """Add services in batches and measure performance."""
                batch_stats = []

                for batch_start in range(0, count, batch_size):
                    batch_end = min(batch_start + batch_size, count)
                    batch_count = batch_end - batch_start

                    with PerformanceProfiler(
                        f"batch_{batch_start}_{batch_end}"
                    ) as profiler:
                        for i in range(batch_start, batch_end):
                            service_name = f"service_{i}"

                            # Simulate service creation overhead
                            service_config = {
                                "name": service_name,
                                "port": 8000 + i,
                                "image": f"test/service_{i}:latest",
                                "environment": {f"SERVICE_ID": str(i)},
                                "dependencies": [
                                    f"service_{j}" for j in range(max(0, i - 2), i)
                                ],
                            }

                            self.services[service_name] = service_config
                            profiler.record_operation(1.0, True)  # Mock 1ms per service

                    metrics = profiler.get_metrics()
                    batch_stats.append(
                        {
                            "batch_size": batch_count,
                            "total_services": len(self.services),
                            "throughput": metrics.throughput_ops_per_sec,
                            "latency_p95": metrics.latency_p95_ms,
                            "memory_usage": metrics.memory_usage_mb,
                        }
                    )

                return batch_stats

            # Required abstract methods
            def prepare_environment(self):
                pass

            def generate_environment_services(self, paths, timestamp):
                pass

            def launch_environment_services(self):
                pass

            def deploy_services(self, services):
                pass

            def _teardown_environment(self):
                pass

            def _do_setup_environment(self):
                pass

            def _do_deploy_services(self, services):
                pass

            def _do_teardown_environment(self):
                pass

            def _get_service_log_directory(self, service):
                return "/tmp/logs"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        env = ScalabilityTestEnv()

        # Test scaling from 10 to 100 services
        scaling_results = []
        for service_count in [10, 25, 50, 75, 100]:
            # Clear previous services for clean measurement
            env.services.clear()

            batch_stats = env.add_services_batch(service_count, batch_size=10)

            # Aggregate batch stats
            total_throughput = sum(stat["throughput"] for stat in batch_stats)
            avg_latency = statistics.mean(stat["latency_p95"] for stat in batch_stats)
            total_memory = sum(stat["memory_usage"] for stat in batch_stats)

            scaling_results.append(
                {
                    "service_count": service_count,
                    "throughput": total_throughput,
                    "latency_p95": avg_latency,
                    "memory_usage": total_memory,
                    "efficiency": total_throughput / max(total_memory, 1),
                }
            )

        # Verify scaling properties
        for i in range(1, len(scaling_results)):
            current = scaling_results[i]
            previous = scaling_results[i - 1]

            # Throughput should not degrade significantly
            throughput_ratio = current["throughput"] / max(previous["throughput"], 1)
            assert (
                throughput_ratio > 0.5
            ), f"Throughput degraded significantly: {throughput_ratio}"

            # Memory usage should scale reasonably
            service_ratio = current["service_count"] / previous["service_count"]
            memory_ratio = current["memory_usage"] / max(previous["memory_usage"], 1)
            assert (
                memory_ratio < service_ratio * 2
            ), f"Memory usage scaling poorly: {memory_ratio} vs {service_ratio}"

    def test_concurrent_environment_performance(self):
        """Test performance with multiple concurrent environments."""

        class ConcurrentEnv(BaseNetworkEnvironment):
            def __init__(self, env_id: int):
                super().__init__(None, f"/tmp/env_{env_id}", "test", "test", Mock())
                self.env_id = env_id
                self.setup_duration = 0
                self.operation_count = 0

            def perform_setup_operations(self, operation_count: int = 20):
                """Perform setup operations for performance testing."""
                start_time = time.perf_counter()

                for i in range(operation_count):
                    # Simulate various setup operations
                    time.sleep(0.001)  # 1ms per operation

                    # Simulate some computational work
                    _ = sum(j * j for j in range(100))

                    self.operation_count += 1

                self.setup_duration = time.perf_counter() - start_time
                return self.setup_duration

            # Required abstract methods
            def prepare_environment(self):
                pass

            def generate_environment_services(self, paths, timestamp):
                pass

            def launch_environment_services(self):
                pass

            def deploy_services(self, services):
                pass

            def _teardown_environment(self):
                pass

            def _do_setup_environment(self):
                pass

            def _do_deploy_services(self, services):
                pass

            def _do_teardown_environment(self):
                pass

            def _get_service_log_directory(self, service):
                return "/tmp/logs"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        # Test with increasing concurrency levels
        concurrency_results = []

        for concurrency_level in [1, 2, 5, 10]:
            environments = [ConcurrentEnv(i) for i in range(concurrency_level)]

            with PerformanceProfiler(f"concurrent_{concurrency_level}") as profiler:
                # Run environments concurrently
                with ThreadPoolExecutor(max_workers=concurrency_level) as executor:
                    futures = [
                        executor.submit(env.perform_setup_operations, 20)
                        for env in environments
                    ]

                    durations = []
                    for future in as_completed(futures):
                        try:
                            duration = future.result()
                            durations.append(duration)
                            profiler.record_operation(duration * 1000, True)
                        except Exception as e:
                            profiler.record_operation(0, False)

            metrics = profiler.get_metrics()

            concurrency_results.append(
                {
                    "concurrency_level": concurrency_level,
                    "throughput": metrics.throughput_ops_per_sec,
                    "avg_duration": statistics.mean(durations) if durations else 0,
                    "memory_usage": metrics.memory_usage_mb,
                    "cpu_utilization": metrics.cpu_percent,
                    "error_rate": metrics.error_rate,
                }
            )

        # Verify concurrency scaling
        for result in concurrency_results:
            # Error rate should remain low
            assert (
                result["error_rate"] < 0.1
            ), f"High error rate at concurrency {result['concurrency_level']}: {result['error_rate']}"

            # CPU utilization should be reasonable
            assert (
                result["cpu_utilization"] < 90
            ), f"CPU overutilization: {result['cpu_utilization']}%"

        # Throughput should generally increase with concurrency (up to a point)
        throughputs = [r["throughput"] for r in concurrency_results]
        assert (
            max(throughputs) > throughputs[0]
        ), "No throughput improvement with concurrency"


@pytest.mark.performance
class TestMemoryPerformance:
    """Test memory usage patterns and leak detection."""

    def test_memory_leak_detection(self):
        """Test for memory leaks during repeated operations."""

        class MemoryTestEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.operation_data = []

            def memory_intensive_operation(self):
                """Perform memory-intensive operation that should not leak."""
                # Create temporary data structures
                large_list = [i * i for i in range(10000)]
                large_dict = {f"key_{i}": f"value_{i}" * 10 for i in range(1000)}

                # Store reference temporarily
                self.operation_data.append((large_list, large_dict))

                # Process data
                result = sum(large_list) + len(large_dict)

                # Clean up (simulate proper cleanup)
                self.operation_data.clear()

                return result

            # Required abstract methods
            def prepare_environment(self):
                pass

            def generate_environment_services(self, paths, timestamp):
                pass

            def launch_environment_services(self):
                pass

            def deploy_services(self, services):
                pass

            def _teardown_environment(self):
                pass

            def _do_setup_environment(self):
                pass

            def _do_deploy_services(self, services):
                pass

            def _do_teardown_environment(self):
                pass

            def _get_service_log_directory(self, service):
                return "/tmp/logs"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        env = MemoryTestEnv()

        # Measure baseline memory
        gc.collect()  # Force garbage collection
        baseline_memory = psutil.virtual_memory().used
        memory_samples = []

        # Perform repeated operations and track memory usage
        for cycle in range(10):
            # Perform multiple operations per cycle
            for op in range(20):
                env.memory_intensive_operation()

            # Force garbage collection and measure memory
            gc.collect()
            current_memory = psutil.virtual_memory().used
            memory_samples.append(current_memory - baseline_memory)

            # Brief pause to allow system stabilization
            time.sleep(0.1)

        # Analyze memory usage pattern
        memory_trend = []
        for i in range(1, len(memory_samples)):
            trend = memory_samples[i] - memory_samples[i - 1]
            memory_trend.append(trend)

        # Calculate average memory growth per cycle
        avg_growth = statistics.mean(memory_trend) if memory_trend else 0
        max_memory = max(memory_samples)

        # Memory leak detection criteria
        memory_growth_mb = avg_growth / (1024 * 1024)
        max_memory_mb = max_memory / (1024 * 1024)

        # Assertions for memory leak detection
        assert (
            memory_growth_mb < 1.0
        ), f"Potential memory leak detected: {memory_growth_mb:.2f}MB/cycle growth"
        assert (
            max_memory_mb < 50.0
        ), f"Excessive memory usage: {max_memory_mb:.2f}MB peak"

        # Verify memory is released after final cleanup
        env.operation_data.clear()
        gc.collect()
        final_memory = psutil.virtual_memory().used
        final_memory_mb = (final_memory - baseline_memory) / (1024 * 1024)

        assert (
            final_memory_mb < 10.0
        ), f"Memory not properly released: {final_memory_mb:.2f}MB remaining"

    def test_memory_efficiency_under_load(self):
        """Test memory efficiency under sustained load."""

        class MemoryEfficientEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.cached_data = {}
                self.max_cache_size = 100

            def efficient_data_processing(self, data_id: str):
                """Process data with efficient memory usage."""
                # Check cache first
                if data_id in self.cached_data:
                    return self.cached_data[data_id]

                # Generate data
                data = {
                    "id": data_id,
                    "values": [i for i in range(1000)],
                    "metadata": {"created": time.time(), "size": 1000},
                }

                # Process data
                result = {
                    "sum": sum(data["values"]),
                    "count": len(data["values"]),
                    "avg": sum(data["values"]) / len(data["values"]),
                }

                # Cache with size limit
                if len(self.cached_data) < self.max_cache_size:
                    self.cached_data[data_id] = result
                else:
                    # Evict oldest entry (simple FIFO)
                    oldest_key = next(iter(self.cached_data))
                    del self.cached_data[oldest_key]
                    self.cached_data[data_id] = result

                return result

            def get_memory_stats(self):
                """Get current memory statistics."""
                return {
                    "cache_size": len(self.cached_data),
                    "cache_memory_estimate": len(self.cached_data)
                    * 100,  # Rough estimate
                    "system_memory": psutil.virtual_memory().used,
                }

            # Required abstract methods
            def prepare_environment(self):
                pass

            def generate_environment_services(self, paths, timestamp):
                pass

            def launch_environment_services(self):
                pass

            def deploy_services(self, services):
                pass

            def _teardown_environment(self):
                pass

            def _do_setup_environment(self):
                pass

            def _do_deploy_services(self, services):
                pass

            def _do_teardown_environment(self):
                pass

            def _get_service_log_directory(self, service):
                return "/tmp/logs"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        env = MemoryEfficientEnv()

        # Measure baseline
        baseline_stats = env.get_memory_stats()

        # Perform load test with memory monitoring
        load_generator = LoadGenerator(target_rps=50, duration_seconds=5)

        def operation():
            data_id = f"data_{time.time()}_{threading.current_thread().ident}"
            return env.efficient_data_processing(data_id)

        results = load_generator.constant_load(operation)

        # Measure final stats
        final_stats = env.get_memory_stats()

        # Calculate metrics
        successful_ops = sum(1 for r in results if r["success"])
        total_ops = len(results)
        memory_delta = final_stats["system_memory"] - baseline_stats["system_memory"]
        memory_per_op = memory_delta / max(total_ops, 1)

        # Efficiency assertions
        assert (
            env.max_cache_size >= final_stats["cache_size"]
        ), "Cache size exceeded limit"
        assert (
            memory_per_op < 1024
        ), f"Memory per operation too high: {memory_per_op} bytes"
        assert (
            successful_ops / total_ops > 0.95
        ), f"Low success rate: {successful_ops}/{total_ops}"


@pytest.mark.performance
class TestLatencyBenchmarks:
    """Benchmark latency characteristics of network environment operations."""

    def test_operation_latency_distribution(self):
        """Test latency distribution of key operations."""

        class LatencyTestEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.latency_measurements = {}

            def measure_operation_latency(
                self, operation_name: str, operation_func: Callable
            ):
                """Measure latency of a specific operation."""
                measurements = []

                for i in range(100):  # 100 samples
                    start_time = time.perf_counter()

                    try:
                        result = operation_func()
                        success = True
                    except Exception:
                        success = False

                    duration_ms = (time.perf_counter() - start_time) * 1000
                    measurements.append(
                        {"duration_ms": duration_ms, "success": success, "iteration": i}
                    )

                self.latency_measurements[operation_name] = measurements
                return measurements

            def port_allocation_operation(self):
                """Simulate port allocation operation."""
                time.sleep(0.001)  # 1ms base latency
                # Simulate some randomness in latency
                additional_delay = random.exponential(
                    0.0005
                )  # Exponential distribution
                time.sleep(additional_delay)
                return 8000 + random.randint(1, 1000)

            def service_registration_operation(self):
                """Simulate service registration operation."""
                time.sleep(0.002)  # 2ms base latency
                # Simulate occasional slower operations
                if random.random() < 0.05:  # 5% chance of slow operation
                    time.sleep(0.01)  # Additional 10ms
                return f"service_{random.randint(1000, 9999)}"

            def environment_validation_operation(self):
                """Simulate environment validation operation."""
                time.sleep(0.0005)  # 0.5ms base latency
                # Simulate CPU-bound work
                _ = sum(i * i for i in range(1000))
                return True

            # Required abstract methods
            def prepare_environment(self):
                pass

            def generate_environment_services(self, paths, timestamp):
                pass

            def launch_environment_services(self):
                pass

            def deploy_services(self, services):
                pass

            def _teardown_environment(self):
                pass

            def _do_setup_environment(self):
                pass

            def _do_deploy_services(self, services):
                pass

            def _do_teardown_environment(self):
                pass

            def _get_service_log_directory(self, service):
                return "/tmp/logs"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        env = LatencyTestEnv()

        # Measure latency for different operations
        operations = [
            ("port_allocation", env.port_allocation_operation),
            ("service_registration", env.service_registration_operation),
            ("environment_validation", env.environment_validation_operation),
        ]

        latency_stats = {}

        for op_name, op_func in operations:
            measurements = env.measure_operation_latency(op_name, op_func)

            # Calculate latency statistics
            durations = [m["duration_ms"] for m in measurements if m["success"]]
            success_rate = sum(1 for m in measurements if m["success"]) / len(
                measurements
            )

            if durations:
                sorted_durations = sorted(durations)
                stats = {
                    "p50": statistics.median(sorted_durations),
                    "p90": sorted_durations[int(0.9 * len(sorted_durations))],
                    "p95": sorted_durations[int(0.95 * len(sorted_durations))],
                    "p99": sorted_durations[int(0.99 * len(sorted_durations))],
                    "mean": statistics.mean(sorted_durations),
                    "std": statistics.stdev(sorted_durations)
                    if len(sorted_durations) > 1
                    else 0,
                    "min": min(sorted_durations),
                    "max": max(sorted_durations),
                    "success_rate": success_rate,
                }
            else:
                stats = {"success_rate": success_rate}

            latency_stats[op_name] = stats

        # Validate latency requirements
        for op_name, stats in latency_stats.items():
            assert (
                stats["success_rate"] > 0.95
            ), f"Low success rate for {op_name}: {stats['success_rate']}"

            if "p95" in stats:
                # Define latency SLAs
                sla_requirements = {
                    "port_allocation": 5.0,  # 5ms p95
                    "service_registration": 15.0,  # 15ms p95
                    "environment_validation": 3.0,  # 3ms p95
                }

                if op_name in sla_requirements:
                    assert (
                        stats["p95"] < sla_requirements[op_name]
                    ), f"P95 latency SLA violation for {op_name}: {stats['p95']:.2f}ms > {sla_requirements[op_name]}ms"

    def test_throughput_vs_latency_tradeoff(self):
        """Test the relationship between throughput and latency."""

        class ThroughputLatencyEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.processing_queue = []
                self.batch_size = 1

            def process_request(self, request_id: str):
                """Process a single request with configurable batching."""
                self.processing_queue.append(request_id)

                # Process in batches for efficiency
                if len(self.processing_queue) >= self.batch_size:
                    batch = self.processing_queue[: self.batch_size]
                    self.processing_queue = self.processing_queue[self.batch_size :]

                    # Simulate batch processing overhead
                    batch_overhead = 0.001 * len(batch)  # 1ms per item in batch
                    time.sleep(batch_overhead)

                    return f"processed_batch_{len(batch)}"

                return "queued"

            def set_batch_size(self, size: int):
                """Configure batch size for throughput/latency tradeoff."""
                self.batch_size = max(1, size)

            def flush_queue(self):
                """Flush remaining items in queue."""
                if self.processing_queue:
                    remaining = len(self.processing_queue)
                    self.processing_queue.clear()
                    return remaining
                return 0

            # Required abstract methods
            def prepare_environment(self):
                pass

            def generate_environment_services(self, paths, timestamp):
                pass

            def launch_environment_services(self):
                pass

            def deploy_services(self, services):
                pass

            def _teardown_environment(self):
                pass

            def _do_setup_environment(self):
                pass

            def _do_deploy_services(self, services):
                pass

            def _do_teardown_environment(self):
                pass

            def _get_service_log_directory(self, service):
                return "/tmp/logs"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        env = ThroughputLatencyEnv()

        # Test different batch sizes
        batch_sizes = [1, 5, 10, 20]
        results = []

        for batch_size in batch_sizes:
            env.set_batch_size(batch_size)

            # Measure throughput and latency for this batch size
            load_generator = LoadGenerator(target_rps=100, duration_seconds=2)

            def process_operation():
                request_id = f"req_{time.time()}_{threading.current_thread().ident}"
                return env.process_request(request_id)

            load_results = load_generator.constant_load(process_operation)

            # Flush any remaining requests
            env.flush_queue()

            # Calculate metrics
            successful_ops = [r for r in load_results if r["success"]]
            if successful_ops:
                latencies = [r["duration_ms"] for r in successful_ops]
                throughput = len(successful_ops) / 2.0  # ops per second
                avg_latency = statistics.mean(latencies)
                p95_latency = (
                    sorted(latencies)[int(0.95 * len(latencies))]
                    if len(latencies) > 1
                    else latencies[0]
                )
            else:
                throughput = avg_latency = p95_latency = 0

            results.append(
                {
                    "batch_size": batch_size,
                    "throughput": throughput,
                    "avg_latency": avg_latency,
                    "p95_latency": p95_latency,
                    "efficiency": throughput
                    / max(p95_latency, 1),  # throughput per ms latency
                }
            )

        # Analyze throughput vs latency tradeoff
        for i, result in enumerate(results):
            # Throughput should generally increase with batch size
            if i > 0:
                throughput_improvement = result["throughput"] / max(
                    results[i - 1]["throughput"], 1
                )
                latency_increase = result["p95_latency"] / max(
                    results[i - 1]["p95_latency"], 1
                )

                # Verify reasonable tradeoff
                assert (
                    throughput_improvement > 0.8
                ), f"Throughput decreased significantly: {throughput_improvement}"
                assert (
                    latency_increase < 3.0
                ), f"Latency increased too much: {latency_increase}"

        # Find optimal batch size (highest efficiency)
        optimal_result = max(results, key=lambda r: r["efficiency"])
        assert (
            optimal_result["batch_size"] > 1
        ), "Optimal batch size should be greater than 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "performance"])
