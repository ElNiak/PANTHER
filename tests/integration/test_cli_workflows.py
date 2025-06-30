"""
Integration Tests for CLI Command Workflows

Tests complete workflows and interactions between different CLI commands,
ensuring they work together correctly in realistic scenarios.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from panther.cli.subcommands.check import CheckCommand
from panther.cli.subcommands.config import ConfigCommand
from panther.cli.subcommands.metrics import MetricsCommand
from panther.cli.subcommands.plugins import PluginsCommand
from panther.cli.subcommands.run import RunCommand


class TestConfigToRunWorkflow:
    """Test workflow from configuration validation to experiment execution."""

    def create_namespace(self, **kwargs):
        """Helper to create argument namespace."""

        class Namespace:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        return Namespace(**kwargs)

    def create_test_config(self, config_dict):
        """Create a temporary config file."""
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(config_dict, temp_file)
        temp_file.close()
        return temp_file.name

    def test_validate_then_run_workflow(self):
        """Test complete workflow: validate config -> run experiment."""
        # Create a valid minimal config
        config_dict = {
            "logging": {"level": "INFO", "enable_colors": True},
            "observers": {"logger": {"enabled": True}},
            "paths": {"output_dir": "outputs"},
            "docker": {"force_build_docker_image": False},
            "tests": [
                {
                    "name": "integration_test",
                    "description": "Integration test workflow",
                    "network_environment": {"type": "docker_compose"},
                    "iterations": 1,
                    "execution_environment": [],
                    "debug_environment": [],
                    "services": {
                        "server": {
                            "name": "server",
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                            "timeout": 60,
                        }
                    },
                    "steps": {"wait": 30},
                }
            ],
        }

        config_path = self.create_test_config(config_dict)

        try:
            # Step 1: Validate configuration
            validate_args = self.create_namespace(
                config=config_path,
                strict=False,
                show_schema=False,
                explain=False,
                debug=False,
            )

            with patch(
                "panther.config.config_manager.ConfigLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock(tests=[])
                )

                validate_result = ConfigCommand._handle_validate(validate_args)
                assert validate_result == 0, "Configuration validation should succeed"

            # Step 2: Run experiment with validated config
            run_args = self.create_namespace(
                config=config_path,
                output_dir="outputs",
                experiment_name="integration_test",
                dry_run=True,  # Use dry-run for integration test
                enable_metrics=False,
                disable_metrics=True,
                debug=False,
            )

            with patch("pathlib.Path.exists", return_value=True), patch(
                "panther.config.ConfigLoader"
            ) as mock_run_loader_class:
                mock_run_loader = MagicMock()
                mock_run_loader_class.return_value = mock_run_loader
                mock_run_loader.load_and_validate_global_config.return_value = None
                mock_run_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock()
                )

                with patch(
                    "panther.core.experiment_manager.ExperimentManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.initialize_experiments.return_value = None
                    mock_manager.run_tests.return_value = True

                    run_result = RunCommand.handle(run_args)
                    assert run_result == 0, "Experiment run should succeed"

        finally:
            Path(config_path).unlink()

    def test_generate_validate_run_workflow(self):
        """Test workflow: generate config -> validate -> run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "generated_config.yaml"

            # Step 1: Generate configuration
            generate_args = self.create_namespace(
                template="minimal", output=str(config_path)
            )

            generate_result = ConfigCommand._handle_generate(generate_args)
            assert generate_result == 0, "Config generation should succeed"
            assert config_path.exists(), "Generated config file should exist"

            # Step 2: Validate generated configuration
            validate_args = self.create_namespace(
                config=str(config_path),
                strict=False,
                show_schema=False,
                explain=False,
                debug=False,
            )

            with patch(
                "panther.config.config_manager.ConfigLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock(tests=[])
                )

                validate_result = ConfigCommand._handle_validate(validate_args)
                assert (
                    validate_result == 0
                ), "Generated config validation should succeed"

            # Step 3: Run with generated and validated config
            run_args = self.create_namespace(
                config=str(config_path),
                output_dir=str(temp_dir / "outputs"),
                experiment_name="generated_test",
                dry_run=True,
                enable_metrics=False,
                disable_metrics=True,
                debug=False,
            )

            with patch("pathlib.Path.exists", return_value=True), patch(
                "panther.config.ConfigLoader"
            ) as mock_run_loader_class:
                mock_run_loader = MagicMock()
                mock_run_loader_class.return_value = mock_run_loader
                mock_run_loader.load_and_validate_global_config.return_value = None
                mock_run_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock()
                )

                with patch(
                    "panther.core.experiment_manager.ExperimentManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.initialize_experiments.return_value = None
                    mock_manager.run_tests.return_value = True

                    run_result = RunCommand.handle(run_args)
                    assert run_result == 0, "Run with generated config should succeed"


class TestPluginsToRunWorkflow:
    """Test workflow from plugin discovery to experiment execution."""

    def create_namespace(self, **kwargs):
        """Helper to create argument namespace."""

        class Namespace:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        return Namespace(**kwargs)

    def test_plugins_list_to_config_workflow(self):
        """Test workflow: list plugins -> create config with discovered plugins -> run."""
        # Step 1: List available plugins
        list_args = self.create_namespace(
            plugins_action="list", type="all", format="json"
        )

        # Mock plugin discovery to return some plugins
        mock_plugins = [
            MagicMock(
                name="picoquic",
                type="iut",
                version="1.0",
                description="QUIC implementation",
            ),
            MagicMock(
                name="aioquic",
                type="iut",
                version="2.0",
                description="Async QUIC implementation",
            ),
        ]

        with patch("panther.plugins.plugin_manager.PluginManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance
            mock_instance.discover_plugins.return_value = None
            mock_instance.get_plugins_by_type.return_value = mock_plugins

            list_result = PluginsCommand._handle_list(list_args)
            assert list_result == 0, "Plugin listing should succeed"

        # Step 2: Create config using discovered plugins
        config_dict = {
            "logging": {"level": "INFO"},
            "tests": [
                {
                    "name": "plugin_workflow_test",
                    "services": {
                        "server": {
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                        }
                    },
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_dict, f)
            config_path = f.name

        try:
            # Step 3: Run experiment with plugin-based config
            run_args = self.create_namespace(
                config=config_path,
                output_dir="outputs",
                experiment_name="plugin_test",
                dry_run=True,
                enable_metrics=False,
                disable_metrics=True,
                debug=False,
            )

            with patch("pathlib.Path.exists", return_value=True), patch(
                "panther.config.ConfigLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_global_config.return_value = None
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock()
                )

                with patch(
                    "panther.core.experiment_manager.ExperimentManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.initialize_experiments.return_value = None
                    mock_manager.run_tests.return_value = True

                    run_result = RunCommand.handle(run_args)
                    assert run_result == 0, "Plugin-based experiment should succeed"

        finally:
            Path(config_path).unlink()

    def test_plugin_validation_workflow(self):
        """Test workflow: scan plugins -> validate plugin -> use in config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock plugin file
            plugin_file = Path(temp_dir) / "test_plugin.py"
            plugin_content = '''
"""Test plugin for integration testing."""

class TestPlugin:
    def __init__(self):
        self.name = "test_plugin"
        self.version = "1.0"

    def execute(self):
        return True
'''
            plugin_file.write_text(plugin_content)

            # Step 1: Scan for plugins
            scan_args = self.create_namespace(directory=temp_dir)

            with patch(
                "panther.plugins.core.plugin_discovery.PluginDiscovery"
            ) as mock_discovery:
                mock_instance = MagicMock()
                mock_discovery.return_value = mock_instance
                mock_instance.list_available_plugins.return_value = {
                    "iut": ["test_plugin"]
                }
                mock_instance.get_plugin_info.return_value = {"version": "1.0"}

                scan_result = PluginsCommand._handle_scan(scan_args)
                assert scan_result == 0, "Plugin scan should succeed"

            # Step 2: Validate discovered plugin
            validate_args = self.create_namespace(plugin_path=str(plugin_file))

            validate_result = PluginsCommand._handle_validate(validate_args)
            assert validate_result == 0, "Plugin validation should succeed"


class TestCheckToRunWorkflow:
    """Test workflow from code quality checks to experiment execution."""

    def create_namespace(self, **kwargs):
        """Helper to create argument namespace."""

        class Namespace:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        return Namespace(**kwargs)

    def test_check_then_run_workflow(self):
        """Test workflow: run quality checks -> run experiment if checks pass."""
        # Step 1: Run quality checks
        check_args = self.create_namespace(
            check_action="lint", include_experimental=False, debug=False
        )

        # Mock successful quality check
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="All checks passed", stderr=""
            )

            check_result = CheckCommand.handle(check_args)
            assert check_result == 0, "Quality checks should pass"

        # Step 2: Run experiment after successful checks
        config_dict = {
            "logging": {"level": "INFO"},
            "tests": [{"name": "quality_checked_test"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_dict, f)
            config_path = f.name

        try:
            run_args = self.create_namespace(
                config=config_path,
                output_dir="outputs",
                experiment_name="quality_test",
                dry_run=True,
                enable_metrics=False,
                disable_metrics=True,
                debug=False,
            )

            with patch("pathlib.Path.exists", return_value=True), patch(
                "panther.config.ConfigLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_global_config.return_value = None
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock()
                )

                with patch(
                    "panther.core.experiment_manager.ExperimentManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.initialize_experiments.return_value = None
                    mock_manager.run_tests.return_value = True

                    run_result = RunCommand.handle(run_args)
                    assert run_result == 0, "Run after quality checks should succeed"

        finally:
            Path(config_path).unlink()


class TestMetricsWorkflow:
    """Test workflow involving metrics collection and analysis."""

    def create_namespace(self, **kwargs):
        """Helper to create argument namespace."""

        class Namespace:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        return Namespace(**kwargs)

    def test_run_with_metrics_then_analyze_workflow(self):
        """Test workflow: run experiment with metrics -> analyze metrics."""
        config_dict = {
            "logging": {"level": "INFO"},
            "tests": [{"name": "metrics_test"}],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_dict, f)
            config_path = f.name

        try:
            # Step 1: Run experiment with metrics enabled
            run_args = self.create_namespace(
                config=config_path,
                output_dir="outputs",
                experiment_name="metrics_experiment",
                dry_run=True,
                enable_metrics=True,
                disable_metrics=False,
                metrics_output_dir="metrics",
                metrics_format="json",
                metrics_interval=1.0,
                metrics_generate_report=True,
                metrics_quiet=False,
                debug=False,
            )

            with patch("pathlib.Path.exists", return_value=True), patch(
                "panther.config.ConfigLoader"
            ) as mock_loader_class, patch(
                "panther.core.metrics.MetricsCollector"
            ) as mock_collector_class, patch(
                "panther.core.metrics.MetricsExporter"
            ) as mock_exporter_class, patch(
                "panther.core.metrics.MetricsReporter"
            ) as mock_reporter_class, patch(
                "panther.core.metrics.ResourceMonitor"
            ) as mock_monitor_class:
                # Setup mocks
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_global_config.return_value = None
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock()
                )

                mock_collector = MagicMock()
                mock_collector_class.return_value = mock_collector

                mock_exporter = MagicMock()
                mock_exporter_class.return_value = mock_exporter
                mock_exporter.export_to_json.return_value = True

                mock_reporter = MagicMock()
                mock_reporter_class.return_value = mock_reporter
                mock_reporter.generate_report.return_value = True

                with patch(
                    "panther.core.experiment_manager.ExperimentManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.initialize_experiments.return_value = None
                    mock_manager.run_tests.return_value = True

                    run_result = RunCommand.handle(run_args)
                    assert run_result == 0, "Run with metrics should succeed"

            # Step 2: Analyze collected metrics
            metrics_args = self.create_namespace(metrics_action="summary")

            with patch(
                "panther.core.metrics.metrics_collector.MetricsCollector"
            ) as mock_collector_class, patch(
                "panther.core.metrics.metrics_reporter.MetricsReporter"
            ) as mock_reporter_class:
                mock_collector = MagicMock()
                mock_collector_class.return_value = mock_collector

                mock_reporter = MagicMock()
                mock_reporter_class.return_value = mock_reporter
                mock_reporter.generate_summary.return_value = {
                    "overview": {"total_metrics": 5, "experiments": 1},
                    "categories": {"performance": 3, "system": 2},
                }

                metrics_result = MetricsCommand._summary_metrics(metrics_args)
                assert metrics_result == 0, "Metrics analysis should succeed"

        finally:
            Path(config_path).unlink()


class TestErrorHandlingWorkflows:
    """Test workflow error handling and recovery scenarios."""

    def create_namespace(self, **kwargs):
        """Helper to create argument namespace."""

        class Namespace:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        return Namespace(**kwargs)

    def test_invalid_config_to_fix_workflow(self):
        """Test workflow: invalid config -> validation error -> fix -> validate -> run."""
        # Step 1: Create invalid config
        invalid_config = {
            "logging": {"level": "INVALID_LEVEL"},  # Invalid log level
            "tests": [],  # Empty tests
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_config, f)
            invalid_config_path = f.name

        try:
            # Step 2: Validate invalid config (should fail)
            validate_args = self.create_namespace(
                config=invalid_config_path,
                strict=True,
                show_schema=False,
                explain=True,
                debug=False,
            )

            validate_result = ConfigCommand._handle_validate(validate_args)
            assert validate_result == 1, "Invalid config validation should fail"

            # Step 3: Fix config
            fixed_config = {
                "logging": {"level": "INFO"},  # Fixed log level
                "tests": [
                    {"name": "fixed_test", "description": "Fixed test configuration"}
                ],
            }

            with open(invalid_config_path, "w") as f:
                yaml.dump(fixed_config, f)

            # Step 4: Validate fixed config
            with patch(
                "panther.config.config_manager.ConfigLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock(tests=[])
                )

                validate_result = ConfigCommand._handle_validate(validate_args)
                assert validate_result == 0, "Fixed config validation should succeed"

            # Step 5: Run with fixed config
            run_args = self.create_namespace(
                config=invalid_config_path,
                output_dir="outputs",
                experiment_name="fixed_test",
                dry_run=True,
                enable_metrics=False,
                disable_metrics=True,
                debug=False,
            )

            with patch("pathlib.Path.exists", return_value=True), patch(
                "panther.config.ConfigLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_global_config.return_value = None
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock()
                )

                with patch(
                    "panther.core.experiment_manager.ExperimentManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.initialize_experiments.return_value = None
                    mock_manager.run_tests.return_value = True

                    run_result = RunCommand.handle(run_args)
                    assert run_result == 0, "Run with fixed config should succeed"

        finally:
            Path(invalid_config_path).unlink()

    def test_plugin_not_found_workflow(self):
        """Test workflow: missing plugin -> plugin scan -> plugin install simulation -> retry."""
        # Step 1: Try to use non-existent plugin
        config_with_missing_plugin = {
            "logging": {"level": "INFO"},
            "tests": [
                {
                    "name": "missing_plugin_test",
                    "services": {
                        "server": {
                            "implementation": {
                                "name": "nonexistent_plugin",
                                "type": "iut",
                            }
                        }
                    },
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_with_missing_plugin, f)
            config_path = f.name

        try:
            # This would normally fail due to missing plugin
            run_args = self.create_namespace(
                config=config_path,
                output_dir="outputs",
                experiment_name="missing_plugin_test",
                dry_run=True,
                enable_metrics=False,
                disable_metrics=True,
                debug=False,
            )

            # Step 2: Scan for available plugins
            scan_args = self.create_namespace(directory=None)

            with patch(
                "panther.plugins.core.plugin_discovery.PluginDiscovery"
            ) as mock_discovery:
                mock_instance = MagicMock()
                mock_discovery.return_value = mock_instance
                mock_instance.list_available_plugins.return_value = {
                    "iut": ["picoquic", "aioquic"]  # Available alternatives
                }

                scan_result = PluginsCommand._handle_scan(scan_args)
                assert scan_result == 0, "Plugin scan should succeed"

            # Step 3: Update config with available plugin
            fixed_config = {
                "logging": {"level": "INFO"},
                "tests": [
                    {
                        "name": "fixed_plugin_test",
                        "services": {
                            "server": {
                                "implementation": {
                                    "name": "picoquic",
                                    "type": "iut",
                                }  # Use available plugin
                            }
                        },
                    }
                ],
            }

            with open(config_path, "w") as f:
                yaml.dump(fixed_config, f)

            # Step 4: Retry with available plugin
            with patch("pathlib.Path.exists", return_value=True), patch(
                "panther.config.ConfigLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_global_config.return_value = None
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock()
                )

                with patch(
                    "panther.core.experiment_manager.ExperimentManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.initialize_experiments.return_value = None
                    mock_manager.run_tests.return_value = True

                    run_result = RunCommand.handle(run_args)
                    assert run_result == 0, "Run with available plugin should succeed"

        finally:
            Path(config_path).unlink()


@pytest.mark.integration
class TestEndToEndWorkflows:
    """Test complete end-to-end workflows simulating real user scenarios."""

    def create_namespace(self, **kwargs):
        """Helper to create argument namespace."""

        class Namespace:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        return Namespace(**kwargs)

    def test_complete_development_workflow(self):
        """Test complete development workflow: generate -> validate -> check -> run -> analyze."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "development_config.yaml"

            # Step 1: Generate initial configuration
            generate_args = self.create_namespace(
                template="basic", output=str(config_path)
            )

            generate_result = ConfigCommand._handle_generate(generate_args)
            assert generate_result == 0, "Config generation should succeed"

            # Step 2: Validate generated configuration
            validate_args = self.create_namespace(
                config=str(config_path),
                strict=False,
                show_schema=True,
                explain=True,
                debug=False,
            )

            with patch("panther.config.config_manager.ConfigLoader") as mock_loader:
                mock_instance = MagicMock()
                mock_loader.return_value = mock_instance
                mock_instance.load_and_validate_experiment_config.return_value = (
                    MagicMock(tests=[])
                )

                validate_result = ConfigCommand._handle_validate(validate_args)
                assert validate_result == 0, "Config validation should succeed"

            # Step 3: Run quality checks
            check_args = self.create_namespace(
                check_action="all", include_experimental=False, debug=False
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0, stdout="All quality checks passed", stderr=""
                )

                check_result = CheckCommand.handle(check_args)
                assert check_result == 0, "Quality checks should pass"

            # Step 4: Run experiment with metrics
            run_args = self.create_namespace(
                config=str(config_path),
                output_dir=str(temp_dir / "outputs"),
                experiment_name="development_workflow",
                dry_run=True,
                enable_metrics=True,
                disable_metrics=False,
                metrics_output_dir=str(temp_dir / "metrics"),
                metrics_format="json",
                metrics_generate_report=True,
                debug=False,
            )

            with patch("pathlib.Path.exists", return_value=True), patch(
                "panther.config.ConfigLoader"
            ) as mock_loader_class, patch(
                "panther.core.metrics.MetricsCollector"
            ), patch(
                "panther.core.metrics.MetricsExporter"
            ), patch(
                "panther.core.metrics.MetricsReporter"
            ), patch(
                "panther.core.metrics.ResourceMonitor"
            ):
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader
                mock_loader.load_and_validate_global_config.return_value = None
                mock_loader.load_and_validate_experiment_config.return_value = (
                    MagicMock()
                )

                with patch(
                    "panther.core.experiment_manager.ExperimentManager"
                ) as mock_manager_class:
                    mock_manager = MagicMock()
                    mock_manager_class.return_value = mock_manager
                    mock_manager.initialize_experiments.return_value = None
                    mock_manager.run_tests.return_value = True

                    run_result = RunCommand.handle(run_args)
                    assert run_result == 0, "Experiment run should succeed"

            # Step 5: Analyze metrics
            metrics_args = self.create_namespace(metrics_action="summary")

            with patch(
                "panther.core.metrics.metrics_collector.MetricsCollector"
            ), patch(
                "panther.core.metrics.metrics_reporter.MetricsReporter"
            ) as mock_reporter_class:
                mock_reporter = MagicMock()
                mock_reporter_class.return_value = mock_reporter
                mock_reporter.generate_summary.return_value = {
                    "overview": {"total_metrics": 10, "experiments": 1},
                    "performance": {"avg_runtime": "30s"},
                    "resource_usage": {"peak_memory": "512MB"},
                }

                metrics_result = MetricsCommand._summary_metrics(metrics_args)
                assert metrics_result == 0, "Metrics analysis should succeed"
