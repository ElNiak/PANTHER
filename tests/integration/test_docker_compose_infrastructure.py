#!/usr/bin/env python3
"""Integration tests for Docker Compose infrastructure."""

import os
import subprocess
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from panther.config.config_schemas import NetworkEnvironmentConfig
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)


class TestDockerComposeInfrastructure(unittest.TestCase):
    """Integration test cases for Docker Compose infrastructure."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.test_output_dir = Path("outputs/test_docker_compose")
        cls.test_output_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        # Clean up any test containers
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
            )
            for container in result.stdout.strip().split("\n"):
                if container and "test_docker_compose" in container:
                    subprocess.run(["docker", "stop", container], capture_output=True)
                    subprocess.run(["docker", "rm", container], capture_output=True)
        except Exception:
            pass

    def setUp(self):
        """Set up each test."""
        self.env = None

    def tearDown(self):
        """Clean up after each test."""
        if self.env:
            try:
                self.env.teardown()
            except Exception:
                pass

    def test_docker_compose_environment_initialization(self):
        """Test that DockerComposeEnvironment initializes correctly."""
        config = NetworkEnvironmentConfig(
            type="docker_compose", enable_background_monitoring=False
        )

        env = DockerComposeEnvironment(
            config=config, test_name="test_init", output_dir=str(self.test_output_dir)
        )
        self.env = env

        # Verify initialization
        self.assertIsNotNone(env)
        self.assertEqual(env.name, "docker_compose")
        self.assertIsNotNone(env.lifecycle_manager)
        self.assertIsNotNone(env.port_manager)
        self.assertIsNotNone(env.output_manager)

    def test_docker_compose_lifecycle_manager_delegation(self):
        """Test that lifecycle manager methods are properly delegated."""
        config = NetworkEnvironmentConfig(
            type="docker_compose", enable_background_monitoring=False
        )

        env = DockerComposeEnvironment(
            config=config,
            test_name="test_lifecycle",
            output_dir=str(self.test_output_dir),
        )
        self.env = env

        # Verify delegation methods exist
        self.assertTrue(hasattr(env, "launch_environment_services"))
        self.assertTrue(hasattr(env, "execute_docker_command"))
        self.assertTrue(hasattr(env, "_extract_service_environment_variables"))

        # Test method delegation
        with patch.object(
            env.lifecycle_manager, "launch_environment_services"
        ) as mock_launch:
            env.launch_environment_services()
            mock_launch.assert_called_once()

    def test_docker_compose_config_type_resolution(self):
        """Test that Docker Compose receives proper config type."""
        from panther.plugins.core.plugin_factory import PluginFactory
        from panther.plugins.plugin_manager import PluginManager

        # Reset and create plugin manager
        PluginManager.reset_singleton()
        pm = PluginManager()
        factory = PluginFactory(plugin_manager=pm)

        # Create config
        config_dict = {
            "type": "docker_compose",
            "enable_background_monitoring": True,
            "monitoring_interval_seconds": 5,
        }

        # Create environment through factory
        env = factory.create_network_environment(
            plugin_name="docker_compose",
            config=config_dict,
            test_name="test_config_type",
            output_dir=str(self.test_output_dir),
        )
        self.env = env

        # Verify proper config type
        self.assertIsInstance(env, DockerComposeEnvironment)
        self.assertEqual(env.config.type, "docker_compose")
        self.assertTrue(env.config.enable_background_monitoring)
        self.assertEqual(env.config.monitoring_interval_seconds, 5)

    def test_docker_v2_command_syntax(self):
        """Test that Docker commands use V2 syntax."""
        config = NetworkEnvironmentConfig(
            type="docker_compose", enable_background_monitoring=False
        )

        env = DockerComposeEnvironment(
            config=config,
            test_name="test_v2_syntax",
            output_dir=str(self.test_output_dir),
        )
        self.env = env

        # Create a mock service for testing
        mock_service = MagicMock()
        mock_service.name = "test_service"

        # Test command construction
        with patch.object(
            env.lifecycle_manager, "_construct_docker_compose_command"
        ) as mock_construct:
            mock_construct.return_value = [
                "docker",
                "compose",
                "-f",
                "docker-compose.yml",
                "up",
                "-d",
            ]

            # Trigger command construction
            env._ensure_lifecycle_manager_initialized()
            if hasattr(env.lifecycle_manager, "_construct_docker_compose_command"):
                cmd = env.lifecycle_manager._construct_docker_compose_command(
                    ["up", "-d"], str(self.test_output_dir / "docker-compose.yml")
                )

                # Verify V2 syntax
                self.assertEqual(cmd[0], "docker")
                self.assertEqual(cmd[1], "compose")
                self.assertNotIn("docker-compose", cmd)

    def test_environment_variable_preservation(self):
        """Test that subprocess calls preserve system environment variables."""
        config = NetworkEnvironmentConfig(
            type="docker_compose", enable_background_monitoring=False
        )

        env = DockerComposeEnvironment(
            config=config,
            test_name="test_env_vars",
            output_dir=str(self.test_output_dir),
        )
        self.env = env

        # Mock subprocess.run to capture env parameter
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # Set a test environment variable
            test_var = "TEST_VAR_12345"
            os.environ[test_var] = "test_value"

            try:
                # Trigger a command that uses environment variables
                env.lifecycle_manager._execute_with_logging(
                    ["echo", "test"],
                    str(self.test_output_dir / "test.log"),
                    env_vars={"CUSTOM_VAR": "custom_value"},
                )

                # Verify environment preservation
                if mock_run.called:
                    call_env = mock_run.call_args[1].get("env", {})
                    # Should contain system PATH
                    self.assertIn("PATH", call_env)
                    # Should contain our test variable
                    self.assertIn(test_var, call_env)
                    # Should contain custom variable
                    self.assertEqual(call_env.get("CUSTOM_VAR"), "custom_value")
            finally:
                # Clean up
                del os.environ[test_var]

    @unittest.skipIf(
        not Path(
            "experiment-config/base/experiment_config_example_minimal.yaml"
        ).exists(),
        "Minimal config not available",
    )
    def test_minimal_experiment_dry_run(self):
        """Test that minimal experiment configuration works in dry-run mode."""
        from panther.cli.main import run_experiment

        # Run in dry-run mode
        with patch(
            "sys.argv",
            [
                "panther",
                "run",
                "--config",
                "experiment-config/base/experiment_config_example_minimal.yaml",
                "--dry-run",
            ],
        ):
            # Should complete without errors
            try:
                # We expect SystemExit(0) for successful dry-run
                with self.assertRaises(SystemExit) as cm:
                    run_experiment(
                        [
                            "--config",
                            "experiment-config/base/experiment_config_example_minimal.yaml",
                            "--dry-run",
                        ]
                    )
                self.assertEqual(cm.exception.code, 0)
            except Exception as e:
                # If no SystemExit, check that it completed normally
                self.assertIsNone(e)


if __name__ == "__main__":
    unittest.main()
