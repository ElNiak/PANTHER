"""
Test cases for base utilities and decorators.

Tests common decorators, error handling, logging setup,
message functions, and command adapters.
"""

import logging
import subprocess
from unittest.mock import MagicMock, Mock, patch

import click
import pytest

from panther.cli_click.core.base import (
    ClickCommandAdapter,
    common_options,
    create_command_adapter,
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

        @common_options
        @click.command()
        def test_command(config, verbose, dry_run):
            click.echo(f"config: {config}, verbose: {verbose}, dry_run: {dry_run}")

        # Test with options
        result = cli_runner.invoke(test_command, ["--verbose", "--dry-run"])
        assert result.exit_code == 0
        assert "verbose: True" in result.output
        assert "dry_run: True" in result.output

    def test_common_options_help(self, cli_runner):
        """Test that common_options adds help text."""

        @common_options
        @click.command()
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

        @common_options
        @click.command()
        def test_command(config, verbose, dry_run):
            click.echo(f"config: {config}")

        result = cli_runner.invoke(test_command, ["--config", str(sample_config_file)])
        assert result.exit_code == 0
        assert str(sample_config_file) in result.output


class TestHandleErrors:
    """Test the handle_errors decorator."""

    def test_handle_keyboard_interrupt(self, cli_runner):
        """Test handling of KeyboardInterrupt."""

        @handle_errors
        @click.command()
        def test_command():
            raise KeyboardInterrupt()

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1  # click.Abort() causes exit code 1
        assert "❌ Operation cancelled by user." in result.output

    def test_handle_subprocess_error(self, cli_runner):
        """Test handling of subprocess.CalledProcessError."""

        @handle_errors
        @click.command()
        def test_command():
            raise subprocess.CalledProcessError(1, "test-command", "error output")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1
        assert "❌ Command failed:" in result.output

    def test_handle_file_not_found(self, cli_runner):
        """Test handling of FileNotFoundError."""

        @handle_errors
        @click.command()
        def test_command():
            raise FileNotFoundError("test file not found")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1
        assert "❌ File not found:" in result.output

    def test_handle_permission_error(self, cli_runner):
        """Test handling of PermissionError."""

        @handle_errors
        @click.command()
        def test_command():
            raise PermissionError("permission denied")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1
        assert "❌ Permission denied:" in result.output

    def test_handle_generic_exception(self, cli_runner):
        """Test handling of generic exceptions."""

        @handle_errors
        @click.command()
        @click.pass_context
        def test_command(ctx):
            # Set debug mode in context
            ctx.ensure_object(dict)
            ctx.obj["debug"] = True
            raise RuntimeError("test error")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 1
        assert "❌ Unexpected error:" in result.output

    def test_handle_success(self, cli_runner):
        """Test that successful commands pass through unchanged."""

        @handle_errors
        @click.command()
        def test_command():
            click.echo("success")
            return 0

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 0
        assert "success" in result.output


class TestSetupLogging:
    """Test logging setup function."""

    def test_setup_logging_debug(self):
        """Test logging setup with debug enabled."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(debug=True, verbose=False)
            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args
            assert kwargs["level"] == logging.DEBUG
            assert "%(asctime)s" in kwargs["format"]

    def test_setup_logging_verbose(self):
        """Test logging setup with verbose enabled."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(debug=False, verbose=True)
            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args
            assert kwargs["level"] == logging.INFO
            assert "%(levelname)s:" in kwargs["format"]

    def test_setup_logging_default(self):
        """Test logging setup with default settings."""
        with patch("logging.basicConfig") as mock_config:
            setup_logging(debug=False, verbose=False)
            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args
            assert kwargs["level"] == logging.WARNING
            assert kwargs["format"] == "%(message)s"


class TestPassContextAndSetupLogging:
    """Test the pass_context_and_setup_logging decorator."""

    def test_context_passing(self, cli_runner):
        """Test that context is properly passed."""

        @pass_context_and_setup_logging
        @click.command()
        def test_command(ctx):
            click.echo(f"debug: {ctx.obj.get('debug', False)}")

        # Create a context with debug enabled
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"debug": True}

        with patch("panther.cli_click.core.base.setup_logging") as mock_setup:
            result = cli_runner.invoke(test_command, obj={"debug": True})
            assert result.exit_code == 0
            mock_setup.assert_called_once()

    def test_logging_setup_from_context(self, cli_runner):
        """Test that logging is set up based on context."""

        @pass_context_and_setup_logging
        @click.command()
        @click.option("--verbose", is_flag=True)
        def test_command(ctx, verbose):
            click.echo("test")

        with patch("panther.cli_click.core.base.setup_logging") as mock_setup:
            result = cli_runner.invoke(
                test_command, ["--verbose"], obj={"debug": False}
            )
            assert result.exit_code == 0
            mock_setup.assert_called_once_with(False, True)


class TestMessageFunctions:
    """Test message output functions."""

    def test_success_message(self, cli_runner):
        """Test success message output."""

        @click.command()
        def test_command():
            success_message("Test success")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 0
        assert "✅ Test success" in result.output

    def test_info_message(self, cli_runner):
        """Test info message output."""

        @click.command()
        def test_command():
            info_message("Test info")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 0
        assert "ℹ️  Test info" in result.output

    def test_warning_message(self, cli_runner):
        """Test warning message output."""

        @click.command()
        def test_command():
            warning_message("Test warning")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 0
        assert "⚠️  Test warning" in result.output

    def test_error_message(self, cli_runner):
        """Test error message output."""

        @click.command()
        def test_command():
            error_message("Test error")

        result = cli_runner.invoke(test_command)
        assert result.exit_code == 0
        assert "❌ Test error" in result.output


class TestClickCommandAdapter:
    """Test the ClickCommandAdapter class."""

    def test_adapter_initialization(self):
        """Test adapter initialization."""
        mock_command = Mock()
        adapter = ClickCommandAdapter(mock_command)
        assert adapter.argparse_command == mock_command

    def test_convert_click_args_to_argparse(self):
        """Test conversion of Click arguments to argparse format."""
        mock_command = Mock()
        adapter = ClickCommandAdapter(mock_command)

        click_kwargs = {"config": "test.yaml", "verbose": True, "debug": False}

        args = adapter.convert_click_args_to_argparse(**click_kwargs)
        assert args.config == "test.yaml"
        assert args.verbose is True
        assert args.debug is False

    def test_handle_with_conversion(self):
        """Test handling commands with argument conversion."""
        mock_command = Mock()
        mock_command.handle.return_value = 0
        adapter = ClickCommandAdapter(mock_command)

        click_kwargs = {"config": "test.yaml", "verbose": True}

        result = adapter.handle_with_conversion(**click_kwargs)
        assert result == 0
        mock_command.handle.assert_called_once()

        # Check that the passed args have the expected attributes
        call_args = mock_command.handle.call_args[0][0]
        assert call_args.config == "test.yaml"
        assert call_args.verbose is True

    def test_create_command_adapter(self):
        """Test the create_command_adapter factory function."""
        mock_command = Mock()
        adapter = create_command_adapter(mock_command)

        assert isinstance(adapter, ClickCommandAdapter)
        assert adapter.argparse_command == mock_command


class TestClickCommandAdapterIntegration:
    """Integration tests for ClickCommandAdapter."""

    def test_adapter_with_real_command(self, cli_runner):
        """Test adapter with a real Click command."""

        # Create a mock argparse command class
        class MockArgparseCommand:
            @staticmethod
            def handle(args):
                # Simulate argparse command behavior
                if hasattr(args, "config") and args.config:
                    return 0  # Success
                return 1  # Failure

        # Create adapter
        adapter = create_command_adapter(MockArgparseCommand)

        # Test successful case
        result = adapter.handle_with_conversion(config="test.yaml", verbose=True)
        assert result == 0

        # Test failure case
        result = adapter.handle_with_conversion(config=None, verbose=False)
        assert result == 1

    def test_adapter_error_handling(self):
        """Test adapter error handling."""

        class FailingArgparseCommand:
            @staticmethod
            def handle(args):
                raise RuntimeError("Command failed")

        adapter = create_command_adapter(FailingArgparseCommand)

        with pytest.raises(RuntimeError, match="Command failed"):
            adapter.handle_with_conversion(config="test.yaml")


class TestDecoratorsIntegration:
    """Integration tests for decorator combinations."""

    def test_combined_decorators(self, cli_runner):
        """Test combining multiple decorators."""

        @handle_errors
        @pass_context_and_setup_logging
        @common_options
        @click.command()
        def test_command(ctx, config, verbose, dry_run):
            click.echo(f"config: {config}, verbose: {verbose}, dry_run: {dry_run}")
            click.echo(f"debug: {ctx.obj.get('debug', False)}")

        with patch("panther.cli_click.core.base.setup_logging"):
            result = cli_runner.invoke(
                test_command, ["--verbose", "--dry-run"], obj={"debug": True}
            )
            assert result.exit_code == 0
            assert "verbose: True" in result.output
            assert "dry_run: True" in result.output
            assert "debug: True" in result.output

    def test_error_handling_with_context(self, cli_runner):
        """Test error handling with context information."""

        @handle_errors
        @pass_context_and_setup_logging
        @click.command()
        def test_command(ctx):
            ctx.obj["debug"] = True
            raise RuntimeError("Test error with debug")

        with patch("panther.cli_click.core.base.setup_logging"):
            result = cli_runner.invoke(test_command, obj={"debug": True})
            assert result.exit_code == 1
            assert "❌ Unexpected error:" in result.output
