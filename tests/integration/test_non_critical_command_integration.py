#!/usr/bin/env python3

"""
Integration test for non-critical command handling in Docker Compose environment.
This test creates a simple environment with an Ivy service and a client service
that has a non-critical command to wait for Ivy to be ready.
"""

import os
import tempfile
import shutil
import argparse
import logging
from pathlib import Path

from panther.core.observer.event_manager import EventManager
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.config_schema import EnvironmentConfig


class MockServiceManager(IServiceManager):
    """Mock service manager for testing."""

    def __init__(self, service_name, is_ivy=False):
        """Initialize with basic properties."""
        self.service_name = service_name
        self.is_ivy = is_ivy
        self.volumes = []
        self.environments = {}
        self.run_cmd = {
            "pre_compile_cmds": ["echo Setting up service"],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "post_run_cmds": [],
            "run_cmd": {
                "timeout": 10,
                "command_binary": "echo",
                "command_args": f"'Running {service_name}'",
                "command_env": {},
                "working_dir": "/app",
            },
        }

        # Set up common properties expected by the environment
        self.role = type("Role", (), {"name": "server" if is_ivy else "client"})
        self.service_type = "testers" if is_ivy else "implementation"
        self.service_config_to_test = type("ServiceConfig", (), {"timeout": 60})
        self.execution_status = {
            "exit_code": None,
            "error_type": None,
            "failed": False,
            "status": "not_started",
        }

        # Add service-specific commands
        if is_ivy:
            # Add special command for Ivy service to signal readiness
            self.run_cmd["post_compile_cmds"].append("mkdir -p /app/sync_logs")
            self.run_cmd["post_compile_cmds"].append(
                "touch /app/sync_logs/ivy_ready.log"
            )
        else:
            # Client service just runs normally
            pass

    def get_service_name(self):
        """Return the service name."""
        return self.service_name

    def get_execution_status(self):
        """Return the execution status."""
        return self.execution_status

    def set_execution_status(self, **kwargs):
        """Update the execution status."""
        self.execution_status.update(kwargs)


def run_non_critical_test():
    """Run a test with a non-critical command to wait for Ivy service."""
    # Create temp directory for test outputs
    output_dir = tempfile.mkdtemp(prefix="panther_non_critical_test_")
    logging.info(f"Created temp directory at {output_dir}")

    try:
        # Set up environment
        env_config = EnvironmentConfig(
            name="non_critical_test",
            environment_type="network_environment",
            environment_sub_type="docker_compose",
        )

        # Create event manager
        event_manager = EventManager()

        # Create Docker Compose environment
        docker_env = DockerComposeEnvironment(
            env_config,
            output_dir,
            "network_environment",
            "docker_compose",
            event_manager,
        )

        # Create mock services
        ivy_service = MockServiceManager("ivy_tester", is_ivy=True)
        client_service = MockServiceManager("test_client")

        # Set up DockerComposeEnvironment with necessary directory structure
        logs_dir = os.path.join(output_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)

        # Add the services to the environment
        docker_env.services_managers = [ivy_service, client_service]
        docker_env._plugin_dir = str(Path(__file__).parent.parent)

        # Need to manually trigger the code that adds non-critical commands
        # This is a simulation of what happens in generate_environment_services()
        if "ivy" in ivy_service.service_name:
            for other_service in docker_env.services_managers:
                if other_service.service_name != ivy_service.service_name:
                    other_service.volumes.append("shared_logs:/app/sync_logs")

                    # Create a non-critical waiting command
                    command_lines = [
                        "while [ ! -f /app/sync_logs/ivy_ready.log ]; do",
                        '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;',
                        "\tsleep 2;",
                        "done;",
                        f'echo "Ivy testers is ready, starting {other_service.service_name}..." >> /app/logs/tester_ready.log;',
                    ]
                    non_critical_cmd = docker_env.create_non_critical_command(
                        command_lines
                    )

                    # Add to post-compile commands
                    other_service.run_cmd["post_compile_cmds"].append(non_critical_cmd)

        # Generate test report summary
        # Create some mock log files to test the non-critical failure detection
        warning_log = os.path.join(logs_dir, "test_client_POST_COMPILE_warning.log")
        with open(warning_log, "w") as f:
            f.write("Non-critical command 'wait for ivy' failed with exit code 1\n")
            f.write(
                "Execution continuing despite error at Wed Jun 01 09:45:18 CEST 2025\n"
            )

        # Set some test status information
        client_service.execution_status = {
            "exit_code": 0,
            "error_type": None,
            "failed": False,
            "status": "completed",
        }

        ivy_service.execution_status = {
            "exit_code": 0,
            "error_type": None,
            "failed": False,
            "status": "completed",
        }

        # Generate the test report summary
        docker_env.generate_test_report_summary()

        # Check if the summary file was generated
        summary_path = os.path.join(logs_dir, "test-execution-summary.log")
        if os.path.exists(summary_path):
            with open(summary_path) as f:
                content = f.read()
                logging.info(f"Test Summary Content:\n{content}")
        else:
            logging.error(f"Test summary file not found at {summary_path}")

        logging.info(f"Test completed. Check {output_dir} for results.")
        return output_dir
    except Exception as e:
        logging.error(f"Test failed: {str(e)}")
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Test non-critical command handling")
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Keep the output directory after the test",
    )
    args = parser.parse_args()

    try:
        output_dir = run_non_critical_test()
        if not args.keep_output:
            logging.info(f"Cleaning up output directory: {output_dir}")
            shutil.rmtree(output_dir, ignore_errors=True)
        else:
            logging.info(f"Output directory preserved at: {output_dir}")
    except Exception:
        logging.exception("Test failed with error:")
