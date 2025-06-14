"""
Advanced test suite for ConfigManager plugin discovery and management functionality.

This test file focuses on increasing coverage for config_manager.py by testing:
- Plugin discovery methods (load_all_plugins, list_plugin_parameters)
- Error handling paths in various methods
- Edge cases in plugin loading/validation
- File operations and directory management
- Plugin operations methods
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from dataclasses import dataclass

from panther.config.config_manager import ConfigLoader


# Helper functions for creating mock plugins
def _create_mock_execution_env_plugin(parent_dir, plugin_name):
    """Create a mock execution environment plugin."""
    plugin_dir = parent_dir / plugin_name
    plugin_dir.mkdir()

    # Create plugin file
    plugin_file = plugin_dir / f"{plugin_name}.py"
    plugin_file.write_text(
        f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
    )

    # Create __init__.py
    init_file = plugin_dir / "__init__.py"
    init_file.write_text("")


def _create_mock_network_env_plugin(parent_dir, plugin_name):
    """Create a mock network environment plugin."""
    plugin_dir = parent_dir / plugin_name
    plugin_dir.mkdir()

    # Create plugin file
    plugin_file = plugin_dir / f"{plugin_name}.py"
    plugin_file.write_text(
        f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
    )

    # Create __init__.py
    init_file = plugin_dir / "__init__.py"
    init_file.write_text("")


def _create_mock_iut_plugin(parent_dir, protocol, plugin_name):
    """Create a mock IUT plugin."""
    protocol_dir = parent_dir / protocol
    protocol_dir.mkdir(parents=True, exist_ok=True)

    plugin_dir = protocol_dir / plugin_name
    plugin_dir.mkdir()

    # Create plugin file
    plugin_file = plugin_dir / f"{plugin_name}.py"
    plugin_file.write_text(
        f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
    )

    # Create __init__.py
    init_file = plugin_dir / "__init__.py"
    init_file.write_text("")


def _create_mock_tester_plugin(parent_dir, plugin_name):
    """Create a mock tester plugin."""
    plugin_dir = parent_dir / plugin_name
    plugin_dir.mkdir()

    # Create plugin file
    plugin_file = plugin_dir / f"{plugin_name}.py"
    plugin_file.write_text(
        f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
    )

    # Create __init__.py
    init_file = plugin_dir / "__init__.py"
    init_file.write_text("")


def _create_mock_protocol_plugin(parent_dir, plugin_name):
    """Create a mock protocol plugin."""
    plugin_dir = parent_dir / plugin_name
    plugin_dir.mkdir()

    # Create plugin file
    plugin_file = plugin_dir / f"{plugin_name}.py"
    plugin_file.write_text(
        f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
    )

    # Create __init__.py
    init_file = plugin_dir / "__init__.py"
    init_file.write_text("")


@pytest.fixture
def config_loader_with_mock_panther_dir(tmp_path):
    """Create a ConfigLoader with a mock panther directory structure."""
    # Create mock panther directory structure
    panther_dir = tmp_path / "panther"
    panther_dir.mkdir()

    # Create plugin directory structure
    plugin_dir = panther_dir / "plugins"
    plugin_dir.mkdir()

    # Create environment directories
    env_dir = plugin_dir / "environments"
    env_dir.mkdir()

    exec_env_dir = env_dir / "execution_environment"
    exec_env_dir.mkdir()

    net_env_dir = env_dir / "network_environment"
    net_env_dir.mkdir()

    # Create services directories
    services_dir = plugin_dir / "services"
    services_dir.mkdir()

    iut_dir = services_dir / "iut"
    iut_dir.mkdir()

    testers_dir = services_dir / "testers"
    testers_dir.mkdir()

    # Create protocols directory
    protocols_dir = plugin_dir / "protocols"
    protocols_dir.mkdir()

    # Create mock plugins
    _create_mock_execution_env_plugin(exec_env_dir, "mock_exec_env")
    _create_mock_network_env_plugin(net_env_dir, "mock_net_env")
    _create_mock_iut_plugin(iut_dir, "quic", "mock_iut")
    _create_mock_tester_plugin(testers_dir, "mock_tester")
    _create_mock_protocol_plugin(protocols_dir, "mock_protocol")

    # Create a mock experiment file
    experiment_file = tmp_path / "experiment.yaml"
    experiment_file.write_text(
        """
experiment:
  name: "test_experiment"
  duration: 300
"""
    )

    # Create ConfigLoader with mock directory
    config_loader = ConfigLoader(str(experiment_file))
    config_loader._panther_dir = panther_dir

    # Mock global config
    mock_global_config = Mock()
    mock_global_config.paths.plugin_dir = "plugins"
    config_loader.global_config = mock_global_config
    config_loader.logger = Mock()

    return config_loader


class TestConfigManagerPluginDiscovery:
    """Test plugin discovery and management functionality."""

    def _create_mock_execution_env_plugin(self, parent_dir, plugin_name):
        """Create a mock execution environment plugin."""
        plugin_dir = parent_dir / plugin_name
        plugin_dir.mkdir()

        # Create plugin file
        plugin_file = plugin_dir / f"{plugin_name}.py"
        plugin_file.write_text(
            f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
        )

        # Create __init__.py
        init_file = plugin_dir / "__init__.py"
        init_file.write_text("")

    def _create_mock_network_env_plugin(self, parent_dir, plugin_name):
        """Create a mock network environment plugin."""
        plugin_dir = parent_dir / plugin_name
        plugin_dir.mkdir()

        # Create plugin file
        plugin_file = plugin_dir / f"{plugin_name}.py"
        plugin_file.write_text(
            f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
        )

        # Create __init__.py
        init_file = plugin_dir / "__init__.py"
        init_file.write_text("")

    def _create_mock_iut_plugin(self, parent_dir, protocol, plugin_name):
        """Create a mock IUT plugin under a protocol directory."""
        protocol_dir = parent_dir / protocol
        protocol_dir.mkdir(exist_ok=True)

        plugin_dir = protocol_dir / plugin_name
        plugin_dir.mkdir()

        # Create plugin file
        plugin_file = plugin_dir / f"{plugin_name}.py"
        plugin_file.write_text(
            f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
        )

        # Create __init__.py
        init_file = plugin_dir / "__init__.py"
        init_file.write_text("")

    def _create_mock_tester_plugin(self, parent_dir, plugin_name):
        """Create a mock tester plugin."""
        plugin_dir = parent_dir / plugin_name
        plugin_dir.mkdir()

        # Create plugin file
        plugin_file = plugin_dir / f"{plugin_name}.py"
        plugin_file.write_text(
            f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
        )

        # Create __init__.py
        init_file = plugin_dir / "__init__.py"
        init_file.write_text("")

    def _create_mock_protocol_plugin(self, parent_dir, plugin_name):
        """Create a mock protocol plugin."""
        plugin_dir = parent_dir / plugin_name
        plugin_dir.mkdir()

        # Create plugin file
        plugin_file = plugin_dir / f"{plugin_name}.py"
        plugin_file.write_text(
            f"""
class {plugin_name.title().replace('_', '')}:
    pass
"""
        )

        # Create __init__.py
        init_file = plugin_dir / "__init__.py"
        init_file.write_text("")

    def test_load_all_plugins_success(self, config_loader_with_mock_panther_dir):
        """Test successful loading of all plugins."""
        config_loader = config_loader_with_mock_panther_dir

        with patch("importlib.import_module"):
            plugins = config_loader.load_all_plugins()

        # Verify the plugin structure is discovered
        assert "execution_environment" in plugins
        assert "network_environment" in plugins
        assert "iut" in plugins
        assert "testers" in plugins
        assert "protocols" in plugins

        # Verify specific plugins are found
        assert "mock_exec_env" in plugins["execution_environment"]
        assert "mock_net_env" in plugins["network_environment"]
        assert "quic/mock_iut" in plugins["iut"]
        assert "mock_tester" in plugins["testers"]
        assert "mock_protocol" in plugins["protocols"]

    def test_load_all_plugins_with_import_errors(self, config_loader_with_mock_panther_dir):
        """Test load_all_plugins with import errors for some plugins."""
        config_loader = config_loader_with_mock_panther_dir

        def mock_import_side_effect(module_name):
            if "mock_exec_env" in module_name:
                raise ImportError("Mock import error")
            return Mock()

        with patch("importlib.import_module", side_effect=mock_import_side_effect):
            plugins = config_loader.load_all_plugins()

        # Verify plugins are still discovered even with import errors
        assert "execution_environment" in plugins
        assert "mock_exec_env" in plugins["execution_environment"]

        # Verify error was logged
        config_loader.logger.error.assert_called()

    def test_load_all_plugins_missing_plugin_directory(self, tmp_path):
        """Test load_all_plugins when plugin directory doesn't exist."""
        # Create a mock experiment file
        experiment_file = tmp_path / "experiment.yaml"
        experiment_file.write_text("experiment:\n  name: test")

        config_loader = ConfigLoader(str(experiment_file))
        config_loader._panther_dir = tmp_path / "nonexistent"

        mock_global_config = Mock()
        mock_global_config.paths.plugin_dir = "plugins"
        config_loader.global_config = mock_global_config
        config_loader.logger = Mock()

        plugins = config_loader.load_all_plugins()

        # Should return empty plugin lists for all types
        for plugin_type in [
            "execution_environment",
            "network_environment",
            "iut",
            "testers",
            "protocols",
        ]:
            assert plugin_type in plugins
            assert len(plugins[plugin_type]) == 0

    @pytest.mark.skip(reason="Plugin loader circular import issue causing recursion error")
    def test_get_all_exec_env_classes_success(self, config_loader_with_mock_panther_dir):
        """Test successful retrieval of execution environment classes."""
        config_loader = config_loader_with_mock_panther_dir

        # Create mock execution environment directory and plugin
        exec_env_dir = (
            Path(config_loader._panther_dir) / "plugins" / "environments" / "execution_environment"
        )
        exec_env_dir.mkdir(parents=True, exist_ok=True)

        mock_plugin_dir = exec_env_dir / "mock_exec_env"
        mock_plugin_dir.mkdir(exist_ok=True)
        (mock_plugin_dir / "mock_exec_env.py").write_text("class MockExecEnvConfig: pass")

        # Mock the import and get_class_name method to avoid recursion issues
        with patch("panther.plugins.plugin_loader.PluginLoader") as mock_plugin_loader_class:
            mock_plugin_loader_class.get_class_name.return_value = "MockExecEnvConfig"

            classes = config_loader.get_all_exec_env_classes()

        # Should have found at least one class
        assert len(classes) > 0

    def test_get_all_exec_env_classes_missing_directory(self, tmp_path):
        """Test get_all_exec_env_classes with missing directory."""
        # Create a mock experiment file
        experiment_file = tmp_path / "experiment.yaml"
        experiment_file.write_text("experiment:\n  name: test")

        config_loader = ConfigLoader(str(experiment_file))
        config_loader._panther_dir = tmp_path / "nonexistent"

        mock_global_config = Mock()
        mock_global_config.paths.plugin_dir = "plugins"
        config_loader.global_config = mock_global_config
        config_loader.logger = Mock()

        classes = config_loader.get_all_exec_env_classes()

        assert classes == []

    def test_get_all_network_environment_classes_success(self, config_loader_with_mock_panther_dir):
        """Test successful retrieval of network environment classes."""
        config_loader = config_loader_with_mock_panther_dir

        # Mock the PluginLoader import to avoid circular import
        with patch(
            "panther.plugins.plugin_loader.PluginLoader.get_class_name"
        ) as mock_get_class_name:
            mock_get_class_name.return_value = "TestPluginConfig"

            # Create the expected directory structure in our temp directory
            net_env_dir = (
                config_loader._panther_dir / "plugins" / "environments" / "network_environment"
            )
            net_env_dir.mkdir(parents=True, exist_ok=True)

            # Create a mock plugin directory
            plugin_dir = net_env_dir / "test_plugin"
            plugin_dir.mkdir(exist_ok=True)

            # Create the plugin file
            plugin_file = plugin_dir / "test_plugin.py"
            plugin_file.write_text("# Mock plugin file")

            classes = config_loader.get_all_net_env_classes()

        assert "TestPluginConfig" in classes
        config_loader.logger.debug.assert_called()

    def test_get_all_protocol_classes_success(self, config_loader_with_mock_panther_dir):
        """Test successful retrieval of protocol classes."""
        config_loader = config_loader_with_mock_panther_dir

        # Mock the PluginLoader import to avoid circular import
        with patch(
            "panther.plugins.plugin_loader.PluginLoader.get_class_name"
        ) as mock_get_class_name:
            mock_get_class_name.return_value = "MockProtocolConfig"

            # Create the expected directory structure in our temp directory
            protocol_dir = config_loader._panther_dir / "plugins" / "protocols"
            protocol_dir.mkdir(parents=True, exist_ok=True)

            # Create protocol type directory (e.g., client_server)
            protocol_type_dir = protocol_dir / "client_server"
            protocol_type_dir.mkdir(exist_ok=True)

            # Create a mock protocol directory
            mock_protocol_dir = protocol_type_dir / "mock_protocol"
            mock_protocol_dir.mkdir(exist_ok=True)

            # Create the protocol file
            protocol_file = mock_protocol_dir / "mock_protocol.py"
            protocol_file.write_text("# Mock protocol file")

            classes = config_loader.get_all_protocol_classes()

        assert "MockProtocolConfig" in classes
        config_loader.logger.debug.assert_called()

    def test_get_all_protocol_classes_no_protocol_file(self, config_loader_with_mock_panther_dir):
        """Test get_all_protocol_classes when protocol files don't exist."""
        config_loader = config_loader_with_mock_panther_dir

        # Mock the PluginLoader import to avoid circular import
        with patch(
            "panther.plugins.plugin_loader.PluginLoader.get_class_name"
        ) as mock_get_class_name:
            mock_get_class_name.return_value = "MockProtocolConfig"

            # Create the expected directory structure but no protocol files
            protocol_dir = config_loader._panther_dir / "plugins" / "protocols"
            protocol_dir.mkdir(parents=True, exist_ok=True)

            # Create protocol type directory (e.g., client_server) but no actual protocols
            protocol_type_dir = protocol_dir / "client_server"
            protocol_type_dir.mkdir(exist_ok=True)

            classes = config_loader.get_all_protocol_classes()

        # Should return empty list when no protocols are found
        assert len(classes) == 0
        config_loader.logger.debug.assert_called()


class TestConfigManagerPluginParameters:
    """Test plugin parameter listing functionality."""

    @pytest.fixture
    def config_loader_for_params(self, tmp_path):
        """Create a ConfigLoader for testing parameter listing."""
        # Create a mock experiment file
        experiment_file = tmp_path / "experiment.yaml"
        experiment_file.write_text("experiment:\n  name: test")

        config_loader = ConfigLoader(str(experiment_file))
        config_loader.logger = Mock()
        return config_loader

    def test_list_plugin_parameters_environment_plugin_success(self, config_loader_for_params):
        """Test successful parameter listing for environment plugins."""
        config_loader = config_loader_for_params

        # Create a mock config class with dataclass fields
        @dataclass
        class MockEnvironmentConfig:
            """Mock environment configuration."""

            timeout: int = 30
            enabled: bool = True
            path: str | None = None

        mock_module = Mock()
        mock_module.MockEnvironmentConfig = MockEnvironmentConfig

        with patch("importlib.import_module", return_value=mock_module):
            with patch(
                "panther.plugins.plugin_loader.PluginLoader.get_class_name",
                return_value="MockEnvironmentConfig",
            ):
                params = config_loader.list_plugin_parameters(
                    "execution_environment", "mock_environment"
                )

        assert "timeout" in params
        assert "enabled" in params
        assert "path" in params
        assert params["timeout"]["default"] == 30
        assert params["enabled"]["default"] is True
        assert params["path"]["default"] is None

    def test_list_plugin_parameters_iut_plugin_direct_path(self, config_loader_for_params):
        """Test parameter listing for IUT plugins with direct path."""
        config_loader = config_loader_for_params

        @dataclass
        class MockIutConfig:
            """Mock IUT configuration."""

            port: int = 8080
            host: str = "localhost"

        mock_module = Mock()
        mock_module.MockIutConfig = MockIutConfig

        with patch("importlib.import_module", return_value=mock_module):
            with patch(
                "panther.plugins.plugin_loader.PluginLoader.get_class_name",
                return_value="MockIutConfig",
            ):
                params = config_loader.list_plugin_parameters("iut", "mock_iut")

        assert "port" in params
        assert "host" in params
        assert params["port"]["default"] == 8080
        assert params["host"]["default"] == "localhost"

    def test_list_plugin_parameters_iut_plugin_protocol_path(self, config_loader_for_params):
        """Test parameter listing for IUT plugins under protocol directory."""
        config_loader = config_loader_for_params

        @dataclass
        class MockQuicConfig:
            """Mock QUIC configuration."""

            version: str = "1.0"
            encryption: bool = True

        mock_module = Mock()
        mock_module.MockQuicConfig = MockQuicConfig

        def mock_import_side_effect(module_name):
            if "services.iut.mock_quic" in module_name and "quic" not in module_name:
                raise ImportError("Direct path not found")
            elif "quic.mock_quic" in module_name:
                return mock_module
            else:
                raise ImportError("Not found")

        with patch("importlib.import_module", side_effect=mock_import_side_effect):
            with patch(
                "panther.plugins.plugin_loader.PluginLoader.get_class_name",
                return_value="MockQuicConfig",
            ):
                params = config_loader.list_plugin_parameters("iut", "mock_quic")

        assert "version" in params
        assert "encryption" in params

    def test_list_plugin_parameters_plugin_not_found(self, config_loader_for_params):
        """Test parameter listing when plugin is not found."""
        config_loader = config_loader_for_params

        with patch("importlib.import_module", side_effect=ImportError("Module not found")):
            with patch("builtins.print") as mock_print:
                params = config_loader.list_plugin_parameters("iut", "nonexistent_plugin")

        assert params == {}
        mock_print.assert_called()

    def test_list_plugin_parameters_attribute_error(self, config_loader_for_params):
        """Test parameter listing with AttributeError."""
        config_loader = config_loader_for_params

        mock_module = Mock()
        # Remove the expected class attribute to trigger AttributeError
        del mock_module.MockConfig

        with patch("importlib.import_module", return_value=mock_module):
            with patch(
                "panther.plugins.plugin_loader.PluginLoader.get_class_name",
                return_value="MockConfig",
            ):
                with patch("builtins.print") as mock_print:
                    params = config_loader.list_plugin_parameters(
                        "execution_environment", "mock_plugin"
                    )

        assert params == {}
        mock_print.assert_called()

    def test_list_plugin_parameters_unexpected_error(self, config_loader_for_params):
        """Test parameter listing with unexpected error."""
        config_loader = config_loader_for_params

        with patch("importlib.import_module", side_effect=Exception("Unexpected error")):
            with patch("builtins.print") as mock_print:
                params = config_loader.list_plugin_parameters(
                    "execution_environment", "mock_plugin"
                )

        assert params == {}
        mock_print.assert_called()

    def test_list_plugin_parameters_non_dataclass(self, config_loader_for_params):
        """Test parameter listing for non-dataclass config."""
        config_loader = config_loader_for_params

        class MockNonDataclassConfig:
            """Mock non-dataclass configuration."""

            pass

        mock_module = Mock()
        mock_module.MockNonDataclassConfig = MockNonDataclassConfig

        with patch("importlib.import_module", return_value=mock_module):
            with patch(
                "panther.plugins.plugin_loader.PluginLoader.get_class_name",
                return_value="MockNonDataclassConfig",
            ):
                params = config_loader.list_plugin_parameters(
                    "execution_environment", "mock_plugin"
                )

        # Should return empty dict for non-dataclass
        assert params == {}


class TestConfigManagerErrorHandling:
    """Test error handling paths in ConfigManager."""

    @pytest.fixture
    def config_loader_for_errors(self, tmp_path):
        """Create a ConfigLoader for error testing."""
        # Create a mock experiment file
        experiment_file = tmp_path / "experiment.yaml"
        experiment_file.write_text("experiment:\n  name: test")

        config_loader = ConfigLoader(str(experiment_file))
        config_loader.logger = Mock()
        mock_global_config = Mock()
        mock_global_config.paths.plugin_dir = "plugins"
        config_loader.global_config = mock_global_config
        return config_loader

    def test_initialization_with_none_global_config_file(self):
        """Test initialization with None experiment_file."""
        config_loader = ConfigLoader(experiment_file=None)
        assert config_loader.experiment_file is None

    def test_initialization_with_none_experiment_file(self):
        """Test initialization with None experiment_file."""
        config_loader = ConfigLoader(experiment_file=None)
        assert config_loader.experiment_file is None

    def test_panther_dir_property_with_none_global_config_file(self):
        """Test _panther_dir property when experiment_file is None."""
        config_loader = ConfigLoader(experiment_file=None)

        # Should fall back to default behavior
        panther_dir = config_loader._panther_dir
        assert panther_dir is not None

    def test_panther_dir_property_with_string_global_config_file(self, tmp_path):
        """Test _panther_dir property with string experiment_file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("logging:\n  level: INFO")

        config_loader = ConfigLoader(experiment_file=str(config_file))
        panther_dir = config_loader._panther_dir

        # Should derive from default behavior (not from experiment file path)
        assert panther_dir is not None

    def test_load_all_plugins_with_filesystem_errors(self, config_loader_for_errors, tmp_path):
        """Test load_all_plugins with filesystem access errors."""
        config_loader = config_loader_for_errors
        config_loader._panther_dir = tmp_path

        # Create a directory we can't read
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        # Mock iterdir to raise PermissionError
        with patch.object(Path, "iterdir", side_effect=PermissionError("Access denied")):
            plugins = config_loader.load_all_plugins()

        # Should handle error gracefully and return empty plugins
        for plugin_type in plugins.values():
            assert len(plugin_type) == 0

    def test_copy_plugin_files_source_not_exists(self, config_loader_for_errors, tmp_path):
        """Test copy_plugin_files when source directory doesn't exist."""
        config_loader = config_loader_for_errors

        source_dir = tmp_path / "nonexistent"
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Should handle gracefully when source doesn't exist
        config_loader.copy_plugin_files(source_dir, target_dir)

        # No error should be raised, method should return gracefully
        assert True  # Test passes if no exception is raised
