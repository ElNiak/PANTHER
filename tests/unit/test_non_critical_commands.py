#!/usr/bin/env python3

"""
Unit tests for non-critical command creation and processing in Docker Compose environment.
"""

import unittest
from unittest.mock import MagicMock

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)
from panther.plugins.environments.config_schema import EnvironmentConfig


class TestNonCriticalCommandCreation(unittest.TestCase):
    """Test the non-critical command creation functionality in Docker Compose environment."""

    def setUp(self):
        """Set up the test environment."""
        # Mock environment config
        env_config = MagicMock(spec=EnvironmentConfig)
        output_dir = "/tmp/output"
        env_type = "network_environment"
        env_sub_type = "docker_compose"
        event_manager = EventManager()

        # Create DockerComposeEnvironment instance
        self.docker_env = DockerComposeEnvironment(
            env_config, output_dir, env_type, env_sub_type, event_manager
        )

    def test_create_single_line_non_critical_command(self):
        """Test creation of a single line non-critical command."""
        command_lines = ["echo 'This is a test'"]
        result = self.docker_env.create_non_critical_command(command_lines)

        expected = "# PANTHER_NON_CRITICAL_COMMAND\necho 'This is a test'"
        self.assertEqual(result, expected)

    def test_create_multi_line_non_critical_command(self):
        """Test creation of a multi-line non-critical command."""
        command_lines = [
            "while [ ! -f /app/sync_logs/ivy_ready.log ]; do",
            '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;',
            "\tsleep 2;",
            "done;",
            'echo "Ivy testers is ready, starting test..." >> /app/logs/tester_ready.log;',
        ]
        result = self.docker_env.create_non_critical_command(command_lines)

        expected = (
            "# PANTHER_NON_CRITICAL_COMMAND\n"
            "while [ ! -f /app/sync_logs/ivy_ready.log ]; do\n"
            '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;\n'
            "\tsleep 2;\n"
            "done;\n"
            'echo "Ivy testers is ready, starting test..." >> /app/logs/tester_ready.log;'
        )
        self.assertEqual(result, expected)

    def test_create_non_critical_command_with_newlines(self):
        """Test creation of a non-critical command with pre-existing newlines."""
        command_lines = [
            "while [ ! -f /app/sync_logs/ivy_ready.log ]; do\n",
            '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;\n',
            "\tsleep 2;\n",
            "done;\n",
        ]
        result = self.docker_env.create_non_critical_command(command_lines)

        expected = (
            "# PANTHER_NON_CRITICAL_COMMAND\n"
            "while [ ! -f /app/sync_logs/ivy_ready.log ]; do\n"
            '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;\n'
            "\tsleep 2;\n"
            "done;"
        )
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
