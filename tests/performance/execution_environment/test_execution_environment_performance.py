"""
Performance benchmarks and stress tests for execution environment plugins.

Tests setup performance, memory usage, scalability, and behavior under extreme loads.
Provides metrics for:
- Environment setup time scaling
- Command generation performance
- Memory consumption patterns
- Concurrent execution performance
- File registration throughput
- Configuration processing speed
"""

import gc
import multiprocessing
import shutil
import statistics
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock

import psutil
import pytest

from panther.config.core.models import ProtocolRole

# Import core components
from panther.core.observer.management.event_manager import EventManager

# Import command generation utilities
from panther.plugins.environments.execution_environment.command_generation_utils import (
    ExecutionEnvironmentCommandBuilder,
    OutputFileManager,
    WrapperCommandGenerator,
    create_execution_environment_builder,
)
from panther.plugins.environments.execution_environment.gperf_cpu.config_schema import (
    GperfCpuConfig,
)
from panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu import (
    GperfCpuEnvironment,
)
from panther.plugins.environments.execution_environment.gperf_heap.config_schema import (
    GperfHeapConfig,
)
from panther.plugins.environments.execution_environment.gperf_heap.gperf_heap import (
    GperfHeapEnvironment,
)
from panther.plugins.environments.execution_environment.helgrind.config_schema import (
    HelgrindConfig,
)
from panther.plugins.environments.execution_environment.helgrind.helgrind import (
    HelgrindEnvironment,
)
from panther.plugins.environments.execution_environment.iterations.config_schema import (
    IterationsConfig,
)
from panther.plugins.environments.execution_environment.iterations.iterations import (
    IterationsEnvironment,
)
from panther.plugins.environments.execution_environment.memcheck.config_schema import (
    MemcheckConfig,
)
from panther.plugins.environments.execution_environment.memcheck.memcheck import (
    MemcheckEnvironment,
)
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)

# Import execution environment components
from panther.plugins.environments.execution_environment.strace.strace import (
    StraceEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        gc.collect()  # Clean up before timing
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time


class MemoryMonitor:
    """Monitor memory usage during operations."""

    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = None
        self.peak_memory = None
        self.final_memory = None

    def start(self):
        """Start monitoring memory."""
        gc.collect()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.initial_memory

    def update_peak(self):
        """Update peak memory usage."""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory

    def stop(self):
        """Stop monitoring and return metrics."""
        gc.collect()
        self.final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        return {
            "initial_mb": self.initial_memory,
            "peak_mb": self.peak_memory,
            "final_mb": self.final_memory,
            "increase_mb": self.final_memory - self.initial_memory,
            "peak_increase_mb": self.peak_memory - self.initial_memory,
        }


def create_mock_services(count: int) -> List[Mock]:
    """Create specified number of mock services for testing."""
    services = []
    for i in range(count):
        service = Mock(spec=IServiceManager)
        service.service_name = f"performance_service_{i:04d}"
        service.role = ProtocolRole.SERVER if i % 2 == 0 else ProtocolRole.CLIENT
        service.run_cmd = {"pre_run_cmds": [], "post_run_cmds": []}
        service.environments = {}
        services.append(service)
    return services


@pytest.mark.performance
class TestExecutionEnvironmentSetupPerformance:
    """Performance tests for environment setup operations."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory for performance tests."""
        temp_dir = tempfile.mkdtemp(prefix="perf_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def event_manager(self):
        """Create event manager."""
        return EventManager()

    @pytest.mark.parametrize("service_count", [1, 5, 10, 25, 50, 100])
    def test_strace_environment_setup_scaling(
        self, temp_output_dir, event_manager, service_count
    ):
        """Test StraceEnvironment setup performance scaling with service count."""
        config = StraceConfig(trace_system_calls=True)
        services = create_mock_services(service_count)

        # Initialize environment
        strace_env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Track operations for performance measurement
        operations = {"register_calls": 0, "modify_calls": 0}

        def mock_register(*args):
            operations["register_calls"] += 1

        def mock_modify(*args):
            operations["modify_calls"] += 1
            return {"success": True}

        strace_env.register_output_file = mock_register
        strace_env.modify_service_commands = mock_modify

        # Measure setup performance
        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        with PerformanceTimer(f"strace_setup_{service_count}_services") as timer:
            strace_env._setup_plugin_specific_environment(services, "20250101_120000")

        memory_metrics = memory_monitor.stop()

        # Performance assertions
        setup_time = timer.duration

        # Setup time should scale reasonably (not exponentially)
        expected_max_time = 0.1 + (service_count * 0.001)  # Base time + linear scaling
        assert (
            setup_time < expected_max_time
        ), f"Setup too slow: {setup_time:.3f}s for {service_count} services"

        # Should process all services
        assert operations["register_calls"] == service_count
        assert operations["modify_calls"] == service_count

        # Memory usage should be reasonable
        memory_per_service = (
            memory_metrics["increase_mb"] / service_count if service_count > 0 else 0
        )
        assert (
            memory_per_service < 1.0
        ), f"Memory usage too high: {memory_per_service:.2f}MB per service"

        # Log performance metrics for analysis
        print(f"\nPerformance metrics for {service_count} services:")
        print(
            f"  Setup time: {setup_time:.3f}s ({setup_time/service_count*1000:.2f}ms per service)"
        )
        print(f"  Memory increase: {memory_metrics['increase_mb']:.2f}MB")
        print(f"  Peak memory: {memory_metrics['peak_mb']:.2f}MB")

    @pytest.mark.parametrize(
        "env_class,config_class",
        [
            (StraceEnvironment, StraceConfig),
            (GperfCpuEnvironment, GperfCpuConfig),
            (GperfHeapEnvironment, GperfHeapConfig),
            (HelgrindEnvironment, HelgrindConfig),
            (MemcheckEnvironment, MemcheckConfig),
            (IterationsEnvironment, IterationsConfig),
        ],
    )
    def test_individual_environment_performance_comparison(
        self, temp_output_dir, event_manager, env_class, config_class
    ):
        """Compare setup performance across different environment types."""
        service_count = 20
        services = create_mock_services(service_count)

        # Create configuration
        if config_class == IterationsConfig:
            config = config_class(iterations=3)  # Multiple iterations for testing
        else:
            config = config_class()

        # Initialize environment
        env = env_class(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type=env_class.__name__.lower(),
            event_manager=event_manager,
        )

        # Mock operations
        operations = {"register_calls": 0, "modify_calls": 0, "commands_generated": 0}

        def mock_register(*args):
            operations["register_calls"] += 1

        def mock_modify(service, mod_type, commands):
            operations["modify_calls"] += 1
            operations["commands_generated"] += len(commands.get("pre_run_cmds", []))
            return {"success": True}

        env.register_output_file = mock_register
        env.modify_service_commands = mock_modify

        # Measure performance
        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        with PerformanceTimer(f"{env_class.__name__}_setup") as timer:
            env._setup_plugin_specific_environment(services, "20250101_120000")

        memory_metrics = memory_monitor.stop()

        # Collect metrics
        metrics = {
            "environment": env_class.__name__,
            "setup_time": timer.duration,
            "services_processed": service_count,
            "register_calls": operations["register_calls"],
            "modify_calls": operations["modify_calls"],
            "commands_generated": operations["commands_generated"],
            "memory_increase_mb": memory_metrics["increase_mb"],
            "time_per_service_ms": (timer.duration / service_count) * 1000,
            "memory_per_service_mb": (
                memory_metrics["increase_mb"] / service_count
                if service_count > 0
                else 0
            ),
        }

        # Performance thresholds (environment-specific)
        max_time_per_service = {
            "StraceEnvironment": 5.0,  # 5ms per service
            "GperfCpuEnvironment": 8.0,  # 8ms per service (more complex)
            "GperfHeapEnvironment": 8.0,  # 8ms per service
            "HelgrindEnvironment": 10.0,  # 10ms per service (Valgrind complexity)
            "MemcheckEnvironment": 10.0,  # 10ms per service (Valgrind complexity)
            "IterationsEnvironment": 6.0,  # 6ms per service (wrapper generation)
        }

        expected_max_time = max_time_per_service.get(env_class.__name__, 10.0)
        assert (
            metrics["time_per_service_ms"] < expected_max_time
        ), f"{env_class.__name__} too slow: {metrics['time_per_service_ms']:.2f}ms per service"

        # Memory usage should be reasonable for all environments
        assert (
            metrics["memory_per_service_mb"] < 0.5
        ), f"{env_class.__name__} memory usage too high: {metrics['memory_per_service_mb']:.3f}MB per service"

        print(f"\n{env_class.__name__} Performance:")
        print(f"  Time per service: {metrics['time_per_service_ms']:.2f}ms")
        print(f"  Memory per service: {metrics['memory_per_service_mb']:.3f}MB")
        print(f"  Commands generated: {metrics['commands_generated']}")


@pytest.mark.performance
class TestCommandGenerationPerformance:
    """Performance tests for command generation utilities."""

    def test_output_file_manager_throughput(self):
        """Test OutputFileManager file registration throughput."""
        mock_callback = Mock()
        manager = OutputFileManager(mock_callback)

        file_count = 1000
        service_names = [f"service_{i:04d}" for i in range(100)]  # 100 services
        file_types = ["profile", "trace", "log", "output", "summary"]

        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        with PerformanceTimer("file_registration_throughput") as timer:
            for i in range(file_count):
                service_name = service_names[i % len(service_names)]
                file_type = file_types[i % len(file_types)]
                file_path = f"/app/logs/{service_name}_{file_type}_{i:06d}.out"

                manager.register_output_file(
                    file_type=file_type,
                    file_path=file_path,
                    service_name=service_name,
                    description=f"Performance test file {i}",
                )

                # Update memory monitoring periodically
                if i % 100 == 0:
                    memory_monitor.update_peak()

        memory_metrics = memory_monitor.stop()

        # Performance metrics
        files_per_second = file_count / timer.duration
        time_per_file_us = (timer.duration / file_count) * 1_000_000  # microseconds

        # Performance assertions
        assert (
            files_per_second > 500
        ), f"File registration too slow: {files_per_second:.1f} files/sec"
        assert (
            time_per_file_us < 2000
        ), f"Time per file too high: {time_per_file_us:.1f}μs"
        assert (
            memory_metrics["increase_mb"] < 50
        ), f"Memory increase too high: {memory_metrics['increase_mb']:.1f}MB"

        # Test retrieval performance
        with PerformanceTimer("file_retrieval") as retrieval_timer:
            all_files = manager.get_registered_files()

            # Test filtering performance
            for service_name in service_names[:10]:  # Test first 10 services
                service_files = manager.get_registered_files(service_name)
                assert len(service_files) > 0

        retrieval_time_ms = retrieval_timer.duration * 1000
        assert (
            retrieval_time_ms < 100
        ), f"File retrieval too slow: {retrieval_time_ms:.1f}ms"

        print(f"\nFile Manager Performance:")
        print(
            f"  Registration: {files_per_second:.1f} files/sec ({time_per_file_us:.1f}μs per file)"
        )
        print(f"  Retrieval: {retrieval_time_ms:.1f}ms for {file_count} files")
        print(f"  Memory usage: {memory_metrics['increase_mb']:.1f}MB")

    def test_wrapper_command_generator_performance(self):
        """Test WrapperCommandGenerator command generation performance."""
        generator = WrapperCommandGenerator()

        command_count = 500
        service_names = [f"service_{i:03d}" for i in range(50)]
        environment_names = ["strace", "gperf_cpu", "memcheck", "helgrind"]

        commands_generated = []
        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        # Test environment wrapper generation
        with PerformanceTimer("wrapper_generation") as timer:
            for i in range(command_count):
                service_name = service_names[i % len(service_names)]
                env_name = environment_names[i % len(environment_names)]

                # Generate various types of wrappers
                if i % 4 == 0:
                    # Basic wrapper
                    wrapper = generator.generate_environment_wrapper(
                        environment_name=env_name,
                        wrapper_command=f"{env_name} -o /tmp/{service_name}.out",
                        service_name=service_name,
                    )
                elif i % 4 == 1:
                    # Wrapper with environment variables
                    wrapper = generator.generate_environment_wrapper(
                        environment_name=env_name,
                        wrapper_command=f"{env_name} -o $OUTPUT_FILE",
                        service_name=service_name,
                        additional_env_vars={
                            "OUTPUT_FILE": f"/tmp/{service_name}.out",
                            "VERBOSE": "1",
                        },
                    )
                elif i % 4 == 2:
                    # Conditional wrapper
                    wrapper = generator.generate_conditional_wrapper(
                        condition=f"command -v {env_name} >/dev/null 2>&1",
                        environment_name=env_name,
                        wrapper_command=f"{env_name} -o /tmp/{service_name}.out",
                        service_name=service_name,
                        fallback_message=f"{env_name} not available",
                    )
                else:
                    # Post-processing command
                    wrapper = generator.generate_post_processing_command(
                        input_file=f"/tmp/{service_name}.raw",
                        output_file=f"/tmp/{service_name}.processed",
                        processing_command=f"process_{env_name} /tmp/{service_name}.raw > /tmp/{service_name}.processed",
                        service_name=service_name,
                        description=f"{env_name} post-processing",
                    )

                commands_generated.append(wrapper)

                # Update memory monitoring
                if i % 50 == 0:
                    memory_monitor.update_peak()

        memory_metrics = memory_monitor.stop()

        # Performance metrics
        commands_per_second = command_count / timer.duration
        time_per_command_us = (timer.duration / command_count) * 1_000_000

        # Performance assertions
        assert (
            commands_per_second > 200
        ), f"Command generation too slow: {commands_per_second:.1f} commands/sec"
        assert (
            time_per_command_us < 5000
        ), f"Time per command too high: {time_per_command_us:.1f}μs"
        assert (
            memory_metrics["increase_mb"] < 20
        ), f"Memory increase too high: {memory_metrics['increase_mb']:.1f}MB"

        # Verify all commands were generated successfully
        assert len(commands_generated) == command_count
        for cmd in commands_generated:
            assert isinstance(cmd, str)
            assert len(cmd) > 0

        print(f"\nWrapper Generator Performance:")
        print(
            f"  Generation: {commands_per_second:.1f} commands/sec ({time_per_command_us:.1f}μs per command)"
        )
        print(f"  Memory usage: {memory_metrics['increase_mb']:.1f}MB")
        print(
            f"  Average command length: {statistics.mean(len(cmd) for cmd in commands_generated):.1f} chars"
        )


@pytest.mark.performance
class TestConcurrentExecutionEnvironmentPerformance:
    """Performance tests for concurrent environment operations."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp(prefix="concurrent_perf_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_concurrent_environment_setup_performance(self, temp_output_dir):
        """Test performance of setting up multiple environments concurrently."""
        num_threads = min(4, multiprocessing.cpu_count())
        services_per_env = 25

        # Environment configurations
        env_configs = [
            (StraceEnvironment, StraceConfig(), "strace"),
            (GperfCpuEnvironment, GperfCpuConfig(), "gperf_cpu"),
            (MemcheckEnvironment, MemcheckConfig(), "memcheck"),
            (IterationsEnvironment, IterationsConfig(iterations=5), "iterations"),
        ]

        def setup_environment(env_config_tuple):
            """Setup single environment (for threading)."""
            env_class, config, env_name = env_config_tuple
            thread_id = threading.get_ident()

            # Create services for this thread
            services = create_mock_services(services_per_env)
            event_manager = EventManager()

            # Initialize environment
            env = env_class(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type=env_name,
                event_manager=event_manager,
            )

            # Track operations
            operations = {"register": 0, "modify": 0}

            def mock_register(*args):
                operations["register"] += 1

            def mock_modify(*args):
                operations["modify"] += 1
                return {"success": True}

            env.register_output_file = mock_register
            env.modify_service_commands = mock_modify

            # Time the setup
            start_time = time.perf_counter()
            env._setup_plugin_specific_environment(services, f"20250101_{thread_id}")
            end_time = time.perf_counter()

            return {
                "environment": env_name,
                "thread_id": thread_id,
                "setup_time": end_time - start_time,
                "services_processed": services_per_env,
                "operations": operations,
            }

        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        # Execute concurrent setups
        with PerformanceTimer("concurrent_environment_setup") as timer:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # Submit all environment setups
                futures = [
                    executor.submit(setup_environment, config) for config in env_configs
                ]

                # Collect results
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)

        memory_metrics = memory_monitor.stop()

        # Analyze results
        total_services = sum(r["services_processed"] for r in results)
        total_setup_time = sum(r["setup_time"] for r in results)
        max_setup_time = max(r["setup_time"] for r in results)

        # Performance assertions
        assert (
            timer.duration < total_setup_time
        ), "Concurrent execution should be faster than sequential"
        speedup = total_setup_time / timer.duration
        assert speedup > 1.5, f"Insufficient concurrency speedup: {speedup:.2f}x"

        # Individual environment performance should still be reasonable
        for result in results:
            time_per_service = (
                result["setup_time"] / result["services_processed"]
            ) * 1000
            assert (
                time_per_service < 20
            ), f"{result['environment']} too slow in concurrent setup: {time_per_service:.1f}ms per service"

        print(f"\nConcurrent Environment Setup Performance:")
        print(
            f"  Total time: {timer.duration:.3f}s (sequential would be {total_setup_time:.3f}s)"
        )
        print(f"  Speedup: {speedup:.2f}x")
        print(f"  Max individual setup time: {max_setup_time:.3f}s")
        print(f"  Total services processed: {total_services}")
        print(f"  Memory usage: {memory_metrics['increase_mb']:.1f}MB")

    def test_environment_builder_concurrent_usage(self, temp_output_dir):
        """Test ExecutionEnvironmentCommandBuilder under concurrent usage."""
        num_threads = 4
        operations_per_thread = 100

        def worker_thread(thread_id):
            """Worker thread for concurrent builder usage."""
            results = {
                "files_registered": 0,
                "commands_added": 0,
                "builds_completed": 0,
            }

            for i in range(operations_per_thread):
                # Create mock service
                service = Mock(spec=IServiceManager)
                service.service_name = f"thread_{thread_id}_service_{i}"
                service.role = ProtocolRole.SERVER
                service.run_cmd = {"pre_run_cmds": []}
                service.environments = {}

                # Create builder
                mock_callback = Mock()
                builder = create_execution_environment_builder(
                    service=service,
                    environment_name=f"test_env_{thread_id}",
                    timestamp=f"20250101_{thread_id:02d}{i:04d}",
                    register_output_callback=mock_callback,
                )

                # Add various operations
                file_path = builder.register_output_file("test", "out", "Test output")
                results["files_registered"] += 1

                builder.add_wrapper_command(
                    wrapper_command=f"test_wrapper_{i}", description=f"Test wrapper {i}"
                )
                results["commands_added"] += 1

                # Mock command modifier
                def mock_modifier(*args):
                    return {"success": True}

                # Build and apply
                builder.build_and_apply(mock_modifier)
                results["builds_completed"] += 1

            return results

        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        # Execute concurrent builder operations
        with PerformanceTimer("concurrent_builder_usage") as timer:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [
                    executor.submit(worker_thread, i) for i in range(num_threads)
                ]
                thread_results = [future.result() for future in as_completed(futures)]

        memory_metrics = memory_monitor.stop()

        # Aggregate results
        total_files = sum(r["files_registered"] for r in thread_results)
        total_commands = sum(r["commands_added"] for r in thread_results)
        total_builds = sum(r["builds_completed"] for r in thread_results)

        expected_total = num_threads * operations_per_thread

        # Verify all operations completed successfully
        assert total_files == expected_total
        assert total_commands == expected_total
        assert total_builds == expected_total

        # Performance metrics
        operations_per_second = (
            total_files + total_commands + total_builds
        ) / timer.duration

        assert (
            operations_per_second > 500
        ), f"Builder operations too slow: {operations_per_second:.1f} ops/sec"
        assert (
            memory_metrics["increase_mb"] < 100
        ), f"Memory usage too high: {memory_metrics['increase_mb']:.1f}MB"

        print(f"\nConcurrent Builder Usage Performance:")
        print(f"  Operations per second: {operations_per_second:.1f}")
        print(f"  Total operations: {total_files + total_commands + total_builds}")
        print(f"  Memory usage: {memory_metrics['increase_mb']:.1f}MB")


@pytest.mark.performance
@pytest.mark.stress
class TestExecutionEnvironmentStressTests:
    """Stress tests for execution environments under extreme loads."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp(prefix="stress_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.slow
    def test_large_scale_service_processing(self, temp_output_dir):
        """Stress test with very large number of services."""
        service_count = 500  # Large number of services
        config = StraceConfig()
        event_manager = EventManager()

        # Create large number of services
        services = create_mock_services(service_count)

        # Initialize environment
        strace_env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Track operations and memory
        operations = {"register": 0, "modify": 0}
        memory_snapshots = []

        def mock_register(*args):
            operations["register"] += 1
            if operations["register"] % 50 == 0:  # Monitor memory every 50 operations
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_snapshots.append(current_memory)

        def mock_modify(*args):
            operations["modify"] += 1
            return {"success": True}

        strace_env.register_output_file = mock_register
        strace_env.modify_service_commands = mock_modify

        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        # Execute stress test
        with PerformanceTimer("large_scale_processing") as timer:
            strace_env._setup_plugin_specific_environment(services, "20250101_120000")

        memory_metrics = memory_monitor.stop()

        # Verify all services were processed
        assert operations["register"] == service_count
        assert operations["modify"] == service_count

        # Performance requirements for large scale
        total_time = timer.duration
        time_per_service = (total_time / service_count) * 1000  # ms

        assert total_time < 30.0, f"Large scale processing too slow: {total_time:.1f}s"
        assert (
            time_per_service < 60.0
        ), f"Time per service too high: {time_per_service:.1f}ms"

        # Memory should not grow excessively
        assert (
            memory_metrics["increase_mb"] < 200
        ), f"Memory usage too high: {memory_metrics['increase_mb']:.1f}MB"

        # Memory growth should be roughly linear, not exponential
        if len(memory_snapshots) > 1:
            memory_growth_rate = (memory_snapshots[-1] - memory_snapshots[0]) / len(
                memory_snapshots
            )
            assert (
                memory_growth_rate < 2.0
            ), f"Memory growth too steep: {memory_growth_rate:.2f}MB per 50 services"

        print(f"\nLarge Scale Stress Test Results:")
        print(f"  Services processed: {service_count}")
        print(f"  Total time: {total_time:.1f}s ({time_per_service:.1f}ms per service)")
        print(f"  Memory usage: {memory_metrics['increase_mb']:.1f}MB")
        print(f"  Peak memory: {memory_metrics['peak_mb']:.1f}MB")

    @pytest.mark.slow
    def test_memory_intensive_environment_combination(self, temp_output_dir):
        """Stress test with multiple memory-intensive environments."""
        service_count = 100
        services = create_mock_services(service_count)

        # Create multiple environments
        environments = [
            (StraceEnvironment, StraceConfig(), "strace"),
            (GperfCpuEnvironment, GperfCpuConfig(), "gperf_cpu"),
            (GperfHeapEnvironment, GperfHeapConfig(), "gperf_heap"),
            (MemcheckEnvironment, MemcheckConfig(), "memcheck"),
            (HelgrindEnvironment, HelgrindConfig(), "helgrind"),
            (IterationsEnvironment, IterationsConfig(iterations=10), "iterations"),
        ]

        memory_monitor = MemoryMonitor()
        memory_monitor.start()

        total_operations = 0
        environment_times = []

        with PerformanceTimer("memory_intensive_combination") as timer:
            for env_class, config, env_name in environments:
                event_manager = EventManager()

                env = env_class(
                    env_config_to_test=config,
                    output_dir=temp_output_dir,
                    env_type="execution",
                    env_sub_type=env_name,
                    event_manager=event_manager,
                )

                # Track operations
                ops = {"register": 0, "modify": 0}

                def make_counters(ops_dict):
                    def mock_register(*args):
                        ops_dict["register"] += 1

                    def mock_modify(*args):
                        ops_dict["modify"] += 1
                        return {"success": True}

                    return mock_register, mock_modify

                reg_func, mod_func = make_counters(ops)
                env.register_output_file = reg_func
                env.modify_service_commands = mod_func

                # Setup environment
                env_start = time.perf_counter()
                env._setup_plugin_specific_environment(services, "20250101_120000")
                env_end = time.perf_counter()

                environment_times.append(env_end - env_start)
                total_operations += ops["register"] + ops["modify"]

                # Update memory monitoring
                memory_monitor.update_peak()

        memory_metrics = memory_monitor.stop()

        # Performance analysis
        total_time = timer.duration
        average_env_time = statistics.mean(environment_times)

        # All environments should complete within reasonable time
        assert (
            total_time < 60.0
        ), f"Combined environment setup too slow: {total_time:.1f}s"
        assert (
            average_env_time < 15.0
        ), f"Average environment time too high: {average_env_time:.1f}s"

        # Memory usage should be manageable even with all environments
        assert (
            memory_metrics["increase_mb"] < 500
        ), f"Memory usage too high: {memory_metrics['increase_mb']:.1f}MB"
        assert (
            memory_metrics["peak_mb"] < 1000
        ), f"Peak memory too high: {memory_metrics['peak_mb']:.1f}MB"

        # Operations should complete successfully
        expected_min_operations = (
            len(environments) * service_count
        )  # At least one operation per env per service
        assert (
            total_operations >= expected_min_operations
        ), f"Not enough operations completed: {total_operations} < {expected_min_operations}"

        print(f"\nMemory Intensive Combination Stress Test:")
        print(f"  Environments: {len(environments)}")
        print(f"  Services per environment: {service_count}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Average environment time: {average_env_time:.1f}s")
        print(f"  Total operations: {total_operations}")
        print(f"  Memory usage: {memory_metrics['increase_mb']:.1f}MB")
        print(f"  Peak memory: {memory_metrics['peak_mb']:.1f}MB")

    @pytest.mark.slow
    def test_repeated_setup_teardown_cycle(self, temp_output_dir):
        """Stress test with repeated setup/teardown cycles to check for memory leaks."""
        cycles = 50
        services_per_cycle = 20
        config = GperfCpuEnvironment

        memory_snapshots = []
        cycle_times = []

        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        for cycle in range(cycles):
            gc.collect()  # Force garbage collection

            # Create fresh services for this cycle
            services = create_mock_services(services_per_cycle)
            event_manager = EventManager()

            # Initialize environment
            env = GperfCpuEnvironment(
                env_config_to_test=GperfCpuConfig(),
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="gperf_cpu",
                event_manager=event_manager,
            )

            # Mock operations
            def mock_register(*args):
                pass

            def mock_modify(*args):
                return {"success": True}

            env.register_output_file = mock_register
            env.modify_service_commands = mock_modify

            # Time this cycle
            cycle_start = time.perf_counter()
            env._setup_plugin_specific_environment(services, f"cycle_{cycle:03d}")
            cycle_end = time.perf_counter()

            cycle_times.append(cycle_end - cycle_start)

            # Clear references to allow garbage collection
            del env
            del services
            del event_manager

            # Monitor memory every 10 cycles
            if cycle % 10 == 0:
                gc.collect()
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                memory_snapshots.append(current_memory)

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # Analyze results
        average_cycle_time = statistics.mean(cycle_times)
        memory_increase = final_memory - initial_memory

        # Performance requirements
        assert (
            average_cycle_time < 1.0
        ), f"Cycle time too high: {average_cycle_time:.3f}s"

        # Memory leak detection
        # Allow some memory increase but it shouldn't be excessive
        max_acceptable_increase = 50  # MB
        assert (
            memory_increase < max_acceptable_increase
        ), f"Possible memory leak: {memory_increase:.1f}MB increase over {cycles} cycles"

        # Memory growth should not be strictly increasing (evidence of leaks)
        if len(memory_snapshots) > 2:
            memory_trend = []
            for i in range(1, len(memory_snapshots)):
                memory_trend.append(memory_snapshots[i] - memory_snapshots[i - 1])

            # Most measurements should show little to no growth
            stable_measurements = sum(
                1 for diff in memory_trend if diff < 2.0
            )  # < 2MB growth
            stability_ratio = stable_measurements / len(memory_trend)

            assert (
                stability_ratio > 0.7
            ), f"Memory growth too consistent, possible leak: {stability_ratio:.2f}"

        print(f"\nRepeated Setup/Teardown Stress Test:")
        print(f"  Cycles: {cycles}")
        print(f"  Services per cycle: {services_per_cycle}")
        print(f"  Average cycle time: {average_cycle_time:.3f}s")
        print(f"  Memory increase: {memory_increase:.1f}MB")
        print(f"  Final memory: {final_memory:.1f}MB")
        print(f"  Memory snapshots: {memory_snapshots}")
