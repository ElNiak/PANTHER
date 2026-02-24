#!/usr/bin/env python3

"""
Integration tests specifically for non-critical command support in Docker Compose environment
"""

import os
import shutil
from unittest.mock import MagicMock

import pytest

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)


class TestNonCriticalCommands:
    """Test suite for non-critical command handling in Docker Compose environment."""

    @pytest.fixture
    def setup_environment(self, tmpdir):
        """Set up a test environment with mock config."""
        env_config = MagicMock(spec=EnvironmentConfig)
        output_dir = str(tmpdir.mkdir("output"))
        env_type = "network_environment"
        env_sub_type = "docker_compose"
        event_manager = EventManager()

        # Create logs directory in output_dir
        os.makedirs(os.path.join(output_dir, "logs"), exist_ok=True)

        # Create DockerComposeEnvironment instance
        docker_env = DockerComposeEnvironment(
            env_config, output_dir, env_type, env_sub_type, event_manager
        )

        # Mock some necessary attributes
        docker_env._plugin_dir = str(tmpdir)
        docker_env.services_managers = []

        # Return test environment
        yield docker_env, output_dir

        # Cleanup after test
        shutil.rmtree(output_dir, ignore_errors=True)

    def test_has_non_critical_failures_no_warnings(self, setup_environment):
        """Test has_non_critical_failures when no warning logs exist."""
        docker_env, output_dir = setup_environment

        # Test with a service that has no warning logs
        assert not docker_env.has_non_critical_failures("test_service")

    def test_has_non_critical_failures_with_warnings(self, setup_environment):
        """Test has_non_critical_failures when warning logs exist."""
        docker_env, output_dir = setup_environment

        # Create a mock warning log file
        service_name = "test_service"
        warning_log = os.path.join(
            output_dir, "logs", f"{service_name}_POST_COMPILE_warning.log"
        )
        with open(warning_log, "w") as f:
            f.write("Non-critical command failed with exit code 1\n")
            f.write("Execution continuing despite error\n")

        # Check for non-critical failures
        assert docker_env.has_non_critical_failures(service_name)

    def test_get_non_critical_failure_details(self, setup_environment):
        """Test get_non_critical_failure_details reads warning logs correctly."""
        docker_env, output_dir = setup_environment

        # Create multiple mock warning log files
        service_name = "test_service"
        post_compile_warning = os.path.join(
            output_dir, "logs", f"{service_name}_POST_COMPILE_warning.log"
        )
        pre_run_warning = os.path.join(
            output_dir, "logs", f"{service_name}_PRE_RUN_warning.log"
        )

        with open(post_compile_warning, "w") as f:
            f.write("Non-critical command 'wait for ivy' failed with exit code 1\n")
            f.write("Execution continuing despite error\n")

        with open(pre_run_warning, "w") as f:
            f.write(
                "Non-critical command 'some other command' failed with exit code 2\n"
            )

        # Get failure details
        details = docker_env.get_non_critical_failure_details(service_name)

        # Verify results
        assert "POST_COMPILE" in details
        assert "PRE_RUN" in details
        assert (
            "Non-critical command 'wait for ivy' failed with exit code 1"
            in details["POST_COMPILE"]
        )
        assert (
            "Non-critical command 'some other command' failed with exit code 2"
            in details["PRE_RUN"]
        )

    def test_generate_test_report_summary_with_warnings(self, setup_environment):
        """Test generate_test_report_summary properly handles warnings."""
        docker_env, output_dir = setup_environment

        # Create a mock service manager
        service_manager = MagicMock()
        service_manager.get_service_name.return_value = "test_service"
        service_manager.get_execution_status.return_value = {
            "exit_code": 0,
            "error_type": "NONE",
            "failed": False,
            "status": "completed",
        }
        docker_env.services_managers = [service_manager]

        # Create a mock warning log
        warning_log = os.path.join(
            output_dir, "logs", "test_service_POST_COMPILE_warning.log"
        )
        with open(warning_log, "w") as f:
            f.write("Non-critical command 'wait for ivy' failed with exit code 1\n")

        # Create mock container status method
        docker_env.get_container_status = MagicMock(return_value="exited normally")

        # Generate test report summary
        docker_env.generate_test_report_summary()

        # Check if summary file was generated with the correct content
        summary_file_path = os.path.join(
            output_dir, "logs", "test-execution-summary.log"
        )
        assert os.path.exists(summary_file_path)

        with open(summary_file_path) as f:
            content = f.read()
            # Check for the expected report content
            assert "OVERALL TEST RESULT: PASSED WITH WARNINGS" in content
            assert "Non-Critical Warnings:" in content
            assert (
                "Note: Non-critical failures are reported but don't mark the test as failed"
                in content
            )
            assert "Status: WARNING" in content
