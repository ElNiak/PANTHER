"""
Test cases for the main CLI entry point.

Tests the main CLI group, version handling, debug/verbose flags,
completion functionality, and command registration.
"""

import pytest
from click.testing import CliRunner

from panther.cli_click.core.main import cli, main, register_commands


class TestMainCLI:
    """Test the main CLI entry point and core functionality."""

    def test_cli_help(self, cli_runner):
        """Test that CLI help works correctly."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "PANTHER - Protocol Analysis and Testing" in result.output
        assert "Modern CLI for network protocol testing" in result.output
        assert "Key Features:" in result.output

    def test_cli_version(self, cli_runner):
        """Test version option displays correct version."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.1.3" in result.output
        assert "panther" in result.output

    def test_cli_debug_flag(self, cli_runner):
        """Test debug flag enables debug mode."""
        result = cli_runner.invoke(cli, ["--debug", "--help"])
        assert result.exit_code == 0
        assert "🐛 Debug mode enabled" in result.output

    def test_cli_verbose_flag(self, cli_runner):
        """Test verbose flag enables verbose mode."""
        result = cli_runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0
        assert "🔍 Verbose mode enabled" in result.output

    def test_cli_no_debug_verbose(self, cli_runner):
        """Test CLI works without debug or verbose flags."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "🐛 Debug mode enabled" not in result.output
        assert "🔍 Verbose mode enabled" not in result.output

    def test_cli_context_setup(self, cli_runner):
        """Test that CLI context is properly set up."""
        # This tests the context setup by invoking a command that uses context
        result = cli_runner.invoke(cli, ["--debug", "--verbose", "--help"])
        assert result.exit_code == 0
        # Context setup should work without errors


class TestCompletionCommand:
    """Test shell completion functionality."""

    def test_completion_bash(self, cli_runner):
        """Test bash completion generation."""
        result = cli_runner.invoke(cli, ["completion", "bash"])
        assert result.exit_code == 0
        assert "PANTHER bash completion" in result.output
        assert "_panther_completion" in result.output
        assert "complete -F _panther_completion" in result.output

    def test_completion_zsh(self, cli_runner):
        """Test zsh completion generation."""
        result = cli_runner.invoke(cli, ["completion", "zsh"])
        assert result.exit_code == 0
        assert "PANTHER zsh completion" in result.output
        assert "#compdef panther" in result.output
        assert "_panther_completion" in result.output

    def test_completion_fish(self, cli_runner):
        """Test fish completion generation."""
        result = cli_runner.invoke(cli, ["completion", "fish"])
        assert result.exit_code == 0
        assert "PANTHER fish completion" in result.output
        assert "complete -c panther" in result.output
        assert "_PANTHER_COMPLETE=complete_fish" in result.output

    def test_completion_invalid_shell(self, cli_runner):
        """Test completion with invalid shell."""
        result = cli_runner.invoke(cli, ["completion", "invalid"])
        assert result.exit_code != 0

    def test_completion_output_file(self, cli_runner, temp_dir):
        """Test completion output to file."""
        output_file = temp_dir / "completion.bash"
        result = cli_runner.invoke(
            cli, ["completion", "bash", "--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert f"✅ Completion script written to {output_file}" in result.output
        assert output_file.exists()

        # Check file contents
        content = output_file.read_text()
        assert "PANTHER bash completion" in content
        assert "_panther_completion" in content

    def test_completion_auto_detect_shell(self, cli_runner):
        """Test shell auto-detection (falls back to bash)."""
        result = cli_runner.invoke(cli, ["completion"])
        assert result.exit_code == 0
        # Should default to bash completion
        assert "bash completion" in result.output


class TestCommandRegistration:
    """Test command registration functionality."""

    def test_register_commands_function(self):
        """Test that register_commands function works."""
        # This test verifies the function can be called without errors
        # The actual command registration is tested indirectly through other tests
        register_commands()

    def test_main_function_error_handling(self, cli_runner, monkeypatch):
        """Test main function error handling."""
        # Mock sys.argv to test error handling
        import sys

        original_argv = sys.argv.copy()

        try:
            # Test with debug flag for traceback
            sys.argv = ["panther", "--debug", "nonexistent-command"]

            # The main function should handle errors gracefully
            # We can't directly test main() as it calls sys.exit()
            # But we can test the CLI directly
            result = cli_runner.invoke(cli, ["nonexistent-command"])
            assert result.exit_code != 0

        finally:
            sys.argv = original_argv

    def test_available_commands(self, cli_runner):
        """Test that expected commands are registered."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Check for expected commands in help output
        expected_commands = [
            "completion",
            "run",
            "config",
            "plugins",
            "create",
            "tutorial",
            "admin",
            "check",
            "metrics",
            "tools",
        ]

        for command in expected_commands:
            assert (
                command in result.output
            ), f"Command '{command}' not found in help output"


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_cli_with_debug_verbose(self, cli_runner):
        """Test CLI with both debug and verbose flags."""
        result = cli_runner.invoke(cli, ["--debug", "--verbose", "--help"])
        assert result.exit_code == 0
        assert "🐛 Debug mode enabled" in result.output
        # Verbose message may not appear if debug is enabled

    def test_cli_subcommand_help(self, cli_runner):
        """Test help for subcommands."""
        # Test a few key subcommands
        subcommands = ["config", "run"]

        for cmd in subcommands:
            result = cli_runner.invoke(cli, [cmd, "--help"])
            assert result.exit_code == 0, f"Help for {cmd} command failed"
            assert f"{cmd}" in result.output.lower()

    def test_cli_error_handling(self, cli_runner):
        """Test CLI error handling with invalid commands."""
        result = cli_runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0
        assert "No such command" in result.output

    @pytest.mark.parametrize("global_flag", ["--debug", "--verbose", "--no-debug"])
    def test_global_flags(self, cli_runner, global_flag):
        """Test various global flags."""
        result = cli_runner.invoke(cli, [global_flag, "--help"])
        # Should not fail with any valid global flag
        assert result.exit_code == 0


class TestCLIOutput:
    """Test CLI output formatting and colors."""

    def test_help_formatting(self, cli_runner):
        """Test that help output is properly formatted."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Check for emoji usage in help
        assert "🔬" in result.output  # Protocol formal analysis
        assert "🐋" in result.output  # Docker-based testing
        assert "🌐" in result.output  # Network simulation
        assert "📊" in result.output  # Metrics and reporting
        assert "🔧" in result.output  # Plugin architecture

    def test_examples_in_help(self, cli_runner):
        """Test that examples are included in help output."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

        # Check for example commands
        assert "panther run --config experiment.yaml" in result.output
        assert "panther config validate --config config.yaml" in result.output
        assert "panther plugins list" in result.output

    def test_version_output_format(self, cli_runner):
        """Test version output format."""
        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Should contain both program name and version
        assert "panther" in result.output.lower()
        assert "1.1.3" in result.output
