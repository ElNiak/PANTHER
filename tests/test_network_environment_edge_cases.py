"""
Comprehensive edge case and stress testing for PANTHER network environments.

This module tests sophisticated failure modes, boundary conditions, and edge cases
identified through codebase analysis including:

- Cascading failure chains and recovery mechanisms
- Resource exhaustion scenarios (memory, disk, file descriptors)
- Port conflict resolution under stress
- Service lifecycle race conditions
- Configuration validation edge cases
- Network failure modes and DNS issues
- Container state management edge cases
- Performance bottlenecks under high load

Test Categories:
- Chaos Engineering: Random failures and resource exhaustion
- Stress Testing: High load, concurrent operations, scaling limits
- Boundary Testing: Resource limits, timeout edges, configuration limits
- Race Condition Testing: Timing-dependent failures
- Failure Recovery Testing: Cascading failures and recovery
"""

import asyncio
import gc
import random
import signal
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from unittest.mock import MagicMock, Mock, patch

import psutil
import pytest

# Hypothesis for property-based edge case testing
from hypothesis import Verbosity, assume, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)

# PANTHER imports
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose_lifecycle_manager import (
    DockerComposeLifecycleManager,
)
from panther.plugins.environments.network_environment.mixins import (
    ConfigurationProcessorMixin,
    ErrorHandlerMixin,
    ServiceHealthCheck,
    ServiceStatus,
    StatusMonitorMixin,
    SubprocessExecutorMixin,
)

# ========== EDGE CASE DATA STRUCTURES ==========


@dataclass
class ResourceExhaustionScenario:
    """Represents a resource exhaustion test scenario."""

    name: str
    resource_type: str
    initial_limit: int
    exhaustion_rate: float
    recovery_threshold: float
    expected_behavior: str


@dataclass
class CascadingFailureStep:
    """Represents a step in a cascading failure scenario."""

    component: str
    failure_type: str
    trigger_delay: float
    impact_radius: List[str]
    recovery_possible: bool


@dataclass
class RaceConditionScenario:
    """Represents a race condition test scenario."""

    name: str
    concurrent_operations: List[str]
    timing_window_ms: int
    expected_winner: Optional[str]
    failure_probability: float


# ========== CHAOS ENGINEERING UTILITIES ==========


class ChaosInjector:
    """Utility for injecting controlled chaos into test scenarios."""

    def __init__(self, failure_rate=0.1, max_delay=0.5):
        self.failure_rate = failure_rate
        self.max_delay = max_delay
        self.active_failures = set()

    def maybe_fail(self, operation_name: str, failure_type: str = "random"):
        """Randomly inject failures based on configuration."""
        if random.random() < self.failure_rate:
            self.active_failures.add(operation_name)
            if failure_type == "timeout":
                time.sleep(random.uniform(0.1, self.max_delay))
                raise TimeoutError(f"Chaos timeout in {operation_name}")
            elif failure_type == "connection":
                raise ConnectionError(f"Chaos connection failure in {operation_name}")
            elif failure_type == "resource":
                raise OSError(f"Chaos resource exhaustion in {operation_name}")
            else:
                raise RuntimeError(f"Chaos failure in {operation_name}")

    def recover_failure(self, operation_name: str):
        """Recover from a previously injected failure."""
        self.active_failures.discard(operation_name)


class ResourceMonitor:
    """Monitor system resources during stress testing."""

    def __init__(self):
        self.baseline_memory = psutil.virtual_memory().used
        self.baseline_cpu = psutil.cpu_percent()
        self.peak_memory = self.baseline_memory
        self.peak_cpu = self.baseline_cpu
        self.monitoring = False
        self.samples = []

    def start_monitoring(self):
        """Start background resource monitoring."""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring and return resource statistics."""
        self.monitoring = False
        if hasattr(self, "monitor_thread"):
            self.monitor_thread.join()

        return {
            "baseline_memory_mb": self.baseline_memory / (1024 * 1024),
            "peak_memory_mb": self.peak_memory / (1024 * 1024),
            "memory_increase_mb": (self.peak_memory - self.baseline_memory)
            / (1024 * 1024),
            "peak_cpu_percent": self.peak_cpu,
            "sample_count": len(self.samples),
        }

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self.monitoring:
            memory = psutil.virtual_memory().used
            cpu = psutil.cpu_percent()

            self.peak_memory = max(self.peak_memory, memory)
            self.peak_cpu = max(self.peak_cpu, cpu)

            self.samples.append(
                {"timestamp": time.time(), "memory": memory, "cpu": cpu}
            )

            time.sleep(0.1)


@contextmanager
def resource_limit_context(memory_limit_mb=None, file_limit=None):
    """Context manager to temporarily limit system resources."""
    original_limits = {}

    try:
        # Note: Actual resource limiting would require system-level changes
        # This is a placeholder for resource constraint testing
        if memory_limit_mb:
            # In real implementation, would use cgroups or similar
            pass

        if file_limit:
            # In real implementation, would set ulimit or similar
            pass

        yield

    finally:
        # Restore original limits
        pass


# ========== BOUNDARY CONDITION TESTS ==========


@pytest.mark.boundary
class TestNetworkEnvironmentBoundaryConditions:
    """Test boundary conditions and resource limits."""

    def test_port_range_exhaustion_recovery(self):
        """Test behavior when all available ports in range are exhausted."""

        class PortExhaustionEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.allocated_ports = set()
                self.port_range = range(50000, 50010)  # Small range for testing

            def allocate_dynamic_port(self):
                """Simulate dynamic port allocation with exhaustion."""
                for port in self.port_range:
                    if port not in self.allocated_ports:
                        self.allocated_ports.add(port)
                        return port
                raise RuntimeError("No ports available in range")

            def release_port(self, port):
                """Release a previously allocated port."""
                self.allocated_ports.discard(port)

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

        env = PortExhaustionEnv()
        allocated_ports = []

        # Allocate all ports in range
        for i in range(10):
            port = env.allocate_dynamic_port()
            allocated_ports.append(port)

        # Next allocation should fail
        with pytest.raises(RuntimeError, match="No ports available"):
            env.allocate_dynamic_port()

        # Release some ports and verify recovery
        env.release_port(allocated_ports[0])
        env.release_port(allocated_ports[1])

        # Should be able to allocate again
        new_port = env.allocate_dynamic_port()
        assert new_port in [allocated_ports[0], allocated_ports[1]]

    @given(st.integers(min_value=1, max_value=1000))
    @settings(max_examples=20)
    def test_service_count_scaling_properties(self, service_count):
        """Property: Environment should handle varying service counts gracefully."""
        assume(service_count <= 100)  # Reasonable limit for testing

        class ScalingTestEnv(BaseNetworkEnvironment):
            def __init__(self, max_services=100):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.max_services = max_services
                self.services = {}

            def add_services_batch(self, count):
                """Add a batch of services and measure performance."""
                start_time = time.time()

                for i in range(count):
                    if len(self.services) >= self.max_services:
                        raise RuntimeError(
                            f"Maximum service limit ({self.max_services}) exceeded"
                        )

                    service_name = f"service_{i}"
                    self.services[service_name] = {
                        "id": i,
                        "port": 8000 + i,
                        "status": "created",
                    }

                duration = time.time() - start_time
                return duration

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

        env = ScalingTestEnv()

        # Property: Service addition should complete without errors
        duration = env.add_services_batch(service_count)

        # Property: All services should be registered
        assert len(env.services) == service_count

        # Property: Performance should be reasonable (< 100ms per service)
        assert duration < (service_count * 0.1)

    def test_environment_variable_resolution_depth_limit(self):
        """Test environment variable resolution with deep nesting and circular references."""

        class VariableResolutionEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.max_resolution_depth = 10

            def resolve_variables_with_depth_limit(self, variables):
                """Resolve variables with protection against infinite recursion."""
                resolved = {}
                resolution_stack = []

                def resolve_value(key, value, depth=0):
                    if depth > self.max_resolution_depth:
                        raise RuntimeError(
                            f"Variable resolution depth limit exceeded for {key}"
                        )

                    if key in resolution_stack:
                        # Circular reference detected
                        return f"${{CIRCULAR_REF_{key}}}"

                    if not isinstance(value, str) or "${" not in value:
                        return value

                    resolution_stack.append(key)

                    # Simple variable substitution logic
                    result = value
                    for var_name, var_value in variables.items():
                        placeholder = f"${{{var_name}}}"
                        if placeholder in result:
                            resolved_var = resolve_value(var_name, var_value, depth + 1)
                            result = result.replace(placeholder, str(resolved_var))

                    resolution_stack.remove(key)
                    return result

                for key, value in variables.items():
                    resolved[key] = resolve_value(key, value)

                return resolved

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

        env = VariableResolutionEnv()

        # Test deep nesting (should succeed within limit)
        deep_vars = {
            "VAR_1": "${VAR_2}",
            "VAR_2": "${VAR_3}",
            "VAR_3": "${VAR_4}",
            "VAR_4": "${VAR_5}",
            "VAR_5": "final_value",
        }

        resolved = env.resolve_variables_with_depth_limit(deep_vars)
        assert resolved["VAR_1"] == "final_value"

        # Test circular reference (should be handled gracefully)
        circular_vars = {
            "VAR_A": "${VAR_B}",
            "VAR_B": "${VAR_A}",
            "VAR_C": "normal_value",
        }

        resolved = env.resolve_variables_with_depth_limit(circular_vars)
        assert "CIRCULAR_REF" in resolved["VAR_A"]
        assert resolved["VAR_C"] == "normal_value"

        # Test depth limit exceeded
        excessive_vars = {}
        for i in range(15):
            excessive_vars[f"VAR_{i}"] = f"${{VAR_{i+1}}}" if i < 14 else "final"

        with pytest.raises(RuntimeError, match="depth limit exceeded"):
            env.resolve_variables_with_depth_limit(excessive_vars)


@pytest.mark.stress
class TestResourceExhaustionScenarios:
    """Test behavior under resource exhaustion conditions."""

    def test_memory_pressure_during_environment_setup(self):
        """Test environment setup behavior under memory pressure."""

        class MemoryStressEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.memory_allocations = []
                self.setup_failed = False

            def setup_with_memory_pressure(self, target_memory_mb=100):
                """Setup environment while allocating memory to create pressure."""
                try:
                    # Allocate memory in chunks to simulate pressure
                    chunk_size = 1024 * 1024  # 1MB chunks
                    chunks_needed = target_memory_mb

                    for i in range(chunks_needed):
                        # Allocate memory chunk
                        chunk = bytearray(chunk_size)
                        # Fill with data to ensure allocation
                        for j in range(0, chunk_size, 1024):
                            chunk[j] = i % 256
                        self.memory_allocations.append(chunk)

                        # Simulate setup work
                        if i % 10 == 0:
                            self._simulate_setup_step(f"step_{i}")

                    return True

                except MemoryError:
                    self.setup_failed = True
                    return False
                finally:
                    # Cleanup memory allocations
                    self.memory_allocations.clear()
                    gc.collect()

            def _simulate_setup_step(self, step_name):
                """Simulate a setup step that might fail under memory pressure."""
                # Simulate some processing
                temp_data = [i for i in range(1000)]
                return len(temp_data) > 0

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

        monitor = ResourceMonitor()
        monitor.start_monitoring()

        env = MemoryStressEnv()

        # Test with moderate memory pressure (should succeed)
        result = env.setup_with_memory_pressure(target_memory_mb=50)
        assert result is True
        assert not env.setup_failed

        # Test with high memory pressure (might fail gracefully)
        result = env.setup_with_memory_pressure(target_memory_mb=200)
        # Either succeeds or fails gracefully without crashing
        assert isinstance(result, bool)

        stats = monitor.stop_monitoring()

        # Verify memory was properly released
        assert (
            stats["memory_increase_mb"] < 100
        )  # Should not have persistent memory leak

    def test_file_descriptor_exhaustion_handling(self):
        """Test handling of file descriptor exhaustion during operations."""

        class FileDescriptorTestEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.open_files = []
                self.operations_completed = 0

            def perform_file_operations_with_limit(self, max_operations=100):
                """Perform file operations until limit is reached."""
                try:
                    for i in range(max_operations):
                        # Create temporary file
                        temp_file = tempfile.NamedTemporaryFile(delete=False)
                        self.open_files.append(temp_file)

                        # Write some data
                        temp_file.write(f"Test data {i}\n".encode())
                        temp_file.flush()

                        self.operations_completed = i + 1

                        # Simulate reaching file descriptor limit
                        if len(self.open_files) > 50:  # Artificial limit for testing
                            raise OSError("Too many open files")

                    return True

                except OSError as e:
                    if "Too many open files" in str(e):
                        return False
                    raise
                finally:
                    # Cleanup open files
                    for temp_file in self.open_files:
                        try:
                            temp_file.close()
                            Path(temp_file.name).unlink(missing_ok=True)
                        except:
                            pass
                    self.open_files.clear()

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

        env = FileDescriptorTestEnv()

        # Should handle file descriptor exhaustion gracefully
        result = env.perform_file_operations_with_limit(max_operations=100)

        # Verify graceful handling
        assert env.operations_completed > 0  # Some operations completed
        assert env.operations_completed <= 100  # Didn't exceed limit
        assert len(env.open_files) == 0  # All files were cleaned up


@pytest.mark.race_conditions
class TestConcurrencyRaceConditions:
    """Test race conditions in concurrent operations."""

    def test_port_allocation_race_condition(self):
        """Test race conditions in concurrent port allocation."""

        class ConcurrentPortManager:
            def __init__(self):
                self.allocated_ports = set()
                self.allocation_lock = threading.Lock()
                self.allocation_attempts = []

            def allocate_port_thread_safe(self, preferred_port=None):
                """Thread-safe port allocation."""
                with self.allocation_lock:
                    if preferred_port and preferred_port not in self.allocated_ports:
                        self.allocated_ports.add(preferred_port)
                        return preferred_port

                    # Find next available port
                    for port in range(50000, 60000):
                        if port not in self.allocated_ports:
                            self.allocated_ports.add(port)
                            return port

                    raise RuntimeError("No ports available")

            def allocate_port_unsafe(self, preferred_port=None):
                """Non-thread-safe port allocation (for testing race conditions)."""
                # Simulate race condition with small delay
                time.sleep(0.001)

                if preferred_port and preferred_port not in self.allocated_ports:
                    self.allocated_ports.add(preferred_port)
                    return preferred_port

                # Find next available port
                for port in range(50000, 60000):
                    if port not in self.allocated_ports:
                        # Simulate race condition window
                        time.sleep(0.001)
                        if port not in self.allocated_ports:  # Check again
                            self.allocated_ports.add(port)
                            return port

                raise RuntimeError("No ports available")

            def release_port(self, port):
                """Release a port."""
                with self.allocation_lock:
                    self.allocated_ports.discard(port)

        # Test thread-safe allocation
        manager = ConcurrentPortManager()

        def allocate_worker(manager, results, worker_id):
            """Worker function for concurrent allocation."""
            try:
                port = manager.allocate_port_thread_safe()
                results[worker_id] = port
            except Exception as e:
                results[worker_id] = str(e)

        # Run concurrent allocations
        results = {}
        threads = []

        for i in range(10):
            thread = threading.Thread(
                target=allocate_worker, args=(manager, results, i)
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify no duplicate ports allocated
        allocated_ports = [port for port in results.values() if isinstance(port, int)]
        assert len(allocated_ports) == len(set(allocated_ports))  # No duplicates
        assert len(allocated_ports) == 10  # All allocations succeeded

    def test_environment_setup_teardown_race(self):
        """Test race conditions between setup and teardown operations."""

        class RaceConditionEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.setup_in_progress = False
                self.teardown_in_progress = False
                self.services_running = []
                self.operation_log = []
                self.lock = threading.Lock()

            def setup_environment_async(self):
                """Asynchronous environment setup."""
                with self.lock:
                    if self.teardown_in_progress:
                        raise RuntimeError("Cannot setup during teardown")
                    self.setup_in_progress = True
                    self.operation_log.append(("setup_start", time.time()))

                try:
                    # Simulate setup work
                    for i in range(5):
                        time.sleep(0.01)  # Simulate setup delay
                        service_name = f"service_{i}"

                        with self.lock:
                            if self.teardown_in_progress:
                                raise RuntimeError("Teardown started during setup")
                            self.services_running.append(service_name)
                            self.operation_log.append(
                                ("service_started", service_name, time.time())
                            )

                    with self.lock:
                        self.setup_in_progress = False
                        self.operation_log.append(("setup_complete", time.time()))

                    return True

                except Exception as e:
                    with self.lock:
                        self.setup_in_progress = False
                        self.operation_log.append(("setup_failed", str(e), time.time()))
                    raise

            def teardown_environment_async(self):
                """Asynchronous environment teardown."""
                with self.lock:
                    if self.setup_in_progress:
                        # Allow teardown to interrupt setup
                        pass
                    self.teardown_in_progress = True
                    self.operation_log.append(("teardown_start", time.time()))

                try:
                    # Stop services in reverse order
                    services_to_stop = self.services_running.copy()

                    for service_name in reversed(services_to_stop):
                        time.sleep(0.01)  # Simulate teardown delay

                        with self.lock:
                            if service_name in self.services_running:
                                self.services_running.remove(service_name)
                                self.operation_log.append(
                                    ("service_stopped", service_name, time.time())
                                )

                    with self.lock:
                        self.teardown_in_progress = False
                        self.operation_log.append(("teardown_complete", time.time()))

                    return True

                except Exception as e:
                    with self.lock:
                        self.teardown_in_progress = False
                        self.operation_log.append(
                            ("teardown_failed", str(e), time.time())
                        )
                    raise

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

        env = RaceConditionEnv()

        # Test race condition: setup and teardown starting simultaneously
        setup_result = None
        teardown_result = None

        def run_setup():
            nonlocal setup_result
            try:
                setup_result = env.setup_environment_async()
            except Exception as e:
                setup_result = str(e)

        def run_teardown():
            nonlocal teardown_result
            try:
                # Start teardown shortly after setup
                time.sleep(0.02)
                teardown_result = env.teardown_environment_async()
            except Exception as e:
                teardown_result = str(e)

        setup_thread = threading.Thread(target=run_setup)
        teardown_thread = threading.Thread(target=run_teardown)

        setup_thread.start()
        teardown_thread.start()

        setup_thread.join()
        teardown_thread.join()

        # Verify consistent final state
        assert len(env.services_running) == 0  # All services should be stopped
        assert not env.setup_in_progress
        assert not env.teardown_in_progress

        # Verify operation log shows consistent sequence
        setup_events = [op for op in env.operation_log if op[0].startswith("setup")]
        teardown_events = [
            op for op in env.operation_log if op[0].startswith("teardown")
        ]

        assert len(setup_events) >= 1  # At least setup_start
        assert len(teardown_events) >= 2  # teardown_start and teardown_complete


@pytest.mark.chaos
class TestChaosEngineeringScenarios:
    """Chaos engineering tests for failure resilience."""

    def test_random_container_kills_during_operations(self):
        """Test resilience to random container termination during operations."""

        class ChaosResistantEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.containers = {}
                self.chaos_injector = ChaosInjector(failure_rate=0.3)
                self.recovery_attempts = 0
                self.max_recovery_attempts = 3

            def deploy_service_with_chaos(self, service_name):
                """Deploy service with potential chaos injection."""
                try:
                    # Simulate container deployment
                    self.chaos_injector.maybe_fail(
                        f"deploy_{service_name}", "connection"
                    )

                    container_id = (
                        f"container_{service_name}_{random.randint(1000, 9999)}"
                    )
                    self.containers[service_name] = {
                        "id": container_id,
                        "status": "running",
                        "restarts": 0,
                    }

                    return container_id

                except Exception as e:
                    # Attempt recovery
                    if self.recovery_attempts < self.max_recovery_attempts:
                        self.recovery_attempts += 1
                        return self.deploy_service_with_chaos(service_name)
                    raise

            def simulate_container_kill(self, service_name):
                """Simulate unexpected container termination."""
                if service_name in self.containers:
                    self.containers[service_name]["status"] = "killed"
                    return True
                return False

            def recover_killed_container(self, service_name):
                """Attempt to recover from killed container."""
                if (
                    service_name in self.containers
                    and self.containers[service_name]["status"] == "killed"
                ):
                    # Simulate restart
                    self.containers[service_name]["status"] = "running"
                    self.containers[service_name]["restarts"] += 1
                    return True
                return False

            def get_system_health(self):
                """Get overall system health status."""
                if not self.containers:
                    return {"status": "empty", "running": 0, "killed": 0}

                running = sum(
                    1 for c in self.containers.values() if c["status"] == "running"
                )
                killed = sum(
                    1 for c in self.containers.values() if c["status"] == "killed"
                )

                status = (
                    "healthy"
                    if killed == 0
                    else "degraded"
                    if running > 0
                    else "critical"
                )

                return {
                    "status": status,
                    "running": running,
                    "killed": killed,
                    "total": len(self.containers),
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

        env = ChaosResistantEnv()

        # Deploy multiple services
        services = ["web", "api", "db", "cache", "monitor"]
        deployed_services = []

        for service in services:
            try:
                container_id = env.deploy_service_with_chaos(service)
                deployed_services.append(service)
            except Exception:
                # Some deployments may fail due to chaos
                pass

        # Verify some services deployed successfully
        assert len(deployed_services) > 0

        initial_health = env.get_system_health()
        assert initial_health["status"] in ["healthy", "degraded"]

        # Simulate random container kills
        killed_services = []
        for service in deployed_services[:2]:  # Kill first 2 services
            if env.simulate_container_kill(service):
                killed_services.append(service)

        post_kill_health = env.get_system_health()
        assert post_kill_health["killed"] == len(killed_services)

        # Attempt recovery
        recovered_services = []
        for service in killed_services:
            if env.recover_killed_container(service):
                recovered_services.append(service)

        final_health = env.get_system_health()

        # Verify system can recover
        assert final_health["running"] >= len(recovered_services)

        # Verify restart tracking
        for service in recovered_services:
            assert env.containers[service]["restarts"] > 0

    def test_network_partition_simulation(self):
        """Test behavior during simulated network partitions."""

        class NetworkPartitionEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.network_partitions = {}
                self.service_connections = {}
                self.connection_timeouts = 0

            def create_network_partition(self, service_a, service_b):
                """Simulate network partition between two services."""
                partition_key = tuple(sorted([service_a, service_b]))
                self.network_partitions[partition_key] = True

            def heal_network_partition(self, service_a, service_b):
                """Heal network partition between two services."""
                partition_key = tuple(sorted([service_a, service_b]))
                self.network_partitions.pop(partition_key, None)

            def attempt_connection(self, from_service, to_service, timeout=1.0):
                """Attempt connection between services with partition checking."""
                partition_key = tuple(sorted([from_service, to_service]))

                # Check if network partition exists
                if self.network_partitions.get(partition_key, False):
                    self.connection_timeouts += 1
                    raise ConnectionError(
                        f"Network partition between {from_service} and {to_service}"
                    )

                # Simulate connection delay
                time.sleep(0.01)

                connection_id = (
                    f"conn_{from_service}_{to_service}_{random.randint(100, 999)}"
                )
                self.service_connections[connection_id] = {
                    "from": from_service,
                    "to": to_service,
                    "established": time.time(),
                }

                return connection_id

            def get_connectivity_status(self):
                """Get overall network connectivity status."""
                active_connections = len(self.service_connections)
                active_partitions = len(self.network_partitions)

                return {
                    "connections": active_connections,
                    "partitions": active_partitions,
                    "timeouts": self.connection_timeouts,
                    "status": "healthy" if active_partitions == 0 else "partitioned",
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

        env = NetworkPartitionEnv()
        services = ["web", "api", "db"]

        # Test normal connectivity
        conn1 = env.attempt_connection("web", "api")
        conn2 = env.attempt_connection("api", "db")

        status = env.get_connectivity_status()
        assert status["status"] == "healthy"
        assert status["connections"] == 2
        assert status["partitions"] == 0

        # Create network partition
        env.create_network_partition("api", "db")

        # Test connection failure due to partition
        with pytest.raises(ConnectionError, match="Network partition"):
            env.attempt_connection("api", "db")

        status = env.get_connectivity_status()
        assert status["status"] == "partitioned"
        assert status["partitions"] == 1
        assert status["timeouts"] == 1

        # Test that other connections still work
        conn3 = env.attempt_connection("web", "api")
        assert conn3 is not None

        # Heal partition and verify recovery
        env.heal_network_partition("api", "db")

        conn4 = env.attempt_connection("api", "db")
        assert conn4 is not None

        final_status = env.get_connectivity_status()
        assert final_status["status"] == "healthy"
        assert final_status["partitions"] == 0


# ========== HYPOTHESIS-BASED EDGE CASE TESTING ==========


@pytest.mark.property_based
class TestHypothesisEdgeCases:
    """Property-based testing for edge cases using Hypothesis."""

    @given(
        st.lists(
            st.text(
                min_size=1,
                max_size=50,
                alphabet=st.characters(categories=("Lu", "Ll", "Nd", "Po")),
            ),
            min_size=1,
            max_size=20,
        ),
        st.integers(min_value=1024, max_value=65535),
    )
    @settings(max_examples=30)
    def test_service_name_and_port_edge_cases(self, service_names, base_port):
        """Property: Service names and ports should be handled robustly."""

        class EdgeCaseTestEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.services = {}
                self.port_conflicts = []

            def register_service(self, name, port):
                """Register service with robust name and port handling."""
                # Sanitize service name
                sanitized_name = "".join(
                    c for c in name if c.isalnum() or c in ["_", "-"]
                )
                if not sanitized_name:
                    sanitized_name = f"service_{hash(name) % 10000}"

                # Check port conflicts
                existing_ports = [s["port"] for s in self.services.values()]
                if port in existing_ports:
                    self.port_conflicts.append((sanitized_name, port))
                    # Assign alternative port
                    port = self._find_alternative_port(port, existing_ports)

                self.services[sanitized_name] = {
                    "original_name": name,
                    "port": port,
                    "conflicts": len(self.port_conflicts),
                }

                return sanitized_name, port

            def _find_alternative_port(self, preferred_port, existing_ports):
                """Find alternative port when conflict occurs."""
                for offset in range(1, 100):
                    candidate = preferred_port + offset
                    if candidate <= 65535 and candidate not in existing_ports:
                        return candidate
                raise RuntimeError("Cannot find alternative port")

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

        env = EdgeCaseTestEnv()

        # Property: All service names should be registered successfully
        registered_services = []
        for i, service_name in enumerate(service_names):
            port = base_port + i
            try:
                name, assigned_port = env.register_service(service_name, port)
                registered_services.append((name, assigned_port))
            except Exception as e:
                # Should not fail for any valid input
                pytest.fail(f"Service registration failed for '{service_name}': {e}")

        # Property: No duplicate ports should be assigned
        assigned_ports = [port for _, port in registered_services]
        assert len(assigned_ports) == len(set(assigned_ports))

        # Property: All services should have valid names
        for name, _ in registered_services:
            assert len(name) > 0
            assert all(c.isalnum() or c in ["_", "-"] for c in name)

        # Property: All ports should be in valid range
        for _, port in registered_services:
            assert 1024 <= port <= 65535

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(max_size=100), st.integers(), st.booleans(), st.none()),
            min_size=0,
            max_size=50,
        )
    )
    @settings(max_examples=20)
    def test_configuration_validation_edge_cases(self, config_dict):
        """Property: Configuration validation should handle arbitrary input safely."""

        class ConfigValidationEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "test", "test", Mock())
                self.validation_errors = []
                self.sanitized_config = {}

            def validate_and_sanitize_config(self, config):
                """Validate and sanitize arbitrary configuration input."""
                errors = []
                sanitized = {}

                try:
                    for key, value in config.items():
                        # Validate key
                        if not isinstance(key, str):
                            errors.append(f"Invalid key type: {type(key)}")
                            continue

                        if not key.strip():
                            errors.append("Empty configuration key")
                            continue

                        sanitized_key = key.strip().replace(" ", "_")

                        # Sanitize value based on type
                        if value is None:
                            sanitized_value = ""
                        elif isinstance(value, bool):
                            sanitized_value = "true" if value else "false"
                        elif isinstance(value, (int, float)):
                            sanitized_value = str(value)
                        elif isinstance(value, str):
                            # Limit string length and remove dangerous characters
                            sanitized_value = value[:1000]  # Length limit
                            # Remove null bytes and other problematic characters
                            sanitized_value = "".join(
                                c
                                for c in sanitized_value
                                if ord(c) >= 32 or c in ["\n", "\t"]
                            )
                        else:
                            sanitized_value = str(value)[:1000]

                        sanitized[sanitized_key] = sanitized_value

                except Exception as e:
                    errors.append(f"Validation error: {e}")

                self.validation_errors = errors
                self.sanitized_config = sanitized

                return len(errors) == 0

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

        env = ConfigValidationEnv()

        # Property: Validation should never crash regardless of input
        try:
            is_valid = env.validate_and_sanitize_config(config_dict)
        except Exception as e:
            pytest.fail(f"Configuration validation crashed on input {config_dict}: {e}")

        # Property: Sanitized config should always be safe
        for key, value in env.sanitized_config.items():
            # Keys should be valid identifiers
            assert isinstance(key, str)
            assert len(key) > 0
            assert all(c.isalnum() or c == "_" for c in key)

            # Values should be safe strings
            assert isinstance(value, str)
            assert len(value) <= 1000
            assert "\x00" not in value  # No null bytes

        # Property: Error reporting should be informative
        if not is_valid:
            assert len(env.validation_errors) > 0
            for error in env.validation_errors:
                assert isinstance(error, str)
                assert len(error) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
