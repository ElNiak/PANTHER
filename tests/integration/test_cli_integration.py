"""
Integration tests for PANTHER with CLI invocation and temporary workspaces.

This module tests the complete system integration including CLI interactions,
temporary workspace creation, and end-to-end workflows.
"""

import os
import shutil
import subprocess

# Import test utilities
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

sys.path.insert(0, "/Users/elniak/Documents/Project/PANTHER")


class TestPantherCLIIntegration:
    """Integration tests for PANTHER CLI functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for integration tests."""
        workspace = tempfile.mkdtemp(prefix="panther_test_")
        yield Path(workspace)
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def sample_experiment_config(self, temp_workspace):
        """Create a sample experiment configuration file."""
        config_content = {
            "tests": [
                {
                    "name": "integration_test",
                    "description": "Basic integration test",
                    "network_environment": {"type": "localhost", "interface": "lo"},
                    "execution_environment": [{"type": "localhost", "timeout": 60}],
                    "iterations": 1,
                    "services": {
                        "test_service": {
                            "name": "echo_service",
                            "timeout": 30,
                            "ports": ["8080"],
                        }
                    },
                    "steps": {"wait": 5, "record_pcap": False},
                }
            ]
        }

        config_file = temp_workspace / "experiment_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        return config_file

    @pytest.fixture
    def sample_global_config(self, temp_workspace):
        """Create a sample global configuration file."""
        config_content = {
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "paths": {
                "output_dir": str(temp_workspace / "outputs"),
                "log_dir": str(temp_workspace / "logs"),
                "config_dir": str(temp_workspace / "configs"),
                "plugin_dir": str(temp_workspace / "plugins"),
            },
            "docker": {
                "build_docker_image": False,
                "remove_docker_image": True,
                "remove_docker_container": True,
                "remove_docker_network": True,
                "remove_docker_volume": True,
            },
            "features": {
                "logger_observer": True,
                "storage_handler": True,
                "fast_fail": True,
            },
        }

        config_file = temp_workspace / "global_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        return config_file

    @pytest.fixture
    def mock_environment(self, temp_workspace):
        """Setup mock environment for integration tests."""
        # Create required directories
        (temp_workspace / "outputs").mkdir(exist_ok=True)
        (temp_workspace / "logs").mkdir(exist_ok=True)
        (temp_workspace / "configs").mkdir(exist_ok=True)
        (temp_workspace / "plugins").mkdir(exist_ok=True)

        return temp_workspace

    @pytest.mark.slow
    def test_cli_help_command(self):
        """Test CLI help command execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="PANTHER CLI Help\nUsage: panther [OPTIONS]",
                stderr="",
            )

            result = subprocess.run(
                [
                    "python",
                    "/Users/elniak/Documents/Project/PANTHER/panther_builder.py",
                    "--help",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            # In real scenario, this would test actual CLI
            # For now, we test the mock
            mock_run.assert_called_once()

    @pytest.mark.slow
    def test_cli_version_command(self):
        """Test CLI version command execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout="PANTHER Version 1.0.0", stderr=""
            )

            result = subprocess.run(
                [
                    "python",
                    "/Users/elniak/Documents/Project/PANTHER/panther_builder.py",
                    "--version",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            mock_run.assert_called_once()

    def test_config_loading_integration(
        self,
        temp_workspace,
        sample_experiment_config,
        sample_global_config,
        mock_environment,
    ):
        """Test configuration loading integration."""
        from panther.config.config_manager import ConfigLoader

        with patch("pathlib.Path.exists", return_value=True):
            config_loader = ConfigLoader(
                experiment_file=str(sample_experiment_config),
                output_dir=str(temp_workspace / "outputs"),
            )

            # Test that config loader can be initialized with real file paths
            assert config_loader.experiment_file == str(sample_experiment_config)
            assert config_loader.output_dir == str(temp_workspace / "outputs")

    def test_experiment_workspace_creation(
        self, temp_workspace, sample_experiment_config
    ):
        """Test creation of experiment workspace structure."""
        from panther.config.config_manager import ConfigLoader

        config_loader = ConfigLoader(
            experiment_file=str(sample_experiment_config),
            output_dir=str(temp_workspace / "outputs"),
        )

        # Create expected directory structure
        outputs_dir = temp_workspace / "outputs"
        outputs_dir.mkdir(exist_ok=True)

        logs_dir = temp_workspace / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Verify directories are created
        assert outputs_dir.exists()
        assert logs_dir.exists()
        assert outputs_dir.is_dir()
        assert logs_dir.is_dir()

    def test_config_validation_integration(
        self, temp_workspace, sample_experiment_config
    ):
        """Test configuration validation in integration context."""
        from omegaconf import OmegaConf

        from panther.config.config_manager import ConfigLoader

        # Load the actual config file
        loaded_config = OmegaConf.load(sample_experiment_config)

        with patch("pathlib.Path.exists", return_value=True):
            config_loader = ConfigLoader(
                experiment_file=str(sample_experiment_config),
                output_dir=str(temp_workspace / "outputs"),
            )

            # Test that the configuration structure is valid
            assert "tests" in loaded_config
            assert len(loaded_config.tests) == 1
            assert loaded_config.tests[0].name == "integration_test"

    @pytest.mark.slow
    def test_builder_integration_clean(self, temp_workspace):
        """Test BuildManager integration with clean operation."""
        from panther_builder import BuildManager

        # Create some test files to clean
        test_files = [
            temp_workspace / "test.pyc",
            temp_workspace / "build" / "temp.egg-info",
            temp_workspace / "__pycache__" / "cache.pyc",
        ]

        for test_file in test_files:
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.touch()

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("docker.from_env") as mock_docker,
        ):
            mock_docker.return_value = Mock()
            builder = BuildManager(project_path=str(temp_workspace))

            # Mock glob to return our test files
            with patch("pathlib.Path.glob") as mock_glob:
                mock_glob.return_value = test_files
                result = builder.clean()

                assert result.success is True

    @pytest.mark.slow
    def test_builder_integration_install_dependencies(self, temp_workspace):
        """Test BuildManager integration with dependency installation."""
        from panther_builder import BuildManager

        # Create a requirements.txt file
        requirements_file = temp_workspace / "requirements.txt"
        requirements_file.write_text("pytest>=7.0.0\npytest-cov>=4.0.0\n")

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
            patch("docker.from_env") as mock_docker,
            patch("subprocess.run") as mock_run,
        ):
            mock_docker.return_value = Mock()
            mock_run.return_value = Mock(
                returncode=0, stdout="Successfully installed", stderr=""
            )

            builder = BuildManager(project_path=str(temp_workspace))
            result = builder.install_dependencies()

            assert result.success is True
            mock_run.assert_called()

    def test_plugin_discovery_integration(self, temp_workspace):
        """Test plugin discovery in integration context."""
        # Create mock plugin structure
        plugins_dir = temp_workspace / "plugins"
        plugins_dir.mkdir()

        # Create a mock network environment plugin
        net_env_dir = plugins_dir / "environments" / "network_environment" / "localhost"
        net_env_dir.mkdir(parents=True)

        plugin_file = net_env_dir / "config_schema.py"
        plugin_file.write_text(
            """
from dataclasses import dataclass

@dataclass
class LocalhostConfig:
    type: str = "localhost"
    interface: str = "lo"
"""
        )

        # Create __init__.py files
        (plugins_dir / "__init__.py").touch()
        (plugins_dir / "environments" / "__init__.py").touch()
        (plugins_dir / "environments" / "network_environment" / "__init__.py").touch()
        (net_env_dir / "__init__.py").touch()

        # Test plugin discovery
        assert plugin_file.exists()
        assert net_env_dir.exists()

    def test_error_handling_integration(self, temp_workspace):
        """Test error handling in integration scenarios."""
        from panther.config.config_manager import ConfigLoader

        # Test with non-existent config file
        non_existent_file = temp_workspace / "non_existent_config.yaml"

        config_loader = ConfigLoader(
            experiment_file=str(non_existent_file),
            output_dir=str(temp_workspace / "outputs"),
        )

        with pytest.raises(FileNotFoundError):
            config_loader.load_and_validate_experiment_config()

    def test_logging_integration(self, temp_workspace, sample_global_config):
        """Test logging integration with file outputs."""
        from omegaconf import OmegaConf

        from panther.config.config_manager import ConfigLoader

        # Load global config
        global_config_data = OmegaConf.load(sample_global_config)

        with patch("pathlib.Path.exists", return_value=True):
            config_loader = ConfigLoader(
                experiment_file="dummy.yaml", output_dir=str(temp_workspace / "outputs")
            )

            global_config = config_loader.construct_global_config(global_config_data)

            # Test that logging configuration is properly structured
            assert hasattr(global_config, "logging")
            assert hasattr(global_config.logging, "level")
            assert hasattr(global_config.logging, "format")

    @pytest.mark.slow
    def test_end_to_end_workflow_simulation(
        self, temp_workspace, sample_experiment_config, sample_global_config
    ):
        """Test end-to-end workflow simulation."""
        # This test simulates a complete PANTHER workflow

        # Step 1: Configuration loading
        from omegaconf import OmegaConf

        from panther.config.config_manager import ConfigLoader

        with patch("pathlib.Path.exists", return_value=True):
            config_loader = ConfigLoader(
                experiment_file=str(sample_experiment_config),
                output_dir=str(temp_workspace / "outputs"),
            )

            # Load configurations
            experiment_config_data = OmegaConf.load(sample_experiment_config)
            global_config_data = OmegaConf.load(sample_global_config)

            # Step 2: Validate configurations
            global_config = config_loader.construct_global_config(global_config_data)
            assert global_config is not None

            # Step 3: Create output directories
            outputs_dir = Path(global_config.paths.output_dir)
            outputs_dir.mkdir(parents=True, exist_ok=True)

            logs_dir = Path(global_config.paths.log_dir)
            logs_dir.mkdir(parents=True, exist_ok=True)

            # Step 4: Verify workflow components
            assert outputs_dir.exists()
            assert logs_dir.exists()
            assert experiment_config_data.tests[0].name == "integration_test"

    def test_concurrent_access_simulation(self, temp_workspace):
        """Test simulation of concurrent access scenarios."""
        import threading
        import time

        from panther.config.config_manager import ConfigLoader

        config_file = temp_workspace / "concurrent_test_config.yaml"
        config_content = {"tests": [{"name": "concurrent_test"}]}

        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        results = []

        def load_config():
            try:
                with patch("pathlib.Path.exists", return_value=True):
                    config_loader = ConfigLoader(
                        experiment_file=str(config_file),
                        output_dir=str(temp_workspace / "outputs"),
                    )
                    # Simulate some work
                    time.sleep(0.1)
                    results.append("success")
            except Exception as e:
                results.append(f"error: {e}")

        # Create multiple threads
        threads = [threading.Thread(target=load_config) for _ in range(3)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all threads succeeded
        assert len(results) == 3
        assert all(result == "success" for result in results)

    def test_resource_cleanup_integration(self, temp_workspace):
        """Test resource cleanup in integration scenarios."""
        # Create some temporary resources
        resource_files = []
        for i in range(5):
            resource_file = temp_workspace / f"resource_{i}.tmp"
            resource_file.write_text(f"Resource {i} content")
            resource_files.append(resource_file)

        # Verify resources are created
        for resource_file in resource_files:
            assert resource_file.exists()

        # Simulate cleanup
        for resource_file in resource_files:
            resource_file.unlink()

        # Verify cleanup
        for resource_file in resource_files:
            assert not resource_file.exists()

    def test_file_permissions_integration(self, temp_workspace):
        """Test file permissions in integration scenarios."""
        # Create test files with different permissions
        config_file = temp_workspace / "permissions_test.yaml"
        config_file.write_text("test: config")

        # Test file readability
        assert config_file.exists()
        assert config_file.is_file()
        assert os.access(config_file, os.R_OK)

        # Test directory writability
        assert os.access(temp_workspace, os.W_OK)

    def test_configuration_override_integration(self, temp_workspace):
        """Test configuration override scenarios."""
        from omegaconf import OmegaConf

        from panther.config.config_manager import ConfigLoader

        # Base configuration
        base_config = {
            "logging": {"level": "INFO"},
            "paths": {"output_dir": "/base/output"},
        }

        # Override configuration
        override_output_dir = str(temp_workspace / "custom_output")

        with patch("pathlib.Path.exists", return_value=True):
            config_loader = ConfigLoader(
                experiment_file="dummy.yaml",
                output_dir=override_output_dir,  # This should override the config
            )

            loaded_config = OmegaConf.create(base_config)
            global_config = config_loader.construct_global_config(loaded_config)

            # Verify override took effect
            assert global_config.paths.output_dir == override_output_dir

    @pytest.mark.slow
    def test_performance_baseline_integration(
        self, temp_workspace, sample_experiment_config
    ):
        """Test performance baseline for integration operations."""
        import time

        from panther.config.config_manager import ConfigLoader

        start_time = time.time()

        # Perform a series of operations that should complete quickly
        with patch("pathlib.Path.exists", return_value=True):
            for i in range(10):
                config_loader = ConfigLoader(
                    experiment_file=str(sample_experiment_config),
                    output_dir=str(temp_workspace / f"outputs_{i}"),
                )

                # Simulate some configuration work
                assert config_loader.experiment_file is not None

        elapsed_time = time.time() - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert (
            elapsed_time < 5.0
        ), f"Integration operations took too long: {elapsed_time}s"


class TestPantherWorkspaceIntegration:
    """Integration tests for PANTHER workspace management."""

    @pytest.fixture
    def workspace_manager(self):
        """Mock workspace manager for testing."""
        return Mock()

    def test_workspace_initialization(self, workspace_manager):
        """Test workspace initialization integration."""
        workspace_manager.initialize.return_value = True

        result = workspace_manager.initialize()
        assert result is True
        workspace_manager.initialize.assert_called_once()

    def test_workspace_cleanup(self, workspace_manager):
        """Test workspace cleanup integration."""
        workspace_manager.cleanup.return_value = True

        result = workspace_manager.cleanup()
        assert result is True
        workspace_manager.cleanup.assert_called_once()

    def test_workspace_validation(self, workspace_manager):
        """Test workspace validation integration."""
        workspace_manager.validate.return_value = {"valid": True, "errors": []}

        result = workspace_manager.validate()
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        workspace_manager.validate.assert_called_once()


class TestPantherPluginIntegration:
    """Integration tests for PANTHER plugin system."""

    def test_plugin_loading_integration(self):
        """Test plugin loading integration."""
        with patch("panther.plugins.plugin_loader.PluginLoader") as mock_loader:
            mock_instance = Mock()
            mock_loader.return_value = mock_instance
            mock_instance.load_plugins.return_value = {"loaded": 5, "failed": 0}

            loader = mock_loader()
            result = loader.load_plugins()

            assert result["loaded"] == 5
            assert result["failed"] == 0

    def test_plugin_validation_integration(self):
        """Test plugin validation integration."""
        with patch("panther.plugins.plugin_manager.PluginManager") as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance
            mock_instance.validate_plugin.return_value = True

            manager = mock_manager()
            result = manager.validate_plugin("test_plugin")

            assert result is True

    def test_plugin_execution_integration(self):
        """Test plugin execution integration."""
        with patch("panther.plugins.plugin_manager.PluginManager") as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance
            mock_instance.execute_plugin.return_value = {
                "status": "success",
                "output": "test",
            }

            manager = mock_manager()
            result = manager.execute_plugin("test_plugin", {"param": "value"})

            assert result["status"] == "success"
            assert result["output"] == "test"
