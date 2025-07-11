"""
Base utilities and decorators for Click commands

Provides common patterns used across all PANTHER Click commands including
error handling, logging setup, and shared options.
"""

import logging
import subprocess
from functools import wraps
from typing import Any, Callable

import click
from termcolor import colored


def common_options(func: Callable) -> Callable:
    """
    Decorator that adds common options to Click commands.

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
    """
    Decorator for consistent error handling across commands.

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
            # BEHAVIORAL EQUIVALENCE: Preserve legacy exit code 130 for Ctrl+C
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
            # BEHAVIORAL EQUIVALENCE: Use legacy logging approach
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
    """
    Configure logging based on debug and verbose flags.

    BEHAVIORAL EQUIVALENCE: Attempts to use LoggerFactory when available
    to preserve legacy logging behavior, falls back to basic logging.

    Args:
        debug: Enable debug-level logging
        verbose: Enable info-level logging
    """
    # BEHAVIORAL EQUIVALENCE: Try to use legacy LoggerFactory if available
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
    """
    Decorator that passes context and sets up logging.

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


def success_message(message: str) -> None:
    """Print a success message with green checkmark.

    BEHAVIORAL EQUIVALENCE: Uses LoggerFactory when available to match legacy behavior.
    """
    try:
        from panther.core.utils.logger_factory import LoggerFactory

        logger = LoggerFactory.get_logger("cli")
        logger.info(f"✅ {message}")
    except ImportError:
        # Fallback to standard logging if LoggerFactory is not available
        try:
            import logging

            logging.info(f"✅ {message}")
        except:
            click.echo(colored(f"✅ {message}", "green"))


def info_message(message: str) -> None:
    """Print an info message with blue icon.

    BEHAVIORAL EQUIVALENCE: Uses LoggerFactory when available to match legacy behavior.
    """
    try:
        from panther.core.utils.logger_factory import LoggerFactory

        logger = LoggerFactory.get_logger("cli")
        logger.info(message)
    except ImportError:
        # Fallback to standard logging if LoggerFactory is not available
        try:
            import logging

            logging.info(f"ℹ️  {message}")
        except:
            click.echo(colored(f"ℹ️  {message}", "blue"))


def warning_message(message: str) -> None:
    """Print a warning message with yellow icon.

    BEHAVIORAL EQUIVALENCE: Uses LoggerFactory when available to match legacy behavior.
    """
    try:
        from panther.core.utils.logger_factory import LoggerFactory

        logger = LoggerFactory.get_logger("cli")
        logger.warning(f"⚠️  {message}")
    except ImportError:
        # Fallback to standard logging if LoggerFactory is not available
        try:
            import logging

            logging.warning(f"⚠️  {message}")
        except:
            click.echo(colored(f"⚠️  {message}", "yellow"))


def error_message(message: str) -> None:
    """Print an error message with red icon.

    BEHAVIORAL EQUIVALENCE: Uses LoggerFactory when available to match legacy behavior.
    """
    try:
        from panther.core.utils.logger_factory import LoggerFactory

        logger = LoggerFactory.get_logger("cli")
        logger.error(f"❌ {message}")
    except ImportError:
        # Fallback to standard logging if LoggerFactory is not available
        try:
            import logging

            logging.error(f"❌ {message}")
        except:
            click.echo(colored(f"❌ {message}", "red"), err=True)


def legacy_command_pattern(func: Callable) -> Callable:
    """
    Decorator that provides legacy command pattern compatibility.

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
