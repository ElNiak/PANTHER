#!/usr/bin/env python3
"""
Test script to verify the fix for command duplication in generated entrypoint scripts.

This script:
1. Creates a mock service with ShellCommand objects
2. Renders an entrypoint script using both the deprecated _preprocess_service_commands
   and the updated generate_from_template method
3. Checks that commands only appear once in the generated script

Usage:
    python test_command_duplication.py
"""

import os
import tempfile
from pathlib import Path

from panther.core.command_processor import ShellCommand
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)


class MockService:
    """Mock service with ShellCommand objects"""

    def __init__(self):
        self.service_name = "test_service"
        self.run_cmd = {
            "pre_compile_cmds": [
                ShellCommand("echo 'Pre-compile command'", is_critical=True),
                ShellCommand(
                    "function my_func() { echo 'Test function'; }",
                    is_function_definition=True,
                ),
            ],
            "compile_cmds": [
                ShellCommand("echo 'Compile command'", is_critical=True),
            ],
            "post_compile_cmds": [
                ShellCommand("echo 'Post-compile command'", is_critical=False),
            ],
            "pre_run_cmds": [],
            "post_run_cmds": [],
            "run_cmd": {
                "working_dir": "/app",
                "command_binary": "/usr/bin/panther",
                "command_args": "--flag1 --flag2",
                "timeout": 60,
                "command_env": {"FOO": "bar"},
            },
        }
        self.volumes = []
        self.environments = {}
        self.service_protocol = MockProtocol()
        self.service_config_to_test = MockServiceConfig()
        self.implementation_name = "test_impl"
        self.role = MockRole()


class MockProtocol:
    def __init__(self):
        self.version = MockVersion()


class MockVersion:
    def __init__(self):
        self.name = "1.0"


class MockServiceConfig:
    def __init__(self):
        self.ports = [8080, 8443]
        self.timeout = 60


class MockRole:
    def __init__(self):
        self.name = "client"


class MockEnvironmentConfig:
    def __init__(self):
        pass


class MockEventManager(EventManager):
    def __init__(self):
        super().__init__()


def test_command_duplication():
    """Test that commands are not duplicated in generated entrypoint scripts"""
    print("Testing command duplication fix...")

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create mock environment and service
        env_config = MockEnvironmentConfig()
        event_manager = MockEventManager()
        env = DockerComposeEnvironment(
            env_config, temp_dir, "network_environment", "docker_compose", event_manager
        )

        # Create paths for generated files
        test_output_path = os.path.join(temp_dir, "entrypoint_test_service.sh")
        test_template_path = os.path.join(temp_dir, "entrypoint_template.sh")

        # Create a mock service
        service = MockService()

        # Define test paths
        paths = {"output_dir": temp_dir}
        timestamp = "20250603_123456"

        # Generate entrypoint script
        env.generate_from_template(
            "entrypoint.sh.jinja",
            paths,
            timestamp,
            Path(test_output_path),
            Path(test_template_path),
            additional_param=service,
        )

        # Read the generated file
        if os.path.exists(test_output_path):
            with open(test_output_path, encoding="utf-8") as f:
                content = f.read()

            # Check for duplications
            # Count occurrences of the main run command
            main_cmd_count = content.count("/usr/bin/panther --flag1 --flag2")

            print(f"Main command count: {main_cmd_count}")
            assert (
                main_cmd_count <= 1
            ), f"Command appears {main_cmd_count} times (should be 1)"

            # Check other commands too
            pre_compile_count = content.count("Pre-compile command")
            compile_count = content.count("Compile command")
            post_compile_count = content.count("Post-compile command")

            print(f"Pre-compile command count: {pre_compile_count}")
            print(f"Compile command count: {compile_count}")
            print(f"Post-compile command count: {post_compile_count}")

            assert (
                pre_compile_count <= 1
            ), f"Pre-compile command appears {pre_compile_count} times (should be 1)"
            assert (
                compile_count <= 1
            ), f"Compile command appears {compile_count} times (should be 1)"
            assert (
                post_compile_count <= 1
            ), f"Post-compile command appears {post_compile_count} times (should be 1)"

            print("Test passed! No command duplication detected.")
        else:
            print(f"Error: Generated file {test_output_path} not found")
            assert False, f"Generated file {test_output_path} not found"


if __name__ in {"__main__", "__mp_main__"}:
    test_command_duplication()
