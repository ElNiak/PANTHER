"""
Comprehensive unit tests for RunCommand CLI.

This module provides exhaustive testing for ALL RunCommand parameters,
including complex integrations, edge cases, and error conditions.
"""

import argparse
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest
import yaml

from panther.cli.subcommands.run import RunCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestRunCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for RunCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return RunCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "run"

    @pytest.fixture
    def mock_config_loader_class(self):
        """Mock ConfigLoader class for testing."""
        with patch("panther.cli.subcommands.run.ConfigLoader") as mock:
            mock_instance = MagicMock()
            mock_instance.load_and_validate_global_config.return_value = MagicMock()
            mock_instance.load_and_validate_experiment_config.return_value = MagicMock()
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_experiment_manager_class(self):
        """Mock ExperimentManager class for testing."""
        with patch("panther.cli.subcommands.run.ExperimentManager") as mock:
            mock_instance = MagicMock()
            mock_instance.initialize_experiments.return_value = True
            mock_instance.run_tests.return_value = True
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_metrics_classes(self):
        """Mock all metrics-related classes."""
        metrics_mocks = {}

        with patch(
            "panther.cli.subcommands.run.MetricsCollector"
        ) as metrics_collector_mock, patch(
            "panther.cli.subcommands.run.MetricsExporter"
        ) as metrics_exporter_mock, patch(
            "panther.cli.subcommands.run.MetricsReporter"
        ) as metrics_reporter_mock, patch(
            "panther.cli.subcommands.run.ResourceMonitor"
        ) as resource_monitor_mock:
            # Setup MetricsCollector
            metrics_collector_instance = MagicMock()
            metrics_collector_mock.return_value = metrics_collector_instance

            # Setup MetricsExporter
            metrics_exporter_instance = MagicMock()
            metrics_exporter_instance.export_to_json.return_value = True
            metrics_exporter_instance.export_to_csv.return_value = True
            metrics_exporter_mock.return_value = metrics_exporter_instance

            # Setup MetricsReporter
            metrics_reporter_instance = MagicMock()
            metrics_reporter_instance.generate_report.return_value = True
            metrics_reporter_mock.return_value = metrics_reporter_instance

            # Setup ResourceMonitor
            resource_monitor_instance = MagicMock()
            resource_monitor_instance.start.return_value = None
            resource_monitor_instance.stop.return_value = None
            resource_monitor_mock.return_value = resource_monitor_instance

            metrics_mocks = {
                "collector_class": metrics_collector_mock,
                "collector_instance": metrics_collector_instance,
                "exporter_class": metrics_exporter_mock,
                "exporter_instance": metrics_exporter_instance,
                "reporter_class": metrics_reporter_mock,
                "reporter_instance": metrics_reporter_instance,
                "monitor_class": resource_monitor_mock,
                "monitor_instance": resource_monitor_instance,
            }

            yield metrics_mocks

    @pytest.fixture
    def mock_logger_factory(self):
        """Mock LoggerFactory for testing."""
        with patch("panther.cli.subcommands.run.LoggerFactory") as mock:
            mock.initialize.return_value = None
            yield mock

    @pytest.fixture
    def sample_experiment_config(self):
        """Sample experiment configuration for testing."""
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

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that RunCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'run' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "run" in subparsers_actions[0].choices

    def test_all_parameter_groups_registered(self):
        """Test that all parameter groups are properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()
        run_parser = None

        for action in parser._subparsers._actions:
            if (
                hasattr(action, "choices")
                and action.choices
                and "run" in action.choices
            ):
                run_parser = action.choices["run"]
                break

        assert run_parser is not None

        # Check for argument groups
        group_titles = [group.title for group in run_parser._action_groups]
        assert "Plugin Directories" in group_titles
        assert "Metrics Options" in group_titles
        assert "Docker User Mapping" in group_titles

    # =============================================================================
    # CORE PARAMETER TESTS
    # =============================================================================

    def test_config_parameter_required(self, tmp_path):
        """Test that --config parameter is required."""
        args = self.create_namespace()
        # Don't set config parameter

        result = RunCommand.handle(args)

        # Should fail without config
        assert result == 1

    def test_config_file_not_found(self, caplog):
        """Test behavior when config file doesn't exist."""
        args = self.create_namespace(
            config="/nonexistent/path/config.yaml", dry_run=False
        )

        result = RunCommand.handle(args)

        assert result == 1
        assert "Configuration file not found" in caplog.text

    def test_basic_config_success(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test successful execution with basic configuration."""
        # Create temporary config file
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            output_dir="outputs",
            experiment_name=None,
            dry_run=False,
            enable_metrics=False,
            disable_metrics=False,
            exec_env_dir="",
            net_env_dir="",
            iut_dir="",
            tester_dir="",
            docker_run_as_host=False,
            docker_user_id=None,
            docker_group_id=None,
            docker_user_name="panther",
        )

        result = RunCommand.handle(args)

        assert result == 0
        mock_config_class.assert_called_once()
        mock_manager_class.assert_called_once()
        mock_manager_instance.run_tests.assert_called_once()

    def test_dry_run_mode(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        caplog,
    ):
        """Test dry-run mode execution."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            dry_run=True,
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        assert "DRY-RUN MODE" in caplog.text

        # Verify dry_run=True was passed to ExperimentManager
        mock_manager_class.assert_called_once()
        call_args = mock_manager_class.call_args
        assert call_args[1]["dry_run"] is True

    def test_output_dir_parameter(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test custom output directory parameter."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        custom_output_dir = "custom/outputs"
        args = self.create_namespace(
            config=str(config_file),
            output_dir=custom_output_dir,
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify output_dir was set on config_loader
        assert mock_config_instance.output_dir == custom_output_dir

    def test_experiment_name_override(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test experiment name override parameter."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        custom_name = "custom_experiment_name"
        args = self.create_namespace(
            config=str(config_file),
            experiment_name=custom_name,
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify experiment_name was passed to ExperimentManager
        mock_manager_class.assert_called_once()
        call_args = mock_manager_class.call_args
        assert call_args[1]["experiment_name"] == custom_name

    # =============================================================================
    # PLUGIN DIRECTORY PARAMETER TESTS
    # =============================================================================

    def test_plugin_directories_parameters(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test all plugin directory parameters."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            exec_env_dir="/custom/exec_env",
            net_env_dir="/custom/net_env",
            iut_dir="/custom/iut",
            tester_dir="/custom/tester",
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify plugin directories were set on config_loader
        assert mock_config_instance.exec_env_dir == "/custom/exec_env"
        assert mock_config_instance.net_env_dir == "/custom/net_env"
        assert mock_config_instance.iut_dir == "/custom/iut"
        assert mock_config_instance.testers_dir == "/custom/tester"

    @pytest.mark.parametrize(
        "plugin_dir_param,value",
        [
            ("exec_env_dir", "/path/to/exec"),
            ("net_env_dir", "/path/to/net"),
            ("iut_dir", "/path/to/iut"),
            ("tester_dir", "/path/to/tester"),
        ],
    )
    def test_individual_plugin_directories(
        self,
        plugin_dir_param,
        value,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test individual plugin directory parameters."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args_dict = {
            "config": str(config_file),
            "exec_env_dir": "",
            "net_env_dir": "",
            "iut_dir": "",
            "tester_dir": "",
            "enable_metrics": False,
            "disable_metrics": False,
        }
        args_dict[plugin_dir_param] = value

        args = self.create_namespace(**args_dict)

        result = RunCommand.handle(args)

        assert result == 0
        # Verify the specific directory was set correctly
        if plugin_dir_param == "tester_dir":
            assert getattr(mock_config_instance, "testers_dir") == value
        else:
            assert getattr(mock_config_instance, plugin_dir_param) == value

    # =============================================================================
    # METRICS PARAMETERS TESTS
    # =============================================================================

    def test_enable_metrics_basic(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
        caplog,
    ):
        """Test basic metrics enabling."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=False,
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        assert "Metrics collection enabled" in caplog.text
        mock_metrics_classes["collector_class"].assert_called_once()
        mock_metrics_classes["exporter_class"].assert_called_once()

    def test_disable_metrics_takes_precedence(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
    ):
        """Test that disable_metrics takes precedence over enable_metrics."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=True,  # This should take precedence
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Metrics classes should not be called when disabled
        mock_metrics_classes["collector_class"].assert_not_called()
        mock_metrics_classes["exporter_class"].assert_not_called()

    def test_metrics_output_dir_parameter(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
    ):
        """Test custom metrics output directory."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        custom_metrics_dir = "custom/metrics/dir"
        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=False,
            metrics_output_dir=custom_metrics_dir,
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify MetricsCollector was called with custom output dir
        mock_metrics_classes["collector_class"].assert_called_once()
        call_args = mock_metrics_classes["collector_class"].call_args
        assert str(call_args[1]["output_dir"]).endswith(custom_metrics_dir)

    @pytest.mark.parametrize("metrics_format", ["json", "csv", "txt"])
    def test_metrics_format_parameter(
        self,
        metrics_format,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
    ):
        """Test different metrics format parameters."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=False,
            metrics_format=metrics_format,
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify appropriate export method was called
        if metrics_format == "json" or metrics_format == "txt":
            mock_metrics_classes[
                "exporter_instance"
            ].export_to_json.assert_called_once()
        elif metrics_format == "csv":
            mock_metrics_classes["exporter_instance"].export_to_csv.assert_called_once()

    def test_metrics_interval_parameter(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
    ):
        """Test metrics interval parameter."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        custom_interval = 5.5
        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=False,
            metrics_interval=custom_interval,
            metrics_disable_resource_monitoring=False,
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify ResourceMonitor was called with custom interval
        mock_metrics_classes["monitor_class"].assert_called_once()
        call_args = mock_metrics_classes["monitor_class"].call_args
        assert call_args[1]["interval"] == custom_interval

    def test_metrics_disable_resource_monitoring(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
    ):
        """Test disabling resource monitoring."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=False,
            metrics_disable_resource_monitoring=True,
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        # ResourceMonitor should not be called when disabled
        mock_metrics_classes["monitor_class"].assert_not_called()

    def test_metrics_generate_report(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
    ):
        """Test metrics report generation."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=False,
            metrics_generate_report=True,
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify MetricsReporter was instantiated and report generation called
        mock_metrics_classes["reporter_class"].assert_called_once()
        mock_metrics_classes["reporter_instance"].generate_report.assert_called_once()

    def test_metrics_quiet_mode(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
        caplog,
    ):
        """Test metrics quiet mode."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=False,
            metrics_quiet=True,
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify metrics messages were suppressed
        assert "Metrics collection enabled" not in caplog.text

    # =============================================================================
    # DOCKER PARAMETER TESTS
    # =============================================================================

    def test_docker_run_as_host_parameter(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test docker run as host parameter."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup global config with docker settings
        mock_global_config = MagicMock()
        mock_global_config.docker.user_mapping.run_as_host_user = False
        mock_config_instance.load_and_validate_global_config.return_value = (
            mock_global_config
        )

        args = self.create_namespace(
            config=str(config_file),
            docker_run_as_host=True,
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify docker setting was overridden
        assert mock_global_config.docker.user_mapping.run_as_host_user is True

    def test_docker_user_id_parameter(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test docker user ID parameter."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup global config with docker settings
        mock_global_config = MagicMock()
        mock_global_config.docker.user_mapping.custom_uid = None
        mock_config_instance.load_and_validate_global_config.return_value = (
            mock_global_config
        )

        custom_uid = 1001
        args = self.create_namespace(
            config=str(config_file),
            docker_user_id=custom_uid,
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify docker user ID was set
        assert mock_global_config.docker.user_mapping.custom_uid == custom_uid

    def test_docker_group_id_parameter(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test docker group ID parameter."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup global config with docker settings
        mock_global_config = MagicMock()
        mock_global_config.docker.user_mapping.custom_gid = None
        mock_config_instance.load_and_validate_global_config.return_value = (
            mock_global_config
        )

        custom_gid = 1001
        args = self.create_namespace(
            config=str(config_file),
            docker_group_id=custom_gid,
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify docker group ID was set
        assert mock_global_config.docker.user_mapping.custom_gid == custom_gid

    def test_docker_user_name_parameter(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test docker user name parameter."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup global config with docker settings
        mock_global_config = MagicMock()
        mock_global_config.docker.user_mapping.user_name = "panther"
        mock_config_instance.load_and_validate_global_config.return_value = (
            mock_global_config
        )

        custom_user_name = "custom_user"
        args = self.create_namespace(
            config=str(config_file),
            docker_user_name=custom_user_name,
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify docker user name was set
        assert mock_global_config.docker.user_mapping.user_name == custom_user_name

    def test_docker_user_name_default_not_overridden(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test that default docker user name is not overridden."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup global config with docker settings
        mock_global_config = MagicMock()
        original_user_name = "original_user"
        mock_global_config.docker.user_mapping.user_name = original_user_name
        mock_config_instance.load_and_validate_global_config.return_value = (
            mock_global_config
        )

        args = self.create_namespace(
            config=str(config_file),
            docker_user_name="panther",  # Default value
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0
        # Verify docker user name was not overridden
        assert mock_global_config.docker.user_mapping.user_name == original_user_name

    # =============================================================================
    # PARAMETER COMBINATION TESTS
    # =============================================================================

    def test_all_parameters_together(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
    ):
        """Test execution with all parameters specified."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup global config with docker settings
        mock_global_config = MagicMock()
        mock_config_instance.load_and_validate_global_config.return_value = (
            mock_global_config
        )

        args = self.create_namespace(
            config=str(config_file),
            output_dir="custom_outputs",
            experiment_name="comprehensive_test",
            dry_run=False,
            exec_env_dir="/custom/exec",
            net_env_dir="/custom/net",
            iut_dir="/custom/iut",
            tester_dir="/custom/tester",
            enable_metrics=True,
            disable_metrics=False,
            metrics_output_dir="custom_metrics",
            metrics_format="csv",
            metrics_interval=2.5,
            metrics_disable_resource_monitoring=False,
            metrics_generate_report=True,
            metrics_quiet=False,
            docker_run_as_host=True,
            docker_user_id=1001,
            docker_group_id=1001,
            docker_user_name="test_user",
        )

        result = RunCommand.handle(args)

        assert result == 0

        # Verify all parameters were processed
        assert mock_config_instance.output_dir == "custom_outputs"
        assert mock_config_instance.exec_env_dir == "/custom/exec"
        assert mock_config_instance.net_env_dir == "/custom/net"
        assert mock_config_instance.iut_dir == "/custom/iut"
        assert mock_config_instance.testers_dir == "/custom/tester"

        # Verify docker settings
        assert mock_global_config.docker.user_mapping.run_as_host_user is True
        assert mock_global_config.docker.user_mapping.custom_uid == 1001
        assert mock_global_config.docker.user_mapping.custom_gid == 1001
        assert mock_global_config.docker.user_mapping.user_name == "test_user"

        # Verify metrics components were initialized
        mock_metrics_classes["collector_class"].assert_called_once()
        mock_metrics_classes["exporter_class"].assert_called_once()
        mock_metrics_classes["reporter_class"].assert_called_once()
        mock_metrics_classes["monitor_class"].assert_called_once()

    def test_conflicting_metrics_parameters(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test conflicting metrics parameters (enable + disable)."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=True,  # Conflicting with enable_metrics
            experiment_name="conflict_test",
        )

        result = RunCommand.handle(args)

        # Should succeed but disable_metrics takes precedence
        assert result == 0

    # =============================================================================
    # ERROR HANDLING TESTS
    # =============================================================================

    def test_config_loader_initialization_error(
        self, tmp_path, sample_experiment_config, caplog
    ):
        """Test error handling when ConfigLoader initialization fails."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        with patch("panther.cli.subcommands.run.ConfigLoader") as mock_config_class:
            mock_config_class.side_effect = Exception("Config loader failed")

            args = self.create_namespace(
                config=str(config_file), enable_metrics=False, disable_metrics=False
            )

            result = RunCommand.handle(args)

            assert result == 1
            assert "Error running experiment" in caplog.text

    def test_experiment_manager_initialization_error(
        self, tmp_path, sample_experiment_config, mock_config_loader_class, caplog
    ):
        """Test error handling when ExperimentManager initialization fails."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        with patch(
            "panther.cli.subcommands.run.ExperimentManager"
        ) as mock_manager_class:
            mock_manager_class.side_effect = Exception("Manager initialization failed")

            args = self.create_namespace(
                config=str(config_file), enable_metrics=False, disable_metrics=False
            )

            result = RunCommand.handle(args)

            assert result == 1
            assert "Error running experiment" in caplog.text

    def test_metrics_initialization_error(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        caplog,
    ):
        """Test warning when metrics initialization fails."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        with patch("panther.cli.subcommands.run.MetricsCollector") as mock_metrics:
            mock_metrics.side_effect = Exception("Metrics initialization failed")

            args = self.create_namespace(
                config=str(config_file),
                enable_metrics=True,
                disable_metrics=False,
                experiment_name="test_experiment",
            )

            result = RunCommand.handle(args)

            # Should succeed with warning
            assert result == 0
            assert "Warning: Failed to initialize metrics" in caplog.text

    def test_resource_monitor_start_error(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
        caplog,
    ):
        """Test warning when resource monitor start fails."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup resource monitor to fail on start
        mock_metrics_classes["monitor_instance"].start.side_effect = Exception(
            "Monitor start failed"
        )

        args = self.create_namespace(
            config=str(config_file),
            enable_metrics=True,
            disable_metrics=False,
            metrics_disable_resource_monitoring=False,
            experiment_name="test_experiment",
        )

        result = RunCommand.handle(args)

        assert result == 0
        assert "Warning: Failed to start resource monitoring" in caplog.text

    def test_keyboard_interrupt_handling(
        self, tmp_path, sample_experiment_config, mock_config_loader_class, caplog
    ):
        """Test handling of keyboard interrupt."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        with patch(
            "panther.cli.subcommands.run.ExperimentManager"
        ) as mock_manager_class:
            mock_manager_class.side_effect = KeyboardInterrupt()

            args = self.create_namespace(
                config=str(config_file), enable_metrics=False, disable_metrics=False
            )

            result = RunCommand.handle(args)

            assert result == 130  # Standard exit code for SIGINT
            assert "Experiment interrupted by user" in caplog.text

    def test_experiment_run_failure(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        caplog,
    ):
        """Test handling when experiment run fails."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup experiment manager to return failure
        mock_manager_instance.run_tests.return_value = False

        args = self.create_namespace(
            config=str(config_file), enable_metrics=False, disable_metrics=False
        )

        result = RunCommand.handle(args)

        assert result == 1
        assert "Experiment failed" in caplog.text

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_very_long_paths(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test handling of very long file paths."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        very_long_path = "/very/long/path/" + "a" * 200 + "/outputs"

        args = self.create_namespace(
            config=str(config_file),
            output_dir=very_long_path,
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0  # Should handle gracefully

    def test_unicode_in_paths(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test handling of unicode characters in paths."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        unicode_path = "/测试/路径/outputs"

        args = self.create_namespace(
            config=str(config_file),
            output_dir=unicode_path,
            experiment_name="测试实验",
            enable_metrics=False,
            disable_metrics=False,
        )

        result = RunCommand.handle(args)

        assert result == 0  # Should handle gracefully

    def test_extreme_metrics_interval_values(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
    ):
        """Test extreme metrics interval values."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        extreme_intervals = [0.01, 0.1, 100.0, 1000.0]

        for interval in extreme_intervals:
            args = self.create_namespace(
                config=str(config_file),
                enable_metrics=True,
                disable_metrics=False,
                metrics_interval=interval,
                metrics_disable_resource_monitoring=False,
                experiment_name="test_experiment",
            )

            result = RunCommand.handle(args)

            assert result == 0  # Should handle extreme values

            # Reset mocks for next iteration
            for mock_obj in mock_metrics_classes.values():
                if hasattr(mock_obj, "reset_mock"):
                    mock_obj.reset_mock()

    def test_extreme_docker_uid_gid_values(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
    ):
        """Test extreme Docker UID/GID values."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup global config with docker settings
        mock_global_config = MagicMock()
        mock_config_instance.load_and_validate_global_config.return_value = (
            mock_global_config
        )

        extreme_values = [0, 1, 65535, 999999]

        for uid_value in extreme_values:
            args = self.create_namespace(
                config=str(config_file),
                docker_user_id=uid_value,
                docker_group_id=uid_value,
                enable_metrics=False,
                disable_metrics=False,
            )

            result = RunCommand.handle(args)

            assert result == 0  # Should handle extreme values
            assert mock_global_config.docker.user_mapping.custom_uid == uid_value
            assert mock_global_config.docker.user_mapping.custom_gid == uid_value

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_workflow_success(
        self,
        tmp_path,
        sample_experiment_config,
        mock_config_loader_class,
        mock_experiment_manager_class,
        mock_metrics_classes,
        mock_logger_factory,
        caplog,
    ):
        """Test complete end-to-end workflow with all components."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_experiment_config, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_manager_class, mock_manager_instance = mock_experiment_manager_class

        # Setup global config with logging settings
        mock_global_config = MagicMock()
        mock_global_config.logging.level.name = "INFO"
        mock_global_config.logging.format = "%(message)s"
        mock_global_config.logging.enable_colors = True
        mock_config_instance.load_and_validate_global_config.return_value = (
            mock_global_config
        )

        args = self.create_namespace(
            config=str(config_file),
            output_dir="test_outputs",
            experiment_name="integration_test",
            dry_run=False,
            enable_metrics=True,
            disable_metrics=False,
            metrics_generate_report=True,
        )

        result = RunCommand.handle(args)

        assert result == 0
        assert "Starting PANTHER experiment" in caplog.text
        assert "Loading experiment configuration" in caplog.text
        assert "Initializing experiment" in caplog.text
        assert "Running tests" in caplog.text
        assert "Experiment completed successfully" in caplog.text

        # Verify all major components were called
        mock_config_class.assert_called_once()
        mock_manager_class.assert_called_once()
        mock_logger_factory.initialize.assert_called_once()
        mock_metrics_classes["collector_class"].assert_called_once()
        mock_metrics_classes["exporter_class"].assert_called_once()
        mock_metrics_classes["reporter_class"].assert_called_once()
        mock_metrics_classes["monitor_class"].assert_called_once()
        mock_metrics_classes["monitor_instance"].start.assert_called_once()
        mock_metrics_classes["monitor_instance"].stop.assert_called_once()
        mock_metrics_classes["reporter_instance"].generate_report.assert_called_once()
