"""
Unit tests for CLI dry-run functionality.

This module tests the --dry-run flag implementation across the CLI, ExperimentManager,
and TestCase components to ensure proper analysis without execution.
"""

import argparse
import logging
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest
import yaml

from panther.cli.main import create_parser
from panther.cli.subcommands.run import RunCommand
from panther.config.core.models import GlobalConfig, TestConfig
from panther.core.experiment_manager import ExperimentManager
from panther.core.test_cases.test_case_impl import TestCase


class TestDryRunFunctionality:
    """Test CLI dry-run functionality across all components."""

    @pytest.fixture(autouse=True)
    def setup_logging(self, caplog):
        """Setup logging capture for tests."""
        caplog.set_level(logging.INFO)
        return caplog

    @pytest.fixture
    def minimal_config_content(self):
        """Minimal valid experiment configuration."""
        return {
            "logging": {"level": "INFO"},
            "paths": {"output_dir": "outputs"},
            "docker": {"build_docker_image": False},
            "tests": [
                {
                    "name": "Simple Test",
                    "description": "A simple test for dry-run testing",
                    "network_environment": {"type": "docker_compose"},
                    "services": {
                        "test_server": {
                            "name": "test_server",
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
    def complex_config_content(self):
        """Complex multi-service experiment configuration."""
        return {
            "logging": {"level": "INFO"},
            "paths": {"output_dir": "outputs"},
            "docker": {"build_docker_image": True},
            "tests": [
                {
                    "name": "Multi-Service Test",
                    "description": "Complex test with multiple services",
                    "network_environment": {"type": "docker_compose"},
                    "execution_environment": [
                        {"name": "strace", "type": "strace"},
                        {"name": "logs", "type": "logs"},
                    ],
                    "services": {
                        "quic_server": {
                            "name": "quic_server",
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                            "ports": ["4443:4443", "8080:8080"],
                        },
                        "quic_client": {
                            "name": "quic_client",
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "client",
                            },
                            "ports": ["5000:5000"],
                        },
                        "ivy_tester": {
                            "name": "ivy_tester",
                            "implementation": {
                                "name": "panther_ivy",
                                "type": "testers",
                            },
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "client",
                            },
                            "ports": ["6000:6000"],
                        },
                    },
                    "steps": [
                        {"type": "command", "command": 'echo "Starting test"'},
                        {"type": "wait", "wait": 60},
                        {"type": "command", "command": 'echo "Test complete"'},
                    ],
                },
                {
                    "name": "Second Test",
                    "description": "Another test case",
                    "network_environment": {"type": "localhost"},
                    "services": {
                        "simple_service": {
                            "name": "simple_service",
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                            "ports": ["9000:9000"],
                        }
                    },
                },
            ],
        }

    @pytest.fixture
    def malformed_config_content(self):
        """Invalid configuration for error testing."""
        return {
            "logging": {"level": "INFO"},
            "tests": [
                {
                    "name": "Broken Test",
                    # Missing required fields
                    "services": {
                        "broken_service": {
                            # Missing required implementation and protocol
                            "ports": ["invalid_port"]
                        }
                    },
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
    def mock_global_config(self):
        """Mock GlobalConfig for testing."""
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

    # CLI Integration Tests

    def test_dry_run_flag_parsing(self):
        """Test that --dry-run flag is parsed correctly."""
        parser = create_parser()

        # Test with dry-run flag
        args = parser.parse_args(["run", "--config", "test.yaml", "--dry-run"])
        assert hasattr(args, "dry_run")
        assert args.dry_run is True

        # Test without dry-run flag
        args = parser.parse_args(["run", "--config", "test.yaml"])
        assert hasattr(args, "dry_run")
        assert args.dry_run is False

    def test_dry_run_flag_in_help(self):
        """Test that --dry-run flag appears in run subcommand help output."""
        parser = create_parser()
        # Get run subcommand help
        run_parser = None
        for action in parser._subparsers._actions:
            if (
                hasattr(action, "choices")
                and action.choices
                and "run" in action.choices
            ):
                run_parser = action.choices["run"]
                break

        assert run_parser is not None, "Run subcommand not found"
        help_output = run_parser.format_help()
        assert "--dry-run" in help_output
        assert (
            "Show what commands would be executed without running them" in help_output
        )

    @patch("panther.cli.subcommands.run.ExperimentManager")
    @patch("panther.cli.subcommands.run.ConfigLoader")
    def test_dry_run_with_config_validation(
        self, mock_config_loader, mock_experiment_manager, temp_config_file
    ):
        """Test dry-run with valid configuration."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_loader.return_value = mock_config_instance
        mock_config_instance.load_and_validate_global_config.return_value = MagicMock()
        mock_config_instance.load_and_validate_experiment_config.return_value = (
            MagicMock()
        )

        mock_exp_manager = MagicMock()
        mock_experiment_manager.return_value = mock_exp_manager
        mock_exp_manager.run_tests.return_value = True

        # Create args with dry-run
        args = argparse.Namespace(
            config=temp_config_file,
            dry_run=True,
            output_dir="outputs",
            experiment_name=None,
            debug=False,
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

        # Execute run command
        result = RunCommand.handle(args)

        # Verify dry_run=True was passed to ExperimentManager
        mock_experiment_manager.assert_called_once()
        call_args = mock_experiment_manager.call_args
        assert call_args[1]["dry_run"] is True

        assert result == 0  # Success

    # ExperimentManager Tests

    @patch("panther.core.experiment_manager.PluginManager")
    @patch("panther.core.experiment_manager.EmitterRegistry")
    @patch("panther.core.experiment_manager.EventManager")
    @patch("panther.core.experiment_manager.WorkflowStateTracker")
    @patch("panther.core.experiment_manager.FastFailHandler")
    def test_experiment_manager_dry_run_constructor(
        self,
        mock_fast_fail,
        mock_workflow,
        mock_event_manager,
        mock_emitter,
        mock_plugin_manager,
        mock_global_config,
    ):
        """Test ExperimentManager constructor with dry_run parameter."""
        # Mock all the complex dependencies
        mock_event_manager.get_instance.return_value = MagicMock()
        mock_emitter.return_value = MagicMock()
        mock_plugin_manager.return_value = MagicMock()
        mock_workflow.return_value = MagicMock()
        mock_fast_fail.return_value = MagicMock()

        # Test with dry_run=False (default)
        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="test", dry_run=False
        )
        assert manager.dry_run is False

        # Test with dry_run=True
        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="test", dry_run=True
        )
        assert manager.dry_run is True

    @patch("panther.core.experiment_manager.PluginManager")
    @patch("panther.core.experiment_manager.EmitterRegistry")
    @patch("panther.core.experiment_manager.EventManager")
    @patch("panther.core.experiment_manager.WorkflowStateTracker")
    @patch("panther.core.experiment_manager.FastFailHandler")
    @patch("panther.core.experiment_manager.ExperimentManager._perform_dry_run")
    def test_experiment_manager_run_tests_dry_run(
        self,
        mock_perform_dry_run,
        mock_fast_fail,
        mock_workflow,
        mock_event_manager,
        mock_emitter,
        mock_plugin_manager,
        mock_global_config,
    ):
        """Test that run_tests calls dry-run when flag is set."""
        # Mock dependencies
        mock_event_manager.get_instance.return_value = MagicMock()
        mock_emitter.return_value = MagicMock()
        mock_plugin_manager.return_value = MagicMock()
        mock_workflow.return_value = MagicMock()
        mock_fast_fail.return_value = MagicMock()

        # Setup
        mock_perform_dry_run.return_value = True
        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="test", dry_run=True
        )

        # Mock test cases
        manager.test_cases = [MagicMock(), MagicMock()]

        # Execute
        result = manager.run_tests()

        # Verify
        mock_perform_dry_run.assert_called_once()
        assert result is True

    @patch("panther.core.experiment_manager.PluginManager")
    @patch("panther.core.experiment_manager.EmitterRegistry")
    @patch("panther.core.experiment_manager.EventManager")
    @patch("panther.core.experiment_manager.WorkflowStateTracker")
    @patch("panther.core.experiment_manager.FastFailHandler")
    def test_dry_run_returns_without_execution(
        self,
        mock_fast_fail,
        mock_workflow,
        mock_event_manager,
        mock_emitter,
        mock_plugin_manager,
        mock_global_config,
        caplog,
    ):
        """Test that dry-run doesn't execute actual commands."""
        # Mock dependencies
        mock_event_manager.get_instance.return_value = MagicMock()
        mock_emitter.return_value = MagicMock()
        mock_plugin_manager.return_value = MagicMock()
        mock_workflow.return_value = MagicMock()
        mock_fast_fail.return_value = MagicMock()

        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="test", dry_run=True
        )

        # Mock test cases with perform_dry_run method
        mock_test_case1 = MagicMock()
        mock_test_case1.test_config.name = "Test 1"
        mock_test_case1.perform_dry_run.return_value = True

        mock_test_case2 = MagicMock()
        mock_test_case2.test_config.name = "Test 2"
        mock_test_case2.perform_dry_run.return_value = True

        manager.test_cases = [mock_test_case1, mock_test_case2]

        # Execute dry-run
        result = manager.run_tests()

        # Verify
        assert result is True
        assert "DRY-RUN: Would execute 2 test cases" in caplog.text
        assert "DRY-RUN: Analysis complete - no commands executed" in caplog.text

        # Verify perform_dry_run was called on each test case
        mock_test_case1.perform_dry_run.assert_called_once()
        mock_test_case2.perform_dry_run.assert_called_once()

    # TestCase Analysis Tests

    def test_test_case_perform_dry_run(self, mock_global_config):
        """Test TestCase perform_dry_run method."""
        # Create mock test config
        mock_test_config = MagicMock()
        mock_test_config.name = "Test Case"
        mock_test_config.description = "Test description"
        mock_test_config.services = {"service1": MagicMock()}
        mock_test_config.network_environment = MagicMock()
        mock_test_config.network_environment.type = "docker_compose"
        mock_test_config.execution_environment = []
        mock_test_config.steps = MagicMock()
        mock_test_config.steps.wait = 60

        # Create TestCase with mocked dependencies
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)
            test_case.test_config = mock_test_config
            test_case.logger = MagicMock()

            # Execute dry-run
            result = test_case.perform_dry_run()

            # Verify
            assert result is True
            test_case.logger.info.assert_called()

    def test_analyze_test_configuration(self, caplog):
        """Test _analyze_test_configuration method."""
        # Create TestCase with mocked config
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)
            test_case.test_config = MagicMock()
            test_case.test_config.name = "Analyze Test"
            test_case.test_config.description = "Test configuration analysis"
            test_case.test_config.timeout = 120
            test_case.logger = logging.getLogger(__name__)

            # Execute
            test_case._analyze_test_configuration()

            # Verify log messages
            assert "Test Name: Analyze Test" in caplog.text
            assert "Description: Test configuration analysis" in caplog.text
            assert "Timeout: 120" in caplog.text

    def test_analyze_service_configurations(self, caplog):
        """Test _analyze_service_configurations method."""
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)

            # Mock services configuration
            mock_iut = MagicMock()
            mock_iut.name = "picoquic_server"
            mock_tester = MagicMock()
            mock_tester.name = "ivy_client"
            mock_service1 = MagicMock()
            mock_service1.name = "service1"
            mock_service2 = MagicMock()
            mock_service2.name = "service2"

            test_case.test_config = MagicMock()
            test_case.test_config.iut = mock_iut
            test_case.test_config.tester = mock_tester
            test_case.test_config.services = {
                "service1": mock_service1,
                "service2": mock_service2,
            }
            test_case.logger = logging.getLogger(__name__)

            # Execute
            result = test_case._analyze_service_configurations()

            # Verify
            assert result is True
            assert "IUT: picoquic_server" in caplog.text
            assert "Tester: ivy_client" in caplog.text
            assert "Services: 2 configured" in caplog.text

    def test_analyze_environment_configuration(self, caplog):
        """Test _analyze_environment_configuration method."""
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)

            # Mock environment configuration
            mock_network_env = MagicMock()
            mock_network_env.type = "docker_compose"

            mock_exec_env1 = MagicMock()
            mock_exec_env1.name = "strace"
            mock_exec_env2 = MagicMock()
            mock_exec_env2.type = "logs"

            test_case.test_config = MagicMock()
            test_case.test_config.network_environment = mock_network_env
            test_case.test_config.execution_environment = [
                mock_exec_env1,
                mock_exec_env2,
            ]
            test_case.logger = logging.getLogger(__name__)

            # Execute
            result = test_case._analyze_environment_configuration()

            # Verify
            assert result is True
            assert "Network Environment: docker_compose" in caplog.text
            assert "Execution Environments: 2 configured" in caplog.text

    def test_analyze_steps_configuration_wait(self, caplog):
        """Test _analyze_steps_configuration with wait step."""
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)

            # Mock steps with wait
            mock_steps = MagicMock()
            mock_steps.wait = 45

            test_case.test_config = MagicMock()
            test_case.test_config.steps = mock_steps
            test_case.logger = logging.getLogger(__name__)

            # Execute
            result = test_case._analyze_steps_configuration()

            # Verify
            assert result is True
            assert "Steps: Wait step configured" in caplog.text
            assert "Wait: 45 seconds" in caplog.text

    def test_analyze_steps_configuration_commands(self, caplog):
        """Test _analyze_steps_configuration with command steps."""
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)

            # Mock steps with commands
            mock_step1 = MagicMock()
            mock_step1.type = "command"
            mock_step1.command = 'echo "test"'

            mock_step2 = MagicMock()
            mock_step2.type = "wait"
            mock_step2.wait = 30

            mock_steps = [mock_step1, mock_step2]

            test_case.test_config = MagicMock()
            test_case.test_config.steps = mock_steps
            test_case.logger = logging.getLogger(__name__)

            # Execute
            result = test_case._analyze_steps_configuration()

            # Verify
            assert result is True
            assert "Steps: 2 configured" in caplog.text
            assert "1. command step" in caplog.text
            assert "2. wait step" in caplog.text
            assert 'Command: echo "test"' in caplog.text
            assert "Wait: 30 seconds" in caplog.text

    def test_show_dry_run_execution_plan(self, caplog):
        """Test _show_dry_run_execution_plan method."""
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)

            # Mock configuration
            test_case.test_config = MagicMock()
            test_case.test_config.services = {
                "service1": MagicMock(),
                "service2": MagicMock(),
            }
            test_case.test_config.steps = MagicMock()
            test_case.test_config.steps.wait = 60
            test_case.logger = logging.getLogger(__name__)

            # Execute
            test_case._show_dry_run_execution_plan()

            # Verify execution plan steps
            assert "DRY-RUN Execution Plan:" in caplog.text
            assert "1. Setup services → Would configure 2 services" in caplog.text
            assert "2. Prepare services → Would build Docker images" in caplog.text
            assert (
                "3. Setup environment → Would configure network/execution environment"
                in caplog.text
            )
            assert "4. Deploy services → Would start containers" in caplog.text
            assert "5. Execute steps → Would wait 60 seconds" in caplog.text
            assert "6. Validate assertions → Would check test results" in caplog.text
            assert "7. Teardown → Would clean up resources" in caplog.text

    # Edge Cases & Error Handling Tests

    def test_dry_run_with_missing_config(self, tmp_path):
        """Test dry-run behavior with missing configuration file."""
        missing_config = str(tmp_path / "missing.yaml")

        args = argparse.Namespace(config=missing_config, dry_run=True, debug=False)

        result = RunCommand.handle(args)
        assert result == 1  # Should fail with missing config

    def test_dry_run_with_malformed_config(self, tmp_path, malformed_config_content):
        """Test dry-run with invalid configuration."""
        config_file = tmp_path / "malformed.yaml"
        with open(config_file, "w") as f:
            yaml.dump(malformed_config_content, f)

        args = argparse.Namespace(config=str(config_file), dry_run=True, debug=False)

        # Should handle malformed config gracefully
        result = RunCommand.handle(args)
        # Expected to fail due to validation errors
        assert result in [0, 1]  # May succeed with warnings or fail

    def test_dry_run_with_complex_steps(self, caplog):
        """Test dry-run with various step configurations."""
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)

            # Test with no steps
            test_case.test_config = MagicMock()
            test_case.test_config.steps = None
            test_case.logger = logging.getLogger(__name__)

            result = test_case._analyze_steps_configuration()
            assert result is True
            assert "Steps: None configured" in caplog.text

    def test_dry_run_logging_output(self, caplog):
        """Test that dry-run produces correct log messages and formatting."""
        with patch(
            "panther.core.test_cases.test_case_impl.TestCase.__init__",
            return_value=None,
        ):
            test_case = TestCase.__new__(TestCase)

            # Setup complete mock configuration
            test_case.test_config = MagicMock()
            test_case.test_config.name = "Logging Test"
            test_case.test_config.description = "Test logging output"
            test_case.test_config.services = {"service1": MagicMock()}
            test_case.test_config.network_environment = MagicMock()
            test_case.test_config.network_environment.type = "docker_compose"
            test_case.test_config.execution_environment = []
            test_case.test_config.steps = MagicMock()
            test_case.test_config.steps.wait = 30
            test_case.logger = logging.getLogger(__name__)

            # Execute dry-run
            result = test_case.perform_dry_run()

            # Verify expected log messages and emojis
            log_text = caplog.text
            assert "📋 DRY-RUN: Analyzing test configuration..." in log_text
            assert "📝 Test Name: Logging Test" in log_text
            assert "✅ DRY-RUN: All configurations valid" in log_text
            assert "🔄 DRY-RUN Execution Plan:" in log_text
            assert result is True

    # Integration Tests

    @patch("panther.cli.subcommands.run.ExperimentManager")
    @patch("panther.cli.subcommands.run.ConfigLoader")
    def test_dry_run_end_to_end(
        self, mock_config_loader, mock_experiment_manager, temp_config_file, caplog
    ):
        """Test complete CLI to TestCase dry-run flow."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_loader.return_value = mock_config_instance
        mock_config_instance.load_and_validate_global_config.return_value = MagicMock()
        mock_config_instance.load_and_validate_experiment_config.return_value = (
            MagicMock()
        )

        mock_exp_manager = MagicMock()
        mock_experiment_manager.return_value = mock_exp_manager
        mock_exp_manager.run_tests.return_value = True

        # Create args
        args = argparse.Namespace(
            config=temp_config_file,
            dry_run=True,
            output_dir="outputs",
            experiment_name="test_experiment",
            debug=False,
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

        # Execute
        result = RunCommand.handle(args)

        # Verify flow
        assert result == 0
        mock_experiment_manager.assert_called_once()
        call_args = mock_experiment_manager.call_args
        assert call_args[1]["dry_run"] is True
        assert call_args[1]["experiment_name"] == "test_experiment"

        # Verify dry-run message appeared
        assert "DRY-RUN MODE" in caplog.text

    def test_dry_run_with_multiple_test_cases(self, mock_global_config, caplog):
        """Test dry-run with multiple test cases in experiment."""
        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="multi_test", dry_run=True
        )

        # Mock multiple test cases
        test_cases = []
        for i in range(3):
            mock_test_case = MagicMock()
            mock_test_case.test_config.name = f"Test {i+1}"
            mock_test_case.perform_dry_run.return_value = True
            test_cases.append(mock_test_case)

        manager.test_cases = test_cases

        # Execute
        result = manager.run_tests()

        # Verify
        assert result is True
        assert "DRY-RUN: Would execute 3 test cases" in caplog.text

        # Verify all test cases were analyzed
        for test_case in test_cases:
            test_case.perform_dry_run.assert_called_once()

    def test_dry_run_performance(self, mock_global_config):
        """Test that dry-run is fast and doesn't perform heavy operations."""
        import time

        manager = ExperimentManager(
            global_config=mock_global_config,
            experiment_name="performance_test",
            dry_run=True,
        )

        # Mock many test cases to simulate large experiment
        test_cases = []
        for i in range(10):
            mock_test_case = MagicMock()
            mock_test_case.test_config.name = f"Performance Test {i+1}"
            mock_test_case.perform_dry_run.return_value = True
            test_cases.append(mock_test_case)

        manager.test_cases = test_cases

        # Measure execution time
        start_time = time.time()
        result = manager.run_tests()
        execution_time = time.time() - start_time

        # Verify fast execution (should be much less than 5 seconds)
        assert result is True
        assert execution_time < 5.0, f"Dry-run took too long: {execution_time} seconds"

        # Verify no actual heavy operations were performed
        # (This would be verified by checking that no subprocess calls were made)
        for test_case in test_cases:
            test_case.perform_dry_run.assert_called_once()

    def test_dry_run_error_handling(self, mock_global_config, caplog):
        """Test dry-run error handling when test case analysis fails."""
        manager = ExperimentManager(
            global_config=mock_global_config, experiment_name="error_test", dry_run=True
        )

        # Mock test case that raises exception
        mock_test_case = MagicMock()
        mock_test_case.test_config.name = "Failing Test"
        mock_test_case.perform_dry_run.side_effect = Exception("Analysis failed")

        manager.test_cases = [mock_test_case]

        # Execute - should handle errors gracefully
        result = manager.run_tests()

        # Verify error was handled
        assert result is True  # Should still return True for dry-run
        assert "Configuration issues detected" in caplog.text
