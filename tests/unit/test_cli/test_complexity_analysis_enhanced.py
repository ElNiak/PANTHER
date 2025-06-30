"""
Enhanced Complexity Analysis Tests with Comprehensive Output Recording

Tests high cyclomatic complexity methods identified through Codacy analysis
with detailed output recording and validation.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from panther.cli.subcommands.admin import AdminCommand
from panther.cli.subcommands.config import ConfigCommand
from panther.cli.subcommands.plugins import PluginsCommand
from panther.cli.subcommands.run import RunCommand

# Import our enhanced test fixtures
from tests.fixtures.test_output_recorder import (
    TestOutputRecorder,
    enhanced_cli_tester,
    test_output_recorder,
)


class TestHighComplexityMethodsEnhanced:
    """Enhanced tests for high cyclomatic complexity methods with output recording."""

    @pytest.mark.complexity
    def test_run_command_handle_comprehensive(
        self, test_output_recorder, enhanced_cli_tester
    ):
        """
        Test RunCommand.handle() method - identified as high complexity by Codacy.
        Records all outputs, metrics, and validation results.
        """
        test_output_recorder.record_output(
            "Starting RunCommand.handle comprehensive test", "test_start"
        )

        # Create test configuration
        config_dict = {
            "logging": {"level": "INFO", "enable_colors": True},
            "observers": {"logger": {"enabled": True}},
            "paths": {"output_dir": "outputs"},
            "docker": {"force_build_docker_image": False},
            "tests": [
                {
                    "name": "complexity_test",
                    "description": "High complexity method test",
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
                        },
                        "client": {
                            "name": "client",
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "client",
                                "target": "server",
                            },
                            "timeout": 60,
                        },
                    },
                    "steps": {"wait": 30},
                }
            ],
        }

        config_path = enhanced_cli_tester.create_temp_config(config_dict)
        test_output_recorder.record_output(
            f"Created test config: {config_path}", "config_creation"
        )

        # Test different execution scenarios
        test_scenarios = [
            {
                "name": "dry_run_scenario",
                "args": {
                    "config": config_path,
                    "output_dir": "outputs",
                    "experiment_name": "complexity_test",
                    "dry_run": True,
                    "enable_metrics": False,
                    "disable_metrics": True,
                    "debug": False,
                },
            },
            {
                "name": "metrics_enabled_scenario",
                "args": {
                    "config": config_path,
                    "output_dir": "outputs",
                    "experiment_name": "metrics_test",
                    "dry_run": True,
                    "enable_metrics": True,
                    "disable_metrics": False,
                    "metrics_output_dir": "metrics",
                    "metrics_format": "json",
                    "metrics_interval": 1.0,
                    "metrics_generate_report": True,
                    "metrics_quiet": False,
                    "debug": False,
                },
            },
            {
                "name": "docker_options_scenario",
                "args": {
                    "config": config_path,
                    "output_dir": "outputs",
                    "experiment_name": "docker_test",
                    "dry_run": True,
                    "docker_run_as_host": True,
                    "docker_user_id": 1000,
                    "docker_group_id": 1000,
                    "docker_user_name": "testuser",
                    "debug": False,
                },
            },
        ]

        for scenario in test_scenarios:
            test_output_recorder.record_output(
                f"Testing scenario: {scenario['name']}", "scenario_start"
            )

            # Create namespace
            args = enhanced_cli_tester.create_namespace(**scenario["args"])

            # Record scenario execution
            with test_output_recorder.capture_subprocess_output():
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
                    # Setup comprehensive mocks
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

                    mock_monitor = MagicMock()
                    mock_monitor_class.return_value = mock_monitor

                    with patch(
                        "panther.core.experiment_manager.ExperimentManager"
                    ) as mock_manager_class:
                        mock_manager = MagicMock()
                        mock_manager_class.return_value = mock_manager
                        mock_manager.initialize_experiments.return_value = None
                        mock_manager.run_tests.return_value = True

                        # Execute and measure
                        result = enhanced_cli_tester.run_command_with_recording(
                            RunCommand, "handle", args, test_output_recorder
                        )

                        # Validate result
                        assert (
                            result == 0
                        ), f"Scenario {scenario['name']} should succeed"

                        # Record validation results
                        test_output_recorder.record_result(
                            f"run_command_{scenario['name']}",
                            "PASS",
                            {
                                "return_code": result,
                                "scenario_config": scenario["args"],
                                "mocks_called": {
                                    "config_loader": mock_loader_class.called,
                                    "experiment_manager": mock_manager_class.called,
                                },
                            },
                        )

            test_output_recorder.record_output(
                f"Completed scenario: {scenario['name']}", "scenario_end"
            )

        # Record comprehensive metrics
        test_output_recorder.record_metric(
            "scenarios_tested", len(test_scenarios), "count"
        )
        test_output_recorder.record_metric(
            "config_file_size", Path(config_path).stat().st_size, "bytes"
        )

        test_output_recorder.record_output(
            "RunCommand.handle comprehensive test completed", "test_end"
        )

    @pytest.mark.complexity
    def test_config_validate_complex_scenarios(
        self, test_output_recorder, enhanced_cli_tester
    ):
        """
        Test ConfigCommand._handle_validate() method with complex validation scenarios.
        Records validation results and error handling.
        """
        test_output_recorder.record_output(
            "Starting ConfigCommand validation complexity test", "test_start"
        )

        # Test configurations with increasing complexity
        test_configs = [
            {
                "name": "minimal_valid",
                "config": {
                    "logging": {"level": "INFO"},
                    "tests": [{"name": "minimal_test"}],
                },
                "expected_result": 0,
            },
            {
                "name": "complex_valid",
                "config": {
                    "logging": {
                        "level": "DEBUG",
                        "format": "%(asctime)s [%(levelname)s] - %(module)s:%(lineno)d - %(message)s",
                        "enable_colors": True,
                    },
                    "observers": {
                        "logger": {"enabled": True, "log_level": "DEBUG"},
                        "metrics": {"enabled": True, "collect_system_metrics": True},
                        "storage": {"enabled": True, "storage_path": "outputs/storage"},
                    },
                    "paths": {
                        "output_dir": "outputs",
                        "log_dir": "outputs/logs",
                        "plugin_dir": "panther/plugins",
                    },
                    "docker": {"force_build_docker_image": True},
                    "tests": [
                        {
                            "name": "complex_test",
                            "description": "Complex test with multiple services",
                            "network_environment": {"type": "docker_compose"},
                            "iterations": 1,
                            "execution_environment": [
                                {"type": "strace"},
                                {"type": "gperf_cpu"},
                            ],
                            "debug_environment": [],
                            "services": {
                                "server": {
                                    "name": "server",
                                    "implementation": {
                                        "name": "picoquic",
                                        "type": "iut",
                                    },
                                    "protocol": {
                                        "name": "quic",
                                        "version": "rfc9000",
                                        "role": "server",
                                    },
                                    "timeout": 120,
                                    "ports": ["4443:4443"],
                                    "generate_new_certificates": True,
                                },
                                "client": {
                                    "name": "client",
                                    "implementation": {
                                        "name": "aioquic",
                                        "type": "iut",
                                    },
                                    "protocol": {
                                        "name": "quic",
                                        "version": "rfc9000",
                                        "role": "client",
                                        "target": "server",
                                    },
                                    "timeout": 120,
                                    "generate_new_certificates": True,
                                },
                            },
                            "steps": {"wait": 90},
                        }
                    ],
                },
                "expected_result": 0,
            },
            {
                "name": "invalid_config",
                "config": {"logging": {"level": "INVALID_LEVEL"}, "tests": []},
                "expected_result": 1,
            },
        ]

        for config_test in test_configs:
            test_output_recorder.record_output(
                f"Testing config: {config_test['name']}", "config_test_start"
            )

            # Create config file
            config_path = enhanced_cli_tester.create_temp_config(config_test["config"])

            # Create args
            args = enhanced_cli_tester.create_namespace(
                config=config_path,
                strict=True,
                show_schema=True,
                explain=True,
                debug=False,
            )

            # Test validation with comprehensive mocking
            with patch(
                "panther.config.config_manager.ConfigLoader"
            ) as mock_loader_class:
                mock_loader = MagicMock()
                mock_loader_class.return_value = mock_loader

                if config_test["expected_result"] == 0:
                    # Mock successful validation
                    mock_loader.load_and_validate_experiment_config.return_value = (
                        MagicMock(tests=[MagicMock(name="test1")])
                    )
                else:
                    # Mock validation failure
                    mock_loader.load_and_validate_experiment_config.side_effect = (
                        Exception("Validation failed")
                    )

                # Execute validation
                result = enhanced_cli_tester.run_command_with_recording(
                    ConfigCommand, "_handle_validate", args, test_output_recorder
                )

                # Validate result
                assert (
                    result == config_test["expected_result"]
                ), f"Config {config_test['name']} validation result mismatch"

                # Record detailed results
                test_output_recorder.record_result(
                    f"config_validate_{config_test['name']}",
                    "PASS" if result == config_test["expected_result"] else "FAIL",
                    {
                        "expected_result": config_test["expected_result"],
                        "actual_result": result,
                        "config_complexity": len(str(config_test["config"])),
                        "config_path": config_path,
                    },
                )

            test_output_recorder.record_output(
                f"Completed config test: {config_test['name']}", "config_test_end"
            )

        # Record metrics
        test_output_recorder.record_metric(
            "config_tests_run", len(test_configs), "count"
        )
        test_output_recorder.record_metric(
            "validation_complexity_covered",
            len([c for c in test_configs if "complex" in c["name"]]),
            "count",
        )

    @pytest.mark.complexity
    def test_admin_docker_operations_complex(
        self, test_output_recorder, enhanced_cli_tester
    ):
        """
        Test AdminCommand._handle_docker() method with complex Docker operations.
        Records Docker command executions and results.
        """
        test_output_recorder.record_output(
            "Starting AdminCommand Docker operations complexity test", "test_start"
        )

        # Test different Docker operations
        docker_operations = [
            {
                "name": "docker_status",
                "args": {
                    "admin_action": "docker",
                    "docker_action": "status",
                    "format": "json",
                    "debug": False,
                },
            },
            {
                "name": "docker_clean",
                "args": {
                    "admin_action": "docker",
                    "docker_action": "clean",
                    "force": True,
                    "debug": False,
                },
            },
            {
                "name": "docker_build",
                "args": {
                    "admin_action": "docker",
                    "docker_action": "build",
                    "force": True,
                    "debug": False,
                },
            },
        ]

        for operation in docker_operations:
            test_output_recorder.record_output(
                f"Testing Docker operation: {operation['name']}", "docker_op_start"
            )

            # Create args
            args = enhanced_cli_tester.create_namespace(**operation["args"])

            # Mock Docker operations
            with test_output_recorder.capture_subprocess_output() as captured_cmds:
                with patch("subprocess.run") as mock_run, patch(
                    "shutil.which", return_value="/usr/bin/docker"
                ):
                    # Mock different return codes based on operation
                    if "status" in operation["name"]:
                        mock_run.return_value = MagicMock(
                            returncode=0, stdout="Docker is running", stderr=""
                        )
                    elif "clean" in operation["name"]:
                        mock_run.return_value = MagicMock(
                            returncode=0, stdout="Cleanup completed", stderr=""
                        )
                    elif "build" in operation["name"]:
                        mock_run.return_value = MagicMock(
                            returncode=0, stdout="Build completed", stderr=""
                        )

                    # Execute Docker operation
                    result = enhanced_cli_tester.run_command_with_recording(
                        AdminCommand, "_handle_docker", args, test_output_recorder
                    )

                    # Record Docker command metrics
                    test_output_recorder.record_metric(
                        f"docker_{operation['name']}_calls",
                        mock_run.call_count,
                        "count",
                    )

                    # Validate and record results
                    expected_result = 0  # All operations should succeed with mocking
                    assert (
                        result == expected_result
                    ), f"Docker operation {operation['name']} should succeed"

                    test_output_recorder.record_result(
                        f"admin_docker_{operation['name']}",
                        "PASS",
                        {
                            "return_code": result,
                            "subprocess_calls": mock_run.call_count,
                            "captured_commands": len(captured_cmds),
                            "operation": operation["args"]["docker_action"],
                        },
                    )

            test_output_recorder.record_output(
                f"Completed Docker operation: {operation['name']}", "docker_op_end"
            )

        # Record overall metrics
        test_output_recorder.record_metric(
            "docker_operations_tested", len(docker_operations), "count"
        )

    @pytest.mark.complexity
    def test_plugins_discovery_complex_scenarios(
        self, test_output_recorder, enhanced_cli_tester
    ):
        """
        Test PluginsCommand._handle_list() with complex plugin discovery scenarios.
        Records plugin discovery metrics and validation results.
        """
        test_output_recorder.record_output(
            "Starting PluginsCommand discovery complexity test", "test_start"
        )

        # Test different plugin discovery scenarios
        discovery_scenarios = [
            {
                "name": "all_plugins_json",
                "args": {
                    "plugins_action": "list",
                    "type": "all",
                    "format": "json",
                    "filter": None,
                },
                "mock_plugins": [
                    MagicMock(
                        name="picoquic",
                        type="iut",
                        version="1.0",
                        description="QUIC implementation",
                        path="/plugins/picoquic",
                    ),
                    MagicMock(
                        name="aioquic",
                        type="iut",
                        version="2.0",
                        description="Async QUIC implementation",
                        path="/plugins/aioquic",
                    ),
                    MagicMock(
                        name="ivy_tester",
                        type="testers",
                        version="1.5",
                        description="Ivy formal verification tester",
                        path="/plugins/ivy",
                    ),
                ],
            },
            {
                "name": "filtered_plugins_table",
                "args": {
                    "plugins_action": "list",
                    "type": "iut",
                    "format": "table",
                    "filter": "quic",
                },
                "mock_plugins": [
                    MagicMock(
                        name="picoquic",
                        type="iut",
                        version="1.0",
                        description="QUIC implementation",
                        path="/plugins/picoquic",
                    ),
                    MagicMock(
                        name="aioquic",
                        type="iut",
                        version="2.0",
                        description="Async QUIC implementation",
                        path="/plugins/aioquic",
                    ),
                ],
            },
            {
                "name": "empty_plugins_result",
                "args": {
                    "plugins_action": "list",
                    "type": "nonexistent",
                    "format": "simple",
                    "filter": None,
                },
                "mock_plugins": [],
            },
        ]

        for scenario in discovery_scenarios:
            test_output_recorder.record_output(
                f"Testing plugin discovery: {scenario['name']}", "discovery_start"
            )

            # Create args
            args = enhanced_cli_tester.create_namespace(**scenario["args"])

            # Mock plugin discovery
            with patch("panther.plugins.plugin_manager.PluginManager") as mock_manager:
                mock_instance = MagicMock()
                mock_manager.return_value = mock_instance
                mock_instance.discover_plugins.return_value = None

                # Mock plugin return based on type filter
                if scenario["args"]["type"] == "all":
                    # Return plugins for each type call
                    mock_instance.get_plugins_by_type.side_effect = (
                        lambda plugin_type: [
                            p for p in scenario["mock_plugins"] if p.type == plugin_type
                        ]
                        if scenario["mock_plugins"]
                        else []
                    )
                else:
                    mock_instance.get_plugins_by_type.return_value = scenario[
                        "mock_plugins"
                    ]

                # Execute plugin discovery
                result = enhanced_cli_tester.run_command_with_recording(
                    PluginsCommand, "_handle_list", args, test_output_recorder
                )

                # Validate result
                assert (
                    result == 0
                ), f"Plugin discovery {scenario['name']} should succeed"

                # Record discovery metrics
                test_output_recorder.record_metric(
                    f"plugins_discovered_{scenario['name']}",
                    len(scenario["mock_plugins"]),
                    "count",
                )
                test_output_recorder.record_metric(
                    f"discovery_calls_{scenario['name']}",
                    mock_instance.discover_plugins.call_count,
                    "count",
                )

                # Record results
                test_output_recorder.record_result(
                    f"plugins_discovery_{scenario['name']}",
                    "PASS",
                    {
                        "return_code": result,
                        "plugins_found": len(scenario["mock_plugins"]),
                        "format": scenario["args"]["format"],
                        "type_filter": scenario["args"]["type"],
                        "discovery_method_called": mock_instance.discover_plugins.called,
                    },
                )

            test_output_recorder.record_output(
                f"Completed plugin discovery: {scenario['name']}", "discovery_end"
            )

        # Record overall metrics
        test_output_recorder.record_metric(
            "discovery_scenarios_tested", len(discovery_scenarios), "count"
        )
        total_plugins_tested = sum(len(s["mock_plugins"]) for s in discovery_scenarios)
        test_output_recorder.record_metric(
            "total_plugins_tested", total_plugins_tested, "count"
        )

    @pytest.mark.complexity
    def test_complex_error_handling_scenarios(
        self, test_output_recorder, enhanced_cli_tester
    ):
        """
        Test complex error handling across all high-complexity methods.
        Records error scenarios and recovery mechanisms.
        """
        test_output_recorder.record_output(
            "Starting complex error handling scenarios test", "test_start"
        )

        # Test error scenarios for each complex method
        error_scenarios = [
            {
                "name": "run_command_config_not_found",
                "command": RunCommand,
                "method": "handle",
                "args": {
                    "config": "/nonexistent/config.yaml",
                    "output_dir": "outputs",
                    "debug": False,
                },
                "expected_error": True,
            },
            {
                "name": "config_validate_file_not_found",
                "command": ConfigCommand,
                "method": "_handle_validate",
                "args": {
                    "config": "/nonexistent/config.yaml",
                    "strict": False,
                    "show_schema": False,
                    "explain": False,
                    "debug": False,
                },
                "expected_error": True,
            },
            {
                "name": "admin_docker_unavailable",
                "command": AdminCommand,
                "method": "_handle_docker",
                "args": {
                    "admin_action": "docker",
                    "docker_action": "status",
                    "debug": False,
                },
                "expected_error": True,
                "mock_setup": lambda: patch("shutil.which", return_value=None),
            },
        ]

        for scenario in error_scenarios:
            test_output_recorder.record_output(
                f"Testing error scenario: {scenario['name']}", "error_scenario_start"
            )

            # Create args
            args = enhanced_cli_tester.create_namespace(**scenario["args"])

            # Setup error conditions
            context_managers = []
            if "mock_setup" in scenario:
                context_managers.append(scenario["mock_setup"]())

            # Execute with error handling
            if context_managers:
                with context_managers[0]:
                    result = enhanced_cli_tester.run_command_with_recording(
                        scenario["command"],
                        scenario["method"],
                        args,
                        test_output_recorder,
                    )
            else:
                result = enhanced_cli_tester.run_command_with_recording(
                    scenario["command"], scenario["method"], args, test_output_recorder
                )

            # Validate error handling
            if scenario["expected_error"]:
                assert (
                    result != 0
                ), f"Error scenario {scenario['name']} should fail gracefully"
                test_output_recorder.record_result(
                    f"error_handling_{scenario['name']}",
                    "PASS",
                    {
                        "return_code": result,
                        "error_handled_gracefully": True,
                        "command": scenario["command"].__name__,
                        "method": scenario["method"],
                    },
                )
            else:
                test_output_recorder.record_result(
                    f"error_handling_{scenario['name']}",
                    "FAIL",
                    {"unexpected_success": True},
                )

            test_output_recorder.record_output(
                f"Completed error scenario: {scenario['name']}", "error_scenario_end"
            )

        # Record error handling metrics
        test_output_recorder.record_metric(
            "error_scenarios_tested", len(error_scenarios), "count"
        )
        successful_error_handling = sum(
            1 for s in error_scenarios if s["expected_error"]
        )
        test_output_recorder.record_metric(
            "successful_error_handling", successful_error_handling, "count"
        )


@pytest.mark.integration
class TestComplexityIntegrationWithOutputs:
    """Integration tests for complex method interactions with comprehensive output recording."""

    @pytest.mark.complexity
    def test_end_to_end_complex_workflow(
        self, test_output_recorder, enhanced_cli_tester
    ):
        """
        Test end-to-end workflow involving multiple high-complexity methods.
        Records the complete workflow execution and interactions.
        """
        test_output_recorder.record_output(
            "Starting end-to-end complex workflow test", "workflow_start"
        )

        workflow_steps = [
            {
                "step": "config_generation",
                "command": ConfigCommand,
                "method": "_handle_generate",
                "description": "Generate initial configuration",
            },
            {
                "step": "config_validation",
                "command": ConfigCommand,
                "method": "_handle_validate",
                "description": "Validate generated configuration",
            },
            {
                "step": "plugin_discovery",
                "command": PluginsCommand,
                "method": "_handle_list",
                "description": "Discover available plugins",
            },
            {
                "step": "experiment_execution",
                "command": RunCommand,
                "method": "handle",
                "description": "Execute experiment with configuration",
            },
        ]

        # Create temporary directory for workflow
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "workflow_config.yaml"

            for i, step in enumerate(workflow_steps):
                test_output_recorder.record_output(
                    f"Executing workflow step {i+1}: {step['description']}",
                    f"step_{i+1}_start",
                )

                # Prepare step-specific arguments
                if step["step"] == "config_generation":
                    args = enhanced_cli_tester.create_namespace(
                        template="basic", output=str(config_path)
                    )
                elif step["step"] == "config_validation":
                    args = enhanced_cli_tester.create_namespace(
                        config=str(config_path),
                        strict=False,
                        show_schema=True,
                        explain=True,
                        debug=False,
                    )
                elif step["step"] == "plugin_discovery":
                    args = enhanced_cli_tester.create_namespace(
                        plugins_action="list", type="all", format="json"
                    )
                elif step["step"] == "experiment_execution":
                    args = enhanced_cli_tester.create_namespace(
                        config=str(config_path),
                        output_dir=str(Path(temp_dir) / "outputs"),
                        experiment_name=f"workflow_test_{i}",
                        dry_run=True,
                        debug=False,
                    )

                # Execute step with appropriate mocking
                if step["step"] == "config_validation":
                    with patch(
                        "panther.config.config_manager.ConfigLoader"
                    ) as mock_loader:
                        mock_instance = MagicMock()
                        mock_loader.return_value = mock_instance
                        mock_instance.load_and_validate_experiment_config.return_value = MagicMock(
                            tests=[]
                        )

                        result = enhanced_cli_tester.run_command_with_recording(
                            step["command"], step["method"], args, test_output_recorder
                        )
                elif step["step"] == "plugin_discovery":
                    with patch(
                        "panther.plugins.plugin_manager.PluginManager"
                    ) as mock_manager:
                        mock_instance = MagicMock()
                        mock_manager.return_value = mock_instance
                        mock_instance.discover_plugins.return_value = None
                        mock_instance.get_plugins_by_type.return_value = [
                            MagicMock(
                                name="picoquic",
                                type="iut",
                                version="1.0",
                                description="QUIC implementation",
                            )
                        ]

                        result = enhanced_cli_tester.run_command_with_recording(
                            step["command"], step["method"], args, test_output_recorder
                        )
                elif step["step"] == "experiment_execution":
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

                            result = enhanced_cli_tester.run_command_with_recording(
                                step["command"],
                                step["method"],
                                args,
                                test_output_recorder,
                            )
                else:
                    result = enhanced_cli_tester.run_command_with_recording(
                        step["command"], step["method"], args, test_output_recorder
                    )

                # Validate step result
                assert result == 0, f"Workflow step {step['step']} should succeed"

                # Record step completion
                test_output_recorder.record_result(
                    f"workflow_step_{step['step']}",
                    "PASS",
                    {
                        "step_number": i + 1,
                        "return_code": result,
                        "description": step["description"],
                        "command": step["command"].__name__,
                        "method": step["method"],
                    },
                )

                test_output_recorder.record_output(
                    f"Completed workflow step {i+1}: {step['description']}",
                    f"step_{i+1}_end",
                )

        # Record workflow metrics
        test_output_recorder.record_metric(
            "workflow_steps_completed", len(workflow_steps), "count"
        )
        test_output_recorder.record_metric("workflow_success_rate", 100.0, "percentage")

        test_output_recorder.record_output(
            "End-to-end complex workflow test completed successfully", "workflow_end"
        )
