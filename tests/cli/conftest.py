"""Shared test fixtures for CLI Click tests.

Provides common fixtures for testing Click commands including
temporary files, mock configurations, and CLI runner instances.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from click.testing import CliRunner

from panther.cli.core.main import cli


@pytest.fixture
def cli_runner():
    """Create a Click testing CLI runner.

    Returns:
        CliRunner: Configured CLI runner for testing commands
    """
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files.

    Returns:
        Path: Temporary directory path
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config():
    """Sample configuration for testing.

    Returns:
        dict: Sample configuration data
    """
    return {
        "logging": {"level": "INFO", "enable_colors": True},
        "observers": {"logger": {"enabled": True}},
        "paths": {"output_dir": "outputs"},
        "tests": [
            {
                "name": "Test Config",
                "description": "Sample test configuration",
                "network_environment": {"type": "docker_compose"},
                "services": {
                    "server": {
                        "implementation": {"name": "picoquic", "type": "iut"},
                        "protocol": {"name": "quic", "role": "server"},
                    }
                },
            }
        ],
    }


@pytest.fixture
def sample_config_file(temp_dir, sample_config):
    """Create a temporary configuration file.

    Args:
        temp_dir: Temporary directory fixture
        sample_config: Sample configuration data fixture

    Returns:
        Path: Path to temporary configuration file
    """
    config_file = temp_dir / "test_config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_config, f)
    return config_file


@pytest.fixture
def invalid_config_file(temp_dir):
    """Create an invalid configuration file for error testing.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path: Path to invalid configuration file
    """
    config_file = temp_dir / "invalid_config.yaml"
    with open(config_file, "w") as f:
        f.write("invalid: yaml: content:\n  - missing\n  key")
    return config_file


@pytest.fixture
def empty_config_file(temp_dir):
    """Create an empty configuration file.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path: Path to empty configuration file
    """
    config_file = temp_dir / "empty_config.yaml"
    config_file.touch()
    return config_file


@pytest.fixture
def mock_argparse_adapter():
    """Mock argparse adapter for testing compatibility layer.

    Returns:
        Mock: Mocked argparse adapter
    """
    mock_adapter = Mock()
    mock_adapter.handle_with_conversion.return_value = 0
    return mock_adapter


@pytest.fixture
def mock_logging():
    """Mock logging configuration for tests.

    Returns:
        Mock: Mocked logging setup
    """
    with patch("panther.cli.core.base.setup_logging") as mock_log:
        yield mock_log


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls for testing command execution.

    Returns:
        Mock: Mocked subprocess module
    """
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "mocked output"
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def env_vars():
    """Set up environment variables for testing.

    Returns:
        dict: Original environment variables (for restoration)
    """
    original_env = os.environ.copy()
    # Set test environment variables
    os.environ["PANTHER_TEST_MODE"] = "1"
    os.environ["PANTHER_DEBUG"] = "0"

    yield os.environ

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_docker():
    """Mock Docker operations for testing.

    Returns:
        Mock: Mocked Docker client
    """
    with patch("docker.from_env") as mock_docker_client:
        mock_client = Mock()
        mock_docker_client.return_value = mock_client

        # Mock container operations
        mock_client.containers.run.return_value = Mock()
        mock_client.containers.list.return_value = []

        # Mock image operations
        mock_client.images.list.return_value = []
        mock_client.images.pull.return_value = Mock()

        yield mock_client


@pytest.fixture
def mock_git():
    """Mock Git operations for testing.

    Returns:
        Mock: Mocked Git operations
    """
    with patch("subprocess.run") as mock_run:
        # Mock git status output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = (
            "On branch main\nnothing to commit, working tree clean"
        )
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def sample_test_results():
    """Sample test results data for testing metrics and reporting.

    Returns:
        dict: Sample test results
    """
    return {
        "test_name": "Sample Test",
        "start_time": "2023-01-01T00:00:00Z",
        "end_time": "2023-01-01T00:01:00Z",
        "duration": 60.0,
        "status": "success",
        "services": {
            "server": {
                "status": "success",
                "logs": ["Server started", "Connection established"],
                "metrics": {
                    "cpu_usage": 15.2,
                    "memory_usage": 128,
                    "network_bytes_sent": 1024,
                    "network_bytes_received": 512,
                },
            }
        },
        "summary": {
            "total_connections": 1,
            "successful_connections": 1,
            "failed_connections": 0,
            "average_latency": 12.5,
        },
    }


@pytest.fixture
def cli_isolated_filesystem(cli_runner):
    """Create an isolated filesystem for CLI testing.

    Args:
        cli_runner: CLI runner fixture

    Returns:
        CliRunner: CLI runner with isolated filesystem
    """
    with cli_runner.isolated_filesystem():
        yield cli_runner


class ClickTestHelper:
    """Helper class for common Click testing patterns."""

    @staticmethod
    def assert_success(result, expected_output=None):
        """Assert that a CLI command succeeded.

        Args:
            result: Click test result
            expected_output: Optional expected output string
        """
        assert result.exit_code == 0, f"Command failed with output: {result.output}"
        if expected_output:
            assert expected_output in result.output

    @staticmethod
    def assert_failure(result, expected_exit_code=1, expected_error=None):
        """Assert that a CLI command failed.

        Args:
            result: Click test result
            expected_exit_code: Expected exit code (default: 1)
            expected_error: Optional expected error string
        """
        assert (
            result.exit_code == expected_exit_code
        ), f"Expected exit code {expected_exit_code}, got {result.exit_code}"
        if expected_error:
            assert expected_error in result.output

    @staticmethod
    def assert_contains_all(result, *expected_strings):
        """Assert that output contains all expected strings.

        Args:
            result: Click test result
            *expected_strings: Strings that should be in output
        """
        for expected in expected_strings:
            assert (
                expected in result.output
            ), f"Expected '{expected}' in output: {result.output}"


@pytest.fixture
def click_helper():
    """Provide ClickTestHelper instance for tests.

    Returns:
        ClickTestHelper: Helper instance
    """
    return ClickTestHelper()


# Parametrized fixtures for testing different scenarios
@pytest.fixture(params=["minimal", "basic", "advanced", "performance", "security"])
def config_template_type(request):
    """Parametrized fixture for different configuration template types.

    Args:
        request: Pytest request object

    Returns:
        str: Configuration template type
    """
    return request.param


@pytest.fixture(params=["text", "json", "yaml"])
def output_format(request):
    """Parametrized fixture for different output formats.

    Args:
        request: Pytest request object

    Returns:
        str: Output format
    """
    return request.param


@pytest.fixture(params=[True, False])
def debug_mode(request):
    """Parametrized fixture for debug mode testing.

    Args:
        request: Pytest request object

    Returns:
        bool: Debug mode flag
    """
    return request.param


@pytest.fixture(params=[True, False])
def verbose_mode(request):
    """Parametrized fixture for verbose mode testing.

    Args:
        request: Pytest request object

    Returns:
        bool: Verbose mode flag
    """
    return request.param
