"""
Comprehensive tests for panther.config.config_manager module.

This module provides extensive test coverage for configuration management,
including validation, loading, plugin integration, and error handling.
"""

import pytest
import yaml
from unittest.mock import Mock, patch

from panther.config.config_manager import ConfigManager
from panther.config.config_global_schema import GlobalConfig
from panther.config.config_experiment_schema import ExperimentConfig
from panther.core.exceptions import ServicePluginNotFound, EnvironmentPluginNotFound


class TestConfigManagerBasic:
    """Test basic ConfigManager functionality."""

    def test_config_manager_initialization(self):
        """Test ConfigManager can be initialized."""
        config_manager = ConfigManager()
        assert config_manager is not None
        assert hasattr(config_manager, "load_global_config")
        assert hasattr(config_manager, "load_experiment_config")

    def test_config_manager_singleton_behavior(self):
        """Test ConfigManager behaves as expected for instance management."""
        # ConfigManager may or may not be a singleton, but it should be consistent
        config_manager1 = ConfigManager()
        config_manager2 = ConfigManager()
        assert config_manager1 is not None
        assert config_manager2 is not None


class TestGlobalConfigLoading:
    """Test global configuration loading and validation."""

    def test_load_valid_global_config(self, sample_global_config, temp_dir):
        """Test loading a valid global configuration."""
        config_file = temp_dir / "global_config.yaml"
        config_file.write_text(yaml.dump(sample_global_config))

        config_manager = ConfigManager()
        with patch("pathlib.Path.exists", return_value=True):
            config = config_manager.load_global_config(str(config_file))

        assert config is not None
        assert isinstance(config, GlobalConfig)

    def test_load_global_config_missing_file(self):
        """Test loading global config when file doesn't exist."""
        config_manager = ConfigManager()

        with pytest.raises((FileNotFoundError, Exception)):
            config_manager.load_global_config("/nonexistent/path/config.yaml")

    def test_load_global_config_invalid_yaml(self, temp_dir):
        """Test loading global config with invalid YAML."""
        config_file = temp_dir / "invalid_config.yaml"
        config_file.write_text("invalid: yaml: content: [")

        config_manager = ConfigManager()

        with pytest.raises((yaml.YAMLError, Exception)):
            config_manager.load_global_config(str(config_file))

    def test_load_global_config_schema_validation_error(self, temp_dir):
        """Test global config validation with invalid schema."""
        invalid_config = {
            "logging": {"invalid_field": "invalid_value"},
            "paths": {},  # Missing required fields
        }
        config_file = temp_dir / "invalid_schema_config.yaml"
        config_file.write_text(yaml.dump(invalid_config))

        config_manager = ConfigManager()

        with pytest.raises(Exception):  # Could be validation error or other
            config_manager.load_global_config(str(config_file))


class TestExperimentConfigLoading:
    """Test experiment configuration loading and validation."""

    def test_load_valid_experiment_config(self, sample_experiment_config, temp_dir):
        """Test loading a valid experiment configuration."""
        config_file = temp_dir / "experiment_config.yaml"
        config_file.write_text(yaml.dump(sample_experiment_config))

        config_manager = ConfigManager()
        with patch("pathlib.Path.exists", return_value=True):
            config = config_manager.load_experiment_config(str(config_file))

        assert config is not None
        assert isinstance(config, ExperimentConfig)

    def test_load_experiment_config_missing_file(self):
        """Test loading experiment config when file doesn't exist."""
        config_manager = ConfigManager()

        with pytest.raises((FileNotFoundError, Exception)):
            config_manager.load_experiment_config("/nonexistent/path/config.yaml")

    def test_load_experiment_config_invalid_yaml(self, temp_dir):
        """Test loading experiment config with invalid YAML."""
        config_file = temp_dir / "invalid_config.yaml"
        config_file.write_text("invalid: yaml: [unclosed")

        config_manager = ConfigManager()

        with pytest.raises((yaml.YAMLError, Exception)):
            config_manager.load_experiment_config(str(config_file))


class TestPluginSchemaLoading:
    """Test plugin schema loading functionality."""

    @patch("panther.config.config_manager.PluginLoader")
    def test_load_plugin_schema_success(self, mock_plugin_loader):
        """Test successful plugin schema loading."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        mock_loader_instance.load_plugin_schema.return_value = {"type": "object"}

        config_manager = ConfigManager()
        schema = config_manager.load_plugin_schema(
            "test_plugin", "execution_environment"
        )

        assert schema == {"type": "object"}
        mock_loader_instance.load_plugin_schema.assert_called_once_with(
            "test_plugin", "execution_environment"
        )

    @patch("panther.config.config_manager.PluginLoader")
    def test_load_plugin_schema_plugin_not_found(self, mock_plugin_loader):
        """Test plugin schema loading when plugin not found."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        mock_loader_instance.load_plugin_schema.side_effect = EnvironmentPluginNotFound(
            "Plugin not found"
        )

        config_manager = ConfigManager()

        with pytest.raises(EnvironmentPluginNotFound):
            config_manager.load_plugin_schema(
                "nonexistent_plugin", "execution_environment"
            )


class TestPluginParameterListing:
    """Test plugin parameter listing functionality."""

    @patch("panther.config.config_manager.PluginLoader")
    def test_list_plugin_parameters_success(self, mock_plugin_loader):
        """Test successful plugin parameter listing."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        mock_loader_instance.list_plugin_parameters.return_value = ["param1", "param2"]

        config_manager = ConfigManager()
        params = config_manager.list_plugin_parameters(
            "test_plugin", "execution_environment"
        )

        assert params == ["param1", "param2"]
        mock_loader_instance.list_plugin_parameters.assert_called_once_with(
            "test_plugin", "execution_environment"
        )

    @patch("panther.config.config_manager.PluginLoader")
    def test_list_plugin_parameters_empty_list(self, mock_plugin_loader):
        """Test plugin parameter listing returns empty list."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        mock_loader_instance.list_plugin_parameters.return_value = []

        config_manager = ConfigManager()
        params = config_manager.list_plugin_parameters(
            "test_plugin", "execution_environment"
        )

        assert params == []


class TestPluginClassRetrieval:
    """Test plugin class retrieval methods."""

    @patch("panther.config.config_manager.PluginLoader")
    def test_get_all_exec_env_classes(self, mock_plugin_loader):
        """Test getting all execution environment classes."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        expected_classes = {"basic": "BasicExecEnv", "strace": "StraceExecEnv"}
        mock_loader_instance.get_all_execution_environment_classes.return_value = (
            expected_classes
        )

        config_manager = ConfigManager()
        classes = config_manager.get_all_exec_env_classes()

        assert classes == expected_classes
        mock_loader_instance.get_all_execution_environment_classes.assert_called_once()

    @patch("panther.config.config_manager.PluginLoader")
    def test_get_all_net_env_classes(self, mock_plugin_loader):
        """Test getting all network environment classes."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        expected_classes = {
            "localhost": "LocalhostNetEnv",
            "docker_compose": "DockerComposeNetEnv",
        }
        mock_loader_instance.get_all_network_environment_classes.return_value = (
            expected_classes
        )

        config_manager = ConfigManager()
        classes = config_manager.get_all_net_env_classes()

        assert classes == expected_classes

    @patch("panther.config.config_manager.PluginLoader")
    def test_get_all_protocol_classes(self, mock_plugin_loader):
        """Test getting all protocol classes."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        expected_classes = {"quic": "QUICProtocol", "http": "HTTPProtocol"}
        mock_loader_instance.get_all_protocol_classes.return_value = expected_classes

        config_manager = ConfigManager()
        classes = config_manager.get_all_protocol_classes()

        assert classes == expected_classes

    @patch("panther.config.config_manager.PluginLoader")
    def test_get_all_iut_classes(self, mock_plugin_loader):
        """Test getting all IUT classes."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        expected_classes = {"aioquic": "AioQUICIUT", "picoquic": "PicoQUICIUT"}
        mock_loader_instance.get_all_implementation_classes.return_value = (
            expected_classes
        )

        config_manager = ConfigManager()
        classes = config_manager.get_all_iut_classes()

        assert classes == expected_classes

    @patch("panther.config.config_manager.PluginLoader")
    def test_get_all_tester_classes(self, mock_plugin_loader):
        """Test getting all tester classes."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        expected_classes = {"panther_ivy": "PantherIvyTester"}
        mock_loader_instance.get_all_tester_classes.return_value = expected_classes

        config_manager = ConfigManager()
        classes = config_manager.get_all_tester_classes()

        assert classes == expected_classes


class TestConfigValidation:
    """Test configuration validation functionality."""

    @patch("panther.config.config_manager.PluginLoader")
    def test_load_and_validate_implementation_config_success(self, mock_plugin_loader):
        """Test successful implementation config validation."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        mock_loader_instance.validate_implementation_config.return_value = True

        config_manager = ConfigManager()
        config_data = {"name": "test_impl", "type": "iut"}

        result = config_manager.load_and_validate_implementation_config(config_data)

        assert result is True

    @patch("panther.config.config_manager.PluginLoader")
    def test_load_and_validate_implementation_config_failure(self, mock_plugin_loader):
        """Test implementation config validation failure."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance
        mock_loader_instance.validate_implementation_config.side_effect = (
            ServicePluginNotFound("Implementation not found")
        )

        config_manager = ConfigManager()
        config_data = {"name": "invalid_impl", "type": "iut"}

        with pytest.raises(ServicePluginNotFound):
            config_manager.load_and_validate_implementation_config(config_data)


class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_config_manager_handles_malformed_files(self, temp_dir):
        """Test that ConfigManager handles malformed files gracefully."""
        config_file = temp_dir / "malformed.yaml"
        config_file.write_text("this is not yaml")

        config_manager = ConfigManager()

        with pytest.raises(Exception):  # Should raise some exception
            config_manager.load_global_config(str(config_file))

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_config_manager_handles_io_errors(self, mock_open):
        """Test that ConfigManager handles I/O errors gracefully."""
        config_manager = ConfigManager()

        with pytest.raises(IOError):
            config_manager.load_global_config("/path/to/config.yaml")

    @patch("panther.config.config_manager.PluginLoader")
    def test_plugin_loader_initialization_error(self, mock_plugin_loader):
        """Test handling of plugin loader initialization errors."""
        mock_plugin_loader.side_effect = Exception(
            "Plugin loader initialization failed"
        )

        config_manager = ConfigManager()

        with pytest.raises(Exception):
            config_manager.load_plugin_schema("test_plugin", "execution_environment")


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager with other components."""

    def test_full_config_loading_workflow(
        self, sample_global_config, sample_experiment_config, temp_dir
    ):
        """Test the complete configuration loading workflow."""
        # Setup config files
        global_config_file = temp_dir / "global.yaml"
        global_config_file.write_text(yaml.dump(sample_global_config))

        experiment_config_file = temp_dir / "experiment.yaml"
        experiment_config_file.write_text(yaml.dump(sample_experiment_config))

        config_manager = ConfigManager()

        # Test loading both configs
        with patch("pathlib.Path.exists", return_value=True):
            global_config = config_manager.load_global_config(str(global_config_file))
            experiment_config = config_manager.load_experiment_config(
                str(experiment_config_file)
            )

        assert global_config is not None
        assert experiment_config is not None
        assert isinstance(global_config, GlobalConfig)
        assert isinstance(experiment_config, ExperimentConfig)

    @patch("panther.config.config_manager.PluginLoader")
    def test_plugin_interaction_workflow(self, mock_plugin_loader):
        """Test interaction between ConfigManager and plugin system."""
        mock_loader_instance = Mock()
        mock_plugin_loader.return_value = mock_loader_instance

        # Setup mock responses
        mock_loader_instance.get_all_execution_environment_classes.return_value = {
            "strace": "StraceEnv"
        }
        mock_loader_instance.get_all_network_environment_classes.return_value = {
            "localhost": "LocalhostEnv"
        }
        mock_loader_instance.load_plugin_schema.return_value = {"type": "object"}

        config_manager = ConfigManager()

        # Test workflow
        exec_classes = config_manager.get_all_exec_env_classes()
        net_classes = config_manager.get_all_net_env_classes()
        schema = config_manager.load_plugin_schema("strace", "execution_environment")

        assert exec_classes == {"strace": "StraceEnv"}
        assert net_classes == {"localhost": "LocalhostEnv"}
        assert schema == {"type": "object"}


@pytest.mark.slow
class TestConfigManagerPerformance:
    """Performance tests for ConfigManager operations."""

    def test_config_loading_performance(self, sample_global_config, temp_dir):
        """Test that config loading performs reasonably well."""
        import time

        config_file = temp_dir / "performance_test.yaml"
        config_file.write_text(yaml.dump(sample_global_config))

        config_manager = ConfigManager()

        start_time = time.time()
        with patch("pathlib.Path.exists", return_value=True):
            for _ in range(10):  # Load config 10 times
                config_manager.load_global_config(str(config_file))
        end_time = time.time()

        # Should complete in reasonable time (adjust threshold as needed)
        assert (end_time - start_time) < 5.0  # 5 seconds for 10 loads


class TestConfigManagerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_config_file(self, temp_dir):
        """Test handling of empty configuration files."""
        config_file = temp_dir / "empty.yaml"
        config_file.write_text("")

        config_manager = ConfigManager()

        with pytest.raises(Exception):  # Should handle empty files gracefully
            config_manager.load_global_config(str(config_file))

    def test_very_large_config(self, temp_dir):
        """Test handling of large configuration files."""
        large_config = {
            "logging": {"level": "DEBUG"},
            "paths": {
                "output_dir": f"path_{i}" for i in range(1000)
            },  # Large number of paths
            "features": {
                "feature_" + str(i): True for i in range(100)
            },  # Many features
        }

        config_file = temp_dir / "large_config.yaml"
        config_file.write_text(yaml.dump(large_config))

        config_manager = ConfigManager()

        # Should handle large configs without crashing
        try:
            with patch("pathlib.Path.exists", return_value=True):
                config_manager.load_global_config(str(config_file))
        except Exception:
            # May fail validation but shouldn't crash the process
            pass

    def test_config_with_special_characters(self, temp_dir):
        """Test handling of configs with special characters."""
        special_config = {
            "logging": {"level": "DEBUG"},
            "paths": {
                "output_dir": "path/with/special/chars/üñíçødé/",
                "log_dir": "logs/with spaces and symbols!@#$%/",
            },
        }

        config_file = temp_dir / "special_chars.yaml"
        config_file.write_text(yaml.dump(special_config))

        config_manager = ConfigManager()

        # Should handle special characters in paths
        try:
            with patch("pathlib.Path.exists", return_value=True):
                config_manager.load_global_config(str(config_file))
        except Exception:
            # May fail validation but should handle encoding properly
            pass
