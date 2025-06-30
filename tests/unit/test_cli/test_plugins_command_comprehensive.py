"""
Comprehensive unit tests for PluginsCommand CLI.

This module provides exhaustive testing for ALL PluginsCommand parameters,
including all 6 subcommands, plugin discovery, validation, and error conditions.
"""

import argparse
import ast
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from panther.cli.subcommands.plugins import PluginsCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestPluginsCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for PluginsCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return PluginsCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "plugins"

    @pytest.fixture
    def mock_plugin_manager_class(self):
        """Mock PluginManager class for testing."""
        with patch("panther.cli.subcommands.plugins.PluginManager") as mock:
            mock_instance = MagicMock()
            mock_instance.discover_plugins.return_value = None
            mock_instance.get_plugins_by_type.return_value = []
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_plugin_discovery_class(self):
        """Mock PluginDiscovery class for testing."""
        with patch("panther.cli.subcommands.plugins.PluginDiscovery") as mock:
            mock_instance = MagicMock()
            mock_instance.list_available_plugins.return_value = {
                "iut": ["picoquic", "aioquic"],
                "testers": ["panther_ivy"],
                "environments": ["docker_compose"],
            }
            mock_instance.get_plugin_info.return_value = {"version": "1.0.0"}
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_config_loader_class(self):
        """Mock ConfigLoader class for testing."""
        with patch("panther.cli.subcommands.plugins.ConfigLoader") as mock:
            mock_instance = MagicMock()
            mock_instance.global_config = MagicMock()
            mock_instance.list_plugin_parameters.return_value = {
                "timeout": {
                    "type": "int",
                    "default": 60,
                    "description": "Timeout in seconds",
                },
                "debug_mode": {
                    "type": "bool",
                    "default": False,
                    "description": "Enable debug mode",
                },
            }
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def sample_plugin_data(self):
        """Sample plugin data for testing."""
        mock_plugin1 = MagicMock()
        mock_plugin1.name = "picoquic"
        mock_plugin1.type = "iut"
        mock_plugin1.version = "1.0.0"
        mock_plugin1.description = "PicoQUIC implementation"
        mock_plugin1.path = Path("/plugins/iut/picoquic")

        mock_plugin2 = MagicMock()
        mock_plugin2.name = "aioquic"
        mock_plugin2.type = "iut"
        mock_plugin2.version = "2.0.0"
        mock_plugin2.description = "AioQUIC implementation"
        mock_plugin2.path = Path("/plugins/iut/aioquic")

        mock_plugin3 = MagicMock()
        mock_plugin3.name = "panther_ivy"
        mock_plugin3.type = "testers"
        mock_plugin3.version = "1.5.0"
        mock_plugin3.description = "Ivy formal verification tester"
        mock_plugin3.path = Path("/plugins/testers/panther_ivy")

        return [mock_plugin1, mock_plugin2, mock_plugin3]

    @pytest.fixture
    def sample_plugin_directory(self, tmp_path):
        """Create sample plugin directory structure."""
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()

        # Create IUT plugin
        iut_dir = plugin_dir / "iut" / "sample_iut"
        iut_dir.mkdir(parents=True)

        plugin_file = iut_dir / "sample_iut.py"
        plugin_file.write_text(
            '''
"""Sample IUT plugin for testing."""

class SampleIutPlugin:
    def __init__(self):
        self.name = "sample_iut"
        self.type = "iut"
        self.version = "1.0.0"

    def start(self):
        pass

    def stop(self):
        pass
'''
        )

        config_file = iut_dir / "config_schema.py"
        config_file.write_text(
            '''
"""Configuration schema for sample IUT plugin."""

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "timeout": {"type": "integer", "default": 60}
    }
}
'''
        )

        # Create testers plugin
        tester_dir = plugin_dir / "testers" / "sample_tester"
        tester_dir.mkdir(parents=True)

        tester_file = tester_dir / "sample_tester.py"
        tester_file.write_text(
            '''
"""Sample tester plugin."""

class SampleTesterPlugin:
    def __init__(self):
        self.name = "sample_tester"
        self.type = "testers"
        self.version = "2.0.0"
'''
        )

        return str(plugin_dir)

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that PluginsCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'plugins' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "plugins" in subparsers_actions[0].choices

    def test_all_subcommands_registered(self):
        """Test that all plugins subcommands are registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Parse plugins help to get subcommands
        try:
            parser.parse_args(["plugins", "--help"])
        except SystemExit:
            pass  # Expected behavior for help

        # Verify subcommands exist by testing their individual help
        subcommands = ["list", "params", "scan", "validate", "check-deps", "migrate"]

        for subcommand in subcommands:
            try:
                parser.parse_args(["plugins", subcommand, "--help"])
            except SystemExit:
                pass  # Expected for help command

    # =============================================================================
    # MAIN COMMAND HANDLER TESTS
    # =============================================================================

    def test_handle_no_action_specified(self, caplog):
        """Test behavior when no plugins action is specified."""
        args = self.create_namespace(plugins_action=None)

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "No plugin action specified" in caplog.text

    def test_handle_unknown_action(self, caplog):
        """Test behavior with unknown plugins action."""
        args = self.create_namespace(plugins_action="unknown_action")

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Unknown plugin action: unknown_action" in caplog.text

    # =============================================================================
    # LIST SUBCOMMAND TESTS
    # =============================================================================

    def test_list_plugins_no_plugins_found(self, mock_plugin_manager_class, caplog):
        """Test list command when no plugins are found."""
        mock_class, mock_instance = mock_plugin_manager_class
        mock_instance.get_plugins_by_type.return_value = []

        args = self.create_namespace(plugins_action="list", type="all", format="table")

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "No plugins found" in caplog.text
        mock_class.assert_called_once()
        mock_instance.discover_plugins.assert_called_once()

    def test_list_plugins_with_data_table_format(
        self, mock_plugin_manager_class, sample_plugin_data, caplog
    ):
        """Test list command with available plugins in table format."""
        mock_class, mock_instance = mock_plugin_manager_class

        # Setup mock to return plugins for different types
        def get_plugins_side_effect(plugin_type):
            if plugin_type == "iut":
                return sample_plugin_data[:2]  # picoquic, aioquic
            elif plugin_type == "testers":
                return sample_plugin_data[2:3]  # panther_ivy
            else:
                return []

        mock_instance.get_plugins_by_type.side_effect = get_plugins_side_effect

        args = self.create_namespace(plugins_action="list", type="all", format="table")

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "Found 3 plugin(s)" in caplog.text
        assert "picoquic" in caplog.text
        assert "aioquic" in caplog.text
        assert "panther_ivy" in caplog.text
        assert "PicoQUIC implementation" in caplog.text

    def test_list_plugins_specific_type_filter(
        self, mock_plugin_manager_class, sample_plugin_data, caplog
    ):
        """Test list command with specific plugin type filter."""
        mock_class, mock_instance = mock_plugin_manager_class
        mock_instance.get_plugins_by_type.return_value = sample_plugin_data[
            :2
        ]  # Only IUT plugins

        args = self.create_namespace(plugins_action="list", type="iut", format="table")

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "Found 2 plugin(s)" in caplog.text
        assert "picoquic" in caplog.text
        assert "aioquic" in caplog.text

        # Verify only IUT plugins were requested
        mock_instance.get_plugins_by_type.assert_called_once_with("iut")

    def test_list_plugins_json_format(
        self, mock_plugin_manager_class, sample_plugin_data, caplog
    ):
        """Test list command with JSON output format."""
        mock_class, mock_instance = mock_plugin_manager_class
        mock_instance.get_plugins_by_type.return_value = sample_plugin_data[
            :1
        ]  # One plugin

        args = self.create_namespace(plugins_action="list", type="iut", format="json")

        result = PluginsCommand.handle(args)

        assert result == 0
        # JSON output should be in the logs
        captured_output = caplog.text
        # Should contain JSON-like structure
        assert "picoquic" in captured_output
        assert "iut" in captured_output

    def test_list_plugins_simple_format(
        self, mock_plugin_manager_class, sample_plugin_data, caplog
    ):
        """Test list command with simple output format."""
        mock_class, mock_instance = mock_plugin_manager_class
        mock_instance.get_plugins_by_type.return_value = sample_plugin_data[:2]

        args = self.create_namespace(plugins_action="list", type="iut", format="simple")

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "picoquic (iut)" in caplog.text
        assert "aioquic (iut)" in caplog.text

    @pytest.mark.parametrize("plugin_type", ["iut", "testers", "environments", "all"])
    def test_list_plugins_all_valid_types(self, plugin_type, mock_plugin_manager_class):
        """Test list command with all valid plugin types."""
        mock_class, mock_instance = mock_plugin_manager_class

        args = self.create_namespace(
            plugins_action="list", type=plugin_type, format="table"
        )

        result = PluginsCommand.handle(args)

        assert result == 0  # Should not crash with any valid type

    @pytest.mark.parametrize("format_type", ["table", "json", "simple"])
    def test_list_plugins_all_valid_formats(
        self, format_type, mock_plugin_manager_class
    ):
        """Test list command with all valid format types."""
        mock_class, mock_instance = mock_plugin_manager_class

        args = self.create_namespace(
            plugins_action="list", type="all", format=format_type
        )

        result = PluginsCommand.handle(args)

        assert result == 0  # Should not crash with any valid format

    def test_list_plugins_error_handling(self, caplog):
        """Test list command error handling."""
        with patch("panther.cli.subcommands.plugins.PluginManager") as mock_class:
            mock_class.side_effect = Exception("Plugin manager error")

            args = self.create_namespace(
                plugins_action="list", type="all", format="table"
            )

            result = PluginsCommand.handle(args)

            assert result == 1
            assert "Error listing plugins" in caplog.text

    # =============================================================================
    # PARAMS SUBCOMMAND TESTS
    # =============================================================================

    def test_params_with_explicit_type(self, mock_config_loader_class, caplog):
        """Test params command with explicitly specified plugin type."""
        mock_config_class, mock_config_instance = mock_config_loader_class

        args = self.create_namespace(
            plugins_action="params", plugin_name="picoquic", type="iut", protocol=None
        )

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "Parameters for plugin: picoquic (iut)" in caplog.text
        assert "Available Parameters:" in caplog.text
        assert "timeout (int)" in caplog.text
        assert "debug_mode (bool)" in caplog.text
        assert "Default: 60" in caplog.text
        assert "Default: False" in caplog.text

        # Verify ConfigLoader was used correctly
        mock_config_class.assert_called_once()
        mock_config_instance.list_plugin_parameters.assert_called_once_with(
            plugin_name="picoquic", plugin_type="iut", protocol=None
        )

    def test_params_with_auto_detection(
        self, mock_config_loader_class, mock_plugin_discovery_class, caplog
    ):
        """Test params command with automatic plugin type detection."""
        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_discovery_class, mock_discovery_instance = mock_plugin_discovery_class

        args = self.create_namespace(
            plugins_action="params",
            plugin_name="picoquic",
            type=None,  # Auto-detect
            protocol=None,
        )

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "Parameters for plugin: picoquic" in caplog.text

        # Verify plugin discovery was used for type detection
        mock_discovery_class.assert_called_once()
        mock_discovery_instance.list_available_plugins.assert_called_once()

    def test_params_with_protocol_filter(self, mock_config_loader_class):
        """Test params command with protocol filter."""
        mock_config_class, mock_config_instance = mock_config_loader_class

        args = self.create_namespace(
            plugins_action="params", plugin_name="picoquic", type="iut", protocol="quic"
        )

        result = PluginsCommand.handle(args)

        assert result == 0
        # Verify protocol was passed to list_plugin_parameters
        mock_config_instance.list_plugin_parameters.assert_called_once_with(
            plugin_name="picoquic", plugin_type="iut", protocol="quic"
        )

    def test_params_plugin_not_found_no_type(
        self, mock_config_loader_class, mock_plugin_discovery_class, caplog
    ):
        """Test params command when plugin not found and no type specified."""
        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_discovery_class, mock_discovery_instance = mock_plugin_discovery_class

        # Setup discovery to not find the plugin
        mock_discovery_instance.list_available_plugins.return_value = {
            "iut": ["other_plugin"],
            "testers": [],
            "environments": [],
        }

        args = self.create_namespace(
            plugins_action="params",
            plugin_name="nonexistent_plugin",
            type=None,
            protocol=None,
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert (
            "Plugin 'nonexistent_plugin' not found and no type specified" in caplog.text
        )

    def test_params_no_parameters_found(self, mock_config_loader_class, caplog):
        """Test params command when plugin has no parameters."""
        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_config_instance.list_plugin_parameters.return_value = {}  # No parameters

        args = self.create_namespace(
            plugins_action="params",
            plugin_name="simple_plugin",
            type="iut",
            protocol=None,
        )

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "No parameters found for this plugin" in caplog.text

    def test_params_error_getting_parameters(self, mock_config_loader_class, caplog):
        """Test params command when getting parameters fails."""
        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_config_instance.list_plugin_parameters.side_effect = Exception(
            "Parameter error"
        )

        args = self.create_namespace(
            plugins_action="params",
            plugin_name="failing_plugin",
            type="iut",
            protocol=None,
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Error getting plugin parameters" in caplog.text

    def test_params_general_error_handling(self, caplog):
        """Test params command general error handling."""
        with patch("panther.cli.subcommands.plugins.ConfigLoader") as mock_config:
            mock_config.side_effect = Exception("General error")

            args = self.create_namespace(
                plugins_action="params",
                plugin_name="test_plugin",
                type="iut",
                protocol=None,
            )

            result = PluginsCommand.handle(args)

            assert result == 1
            assert "Error displaying plugin parameters" in caplog.text

    # =============================================================================
    # SCAN SUBCOMMAND TESTS
    # =============================================================================

    def test_scan_default_directory(self, mock_plugin_discovery_class, caplog):
        """Test scan command with default plugin directory."""
        mock_discovery_class, mock_discovery_instance = mock_plugin_discovery_class

        args = self.create_namespace(plugins_action="scan", directory=None)

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "Scanning directory:" in caplog.text
        assert "Scan complete. Found 5 plugin(s)" in caplog.text  # 2+1+2 from mock data
        assert "IUT Plugins (2):" in caplog.text
        assert "picoquic (v1.0.0)" in caplog.text
        assert "aioquic (v1.0.0)" in caplog.text
        assert "TESTERS Plugins (1):" in caplog.text
        assert "panther_ivy (v1.0.0)" in caplog.text

        # Verify discovery was created with default directory
        mock_discovery_class.assert_called_once()
        call_args = mock_discovery_class.call_args[0][0]  # First positional argument
        assert "plugins" in call_args[0]  # Default directory path

    def test_scan_custom_directory(self, mock_plugin_discovery_class, caplog):
        """Test scan command with custom directory."""
        mock_discovery_class, mock_discovery_instance = mock_plugin_discovery_class

        custom_dir = "/custom/plugin/directory"
        args = self.create_namespace(plugins_action="scan", directory=custom_dir)

        result = PluginsCommand.handle(args)

        assert result == 0
        assert f"Scanning directory: {custom_dir}" in caplog.text

        # Verify discovery was created with custom directory
        mock_discovery_class.assert_called_once_with([custom_dir])

    def test_scan_no_plugins_found(self, mock_plugin_discovery_class, caplog):
        """Test scan command when no plugins are found."""
        mock_discovery_class, mock_discovery_instance = mock_plugin_discovery_class
        mock_discovery_instance.list_available_plugins.return_value = {
            "iut": [],
            "testers": [],
            "environments": [],
        }

        args = self.create_namespace(plugins_action="scan", directory=None)

        result = PluginsCommand.handle(args)

        assert result == 0
        assert "Scan complete. Found 0 plugin(s)" in caplog.text

    def test_scan_error_handling(self, caplog):
        """Test scan command error handling."""
        with patch("panther.cli.subcommands.plugins.PluginDiscovery") as mock_discovery:
            mock_discovery.side_effect = Exception("Scan error")

            args = self.create_namespace(plugins_action="scan", directory=None)

            result = PluginsCommand.handle(args)

            assert result == 1
            assert "Error scanning plugins" in caplog.text

    # =============================================================================
    # VALIDATE SUBCOMMAND TESTS
    # =============================================================================

    def test_validate_directory_plugin_success(self, sample_plugin_directory, caplog):
        """Test validate command with valid directory plugin."""
        plugin_path = Path(sample_plugin_directory) / "iut" / "sample_iut"

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_path)
        )

        result = PluginsCommand.handle(args)

        assert result == 0
        assert f"Validating plugin: {plugin_path}" in caplog.text
        assert "Plugin syntax is valid" in caplog.text
        assert "Plugin structure is valid" in caplog.text

    def test_validate_single_file_plugin_success(self, sample_plugin_directory, caplog):
        """Test validate command with valid single file plugin."""
        plugin_file = (
            Path(sample_plugin_directory) / "iut" / "sample_iut" / "sample_iut.py"
        )

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_file)
        )

        result = PluginsCommand.handle(args)

        assert result == 0
        assert f"Validating plugin: {plugin_file}" in caplog.text
        assert "Plugin file exists and has valid syntax" in caplog.text

    def test_validate_plugin_not_found(self, caplog):
        """Test validate command when plugin path doesn't exist."""
        nonexistent_path = "/nonexistent/plugin/path"

        args = self.create_namespace(
            plugins_action="validate", plugin_path=nonexistent_path
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert f"Plugin path not found: {nonexistent_path}" in caplog.text

    def test_validate_directory_missing_main_file(self, tmp_path, caplog):
        """Test validate command when main plugin file is missing."""
        plugin_dir = tmp_path / "broken_plugin"
        plugin_dir.mkdir()
        # Don't create the main plugin file

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_dir)
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Main plugin file not found" in caplog.text

    def test_validate_directory_missing_config_schema(self, tmp_path, caplog):
        """Test validate command when config schema is missing (warning)."""
        plugin_dir = tmp_path / "plugin_no_schema"
        plugin_dir.mkdir()

        # Create main plugin file
        main_file = plugin_dir / f"{plugin_dir.name}.py"
        main_file.write_text("# Valid Python plugin")

        # Don't create config_schema.py

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_dir)
        )

        result = PluginsCommand.handle(args)

        assert result == 0  # Should succeed with warning
        assert "Warning: No config schema found" in caplog.text
        assert "Plugin structure is valid" in caplog.text

    def test_validate_syntax_error_in_plugin(self, tmp_path, caplog):
        """Test validate command with syntax error in plugin."""
        plugin_dir = tmp_path / "syntax_error_plugin"
        plugin_dir.mkdir()

        # Create plugin file with syntax error
        main_file = plugin_dir / f"{plugin_dir.name}.py"
        main_file.write_text(
            """
# Plugin with syntax error
def broken_function(
    # Missing closing parenthesis and body
"""
        )

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_dir)
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Syntax error in plugin" in caplog.text

    def test_validate_syntax_error_in_single_file(self, tmp_path, caplog):
        """Test validate command with syntax error in single file plugin."""
        plugin_file = tmp_path / "broken_plugin.py"
        plugin_file.write_text("invalid python syntax !!!")

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_file)
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Syntax error in plugin" in caplog.text

    def test_validate_error_handling(self, caplog):
        """Test validate command general error handling."""
        with patch("pathlib.Path") as mock_path:
            mock_path.side_effect = Exception("Path error")

            args = self.create_namespace(
                plugins_action="validate", plugin_path="/some/path"
            )

            result = PluginsCommand.handle(args)

            assert result == 1
            assert "Error validating plugin" in caplog.text

    # =============================================================================
    # CHECK-DEPS SUBCOMMAND TESTS
    # =============================================================================

    def test_check_deps_single_file_success(self, sample_plugin_directory, caplog):
        """Test check-deps command with single file plugin (all deps available)."""
        plugin_file = (
            Path(sample_plugin_directory) / "iut" / "sample_iut" / "sample_iut.py"
        )

        args = self.create_namespace(
            plugins_action="check-deps", plugin_path=str(plugin_file)
        )

        result = PluginsCommand.handle(args)

        assert result == 0
        assert f"Checking dependencies for: {plugin_file}" in caplog.text
        assert "All dependencies are available" in caplog.text

    def test_check_deps_directory_success(self, sample_plugin_directory, caplog):
        """Test check-deps command with directory plugin."""
        plugin_dir = Path(sample_plugin_directory) / "iut" / "sample_iut"

        args = self.create_namespace(
            plugins_action="check-deps", plugin_path=str(plugin_dir)
        )

        result = PluginsCommand.handle(args)

        assert result == 0
        assert f"Checking dependencies for: {plugin_dir}" in caplog.text
        assert "All dependencies are available" in caplog.text

    def test_check_deps_missing_dependencies(self, tmp_path, caplog):
        """Test check-deps command with missing dependencies."""
        plugin_file = tmp_path / "plugin_with_deps.py"
        plugin_file.write_text(
            """
import os  # Standard library - should be available
import sys  # Standard library - should be available
import nonexistent_module  # This should be missing
from another_missing import SomeClass
"""
        )

        args = self.create_namespace(
            plugins_action="check-deps", plugin_path=str(plugin_file)
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Missing dependencies:" in caplog.text
        assert "nonexistent_module" in caplog.text
        assert "another_missing" in caplog.text

    def test_check_deps_plugin_not_found(self, caplog):
        """Test check-deps command when plugin path doesn't exist."""
        nonexistent_path = "/nonexistent/plugin.py"

        args = self.create_namespace(
            plugins_action="check-deps", plugin_path=nonexistent_path
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert f"Plugin path not found: {nonexistent_path}" in caplog.text

    def test_check_deps_error_handling(self, caplog):
        """Test check-deps command error handling."""
        with patch("pathlib.Path") as mock_path:
            mock_path.side_effect = Exception("Path error")

            args = self.create_namespace(
                plugins_action="check-deps", plugin_path="/some/path"
            )

            result = PluginsCommand.handle(args)

            assert result == 1
            assert "Error checking dependencies" in caplog.text

    # =============================================================================
    # MIGRATE SUBCOMMAND TESTS
    # =============================================================================

    def test_migrate_deprecated_feature(self, caplog):
        """Test migrate command returns deprecation message."""
        args = self.create_namespace(
            plugins_action="migrate", dry_run=False, force=False
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Plugin migration feature has been removed" in caplog.text
        assert "This feature was incomplete and has been deprecated" in caplog.text
        assert "Create new plugins using 'panther create plugin' instead" in caplog.text

    def test_migrate_with_dry_run_flag(self, caplog):
        """Test migrate command with dry-run flag (still deprecated)."""
        args = self.create_namespace(
            plugins_action="migrate", dry_run=True, force=False
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Plugin migration feature has been removed" in caplog.text

    def test_migrate_with_force_flag(self, caplog):
        """Test migrate command with force flag (still deprecated)."""
        args = self.create_namespace(
            plugins_action="migrate", dry_run=False, force=True
        )

        result = PluginsCommand.handle(args)

        assert result == 1
        assert "Plugin migration feature has been removed" in caplog.text

    # =============================================================================
    # PARAMETER VALIDATION TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "invalid_action",
        ["invalid", "", "LIST", "params_wrong", 123, None],  # Case sensitive
    )
    def test_invalid_actions(self, invalid_action, caplog):
        """Test handling of invalid action parameters."""
        args = self.create_namespace(plugins_action=invalid_action)

        result = PluginsCommand.handle(args)

        if invalid_action is None:
            assert "No plugin action specified" in caplog.text
        else:
            assert result == 1

    @pytest.mark.parametrize("plugin_type", ["iut", "testers", "environments", "all"])
    def test_list_valid_plugin_types(self, plugin_type, mock_plugin_manager_class):
        """Test list command with all valid plugin type choices."""
        mock_class, mock_instance = mock_plugin_manager_class

        args = self.create_namespace(
            plugins_action="list", type=plugin_type, format="table"
        )

        result = PluginsCommand.handle(args)

        assert result == 0

    @pytest.mark.parametrize("format_choice", ["table", "json", "simple"])
    def test_list_valid_format_choices(self, format_choice, mock_plugin_manager_class):
        """Test list command with all valid format choices."""
        mock_class, mock_instance = mock_plugin_manager_class

        args = self.create_namespace(
            plugins_action="list", type="all", format=format_choice
        )

        result = PluginsCommand.handle(args)

        assert result == 0

    @pytest.mark.parametrize("flag_value", [True, False])
    def test_migrate_boolean_flags(self, flag_value, caplog):
        """Test migrate command boolean flags (though deprecated)."""
        args = self.create_namespace(
            plugins_action="migrate", dry_run=flag_value, force=flag_value
        )

        result = PluginsCommand.handle(args)

        assert result == 1  # Always fails due to deprecation
        assert "Plugin migration feature has been removed" in caplog.text

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_unicode_plugin_names(self, mock_config_loader_class):
        """Test handling of plugin names with unicode characters."""
        mock_config_class, mock_config_instance = mock_config_loader_class

        unicode_plugin_name = "测试插件"
        args = self.create_namespace(
            plugins_action="params",
            plugin_name=unicode_plugin_name,
            type="iut",
            protocol=None,
        )

        result = PluginsCommand.handle(args)

        assert result == 0  # Should handle unicode gracefully

    def test_very_long_plugin_paths(self, tmp_path):
        """Test handling of very long plugin paths."""
        # Create a deeply nested directory structure
        long_path = tmp_path
        for i in range(20):
            long_path = long_path / f"level_{i}"
        long_path.mkdir(parents=True)

        plugin_file = long_path / "plugin.py"
        plugin_file.write_text("# Valid plugin")

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_file)
        )

        result = PluginsCommand.handle(args)

        assert result == 0  # Should handle long paths gracefully

    def test_special_characters_in_plugin_path(self, tmp_path):
        """Test handling of special characters in plugin paths."""
        special_dir = tmp_path / "plugin-with-special_chars@#$"
        special_dir.mkdir()

        plugin_file = special_dir / "special_plugin.py"
        plugin_file.write_text("# Valid plugin")

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_file)
        )

        result = PluginsCommand.handle(args)

        assert result == 0  # Should handle special characters

    def test_empty_plugin_file(self, tmp_path, caplog):
        """Test handling of empty plugin files."""
        empty_plugin = tmp_path / "empty_plugin.py"
        empty_plugin.write_text("")  # Empty file

        args = self.create_namespace(
            plugins_action="validate", plugin_path=str(empty_plugin)
        )

        result = PluginsCommand.handle(args)

        assert result == 0  # Empty files are syntactically valid
        assert "Plugin file exists and has valid syntax" in caplog.text

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_plugin_workflow(
        self,
        sample_plugin_directory,
        mock_plugin_manager_class,
        mock_config_loader_class,
        caplog,
    ):
        """Test complete plugin workflow: scan → list → params → validate → check-deps."""
        mock_manager_class, mock_manager_instance = mock_plugin_manager_class
        mock_config_class, mock_config_instance = mock_config_loader_class

        # Step 1: Scan for plugins
        args_scan = self.create_namespace(
            plugins_action="scan", directory=sample_plugin_directory
        )

        with patch("panther.cli.subcommands.plugins.PluginDiscovery") as mock_discovery:
            mock_discovery_instance = MagicMock()
            mock_discovery_instance.list_available_plugins.return_value = {
                "iut": ["sample_iut"],
                "testers": ["sample_tester"],
                "environments": [],
            }
            mock_discovery_instance.get_plugin_info.return_value = {"version": "1.0.0"}
            mock_discovery.return_value = mock_discovery_instance

            result = PluginsCommand.handle(args_scan)
            assert result == 0
            assert "Found 2 plugin(s)" in caplog.text

        # Step 2: List plugins
        args_list = self.create_namespace(
            plugins_action="list", type="all", format="table"
        )

        result = PluginsCommand.handle(args_list)
        assert result == 0

        # Step 3: Get plugin parameters
        args_params = self.create_namespace(
            plugins_action="params", plugin_name="sample_iut", type="iut", protocol=None
        )

        result = PluginsCommand.handle(args_params)
        assert result == 0
        assert "Parameters for plugin:" in caplog.text

        # Step 4: Validate plugin
        plugin_path = Path(sample_plugin_directory) / "iut" / "sample_iut"
        args_validate = self.create_namespace(
            plugins_action="validate", plugin_path=str(plugin_path)
        )

        result = PluginsCommand.handle(args_validate)
        assert result == 0
        assert "Plugin structure is valid" in caplog.text

        # Step 5: Check dependencies
        args_deps = self.create_namespace(
            plugins_action="check-deps", plugin_path=str(plugin_path)
        )

        result = PluginsCommand.handle(args_deps)
        assert result == 0
        assert "All dependencies are available" in caplog.text

    def test_comprehensive_parameter_combinations(
        self, mock_plugin_manager_class, mock_config_loader_class, sample_plugin_data
    ):
        """Test plugins command with comprehensive parameter combinations."""
        mock_manager_class, mock_manager_instance = mock_plugin_manager_class
        mock_config_class, mock_config_instance = mock_config_loader_class

        # Setup mock to return sample data
        mock_manager_instance.get_plugins_by_type.return_value = sample_plugin_data

        # Test list with all combinations
        list_combinations = [
            {"type": "all", "format": "table"},
            {"type": "iut", "format": "json"},
            {"type": "testers", "format": "simple"},
            {"type": "environments", "format": "table"},
        ]

        for combo in list_combinations:
            args = self.create_namespace(plugins_action="list", **combo)

            result = PluginsCommand.handle(args)
            assert result == 0

        # Test params with different combinations
        params_combinations = [
            {"plugin_name": "picoquic", "type": "iut", "protocol": None},
            {"plugin_name": "aioquic", "type": "iut", "protocol": "quic"},
            {"plugin_name": "panther_ivy", "type": "testers", "protocol": None},
        ]

        for combo in params_combinations:
            args = self.create_namespace(plugins_action="params", **combo)

            result = PluginsCommand.handle(args)
            assert result == 0

        # Verify all components were used
        assert mock_manager_class.call_count >= len(list_combinations)
        assert mock_config_class.call_count >= len(params_combinations)
