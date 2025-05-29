"""
Comprehensive pytest configuration and fixtures for PANTHER testing.

This module provides shared fixtures and utilities for testing all aspects
of the PANTHER framework, including mocked dependencies, temporary environments,
and test data generation strategies.
"""

import pytest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
import logging

# Suppress Docker warnings for tests
logging.getLogger("docker").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


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
def sample_global_config():
    """Provide a minimal valid global configuration."""
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
        "execution_environments": [{"type": "basic"}],
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
    """Provide a mock Docker client."""
    client = Mock()
    client.containers = Mock()
    client.images = Mock()
    client.networks = Mock()
    client.volumes = Mock()

    # Mock container operations
    mock_container = Mock()
    mock_container.id = "test_container_id"
    mock_container.logs.return_value = b"test logs"
    mock_container.wait.return_value = {"StatusCode": 0}
    client.containers.run.return_value = mock_container
    client.containers.get.return_value = mock_container

    return client


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
    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
        patch("socket.socket") as mock_socket,
    ):
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
    """Mock subprocess calls for testing CLI interactions."""
    with patch("subprocess.run") as mock_run, patch("subprocess.Popen") as mock_popen:
        # Mock successful process execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""

        mock_run.return_value = mock_result
        mock_popen.return_value.communicate.return_value = ("output", "")
        mock_popen.return_value.returncode = 0

        yield {"run": mock_run, "popen": mock_popen}


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

    # Create outputs directory
    outputs_dir = exp_dir / "outputs"
    outputs_dir.mkdir()

    yield exp_dir


@pytest.fixture
def mock_file_system():
    """Mock file system operations."""
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("shutil.rmtree") as mock_rmtree,
    ):
        mock_exists.return_value = True

        yield {"exists": mock_exists, "mkdir": mock_mkdir, "rmtree": mock_rmtree}


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
    """Setup function called for each test item."""
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


# ===== LEGACY COMPATIBILITY =====


@pytest.fixture
def mock_plugin_directory_legacy():
    """Legacy fixture for backwards compatibility."""
    with tempfile.TemporaryDirectory() as tempdir:
        plugin_path = os.path.join(tempdir, "dummy_plugin.py")
        with open(plugin_path, "w") as f:
            f.write("class Plugin: pass")
        yield tempdir
