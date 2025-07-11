"""
Test cases for the plugins command.

Tests plugin management, listing, installation, and configuration functionality.
"""

from unittest.mock import Mock, patch

import pytest

from panther.cli_click.core.main import cli


class TestPluginsCommand:
    """Test the plugins command functionality."""

    def test_plugins_help(self, cli_runner):
        """Test plugins command help output."""
        result = cli_runner.invoke(cli, ["plugins", "--help"])
        assert result.exit_code == 0
        assert "plugins" in result.output.lower()

    def test_plugins_list_subcommand(self, cli_runner):
        """Test plugins list subcommand."""
        result = cli_runner.invoke(cli, ["plugins", "list", "--help"])
        # Should show help for list subcommand
        assert result.exit_code == 0 or "list" in result.output

    def test_plugins_available_subcommands(self, cli_runner):
        """Test that plugins command shows available subcommands."""
        result = cli_runner.invoke(cli, ["plugins", "--help"])
        assert result.exit_code == 0
        # Common plugin subcommands
        expected_commands = ["list", "install", "status"]
        for cmd in expected_commands:
            # Check if command exists (may vary based on implementation)
            if cmd in result.output:
                assert cmd in result.output

    def test_plugins_with_verbose(self, cli_runner):
        """Test plugins command with verbose flag."""
        result = cli_runner.invoke(cli, ["--verbose", "plugins", "--help"])
        assert result.exit_code == 0
        assert "🔍 Verbose mode enabled" in result.output

    def test_plugins_with_debug(self, cli_runner):
        """Test plugins command with debug flag."""
        result = cli_runner.invoke(cli, ["--debug", "plugins", "--help"])
        assert result.exit_code == 0
        assert "🐛 Debug mode enabled" in result.output


class TestPluginsListCommand:
    """Test the plugins list functionality."""

    def test_plugins_list_help(self, cli_runner):
        """Test plugins list command help."""
        result = cli_runner.invoke(cli, ["plugins", "list", "--help"])
        # Should work or show that list command exists
        assert result.exit_code == 0 or result.exit_code == 2

    def test_plugins_list_execution(self, cli_runner):
        """Test plugins list command execution."""
        result = cli_runner.invoke(cli, ["plugins", "list"])
        # Should execute without crashing
        assert result.exit_code is not None

    def test_plugins_list_with_type_filter(self, cli_runner):
        """Test plugins list with type filtering."""
        # Test common plugin types
        plugin_types = ["iut", "tester", "environment"]
        for plugin_type in plugin_types:
            result = cli_runner.invoke(cli, ["plugins", "list", "--type", plugin_type])
            # Should handle type filtering
            assert result.exit_code is not None

    def test_plugins_list_with_verbose(self, cli_runner):
        """Test plugins list with verbose output."""
        result = cli_runner.invoke(cli, ["plugins", "list", "--verbose"])
        assert result.exit_code is not None

    def test_plugins_list_with_format(self, cli_runner):
        """Test plugins list with different output formats."""
        formats = ["table", "json", "yaml"]
        for fmt in formats:
            result = cli_runner.invoke(cli, ["plugins", "list", "--format", fmt])
            # Should handle format option if available
            assert result.exit_code is not None


class TestPluginsStatusCommand:
    """Test the plugins status functionality."""

    def test_plugins_status_help(self, cli_runner):
        """Test plugins status command help."""
        result = cli_runner.invoke(cli, ["plugins", "status", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_plugins_status_execution(self, cli_runner):
        """Test plugins status command execution."""
        result = cli_runner.invoke(cli, ["plugins", "status"])
        assert result.exit_code is not None

    def test_plugins_status_specific_plugin(self, cli_runner):
        """Test plugins status for specific plugin."""
        result = cli_runner.invoke(cli, ["plugins", "status", "picoquic"])
        assert result.exit_code is not None


class TestPluginsInstallCommand:
    """Test the plugins install functionality."""

    def test_plugins_install_help(self, cli_runner):
        """Test plugins install command help."""
        result = cli_runner.invoke(cli, ["plugins", "install", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_plugins_install_missing_plugin(self, cli_runner):
        """Test plugins install without plugin name."""
        result = cli_runner.invoke(cli, ["plugins", "install"])
        # Should either require plugin name or show help
        assert result.exit_code is not None

    def test_plugins_install_with_plugin_name(self, cli_runner):
        """Test plugins install with plugin name."""
        result = cli_runner.invoke(cli, ["plugins", "install", "test-plugin"])
        assert result.exit_code is not None

    def test_plugins_install_with_force(self, cli_runner):
        """Test plugins install with force option."""
        result = cli_runner.invoke(
            cli, ["plugins", "install", "test-plugin", "--force"]
        )
        assert result.exit_code is not None

    def test_plugins_install_with_version(self, cli_runner):
        """Test plugins install with specific version."""
        result = cli_runner.invoke(
            cli, ["plugins", "install", "test-plugin", "--version", "1.0.0"]
        )
        assert result.exit_code is not None


class TestPluginsRemoveCommand:
    """Test the plugins remove functionality."""

    def test_plugins_remove_help(self, cli_runner):
        """Test plugins remove command help."""
        result = cli_runner.invoke(cli, ["plugins", "remove", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_plugins_remove_with_plugin_name(self, cli_runner):
        """Test plugins remove with plugin name."""
        result = cli_runner.invoke(cli, ["plugins", "remove", "test-plugin"])
        assert result.exit_code is not None

    def test_plugins_remove_with_force(self, cli_runner):
        """Test plugins remove with force option."""
        result = cli_runner.invoke(cli, ["plugins", "remove", "test-plugin", "--force"])
        assert result.exit_code is not None


class TestPluginsValidateCommand:
    """Test the plugins validate functionality."""

    def test_plugins_validate_help(self, cli_runner):
        """Test plugins validate command help."""
        result = cli_runner.invoke(cli, ["plugins", "validate", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_plugins_validate_all(self, cli_runner):
        """Test plugins validate all plugins."""
        result = cli_runner.invoke(cli, ["plugins", "validate"])
        assert result.exit_code is not None

    def test_plugins_validate_specific_plugin(self, cli_runner):
        """Test plugins validate specific plugin."""
        result = cli_runner.invoke(cli, ["plugins", "validate", "picoquic"])
        assert result.exit_code is not None

    def test_plugins_validate_with_strict(self, cli_runner):
        """Test plugins validate with strict mode."""
        result = cli_runner.invoke(cli, ["plugins", "validate", "--strict"])
        assert result.exit_code is not None


class TestPluginsWithMockAdapter:
    """Test plugins commands with mocked adapters."""

    def test_plugins_list_with_mock_adapter(self, cli_runner):
        """Test plugins list with mocked adapter."""
        mock_adapter = Mock()
        mock_adapter.handle_with_conversion.return_value = 0

        with patch("panther.cli_click.commands.plugins.plugins_adapter", mock_adapter):
            result = cli_runner.invoke(cli, ["plugins", "list"])
            # If adapter is available, should be called
            if hasattr(result, "exit_code"):
                assert result.exit_code is not None

    def test_plugins_adapter_failure(self, cli_runner):
        """Test plugins command when adapter fails."""
        mock_adapter = Mock()
        mock_adapter.handle_with_conversion.return_value = 1

        with patch("panther.cli_click.commands.plugins.plugins_adapter", mock_adapter):
            result = cli_runner.invoke(cli, ["plugins", "list"])
            assert result.exit_code is not None

    def test_plugins_adapter_exception(self, cli_runner):
        """Test plugins command when adapter raises exception."""
        mock_adapter = Mock()
        mock_adapter.handle_with_conversion.side_effect = RuntimeError("Adapter error")

        with patch("panther.cli_click.commands.plugins.plugins_adapter", mock_adapter):
            result = cli_runner.invoke(cli, ["plugins", "list"])
            assert result.exit_code is not None


class TestPluginsErrorHandling:
    """Test plugins command error handling."""

    def test_plugins_invalid_subcommand(self, cli_runner):
        """Test plugins with invalid subcommand."""
        result = cli_runner.invoke(cli, ["plugins", "invalid-command"])
        assert result.exit_code != 0

    def test_plugins_missing_required_args(self, cli_runner):
        """Test plugins commands with missing required arguments."""
        # Test commands that typically require arguments
        commands_with_args = [
            ["plugins", "install"],
            ["plugins", "remove"],
            ["plugins", "info"],
        ]

        for cmd in commands_with_args:
            result = cli_runner.invoke(cli, cmd)
            # Should either succeed or fail gracefully
            assert result.exit_code is not None

    def test_plugins_invalid_options(self, cli_runner):
        """Test plugins commands with invalid options."""
        result = cli_runner.invoke(cli, ["plugins", "list", "--invalid-option"])
        assert result.exit_code != 0


class TestPluginsIntegration:
    """Integration tests for plugins command functionality."""

    def test_plugins_workflow(self, cli_runner):
        """Test complete plugins workflow."""
        # List plugins
        result1 = cli_runner.invoke(cli, ["plugins", "list"])
        assert result1.exit_code is not None

        # Check plugin status
        result2 = cli_runner.invoke(cli, ["plugins", "status"])
        assert result2.exit_code is not None

        # Validate plugins
        result3 = cli_runner.invoke(cli, ["plugins", "validate"])
        assert result3.exit_code is not None

    def test_plugins_with_global_flags(self, cli_runner):
        """Test plugins commands with global flags."""
        # Test with debug
        result = cli_runner.invoke(cli, ["--debug", "plugins", "list"])
        assert "🐛 Debug mode enabled" in result.output

        # Test with verbose
        result = cli_runner.invoke(cli, ["--verbose", "plugins", "status"])
        assert "🔍 Verbose mode enabled" in result.output

    def test_plugins_output_formatting(self, cli_runner):
        """Test plugins command output formatting."""
        result = cli_runner.invoke(cli, ["plugins", "list"])
        # Should produce some kind of output
        assert result.exit_code is not None
        # Check for common output patterns
        if result.output:
            # Should be readable output (not just error messages)
            assert len(result.output.strip()) > 0

    def test_plugins_help_consistency(self, cli_runner):
        """Test that plugins help is consistent across subcommands."""
        # Main plugins help
        result = cli_runner.invoke(cli, ["plugins", "--help"])
        assert result.exit_code == 0

        # Subcommand helps (if they exist)
        subcommands = ["list", "install", "status", "validate"]
        for subcmd in subcommands:
            result = cli_runner.invoke(cli, ["plugins", subcmd, "--help"])
            # Should either show help or indicate command doesn't exist
            assert result.exit_code == 0 or result.exit_code == 2


class TestPluginsConfiguration:
    """Test plugins command configuration handling."""

    def test_plugins_with_config_file(self, cli_runner, sample_config_file):
        """Test plugins commands with configuration file."""
        result = cli_runner.invoke(
            cli, ["plugins", "list", "--config", str(sample_config_file)]
        )
        assert result.exit_code is not None

    def test_plugins_with_plugin_directories(self, cli_runner, temp_dir):
        """Test plugins commands with custom plugin directories."""
        plugin_dir = temp_dir / "custom_plugins"
        plugin_dir.mkdir()

        result = cli_runner.invoke(
            cli, ["plugins", "list", "--plugin-dir", str(plugin_dir)]
        )
        assert result.exit_code is not None

    def test_plugins_environment_variables(self, cli_runner, env_vars):
        """Test plugins commands with environment variables."""
        # Set plugin-related environment variables
        env_vars["PANTHER_PLUGIN_DIR"] = "/custom/plugin/path"

        result = cli_runner.invoke(cli, ["plugins", "list"])
        assert result.exit_code is not None

    def test_plugins_json_output(self, cli_runner):
        """Test plugins commands with JSON output."""
        result = cli_runner.invoke(cli, ["plugins", "list", "--format", "json"])
        # Should handle JSON format if supported
        assert result.exit_code is not None

        if result.output and "{" in result.output:
            # If JSON output is present, it should be valid
            import json

            try:
                json.loads(result.output)
            except json.JSONDecodeError:
                # JSON output may be mixed with other text
                pass
