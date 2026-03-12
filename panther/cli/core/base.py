"""Base utilities and decorators for Click commands.

Provides common patterns used across all PANTHER Click commands including
error handling, logging setup, and shared options.
"""

import logging
import subprocess
from functools import wraps
from typing import Any, Callable

import click
from termcolor import colored

FEATURED_EXAMPLE_ATTR = "_panther_featured_example"


def featured_example(example_text: str):
    """Attach a featured example to a Click command for top-level help."""

    def decorator(cmd):
        setattr(cmd, FEATURED_EXAMPLE_ATTR, example_text)
        return cmd

    return decorator


class PantherGroup(click.Group):
    """Custom Click Group that auto-generates an Examples section from commands."""

    def format_help(self, ctx, formatter):
        """Format help text with auto-generated Examples section."""
        super().format_help(ctx, formatter)
        examples = []
        for name in sorted(self.list_commands(ctx)):
            cmd = self.get_command(ctx, name)
            if cmd and hasattr(cmd, FEATURED_EXAMPLE_ATTR):
                examples.append(getattr(cmd, FEATURED_EXAMPLE_ATTR))
        if examples:
            formatter.write("\n")
            with formatter.section("Examples"):
                for ex in examples:
                    formatter.write(f"  {ex}\n")
            formatter.write("\n  Use 'panther COMMAND --help' for details.\n")


def common_options(func: Callable) -> Callable:
    """Decorator that adds common options to Click commands.

    Adds frequently used options like --config, --verbose that are
    shared across multiple PANTHER commands.

    Args:
        func: Click command function to decorate

    Returns:
        Decorated function with common options added
    """

    @click.option(
        "--config", "-c", type=click.Path(exists=True), help="Configuration file path"
    )
    @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
    @click.option(
        "--dry-run", is_flag=True, help="Show what would be executed without running"
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def handle_errors(func: Callable) -> Callable:
    """Decorator for consistent error handling across commands.

    Provides unified error handling for common exceptions like
    KeyboardInterrupt, subprocess errors, and unexpected exceptions.
    Preserves legacy CLI exit codes for shell script compatibility.

    Args:
        func: Click command function to decorate

    Returns:
        Decorated function with error handling
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        import sys

        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            click.echo(colored("⚠️  Operation cancelled by user", "yellow"), err=True)
            sys.exit(130)
        except subprocess.CalledProcessError as e:
            click.echo(colored(f"❌ Command failed: {e}", "red"), err=True)
            sys.exit(1)
        except FileNotFoundError as e:
            click.echo(colored(f"❌ File not found: {e}", "red"), err=True)
            sys.exit(1)
        except PermissionError as e:
            click.echo(colored(f"❌ Permission denied: {e}", "red"), err=True)
            sys.exit(1)
        except Exception as e:
            ctx = click.get_current_context(silent=True)
            debug = ctx.obj.get("debug", False) if ctx and ctx.obj else False

            if debug:
                import logging

                logging.error(f"❌ Error: {e}", exc_info=True)
            else:
                click.echo(colored(f"❌ Error: {e}", "red"), err=True)
            sys.exit(1)

    return wrapper


def setup_logging(debug: bool = False, verbose: bool = False) -> None:
    """Configure logging based on debug and verbose flags.

    Uses LoggerFactory when available, falls back to basic logging.

    Args:
        debug: Enable debug-level logging
        verbose: Enable info-level logging
    """
    try:
        from panther.core.utils.logger_factory import LoggerFactory

        # Use LoggerFactory default configuration - format comes from factory defaults
        if debug:
            LoggerFactory.initialize(
                {
                    "level": "DEBUG",
                    "enable_colors": True,
                }
            )
        elif verbose:
            LoggerFactory.initialize(
                {
                    "level": "INFO",
                    "enable_colors": True,
                }
            )
        else:
            LoggerFactory.initialize(
                {
                    "level": "WARNING",
                    "enable_colors": True,
                }
            )
    except ImportError:
        # Fallback to basic logging if LoggerFactory is not available
        # Use consistent format across all modes
        format_str = "%(asctime)s [%(levelname)s] - %(name)s - %(message)s"

        if debug:
            level = logging.DEBUG
        elif verbose:
            level = logging.INFO
        else:
            level = logging.WARNING

        logging.basicConfig(
            level=level, format=format_str, handlers=[logging.StreamHandler()]
        )


def pass_context_and_setup_logging(func: Callable) -> Callable:
    """Decorator that passes context and sets up logging.

    Combines context passing with logging setup based on debug/verbose flags.

    Args:
        func: Click command function to decorate

    Returns:
        Decorated function with context and logging setup
    """

    @click.pass_context
    @wraps(func)
    def wrapper(ctx, *args, **kwargs):
        # Setup logging based on context
        debug = ctx.obj.get("debug", False)
        verbose = kwargs.get("verbose", False) or ctx.obj.get("verbose", False)
        setup_logging(debug, verbose)

        return func(ctx, *args, **kwargs)

    return wrapper


_MESSAGE_STYLES = {
    "success": ("✅ ", "green", "info"),
    "info": ("ℹ️  ", "blue", "info"),
    "warning": ("⚠️  ", "yellow", "warning"),
    "error": ("❌ ", "red", "error"),
}


def _cli_message(message: str, style: str) -> None:
    """Print a styled CLI message with LoggerFactory/logging/click fallback."""
    prefix, color, log_level = _MESSAGE_STYLES[style]
    formatted = f"{prefix}{message}"
    try:
        from panther.core.utils.logger_factory import LoggerFactory

        logger = LoggerFactory.get_logger("cli")
        getattr(logger, log_level)(formatted)
    except ImportError:
        try:
            import logging

            getattr(logging, log_level)(formatted)
        except Exception:
            click.echo(colored(formatted, color), err=(style == "error"))


def success_message(message: str) -> None:
    """Display a success message."""
    _cli_message(message, "success")


def info_message(message: str) -> None:
    """Display an informational message."""
    _cli_message(message, "info")


def warning_message(message: str) -> None:
    """Display a warning message."""
    _cli_message(message, "warning")


def error_message(message: str) -> None:
    """Display an error message."""
    _cli_message(message, "error")


def legacy_command_pattern(func: Callable) -> Callable:
    """Decorator that provides legacy command pattern compatibility.

    Enables Click commands to behave more like legacy BaseCommand pattern
    with proper return code handling and error patterns.

    Args:
        func: Click command function to decorate

    Returns:
        Decorated function with legacy behavior patterns
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # Legacy commands return 0 for success, None is treated as success
            if result is None:
                return 0
            return result
        except Exception as e:
            # Let error handling decorator handle the exception
            raise

    return wrapper
