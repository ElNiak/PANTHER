"""
Shared fixtures and utilities for execution environment tests.
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock

import pytest

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig


@pytest.fixture
def event_manager():
    """Provide a clean EventManager instance for tests."""
    return EventManager()


@pytest.fixture
def temp_output_dir():
    """Provide a temporary directory for test outputs."""
    temp_dir = tempfile.mkdtemp(prefix="panther_exec_env_test_")
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_docker_client():
    """Provide a mock Docker client for testing."""
    mock_client = Mock()
    mock_container = Mock()
    mock_container.id = "test_container_123"
    mock_container.status = "running"
    mock_container.logs.return_value = b"test output"
    mock_container.wait.return_value = {"StatusCode": 0}

    mock_client.containers.run.return_value = mock_container
    mock_client.containers.get.return_value = mock_container
    mock_client.images.build.return_value = (Mock(), [])
    mock_client.images.get.return_value = Mock()

    return mock_client


@pytest.fixture
def base_environment_config():
    """Provide a basic environment configuration for testing."""
    return EnvironmentConfig(
        type="execution",
        config={
            "timeout": 300,
            "cleanup_on_exit": True,
            "memory_limit": "1g",
            "cpu_limit": 1.0,
        },
    )


@pytest.fixture
def gperf_cpu_config():
    """Provide a gperf_cpu specific configuration."""
    return {
        "type": "gperf_cpu",
        "config": {
            "base_image": "panther/profiling:latest",
            "profiling": {
                "frequency": 100,
                "duration": 60,
                "output_format": "callgrind",
            },
            "analysis": {
                "generate_flamegraph": True,
                "include_kernel": False,
                "filter_functions": ["malloc", "free"],
            },
        },
    }


@pytest.fixture
def gperf_heap_config():
    """Provide a gperf_heap specific configuration."""
    return {
        "type": "gperf_heap",
        "config": {
            "base_image": "panther/profiling:latest",
            "profiling": {
                "sampling_rate": 524288,
                "track_allocations": True,
                "track_deallocations": True,
            },
            "analysis": {
                "generate_heap_dump": True,
                "detect_leaks": True,
                "growth_analysis": True,
            },
        },
    }


@pytest.fixture
def strace_config():
    """Provide a strace specific configuration."""
    return {
        "type": "strace",
        "config": {
            "base_image": "panther/debug:latest",
            "tracing": {
                "trace_children": True,
                "follow_forks": True,
                "syscalls": ["network", "file", "process"],
                "output_format": "json",
            },
            "filtering": {
                "exclude_syscalls": ["clock_gettime", "gettimeofday"],
                "include_only": ["send", "recv", "connect", "bind"],
            },
        },
    }


@pytest.fixture
def helgrind_config():
    """Provide a helgrind specific configuration."""
    return {
        "type": "helgrind",
        "config": {
            "base_image": "panther/valgrind:latest",
            "analysis": {
                "track_lockorders": True,
                "check_races": True,
                "history_level": "full",
            },
            "reporting": {
                "show_reachable": True,
                "leak_check": "full",
                "track_origins": True,
            },
        },
    }


@pytest.fixture
def memcheck_config():
    """Provide a memcheck specific configuration."""
    return {
        "type": "memcheck",
        "config": {
            "base_image": "panther/valgrind:latest",
            "checks": {
                "leak_check": "full",
                "show_reachable": True,
                "track_origins": True,
                "undef_value_errors": True,
            },
            "suppressions": [
                "/app/suppressions/openssl.supp",
                "/app/suppressions/system.supp",
            ],
        },
    }


@pytest.fixture
def iterations_config():
    """Provide an iterations specific configuration."""
    return {
        "type": "iterations",
        "config": {
            "base_environment": "docker_container",
            "iterations": {
                "count": 10,  # Reduced for testing
                "parallel": 2,
                "timeout": 60,  # Reduced for testing
            },
            "statistics": {
                "collect_timing": True,
                "collect_metrics": True,
                "confidence_interval": 0.95,
            },
            "failure_handling": {"continue_on_failure": True, "max_failures": 3},
        },
    }


@pytest.fixture
def mock_service_manager():
    """Provide a mock service manager for testing."""
    manager = Mock()
    manager.get_name.return_value = "test_service"
    manager.get_command.return_value = ["echo", "test"]
    manager.is_running.return_value = False
    manager.start.return_value = True
    manager.stop.return_value = True
    manager.get_logs.return_value = "test logs"
    return manager


@pytest.fixture
def sample_test_files(temp_output_dir):
    """Create sample test files for validation."""
    test_files = {}

    # Create sample CPU profile
    cpu_prof = os.path.join(temp_output_dir, "cpu.prof")
    with open(cpu_prof, "w") as f:
        f.write("sample cpu profile data")
    test_files["cpu_prof"] = cpu_prof

    # Create sample heap profile
    heap_prof = os.path.join(temp_output_dir, "heap.prof")
    with open(heap_prof, "w") as f:
        f.write("sample heap profile data")
    test_files["heap_prof"] = heap_prof

    # Create sample strace output
    strace_log = os.path.join(temp_output_dir, "strace.log")
    with open(strace_log, "w") as f:
        f.write('{"syscall": "write", "fd": 1, "count": 13}\n')
    test_files["strace_log"] = strace_log

    # Create sample valgrind output
    valgrind_log = os.path.join(temp_output_dir, "valgrind.log")
    with open(valgrind_log, "w") as f:
        f.write("==12345== Memcheck, a memory error detector\n")
    test_files["valgrind_log"] = valgrind_log

    return test_files


class MockExecutionEnvironment:
    """Mock execution environment for testing base functionality."""

    def __init__(self, env_config, output_dir, env_type, env_sub_type, event_manager):
        self.env_config_to_test = env_config
        self.output_dir = output_dir
        self.env_type = env_type
        self.env_sub_type = env_sub_type
        self.event_manager = event_manager
        self.services_managers = []
        self.test_config = None

    def setup_environment(self):
        """Mock setup implementation."""
        pass

    def teardown_environment(self):
        """Mock teardown implementation."""
        pass

    def is_network_environment(self):
        """Mock network environment check."""
        return False


@pytest.fixture
def mock_execution_environment(base_environment_config, temp_output_dir, event_manager):
    """Provide a mock execution environment instance."""
    return MockExecutionEnvironment(
        env_config=base_environment_config,
        output_dir=temp_output_dir,
        env_type="execution",
        env_sub_type="mock",
        event_manager=event_manager,
    )


def create_test_config(env_type: str, **overrides) -> Dict[str, Any]:
    """Utility function to create test configurations with overrides."""
    base_config = {
        "type": env_type,
        "config": {
            "timeout": 60,  # Reduced for testing
            "cleanup_on_exit": True,
            "memory_limit": "512m",  # Reduced for testing
            "cpu_limit": 0.5,  # Reduced for testing
        },
    }

    # Apply overrides
    if overrides:
        base_config["config"].update(overrides)

    return base_config


def assert_valid_command(command: str, expected_components: list):
    """Utility to validate generated commands contain expected components."""
    assert isinstance(command, str), f"Command should be string, got {type(command)}"
    assert command.strip(), "Command should not be empty"

    for component in expected_components:
        assert component in command, f"Command missing expected component: {component}"


def assert_environment_lifecycle(env_instance):
    """Utility to test standard environment lifecycle methods."""
    # Test setup
    env_instance.setup_environment()

    # Test teardown
    env_instance.teardown_environment()

    # Test network environment check
    assert not env_instance.is_network_environment()
