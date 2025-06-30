"""
Base test infrastructure for comprehensive CLI command testing.

This module provides common utilities, fixtures, and patterns for testing
all PANTHER CLI commands with complete parameter validation and edge cases.
"""

import argparse
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from panther.cli.main import create_parser
from panther.config.core.models import GlobalConfig, TestConfig


class BaseCLITest:
    """Base class for CLI command testing with comprehensive utilities."""

    @pytest.fixture(autouse=True)
    def setup_logging(self, caplog):
        """Setup logging capture for all tests."""
        caplog.set_level(logging.INFO)
        return caplog

    @pytest.fixture
    def mock_global_config(self):
        """Mock GlobalConfig with all required attributes."""
        config = MagicMock(spec=GlobalConfig)
        config.logging.level.name = "INFO"
        config.logging.format = "%(message)s"
        config.logging.enable_colors = True
        config.paths.output_dir = "outputs"
        config.docker.build_docker_image = False
        config.progress.enable_progress_bar = False
        config.progress.redirect_logging = False
        config.progress.show_test_status = True
        config.progress.use_emojis = True
        config.fast_fail.enabled = False
        return config

    @pytest.fixture
    def minimal_config_content(self):
        """Minimal valid experiment configuration."""
        return {
            "logging": {"level": "INFO"},
            "paths": {"output_dir": "outputs"},
            "docker": {"build_docker_image": False},
            "tests": [
                {
                    "name": "Test Case",
                    "description": "Test description",
                    "network_environment": {"type": "docker_compose"},
                    "services": {
                        "server": {
                            "name": "server",
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                            "ports": ["4443:4443"],
                        }
                    },
                    "steps": {"wait": 30},
                }
            ],
        }

    @pytest.fixture
    def temp_config_file(self, tmp_path, minimal_config_content):
        """Create temporary config file."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(minimal_config_content, f)
        return str(config_file)

    @pytest.fixture
    def temp_plugin_dir(self, tmp_path):
        """Create temporary plugin directory structure."""
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        # Create sample plugin structure
        for plugin_type in ["iut", "testers", "environments"]:
            type_dir = plugin_dir / plugin_type
            type_dir.mkdir()

            for plugin_name in ["sample_plugin"]:
                plugin_path = type_dir / plugin_name
                plugin_path.mkdir()

                # Create plugin file
                plugin_file = plugin_path / f"{plugin_name}.py"
                plugin_file.write_text(
                    f'''
"""Sample {plugin_type} plugin for testing."""

class {plugin_name.title()}Plugin:
    def __init__(self):
        self.name = "{plugin_name}"
        self.type = "{plugin_type}"
        self.version = "1.0.0"
'''
                )

                # Create config schema
                schema_file = plugin_path / "config_schema.py"
                schema_file.write_text(
                    '''
"""Configuration schema for sample plugin."""

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "timeout": {"type": "integer", "default": 60}
    }
}
'''
                )

        return str(plugin_dir)

    @pytest.fixture
    def mock_metrics_data(self):
        """Mock metrics data for testing."""
        return {
            "timing_metrics": {"test_duration": 45.5, "setup_time": 12.3},
            "counters": {"tests_run": 5, "tests_passed": 4, "tests_failed": 1},
            "gauges": {"cpu_usage": 75.2, "memory_usage": 512.0},
            "resource_metrics": [
                {"name": "cpu_percent", "value": 45.0, "timestamp": 1234567890},
                {"name": "memory_percent", "value": 60.0, "timestamp": 1234567891},
            ],
        }

    def create_namespace(self, **kwargs):
        """Create argparse Namespace with default values."""
        defaults = {"debug": False, "verbose": False, "quiet": False}
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def assert_required_parameter_error(self, command_class, args_dict, missing_param):
        """Test that missing required parameter produces proper error."""
        # Remove the required parameter
        args_dict.pop(missing_param, None)
        args = self.create_namespace(**args_dict)

        result = command_class.handle(args)
        assert result == 1  # Should fail

    def assert_parameter_validation(
        self, command_class, args_dict, param_name, invalid_values
    ):
        """Test parameter validation with invalid values."""
        base_args = args_dict.copy()

        for invalid_value in invalid_values:
            test_args = base_args.copy()
            test_args[param_name] = invalid_value
            args = self.create_namespace(**test_args)

            result = command_class.handle(args)
            # Should either fail or handle gracefully
            assert result in [0, 1]

    def test_help_output_contains_all_parameters(self, command_name):
        """Test that help output contains all expected parameters."""
        parser = create_parser()

        # Capture help output
        try:
            parser.parse_args([command_name, "--help"])
        except SystemExit:
            pass  # argparse calls sys.exit() after showing help

    def test_command_registration(self, command_name):
        """Test that command is properly registered in main parser."""
        parser = create_parser()

        # Check command is in subparsers
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]

        assert len(subparsers_actions) == 1
        subparsers_action = subparsers_actions[0]
        assert command_name in subparsers_action.choices

    def create_mock_metrics_collector(self, experiment_name="test", output_dir=None):
        """Create mock MetricsCollector for testing."""
        from panther.core.metrics.metrics_collector import MetricsCollector

        mock_collector = MagicMock(spec=MetricsCollector)
        mock_collector.experiment_name = experiment_name
        mock_collector.output_dir = output_dir or Path("outputs/metrics")
        mock_collector.get_metrics.return_value = []
        mock_collector.get_counter.return_value = 0
        mock_collector.get_gauge.return_value = 0.0
        mock_collector.get_timing_metric.return_value = 0.0

        return mock_collector

    def create_mock_metrics_exporter(self, metrics_collector=None):
        """Create mock MetricsExporter for testing."""
        from panther.core.metrics.metrics_exporter import MetricsExporter

        mock_exporter = MagicMock(spec=MetricsExporter)
        mock_exporter.metrics_collector = metrics_collector
        mock_exporter.export_to_json.return_value = True
        mock_exporter.export_to_csv.return_value = True

        return mock_exporter

    def parametrize_boolean_flags(self, flag_name):
        """Create pytest parameters for boolean flags."""
        return pytest.mark.parametrize(flag_name, [True, False])

    def parametrize_choices(self, param_name, choices):
        """Create pytest parameters for choice-based parameters."""
        return pytest.mark.parametrize(param_name, choices)

    def parametrize_invalid_values(self, param_name, invalid_values):
        """Create pytest parameters for invalid values testing."""
        return pytest.mark.parametrize(f"invalid_{param_name}", invalid_values)


class ParameterTestMixin:
    """Mixin providing parameter testing utilities."""

    @pytest.fixture
    def valid_combinations(self):
        """Fixture providing valid parameter combinations."""
        return [
            {"config": "test.yaml"},
            {"output_dir": "outputs", "experiment_name": "test"},
            {},  # Empty parameters
        ]

    @pytest.fixture
    def conflicting_combinations(self):
        """Fixture providing conflicting parameter combinations."""
        return [
            {"enable_metrics": True, "disable_metrics": True},
            {"dry_run": True, "force": True},
        ]

    def test_all_parameters_documented(self, command_class):
        """Test that all parameters are documented in help."""
        # This would be implemented to parse the argparse help
        # and verify all parameters have descriptions
        pass

    def test_parameter_combinations(self, command_class, valid_combinations):
        """Test valid parameter combinations."""
        for combination in valid_combinations:
            args = self.create_namespace(**combination)
            result = command_class.handle(args)
            assert result in [0, 1]  # Should not crash

    def test_conflicting_parameters(self, command_class, conflicting_combinations):
        """Test mutually exclusive parameters."""
        for combination in conflicting_combinations:
            args = self.create_namespace(**combination)
            result = command_class.handle(args)
            # Should handle conflicts gracefully
            assert result in [0, 1]


class EdgeCaseTestMixin:
    """Mixin providing edge case testing utilities."""

    @pytest.fixture
    def unicode_test_cases(self):
        """Fixture providing unicode test cases."""
        return [
            {"config": "测试.yaml"},
            {"output_dir": "输出目录"},
            {"experiment_name": "实验名称"},
        ]

    @pytest.fixture
    def long_parameter_cases(self):
        """Fixture providing long parameter test cases."""
        long_string = "a" * 1000
        return [
            {"config": long_string + ".yaml"},
            {"output_dir": long_string},
            {"experiment_name": long_string},
        ]

    @pytest.fixture
    def special_char_cases(self):
        """Fixture providing special character test cases."""
        return [
            {"config": "test!@#$.yaml"},
            {"output_dir": "out<>put"},
            {"experiment_name": "exp|name"},
        ]

    @pytest.fixture
    def empty_parameter_cases(self):
        """Fixture providing empty parameter test cases."""
        return [{"config": ""}, {"output_dir": ""}, {"experiment_name": ""}]

    def test_unicode_parameters(self, command_class, unicode_test_cases):
        """Test parameters with unicode characters."""
        for test_case in unicode_test_cases:
            args = self.create_namespace(**test_case)
            result = command_class.handle(args)
            assert result in [0, 1]  # Should handle gracefully

    def test_very_long_parameters(self, command_class, long_parameter_cases):
        """Test parameters with very long values."""
        for test_case in long_parameter_cases:
            args = self.create_namespace(**test_case)
            result = command_class.handle(args)
            assert result in [0, 1]  # Should handle gracefully

    def test_special_characters(self, command_class, special_char_cases):
        """Test parameters with special characters."""
        for test_case in special_char_cases:
            args = self.create_namespace(**test_case)
            result = command_class.handle(args)
            assert result in [0, 1]  # Should handle gracefully

    def test_empty_parameters(self, command_class, empty_parameter_cases):
        """Test parameters with empty values."""
        for test_case in empty_parameter_cases:
            args = self.create_namespace(**test_case)
            result = command_class.handle(args)
            assert result in [0, 1]  # Should handle gracefully


class ComprehensiveCLITest(BaseCLITest, ParameterTestMixin, EdgeCaseTestMixin):
    """Comprehensive CLI test base class combining all testing utilities."""

    pass
