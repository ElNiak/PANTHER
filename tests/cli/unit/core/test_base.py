"""Test cases for base utilities and decorators.

Tests common decorators, error handling, logging setup,
and message functions.
"""

import logging
import subprocess
from unittest.mock import patch

import click
import pytest

from panther.cli.core.base import (
    common_options,
    error_message,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    setup_logging,
    success_message,
    warning_message,
)


class TestCommonOptions:
    """Test the common_options decorator."""

    def test_common_options_decorator(self, cli_runner):
        """Test that common_options adds expected options."""

        @click.command()
        @common_options
        def test_command(config, verbose, dry_run):
            click.echo(f"config: {config}, verbose: {verbose}, dry_run: {dry_run}")

        # Test with options
        result = cli_runner.invoke(test_command, ["--verbose", "--dry-run"])
        assert result.exit_code == 0
        assert "verbose: True" in result.output
        assert "dry_run: True" in result.output

    def test_common_options_help(self, cli_runner):
        """Test that common_options adds help text."""

        @click.command()
        @common_options
        def test_command(config, verbose, dry_run):
            pass

        result = cli_runner.invoke(test_command, ["--help"])
        assert result.exit_code == 0
        assert "--config" in result.output
        assert "--verbose" in result.output
        assert "--dry-run" in result.output
        assert "Configuration file path" in result.output

    def test_common_options_with_config_file(self, cli_runner, sample_config_file):
        """Test common_options with actual config file."""

        @click.command()
        @common_options
        def test_command(config, verbose, dry_run):
            click.echo(f"config: {config}")

        result = cli_runner.invoke(test_command, ["--config", str(sample_config_file)])
        assert result.exit_code == 0
        assert str(sample_config_file) in result.output


class TestHandleErrors:
    """Test the handle_errors decorator."""

    def test_handle_keyboard_interrupt(self, cli_runner):
        """Test handling of KeyboardInterrupt."""

        @click.command()
        @handle_errors
        def test_command():
            raise KeyboardInterrupt()

        result = cli_runner.invoke(test_command)
        assert result.exit_code != 0
        assert "Operation cancelled by user" in result.output

    def test_handle_subprocess_error(self, cli_runner):
        """Test handling of subprocess.CalledProcessError."""

        @click.command()
        @handle_errors
        def test_command():
            raise subprocess.CalledProcessError(1, "test-command", "error output")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1
        assert "Command failed:" in result.output

    def test_handle_file_not_found(self, cli_runner):
        """Test handling of FileNotFoundError."""

        @click.command()
        @handle_errors
        def test_command():
            raise FileNotFoundError("test file not found")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1
        assert "File not found:" in result.output

    def test_handle_permission_error(self, cli_runner):
        """Test handling of PermissionError."""

        @click.command()
        @handle_errors
        def test_command():
            raise PermissionError("permission denied")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1
        assert "Permission denied:" in result.output

    def test_handle_generic_exception(self, cli_runner):
        """Test handling of generic exceptions (non-debug mode uses click.echo)."""

        @click.command()
        @handle_errors
        def test_command():
            raise RuntimeError("test error")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1
        assert "Error: test error" in result.output

    def test_handle_success(self, cli_runner):
        """Test that successful commands pass through unchanged."""

        @click.command()
        @handle_errors
        def test_command():
            click.echo("success")
            return 0

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 0
        assert "success" in result.output


class TestSetupLogging:
    """Test logging setup function."""

    def test_setup_logging_debug(self):
        """Test logging setup with debug enabled uses LoggerFactory."""
        with patch(
            "panther.core.utils.logger_factory.LoggerFactory.initialize"
        ) as mock_init:
            setup_logging(debug=True, verbose=False)
            mock_init.assert_called_once()
            config = mock_init.call_args[0][0]
            assert config["level"] == "DEBUG"

    def test_setup_logging_verbose(self):
        """Test logging setup with verbose enabled uses LoggerFactory."""
        with patch(
            "panther.core.utils.logger_factory.LoggerFactory.initialize"
        ) as mock_init:
            setup_logging(debug=False, verbose=True)
            mock_init.assert_called_once()
            config = mock_init.call_args[0][0]
            assert config["level"] == "INFO"

    def test_setup_logging_default(self):
        """Test logging setup with defaults uses LoggerFactory."""
        with patch(
            "panther.core.utils.logger_factory.LoggerFactory.initialize"
        ) as mock_init:
            setup_logging(debug=False, verbose=False)
            mock_init.assert_called_once()
            config = mock_init.call_args[0][0]
            assert config["level"] == "WARNING"


class TestPassContextAndSetupLogging:
    """Test the pass_context_and_setup_logging decorator."""

    def test_context_passing(self, cli_runner):
        """Test that context is properly passed."""

        @click.command()
        @pass_context_and_setup_logging
        def test_command(ctx):
            click.echo(f"debug: {ctx.obj.get('debug', False)}")

        with patch("panther.cli.core.base.setup_logging") as mock_setup:
            result = cli_runner.invoke(test_command, obj={"debug": True})
            assert result.exit_code == 0
            mock_setup.assert_called_once()

    def test_logging_setup_from_context(self, cli_runner):
        """Test that logging is set up based on context."""

        @click.command()
        @click.option("--verbose", is_flag=True)
        @pass_context_and_setup_logging
        def test_command(ctx, verbose):
            click.echo("test")

        with patch("panther.cli.core.base.setup_logging") as mock_setup:
            result = cli_runner.invoke(
                test_command, ["--verbose"], obj={"debug": False}
            )
            assert result.exit_code == 0
            mock_setup.assert_called_once_with(False, True)


class TestMessageFunctions:
    """Test message output functions."""

    def test_success_message(self):
        """Test success message calls _cli_message with success style."""
        with patch("panther.cli.core.base._cli_message") as mock_msg:
            success_message("Test success")
            mock_msg.assert_called_once_with("Test success", "success")

    def test_info_message(self):
        """Test info message calls _cli_message with info style."""
        with patch("panther.cli.core.base._cli_message") as mock_msg:
            info_message("Test info")
            mock_msg.assert_called_once_with("Test info", "info")

    def test_warning_message(self):
        """Test warning message calls _cli_message with warning style."""
        with patch("panther.cli.core.base._cli_message") as mock_msg:
            warning_message("Test warning")
            mock_msg.assert_called_once_with("Test warning", "warning")

    def test_error_message(self):
        """Test error message calls _cli_message with error style."""
        with patch("panther.cli.core.base._cli_message") as mock_msg:
            error_message("Test error")
            mock_msg.assert_called_once_with("Test error", "error")


class TestDecoratorsIntegration:
    """Integration tests for decorator combinations."""

    def test_combined_decorators(self, cli_runner):
        """Test combining multiple decorators."""

        @click.command()
        @common_options
        @pass_context_and_setup_logging
        def test_command(ctx, config, verbose, dry_run):
            click.echo(f"config: {config}, verbose: {verbose}, dry_run: {dry_run}")
            click.echo(f"debug: {ctx.obj.get('debug', False)}")

        with patch("panther.cli.core.base.setup_logging"):
            result = cli_runner.invoke(
                test_command, ["--verbose", "--dry-run"], obj={"debug": True}
            )
            assert result.exit_code == 0
            assert "verbose: True" in result.output
            assert "dry_run: True" in result.output
            assert "debug: True" in result.output

    def test_error_handling_with_context(self, cli_runner):
        """Test error handling with context information (debug mode logs to logging)."""

        @click.command()
        @handle_errors
        @pass_context_and_setup_logging
        def test_command(ctx):
            ctx.obj["debug"] = True
            raise RuntimeError("Test error with debug")

        with patch("panther.cli.core.base.setup_logging"):
            # Clear stale handlers from LoggerFactory initialized by prior tests
            # to prevent ValueError: I/O operation on closed file
            logging.root.handlers.clear()
            result = cli_runner.invoke(test_command, obj={"debug": True})
            assert result.exit_code == 1
