"""
Comprehensive pytest configuration and fixtures for PANTHER testing.

This module provides shared fixtures and utilities for testing all aspects
of the PANTHER framework, including mocked dependencies, temporary environments,
and test data generation strategies.
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

# Suppress Docker warnings for tests
logging.getLogger("docker").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Conditionally enable the metrics plugin (skip if running with -p no:panther_metrics)
import sys

if not any("no:panther_metrics" in arg for arg in sys.argv):
    try:
        import panther.metrics.pytest_plugin

        pytest_plugins = ["panther.metrics.pytest_plugin"]
    except ImportError:
        # Plugin not available, skip loading
        pass


# ===== PYTEST CONFIGURATION =====


def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "requires_docker: marks tests that require Docker daemon"
    )
    config.addinivalue_line(
        "markers", "requires_network: marks tests that require network access"
    )


# ===== CORE FIXTURES =====


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "tests_ressources"


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that gets cleaned up."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


# ===== CONFIG FIXTURES =====


@pytest.fixture
def sample_global_config_dict():
    """Provide a minimal valid global configuration as dictionary."""
    return {
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
        },
        "paths": {
            "output_dir": "panther/outputs",
            "log_dir": "panther/outputs",
            "config_dir": "panther/configs",
            "plugin_dir": "panther/plugins",
            "services_dir": "services",
            "iut_dir": "iut",
            "testers_dir": "testers",
        },
        "optional_paths": {
            "exec_env_dir": "",
            "net_env_dir": "",
            "iut_dir": "",
            "testers_dir": "",
        },
        "docker": {
            "build_docker_image": True,
            "remove_docker_image": True,
            "remove_docker_container": True,
            "remove_docker_network": True,
            "remove_docker_volume": True,
        },
        "features": {
            "logger_observer": True,
            "storage_handler": True,
            "fast_fail": True,
        },
    }


@pytest.fixture
def sample_experiment_config():
    """Provide a minimal valid experiment configuration."""
    return {
        "name": "test_experiment",
        "description": "Test experiment description",
        "network_environment": {"type": "localhost_container"},
        "execution_environment": [{"type": "basic"}],
        "iterations": 1,
        "services": {
            "test_service": {
                "name": "test_service",
                "timeout": 100,
                "implementation": {
                    "name": "test_impl",
                    "type": "iut",
                    "shadow_compatible": False,
                    "gperf_compatible": False,
                },
                "protocol": {
                    "name": "test_protocol",
                    "version": "1.0",
                    "role": "client",
                    "target": "server",
                    "protocol_type": "client_server",
                },
                "ports": [],
                "generate_new_certificates": False,
                "volumes": [],
                "directories_to_start": [],
            }
        },
        "steps": None,
        "assertions": None,
    }


@pytest.fixture
def valid_cfg_dict():
    """Provide a valid global configuration dictionary."""
    return {
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "paths": {
            "output_dir": "/tmp/panther/outputs",
            "log_dir": "/tmp/panther/logs",
            "config_dir": "/tmp/panther/configs",
            "plugin_dir": "/tmp/panther/plugins",
        },
        "docker": {
            "build_docker_image": True,
            "remove_docker_image": False,
            "remove_docker_container": True,
            "remove_docker_network": True,
            "remove_docker_volume": False,
        },
        "features": {
            "logger_observer": True,
            "storage_handler": True,
            "fast_fail": False,
        },
    }


@pytest.fixture
def valid_experiment_cfg_dict():
    """Provide a valid experiment configuration dictionary."""
    return {
        "tests": [
            {
                "name": "test_basic_functionality",
                "description": "Basic functionality test",
                "network_environment": {"type": "docker_compose", "version": "3.8"},
                "execution_environment": [{"type": "localhost", "timeout": 300}],
                "iterations": 5,
                "services": {
                    "test_service": {
                        "name": "test_service",
                        "implementation": {"name": "test_impl", "type": "iut"},
                        "protocol": {
                            "name": "test_protocol",
                            "version": "1.0",
                            "role": "client",
                        },
                        "ports": [8080, 8081],
                        "timeout": 30,
                        "generate_new_certificates": False,
                    }
                },
                "steps": {"wait": 10, "record_pcap": True},
                "assertions": [
                    {
                        "type": "service_responsive",
                        "service": "test_service",
                        "endpoint": "/health",
                        "expected_status": 200,
                    }
                ],
            }
        ]
    }


@pytest.fixture
def minimal_cfg_dict():
    """Provide a minimal configuration dictionary for testing defaults."""
    return {"logging": {"level": "INFO"}}


@pytest.fixture
def empty_cfg_dict():
    """Provide an empty configuration dictionary for testing error handling."""
    return {}


# ===== PLUGIN FIXTURES =====


@pytest.fixture
def mock_plugin_directory(temp_dir):
    """Create a temporary plugin directory with test plugins."""
    plugin_dir = temp_dir / "plugins"
    plugin_dir.mkdir()

    # Create a dummy plugin
    dummy_plugin = plugin_dir / "dummy_plugin.py"
    dummy_plugin.write_text(
        """
class DummyPlugin:
    def __init__(self):
        self.name = "dummy"

    def run(self):
        return "dummy_result"
"""
    )

    # Create plugin metadata
    metadata_file = plugin_dir / "plugin.yaml"
    metadata_file.write_text(
        """
name: dummy_plugin
version: 1.0.0
type: test
description: Test plugin for testing
"""
    )

    yield plugin_dir


@pytest.fixture
def mock_service_plugin():
    """Provide a mock service plugin."""
    plugin = Mock()
    plugin.name = "test_service"
    plugin.run.return_value = {"success": True, "output": "test output"}
    plugin.validate_config.return_value = True
    plugin.setup.return_value = None
    plugin.teardown.return_value = None
    return plugin


@pytest.fixture
def mock_environment_plugin():
    """Provide a mock environment plugin."""
    plugin = Mock()
    plugin.name = "test_environment"
    plugin.setup_environment.return_value = {"env_var": "value"}
    plugin.cleanup_environment.return_value = None
    plugin.is_available.return_value = True
    return plugin


# ===== DOCKER FIXTURES =====


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for BuildManager tests."""
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.version.return_value = {
        "Version": "20.10.0",
        "ApiVersion": "1.41",
        "Platform": {"Name": "Docker Engine - Community"},
    }

    # Mock images
    mock_client.images.build.return_value = (Mock(), [])
    mock_client.images.get.return_value = Mock()
    mock_client.images.remove.return_value = True

    # Mock containers
    mock_client.containers.run.return_value = Mock()
    mock_client.containers.list.return_value = []

    return mock_client


@pytest.fixture
def mock_docker_unavailable():
    """Mock Docker as unavailable for testing fallback behavior."""
    with patch("docker.from_env") as mock_docker:
        mock_docker.side_effect = Exception("Docker not available")
        yield


# ===== NETWORK & SYSTEM FIXTURES =====


@pytest.fixture
def mock_network_calls():
    """Mock all network-related calls."""
    with patch("requests.get") as mock_get, patch("requests.post") as mock_post, patch(
        "socket.socket"
    ) as mock_socket:
        # Mock successful HTTP responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.text = "success"

        mock_get.return_value = mock_response
        mock_post.return_value = mock_response

        yield {"get": mock_get, "post": mock_post, "socket": mock_socket}


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for command execution tests."""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "Command executed successfully"
    mock_result.stderr = ""
    mock_result.check_returncode.return_value = None
    return mock_result


# ===== FILE SYSTEM FIXTURES =====


@pytest.fixture
def temp_experiment_directory(temp_dir, sample_experiment_config):
    """Create a temporary experiment directory with sample files."""
    exp_dir = temp_dir / "experiment"
    exp_dir.mkdir()

    # Create config file
    config_file = exp_dir / "experiment_config.yaml"
    config_file.write_text(yaml.dump(sample_experiment_config))

    # Create logs directory
    logs_dir = exp_dir / "logs"
    logs_dir.mkdir()

    yield exp_dir


@pytest.fixture
def mock_file_system():
    """Mock file system operations for builder tests."""
    with patch("pathlib.Path.exists", return_value=True), patch(
        "pathlib.Path.is_dir", return_value=True
    ), patch("pathlib.Path.is_file", return_value=True), patch(
        "pathlib.Path.glob"
    ) as mock_glob, patch(
        "pathlib.Path.unlink"
    ) as mock_unlink, patch(
        "pathlib.Path.rmdir"
    ) as mock_rmdir:
        mock_glob.return_value = []
        yield {"glob": mock_glob, "unlink": mock_unlink, "rmdir": mock_rmdir}


# ===== TIME & RANDOM FIXTURES =====


@pytest.fixture
def freeze_time():
    """Freeze time for deterministic testing."""
    with patch("time.time") as mock_time, patch("time.sleep") as mock_sleep:
        mock_time.return_value = 1640995200.0  # 2022-01-01 00:00:00 UTC

        yield {"time": mock_time, "sleep": mock_sleep}


@pytest.fixture
def deterministic_random():
    """Provide deterministic random values for testing."""
    with patch("random.random") as mock_random, patch("random.choice") as mock_choice:
        mock_random.return_value = 0.5
        mock_choice.return_value = "test_choice"

        yield {"random": mock_random, "choice": mock_choice}


# ===== PYTEST MARKS & HELPERS =====


def pytest_runtest_setup(item):
    """Consolidated setup function called for each test item."""
    # Skip Docker tests if Docker is not available
    if "requires_docker" in item.keywords:
        try:
            import docker

            docker.from_env().ping()
        except Exception:
            pytest.skip("Docker daemon not available")

    # Skip network tests if network is not available
    if "requires_network" in item.keywords:
        try:
            import socket

            socket.create_connection(("8.8.8.8", 53), timeout=3)
        except OSError:
            pytest.skip("Network not available")

    # Skip slow tests unless explicitly requested
    if "slow" in item.keywords and not item.config.getoption(
        "--run-slow", default=False
    ):
        pytest.skip("slow test skipped (use --run-slow to run)")


# ===== LEGACY COMPATIBILITY =====


@pytest.fixture
def mock_plugin_directory_legacy():
    """Legacy fixture for backwards compatibility."""
    with tempfile.TemporaryDirectory() as tempdir:
        plugin_path = os.path.join(tempdir, "dummy_plugin.py")
        with open(plugin_path, "w") as f:
            f.write("class Plugin: pass")
        yield tempdir


# ===== CONFIG TEST FIXTURES =====


@pytest.fixture
def temp_config_dir(temp_dir):
    """Create a temporary directory for config tests."""
    temp_dir = tempfile.mkdtemp(prefix="panther_test_config_")
    config_path = Path(temp_dir)

    # Create config directory structure
    (config_path / "configs").mkdir()
    (config_path / "outputs").mkdir()
    (config_path / "logs").mkdir()
    (config_path / "plugins").mkdir()

    yield config_path

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_global_config_data():
    """Sample global configuration data."""
    return {
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "paths": {
            "output_dir": "/tmp/panther/outputs",
            "log_dir": "/tmp/panther/logs",
            "config_dir": "/tmp/panther/configs",
            "plugin_dir": "/tmp/panther/plugins",
            "services_dir": "services",
            "iut_dir": "iut",
            "testers_dir": "testers",
        },
        "docker": {
            "build_docker_image": True,
            "remove_docker_image": True,
            "remove_docker_container": True,
            "remove_docker_network": True,
            "remove_docker_volume": True,
        },
        "features": {
            "logger_observer": True,
            "storage_handler": True,
            "fast_fail": True,
        },
    }


@pytest.fixture
def sample_experiment_config_data():
    """Sample experiment configuration data."""
    return {
        "tests": [
            {
                "name": "test_web_service",
                "description": "Test web service functionality",
                "network_environment": {
                    "type": "docker_compose",
                    "version": "3.8",
                    "network_name": "test_network",
                },
                "execution_environment": [
                    {"type": "localhost", "timeout": 300, "cpu_cores": 2}
                ],
                "iterations": 3,
                "services": {
                    "web_server": {
                        "name": "nginx",
                        "timeout": 120,
                        "implementation": {"name": "picoquic", "type": "iut"},
                        "protocol": {"name": "quic", "version": "rfc9000"},
                        "ports": ["80", "443"],
                        "generate_new_certificates": False,
                        "volumes": ["/var/www:/var/www"],
                        "directories_to_start": ["/var/www"],
                    },
                    "database": {
                        "name": "postgres",
                        "timeout": 60,
                        "implementation": {"name": "postgres_impl", "type": "iut"},
                        "protocol": {"name": "postgresql", "version": "13"},
                        "ports": ["5432"],
                        "generate_new_certificates": False,
                    },
                },
                "steps": {"wait": 45, "record_pcap": True},
                "assertions": [
                    {
                        "type": "service_responsive",
                        "service": "web_server",
                        "endpoint": "/health",
                        "expected_status": 200,
                    },
                    {
                        "type": "data_integrity",
                        "service": "database",
                        "endpoint": "/status",
                        "expected_status": 200,
                    },
                ],
            },
            {
                "name": "test_load_balancing",
                "description": "Test load balancing functionality",
                "network_environment": {"type": "docker_compose", "version": "3.8"},
                "execution_environment": [{"type": "localhost", "timeout": 180}],
                "iterations": 1,
                "services": {
                    "load_balancer": {
                        "name": "haproxy",
                        "timeout": 90,
                        "ports": ["80", "8080"],
                    }
                },
            },
        ]
    }


@pytest.fixture
def global_config_file(temp_config_dir, sample_global_config_data):
    """Create a global configuration YAML file."""
    config_file = temp_config_dir / "global_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_global_config_data, f)
    return config_file


@pytest.fixture
def experiment_config_file(temp_config_dir, sample_experiment_config_data):
    """Create an experiment configuration YAML file."""
    config_file = temp_config_dir / "experiment_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_experiment_config_data, f)
    return config_file


@pytest.fixture
def config_loader_instance(temp_config_dir):
    """Provide configured ConfigLoader instance."""
    from panther.config.config_manager import ConfigLoader

    return ConfigLoader(config_dir=temp_config_dir)


# ===== CORE FIXTURES =====


@pytest.fixture
def mock_experiment_manager():
    """Mock ExperimentManager for core testing."""
    mock_manager = Mock()
    mock_manager.load_experiment.return_value = True
    mock_manager.run_experiment.return_value = {"status": "success", "results": {}}
    mock_manager.validate_experiment.return_value = True
    mock_manager.get_experiment_status.return_value = "completed"
    mock_manager.cleanup_experiment.return_value = True
    return mock_manager


@pytest.fixture
def mock_plugin_manager():
    """Mock plugin system for core testing."""
    mock_manager = Mock()
    mock_manager.load_plugins.return_value = True
    mock_manager.get_available_plugins.return_value = ["test_plugin", "mock_plugin"]
    mock_manager.execute_plugin.return_value = {"status": "success"}
    mock_manager.validate_plugin.return_value = True
    return mock_manager


@pytest.fixture
def core_experiment_manager_instance(mock_plugin_manager, temp_config_dir):
    """Provide configured ExperimentManager instance."""
    with patch(
        "panther.core.experiment_manager.PluginManager",
        return_value=mock_plugin_manager,
    ):
        from panther.core.experiment_manager import ExperimentManager

        return ExperimentManager(config_dir=temp_config_dir)


# ===== INTEGRATION FIXTURES =====


@pytest.fixture
def integration_workspace(temp_dir):
    """Create complete temporary workspace for integration testing."""
    workspace = temp_dir / "integration_workspace"
    workspace.mkdir()

    # Create comprehensive project structure

    # Source code
    src_dir = workspace / "panther"
    src_dir.mkdir()
    (src_dir / "__init__.py").write_text('__version__ = "0.1.0"')

    # Configuration
    config_dir = workspace / "config"
    config_dir.mkdir()

    global_config = {
        "project_name": "panther_integration_test",
        "version": "0.1.0",
        "description": "Integration test workspace",
    }

    with open(config_dir / "global_config.yaml", "w") as f:
        yaml.dump(global_config, f)

    # Tests directory
    tests_dir = workspace / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").touch()
    (tests_dir / "test_integration.py").write_text(
        """
import pytest

def test_integration_example():
    assert True

def test_integration_math():
    assert 2 + 2 == 4
"""
    )

    # Documentation
    docs_dir = workspace / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Integration Test Documentation")

    # Build configuration
    (workspace / "setup.py").write_text(
        """
from setuptools import setup, find_packages
setup(
    name="panther-integration-test",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["pyyaml>=5.0"],
)
"""
    )

    (workspace / "pyproject.toml").write_text(
        """
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "panther-integration-test"
version = "0.1.0"
dependencies = ["pyyaml>=5.0"]
"""
    )

    # Docker configuration
    (workspace / "Dockerfile").write_text(
        """
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -e .
"""
    )

    # CI configuration
    (workspace / ".github").mkdir()
    (workspace / ".github" / "workflows").mkdir()
    (workspace / ".github" / "workflows" / "ci.yml").write_text(
        """
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      - name: Install dependencies
        run: pip install -e .
      - name: Run tests
        run: pytest
"""
    )

    return workspace


@pytest.fixture
def performance_timer():
    """Provide performance timing utility for tests."""
    import contextlib
    import time

    @contextlib.contextmanager
    def timer(operation_name, max_duration=None):
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            print(f"\n{operation_name} took {duration:.2f} seconds")

            if max_duration and duration > max_duration:
                pytest.fail(
                    f"{operation_name} took {duration:.2f}s, exceeding limit of {max_duration}s"
                )

    return timer


# ===== NETWORK AND EXTERNAL SERVICE FIXTURES =====


@pytest.fixture
def mock_network_service():
    """Mock external network service for testing."""
    mock_service = Mock()
    mock_service.get.return_value = {"status": "ok", "data": "test_response"}
    mock_service.post.return_value = {"status": "created", "id": "test_id"}
    mock_service.is_available.return_value = True
    return mock_service


@pytest.fixture
def mock_docker_registry():
    """Mock Docker registry for container testing."""
    mock_registry = Mock()
    mock_registry.push_image.return_value = True
    mock_registry.pull_image.return_value = True
    mock_registry.list_images.return_value = ["test:latest", "panther:dev"]
    mock_registry.delete_image.return_value = True
    return mock_registry


# ===== ERROR SIMULATION FIXTURES =====


@pytest.fixture
def error_scenarios():
    """Provide various error scenarios for testing."""
    return {
        "subprocess_error": subprocess.CalledProcessError(1, "test_command"),
        "docker_error": Exception("Docker daemon not available"),
        "file_not_found": FileNotFoundError("Required file not found"),
        "permission_error": PermissionError("Permission denied"),
        "network_error": ConnectionError("Network unreachable"),
        "timeout_error": TimeoutError("Operation timed out"),
        "memory_error": MemoryError("Out of memory"),
        "keyboard_interrupt": KeyboardInterrupt("User interrupted"),
    }


# ===== DATA GENERATION FIXTURES =====


@pytest.fixture
def test_data_generator():
    """Provide test data generation utilities."""
    import random
    import string

    class TestDataGenerator:
        @staticmethod
        def random_string(length=10):
            return "".join(
                random.choices(string.ascii_letters + string.digits, k=length)
            )

        @staticmethod
        def random_config():
            return {
                "name": TestDataGenerator.random_string(8),
                "version": f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}",
                "type": random.choice(["test", "performance", "integration"]),
                "parameters": {
                    "duration": random.randint(10, 300),
                    "iterations": random.randint(1, 100),
                },
            }

        @staticmethod
        def random_project_structure(base_path):
            """Generate random project structure for testing."""
            project_path = Path(base_path) / TestDataGenerator.random_string(8)
            project_path.mkdir(exist_ok=True)

            # Create random files
            for i in range(random.randint(1, 5)):
                file_path = project_path / f"file_{i}.py"
                file_path.write_text(
                    f"# Random content {TestDataGenerator.random_string(20)}"
                )

            return project_path

    return TestDataGenerator()


# ===== CLEANUP FIXTURES =====


@pytest.fixture(autouse=True)
def cleanup_test_artifacts(temp_dir):
    """Automatically clean up test artifacts after each test."""
    yield

    # Clean up any leftover Docker containers/images
    try:
        import docker

        client = docker.from_env()

        # Remove test containers
        for container in client.containers.list(all=True):
            if "test" in container.name.lower() or "panther" in container.name.lower():
                try:
                    container.remove(force=True)
                except:
                    pass

        # Remove test images
        for image in client.images.list():
            for tag in image.tags:
                if "test" in tag.lower() or "panther" in tag.lower():
                    try:
                        client.images.remove(image.id, force=True)
                    except:
                        pass
    except:
        pass  # Docker not available or other error


# ===== PYTEST HOOKS =====


def pytest_addoption(parser):
    """Add custom pytest command line options."""
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--run-docker",
        action="store_true",
        default=False,
        help="run tests that require Docker",
    )


# ===== MODERN PANTHER FIXTURES =====


@pytest.fixture
def mock_event_manager():
    """Mock event manager for testing event-driven components."""
    from unittest.mock import Mock

    from panther.core.observer.management.event_manager import EventManager

    return Mock(spec=EventManager)


@pytest.fixture
def mock_command_processor():
    """Mock command processor for testing command generation."""
    from unittest.mock import Mock

    from panther.core.command_processor import CommandProcessor

    return Mock(spec=CommandProcessor)


@pytest.fixture
def sample_service_config():
    """Sample service configuration for testing."""
    return {
        "implementation": {"name": "test_impl", "type": "iut"},
        "protocol": {"name": "test_protocol", "version": "1.0", "role": "client"},
        "timeout": 60,
        "generate_new_certificates": True,
    }


@pytest.fixture
def sample_test_config():
    """Sample test configuration for testing."""
    from panther.config.core.models.experiment import TestConfig

    return TestConfig(
        name="test_case",
        description="Test case description",
        network_environment={"type": "docker_compose"},
        services={},
    )


@pytest.fixture
def sample_global_config():
    """Sample global configuration for testing."""
    from panther.config.core.models.global_config import GlobalConfig

    return GlobalConfig(
        logging={"level": "INFO", "format": "%(levelname)s - %(message)s"},
        paths={"output_dir": "outputs", "log_dir": "outputs/logs"},
        docker={"build_docker_image": False},
    )


# ===== SHARED UTILITIES =====


@pytest.fixture
def assert_file_exists():
    """Utility for asserting file existence."""

    def _assert_file_exists(file_path, should_exist=True):
        path = Path(file_path)
        if should_exist:
            assert path.exists(), f"File {file_path} should exist but doesn't"
        else:
            assert not path.exists(), f"File {file_path} should not exist but does"

    return _assert_file_exists


@pytest.fixture
def assert_command_output():
    """Utility for asserting command output patterns."""

    def _assert_command_output(result, expected_patterns=None, error_patterns=None):
        if expected_patterns:
            for pattern in expected_patterns:
                assert (
                    pattern in result.stdout or pattern in result.stderr
                ), f"Expected pattern '{pattern}' not found in output"

        if error_patterns:
            for pattern in error_patterns:
                assert (
                    pattern not in result.stdout and pattern not in result.stderr
                ), f"Error pattern '{pattern}' found in output"

    return _assert_command_output
