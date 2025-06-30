"""Test execution optimizations and performance enhancements."""
import gc
import os
import sys
import tempfile
import threading
import time
import weakref
from pathlib import Path
from unittest.mock import Mock

import psutil
import pytest

# ===== PERFORMANCE MONITORING =====


@pytest.fixture(scope="session", autouse=True)
def performance_monitor():
    """Monitor test performance and resource usage."""
    start_time = time.time()
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    yield

    end_time = time.time()
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    execution_time = end_time - start_time
    memory_diff = final_memory - initial_memory

    print(f"\\nTest Suite Performance Summary:")
    print(f"  Total execution time: {execution_time:.2f} seconds")
    print(f"  Memory usage change: {memory_diff:+.2f} MB")
    print(f"  Peak memory: {final_memory:.2f} MB")


# ===== FAST MOCK FACTORIES =====


class FastMockFactory:
    """Factory for creating lightweight mocks with caching."""

    _mock_cache = weakref.WeakValueDictionary()
    _lock = threading.Lock()

    @classmethod
    def get_event_manager_mock(cls):
        """Get cached event manager mock."""
        with cls._lock:
            cache_key = "event_manager"
            if cache_key not in cls._mock_cache:
                mock = Mock()
                mock.emit_event = Mock()
                mock.add_observer = Mock()
                mock.remove_observer = Mock()
                cls._mock_cache[cache_key] = mock
            return cls._mock_cache[cache_key]

    @classmethod
    def get_service_manager_mock(cls, service_name="test_service"):
        """Get cached service manager mock."""
        cache_key = f"service_manager_{service_name}"
        with cls._lock:
            if cache_key not in cls._mock_cache:
                mock = Mock()
                mock.service_name = service_name
                mock.generate_commands = Mock(
                    return_value={"run_cmd": {"command_binary": "test", "timeout": 60}}
                )
                mock.validate_config = Mock(return_value=True)
                cls._mock_cache[cache_key] = mock
            return cls._mock_cache[cache_key]

    @classmethod
    def get_command_processor_mock(cls):
        """Get cached command processor mock."""
        with cls._lock:
            cache_key = "command_processor"
            if cache_key not in cls._mock_cache:
                mock = Mock()
                mock.generate_commands = Mock(
                    return_value={"run_cmd": {"command_binary": "test"}}
                )
                mock.validate_command = Mock(return_value=True)
                cls._mock_cache[cache_key] = mock
            return cls._mock_cache[cache_key]


@pytest.fixture
def fast_event_manager():
    """Fast event manager mock using factory cache."""
    return FastMockFactory.get_event_manager_mock()


@pytest.fixture
def fast_service_manager():
    """Fast service manager mock using factory cache."""
    return FastMockFactory.get_service_manager_mock()


@pytest.fixture
def fast_command_processor():
    """Fast command processor mock using factory cache."""
    return FastMockFactory.get_command_processor_mock()


# ===== MEMORY OPTIMIZATION =====


@pytest.fixture(autouse=True)
def memory_cleanup():
    """Automatic memory cleanup after each test."""
    yield
    # Force garbage collection after each test
    gc.collect()


@pytest.fixture(scope="session")
def shared_temp_dir():
    """Shared temporary directory for the entire test session."""
    with tempfile.TemporaryDirectory(prefix="panther_test_session_") as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def fast_temp_dir(shared_temp_dir):
    """Fast temporary directory using shared session directory."""
    test_dir = shared_temp_dir / f"test_{int(time.time() * 1000000)}"
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    # Cleanup handled by session-level fixture


# ===== TEST DATA OPTIMIZATION =====


class TestDataCache:
    """Cache for frequently used test data."""

    _cache = {}

    @classmethod
    def get_sample_config(cls, config_type="basic"):
        """Get cached sample configuration."""
        if config_type not in cls._cache:
            if config_type == "basic":
                cls._cache[config_type] = {
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {
                        "name": "quic",
                        "version": "rfc9000",
                        "role": "server",
                    },
                    "timeout": 60,
                }
            elif config_type == "client":
                cls._cache[config_type] = {
                    "implementation": {"name": "aioquic", "type": "iut"},
                    "protocol": {
                        "name": "quic",
                        "version": "rfc9000",
                        "role": "client",
                    },
                    "timeout": 60,
                }
            elif config_type == "ivy":
                cls._cache[config_type] = {
                    "implementation": {
                        "name": "panther_ivy",
                        "type": "testers",
                        "test": "quic_test",
                    },
                    "protocol": {
                        "name": "quic",
                        "version": "rfc9000",
                        "role": "server",
                    },
                    "timeout": 120,
                }
        return cls._cache[config_type].copy()  # Return copy to prevent mutation


@pytest.fixture
def cached_basic_config():
    """Cached basic service configuration."""
    return TestDataCache.get_sample_config("basic")


@pytest.fixture
def cached_client_config():
    """Cached client service configuration."""
    return TestDataCache.get_sample_config("client")


@pytest.fixture
def cached_ivy_config():
    """Cached Ivy service configuration."""
    return TestDataCache.get_sample_config("ivy")


# ===== PARALLEL EXECUTION OPTIMIZATION =====


def pytest_configure(config):
    """Configure pytest for optimal parallel execution."""
    # Set optimal worker count if not specified
    if config.getoption("--dist", default=None) == "worksteal":
        num_workers = config.getoption("-n", default="auto")
        if num_workers == "auto":
            # Use CPU count but cap at 8 for memory considerations
            optimal_workers = min(os.cpu_count(), 8)
            config.option.numprocesses = optimal_workers


def pytest_collection_modifyitems(config, items):
    """Optimize test collection and ordering."""

    # Sort tests by estimated execution time (fast tests first)
    def test_priority(item):
        # Fast tests: unit tests without external dependencies
        if "unit" in item.keywords and "slow" not in item.keywords:
            return 0
        # Medium tests: integration tests
        elif "integration" in item.keywords:
            return 1
        # Slow tests: e2e, requires_docker, requires_network
        elif any(
            marker in item.keywords
            for marker in ["slow", "requires_docker", "requires_network"]
        ):
            return 2
        # Property-based tests (can be variable)
        elif "property_based" in item.keywords:
            return 1.5
        else:
            return 1

    items.sort(key=test_priority)


# ===== RESOURCE MONITORING =====


class ResourceMonitor:
    """Monitor resource usage during test execution."""

    def __init__(self):
        self.process = psutil.Process()
        self.start_memory = None
        self.peak_memory = 0
        self.start_time = None

    def start_monitoring(self):
        """Start monitoring resources."""
        self.start_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = self.start_memory
        self.start_time = time.time()

    def update_peak_memory(self):
        """Update peak memory usage."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)

    def get_stats(self):
        """Get current resource statistics."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        return {
            "current_memory_mb": current_memory,
            "peak_memory_mb": self.peak_memory,
            "memory_delta_mb": current_memory - (self.start_memory or 0),
            "elapsed_time_s": elapsed_time,
        }


@pytest.fixture(scope="session")
def resource_monitor():
    """Session-scoped resource monitor."""
    monitor = ResourceMonitor()
    monitor.start_monitoring()
    yield monitor


@pytest.fixture(autouse=True)
def track_test_resources(resource_monitor, request):
    """Track resources for individual tests."""
    test_start_time = time.time()
    test_start_memory = psutil.Process().memory_info().rss / 1024 / 1024

    yield

    test_end_time = time.time()
    test_end_memory = psutil.Process().memory_info().rss / 1024 / 1024
    test_duration = test_end_time - test_start_time
    memory_delta = test_end_memory - test_start_memory

    # Update peak memory
    resource_monitor.update_peak_memory()

    # Log slow tests or high memory usage
    if test_duration > 5.0:  # Tests taking more than 5 seconds
        print(f"\\nSLOW TEST: {request.node.nodeid} took {test_duration:.2f}s")

    if memory_delta > 50:  # Tests using more than 50MB
        print(f"\\nHIGH MEMORY: {request.node.nodeid} used {memory_delta:+.2f}MB")


# ===== SELECTIVE TEST EXECUTION =====


def pytest_runtest_setup(item):
    """Optimized test setup with selective execution."""
    # Skip expensive tests in fast mode
    if item.config.getoption("--fast", default=False):
        slow_markers = ["slow", "requires_docker", "requires_network", "e2e"]
        if any(marker in item.keywords for marker in slow_markers):
            pytest.skip("Skipping slow test in fast mode")

    # Skip Docker tests if Docker is not available (optimized check)
    if "requires_docker" in item.keywords:
        if not _is_docker_available():
            pytest.skip("Docker daemon not available")


def pytest_addoption(parser):
    """Add optimization-related command line options."""
    parser.addoption(
        "--fast",
        action="store_true",
        default=False,
        help="Run only fast tests (skip slow, docker, network tests)",
    )
    parser.addoption(
        "--profile",
        action="store_true",
        default=False,
        help="Enable detailed performance profiling",
    )


# ===== UTILITY FUNCTIONS =====


def _is_docker_available():
    """Fast check for Docker availability with caching."""
    if not hasattr(_is_docker_available, "_cached_result"):
        try:
            import docker

            client = docker.from_env()
            client.ping()
            _is_docker_available._cached_result = True
        except Exception:
            _is_docker_available._cached_result = False

    return _is_docker_available._cached_result


# ===== CLEANUP OPTIMIZATIONS =====


@pytest.fixture(scope="session", autouse=True)
def session_cleanup():
    """Session-level cleanup optimizations."""
    yield

    # Clear all caches at end of session
    FastMockFactory._mock_cache.clear()
    TestDataCache._cache.clear()

    # Force final garbage collection
    gc.collect()


# ===== TEST RESULT OPTIMIZATION =====


class OptimizedResultCollector:
    """Optimized result collection for test metrics."""

    def __init__(self):
        self.results = []
        self.summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total_time": 0,
            "average_time": 0,
        }

    def add_result(self, test_name, status, duration):
        """Add test result efficiently."""
        self.results.append({"name": test_name, "status": status, "duration": duration})

        self.summary["total_tests"] += 1
        self.summary[status] += 1
        self.summary["total_time"] += duration
        self.summary["average_time"] = (
            self.summary["total_time"] / self.summary["total_tests"]
        )

    def get_slow_tests(self, threshold=1.0):
        """Get tests slower than threshold."""
        return [r for r in self.results if r["duration"] > threshold]


@pytest.fixture(scope="session")
def result_collector():
    """Session-scoped result collector."""
    return OptimizedResultCollector()


# ===== PYTEST HOOKS FOR OPTIMIZATION =====


def pytest_runtest_call(pyfuncitem):
    """Optimized test execution with monitoring."""
    # This hook can be used to add custom timing or monitoring
    # Currently just allows normal execution
    pass


def pytest_sessionfinish(session, exitstatus):
    """Session finish with performance summary."""
    if session.config.getoption("--profile", default=False):
        # Print detailed performance summary
        duration = getattr(session, "duration", 0)
        print(f"\\n{'='*60}")
        print(f"PERFORMANCE SUMMARY")
        print(f"{'='*60}")
        print(f"Total session time: {duration:.2f}s")
        print(f"Tests collected: {len(session.items)}")

        if hasattr(session, "testsfailed"):
            print(f"Tests failed: {session.testsfailed}")
        if hasattr(session, "testscollected"):
            print(f"Tests collected: {session.testscollected}")
