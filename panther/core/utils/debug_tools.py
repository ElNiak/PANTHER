from typing import Any, Callable, Optional, TypeVar, Union, cast

"""
Debug utility tools for PANTHER framework.
"""

import functools
import logging
import time
from collections.abc import Callable
from pathlib import Path

F = TypeVar("F", bound=Callable[..., Any])


class DebugTools:
    """

    Debug tools for tracing and monitoring event flow and plugin integration.
    """

    @staticmethod
    def trace_method_calls(logger: logging.Optional[Logger] = None) -> Callable[[F], F]:
        """
        Decorator to trace method calls with args, kwargs, and return values.

        Args:
            logger: Optional logger to use; if not provided, will use the module's logger

        Returns:
            Decorator function that wraps the target method
        """

        def decorator(func: F) -> F:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                log = logger or logging.getLogger(func.__module__)

                # Format arguments for logging
                arg_str = ", ".join([repr(a) for a in args[1:]])  # Skip self
                kwarg_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
                combined_args = ", ".join(filter(None, [arg_str, kwarg_str]))

                # Get class name if method
                if args and hasattr(args[0], "__class__"):
                    class_name = args[0].__class__.__name__
                    method_name = f"{class_name}.{func.__name__}"
                else:
                    method_name = func.__name__

                log.debug("ENTER: %s(%s)", method_name, combined_args)

                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    log.debug("EXIT: %s -> %r (%0.3fs)", method_name, result, elapsed)
                    return result
                except Exception as e:
                    elapsed = time.time() - start_time
                    log.error(
                        "ERROR: %s -> %s: %s (%0.3fs)",
                        method_name,
                        type(e).__name__,
                        str(e),
                        elapsed,
                    )
                    raise

            return cast(F, wrapper)

        return decorator

    @staticmethod
    def setup_verbose_logging(output_dir: str, level: int = logging.DEBUG) -> Path:
        """
        Setup verbose logging for debugging.

        Args:
            output_dir: Directory to write log files
            level: Logging level to use

        Returns:
            Path to the log directory
        """
        # Create logs directory if it doesn't exist
        log_dir = Path(output_dir) / "debug_logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Create file handler for combined logs
        combined_handler = logging.FileHandler(log_dir / "debug_all.log")
        combined_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        combined_handler.setFormatter(combined_formatter)
        combined_handler.setLevel(level)
        root_logger.addHandler(combined_handler)

        # Create file handler for errors only
        error_handler = logging.FileHandler(log_dir / "debug_errors.log")
        error_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s"
        )
        error_handler.setFormatter(error_formatter)
        error_handler.setLevel(logging.WARNING)
        root_logger.addHandler(error_handler)

        # Create event log handler
        event_handler = logging.FileHandler(log_dir / "events.log")
        event_formatter = logging.Formatter("%(asctime)s - EVENT - %(message)s")
        event_handler.setFormatter(event_formatter)
        event_handler.setLevel(logging.INFO)

        # Create plugin log handler
        plugin_handler = logging.FileHandler(log_dir / "plugins.log")
        plugin_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        plugin_handler.setFormatter(plugin_formatter)
        plugin_handler.setLevel(logging.DEBUG)

        # Add specialized loggers
        logging.getLogger("EventManager").addHandler(event_handler)
        logging.getLogger("PluginRegistry").addHandler(plugin_handler)

        return log_dir
