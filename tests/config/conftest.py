"""
Shared fixtures and configuration for PANTHER config subsystem tests.

This module provides fixtures for testing configuration loading, validation,
and environment overrides with comprehensive mocking to ensure deterministic,
side-effect-free tests.
"""

import pytest
import os
import yaml
import json
from unittest.mock import Mock, patch
from contextlib import contextmanager

from hypothesis import settings, HealthCheck

# Configure Hypothesis for CI-friendly testing
settings.register_profile(
    "ci",
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("ci")


@pytest.fixture
def valid_cfg_dict():
    """Returns a minimal valid config Python dict."""
    return {
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
        },
        "paths": {
            "output_dir": "outputs",
            "log_dir": "outputs/logs",
            "config_dir": "configs",
            "plugin_dir": "plugins",
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
def valid_experiment_cfg_dict():
    """Returns a minimal valid experiment config dict."""
    return {
        "tests": [
            {
                "name": "test_basic",
                "description": "Basic test case",
                "network_environment": {"type": "docker_compose"},
                "execution_environments": [{"type": "localhost"}],
                "iterations": 1,
                "services": {
                    "test_service": {
                        "implementation": {"name": "test_impl", "version": "1.0.0"},
                        "protocol": {"name": "quic", "version": "v1"},
                    }
                },
                "steps": {"wait": 60, "record_pcap": False},
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
def tmp_cfg_file(tmp_path, valid_cfg_dict):
    """Writes valid_cfg_dict to a temp YAML file and yields its Path."""
    cfg_file = tmp_path / "config.yaml"
    with open(cfg_file, "w") as f:
        yaml.dump(valid_cfg_dict, f, default_flow_style=False)
    return cfg_file


@pytest.fixture
def tmp_experiment_file(tmp_path, valid_experiment_cfg_dict):
    """Writes valid experiment config to a temp YAML file and yields its Path."""
    exp_file = tmp_path / "experiment.yaml"
    with open(exp_file, "w") as f:
        yaml.dump(valid_experiment_cfg_dict, f, default_flow_style=False)
    return exp_file


@pytest.fixture
def tmp_json_file(tmp_path, valid_cfg_dict):
    """Writes valid_cfg_dict to a temp JSON file and yields its Path."""
    cfg_file = tmp_path / "config.json"
    with open(cfg_file, "w") as f:
        json.dump(valid_cfg_dict, f, indent=2)
    return cfg_file


@contextmanager
def mock_env(**env_vars):
    """Context manager that temporarily sets/clears os.environ."""
    original_env = dict(os.environ)
    try:
        # Clear existing vars and set new ones
        os.environ.clear()
        os.environ.update(env_vars)
        yield
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@pytest.fixture
def mock_env_fixture():
    """Fixture wrapper for mock_env context manager."""
    return mock_env


@pytest.fixture
def mock_file_system(tmp_path):
    """Mock file system with known structure for testing."""
    # Create directory structure
    (tmp_path / "panther" / "config").mkdir(parents=True)
    (tmp_path / "panther" / "plugins").mkdir(parents=True)
    (tmp_path / "configs").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "logs").mkdir()

    return tmp_path


@pytest.fixture
def config_loader_mock():
    """Create a mocked ConfigLoader for isolated testing."""
    with patch("panther.config.config_manager.ConfigLoader") as mock_loader:
        instance = Mock()
        mock_loader.return_value = instance
        yield instance


@pytest.fixture
def mock_plugin_directories(tmp_path):
    """Create mock plugin directory structure."""
    plugin_dirs = {
        "exec_env": tmp_path / "exec_env",
        "net_env": tmp_path / "net_env",
        "iut": tmp_path / "iut",
        "testers": tmp_path / "testers",
    }

    for dir_path in plugin_dirs.values():
        dir_path.mkdir(parents=True)
        # Add some dummy files
        (dir_path / "config.yaml").write_text("dummy: config")
        (dir_path / "__init__.py").write_text("# dummy plugin")

    return plugin_dirs


@pytest.fixture
def sample_invalid_configs():
    """Collection of invalid config dictionaries for negative testing."""
    return {
        "missing_logging": {
            "paths": {"output_dir": "outputs"},
            "docker": {"build_docker_image": True},
        },
        "invalid_logging_level": {
            "logging": {"level": "INVALID_LEVEL"},
            "paths": {"output_dir": "outputs"},
            "docker": {"build_docker_image": True},
        },
        "missing_paths": {
            "logging": {"level": "DEBUG"},
            "docker": {"build_docker_image": True},
        },
        "empty_config": {},
        "malformed_docker": {
            "logging": {"level": "DEBUG"},
            "paths": {"output_dir": "outputs"},
            "docker": {"build_docker_image": "not_a_boolean"},
        },
    }


@pytest.fixture
def mock_yaml_loader():
    """Mock YAML loader to control file loading behavior."""
    with patch("yaml.safe_load") as mock_load:
        yield mock_load


@pytest.fixture
def mock_omegaconf():
    """Mock OmegaConf for controlled configuration object creation."""
    with patch("omegaconf.OmegaConf") as mock_omega:
        yield mock_omega


@pytest.fixture
def environment_variables():
    """Common environment variables for testing overrides."""
    return {
        "PANTHER_DEBUG": "true",
        "PANTHER_LOG_LEVEL": "INFO",
        "PANTHER_OUTPUT_DIR": "/custom/output",
        "PANTHER_PLUGIN_DIR": "/custom/plugins",
        "PANTHER_DOCKER_BUILD": "false",
        "PANTHER_FAST_FAIL": "true",
        "PANTHER_ITERATIONS": "5",
    }


@pytest.fixture
def mock_importlib():
    """Mock importlib for plugin loading tests."""
    with (
        patch("importlib.import_module") as mock_import,
        patch("importlib.util.spec_from_file_location") as mock_spec,
        patch("importlib.util.module_from_spec") as mock_module,
    ):
        yield {
            "import_module": mock_import,
            "spec_from_file_location": mock_spec,
            "module_from_spec": mock_module,
        }


@pytest.fixture(autouse=True)
def suppress_logging():
    """Suppress logging during tests unless explicitly needed."""
    import logging

    logging.getLogger("panther").setLevel(logging.CRITICAL)
    logging.getLogger("ConfigLoader").setLevel(logging.CRITICAL)
    logging.getLogger("PluginFinder").setLevel(logging.CRITICAL)
    logging.getLogger("PluginParameters").setLevel(logging.CRITICAL)


@pytest.fixture
def mock_pathlib():
    """Mock pathlib operations for file system isolation."""
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("pathlib.Path.glob") as mock_glob,
    ):
        yield {"exists": mock_exists, "mkdir": mock_mkdir, "glob": mock_glob}


# Hypothesis strategies for property-based testing
from hypothesis import strategies as st

# Configuration value strategies
log_levels = st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
boolean_values = st.booleans()
port_numbers = st.integers(min_value=1024, max_value=65535)
timeout_values = st.integers(min_value=1, max_value=3600)
iteration_counts = st.integers(min_value=1, max_value=1000)

# Path strategies (valid filesystem paths)
valid_paths = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=32, max_codepoint=126
    ),
    min_size=1,
    max_size=100,
).filter(
    lambda x: all(c not in x for c in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"])
)

# Plugin name strategies
plugin_names = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=32, max_codepoint=126
    ),
    min_size=3,
    max_size=50,
).filter(lambda x: x.replace("_", "").replace("-", "").isalnum())

# Service name strategies
service_names = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=32, max_codepoint=126
    ),
    min_size=1,
    max_size=50,
).filter(lambda x: x.replace("_", "").replace("-", "").isalnum())
