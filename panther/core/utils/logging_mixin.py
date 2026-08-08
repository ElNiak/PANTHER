"""Logging mixin with feature-aware capabilities for PANTHER components."""

from typing import Any, Dict, Optional, Union

"""
Logging Mixin

This module provides a reusable logging mixin for classes across PANTHER.
"""

import logging

from .config_summarizer import ConfigSummarizer
from .logger_factory import LoggerFactory

# Add TRACE level
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


class LoggerMixin:
    """Enhanced logging mixin that combines traditional logging with feature-aware capabilities.

    This mixin automatically creates a logger based on the class name
    and provides common logging patterns used throughout PANTHER, now with
    feature-specific logging level support.
    """

    def __init__(self, *args, **kwargs):
        """Initialize mixin state."""
        super().__init__(*args, **kwargs)
        self._logger: Optional[logging.Logger] = None
        self._log_context = {}
        # Initialize feature-aware logging
        self.__init_logger__()

    def __init_logger__(self, feature: Optional[str] = None):
        """Initialize the logger for this component.

        Args:
            feature: Optional explicit feature name. If not provided,
                    will be auto-detected from class name.
        """
        class_name = self.__class__.__name__
        module_name = self.__class__.__module__

        logger_name = f"{module_name}.{class_name}"

        if not feature:
            feature = self._auto_detect_feature()

        self._logger = (
            LoggerFactory.get_feature_logger(logger_name, feature)
            if feature
            else LoggerFactory.get_logger(logger_name)
        )

        self._feature = feature

    @property
    def logger(self) -> logging.Logger:
        """Get or create a logger for this class.

        Returns:
            logging.Logger: Logger instance named after the class
        """
        if not hasattr(self, "_logger") or self._logger is None:
            self.__init_logger__()

            # Add trace method if not already present
            if not hasattr(self._logger, "trace"):
                self._logger.trace = lambda msg, *args, **kwargs: self._logger.log(
                    TRACE, msg, *args, **kwargs
                )
        return self._logger

    def _auto_detect_feature(self) -> Optional[str]:
        """Auto-detect the appropriate feature for this component.

        Returns:
            Detected feature name or None if no match found
        """
        class_name = self.__class__.__name__.lower()
        module_name = self.__class__.__module__.lower()

        feature_patterns = {
            "command_generation": ["command", "cmd"],
            "template_rendering": ["template", "render"],
            "docker_operations": ["docker", "container"],
            "config_processing": ["config", "configuration"],
            "event_system": ["event", "emitter", "state"],
            "file_operations": ["file", "output", "storage"],
            "service_managers": ["service", "manager"],
            "ivy_operations": ["ivy"],
            "quic_services": [
                "quic",
                "picoquic",
                "aioquic",
                "lsquic",
                "mvfst",
                "quiche",
                "quinn",
            ],
            "plugin_loading": ["plugin", "loader"],
            "network_environments": ["network", "environment"],
            "execution_environment": [
                "execution",
                "strace",
                "gperf",
                "memcheck",
                "helgrind",
            ],
            "docker_compose": ["compose"],
            "shadow_ns": ["shadow"],
            "localhost_container": ["localhost"],
            "observer_operations": ["observer"],
            "certificate_management": ["cert", "certificate", "tls"],
            "network_setup": ["network"],
            "port_management": ["port"],
            "protocol_communication": ["protocol"],
            "metrics_collection": ["metrics", "monitor"],
            "data_storage": ["storage", "store"],
            "result_processing": ["result"],
            "test_execution": ["test", "experiment"],
            "validation_checks": ["validation", "validator"],
            "error_handling": ["error", "exception", "fail"],
        }

        for feature, patterns in feature_patterns.items():
            for pattern in patterns:
                if pattern in class_name or pattern in module_name:
                    return feature

        return None

    def log_with_feature(self, level: str, message: str, *args, **kwargs):
        """Log a message with explicit feature context.

        Args:
            level: Logging level (DEBUG, INFO, etc.)
            message: Log message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        if not hasattr(self, "logger"):
            self.__init_logger__()

        log_method = getattr(self.logger, level.lower(), None)
        if log_method:
            log_method(message, *args, **kwargs)

    def trace(self, message: str, *args, **kwargs):
        """Log a TRACE level message."""
        if not hasattr(self, "logger"):
            self.__init_logger__()
        if hasattr(self.logger, "trace"):
            self.logger.trace(message, *args, **kwargs)

    def debug(self, message: str, *args, **kwargs):
        """Log a DEBUG level message."""
        if not hasattr(self, "logger"):
            self.__init_logger__()
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log an INFO level message."""
        if not hasattr(self, "logger"):
            self.__init_logger__()
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log a WARNING level message."""
        if not hasattr(self, "logger"):
            self.__init_logger__()
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log an ERROR level message."""
        if not hasattr(self, "logger"):
            self.__init_logger__()
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log a CRITICAL level message."""
        if not hasattr(self, "logger"):
            self.__init_logger__()
        self.logger.critical(message, *args, **kwargs)

    def get_effective_feature(self) -> Optional[str]:
        """Get the effective feature for this component.

        Returns:
            Feature name or None if no feature detected
        """
        return getattr(self, "_feature", None)

    def update_feature_level(self, level: str):
        """Update the logging level for this component's feature.

        Args:
            level: New logging level (DEBUG, INFO, etc.)
        """
        if hasattr(self, "_feature") and self._feature:
            LoggerFactory.update_feature_level(self._feature, level)
            self.__init_logger__(self._feature)

    def log_initialization(self, entity_name: str, additional_info: str = "") -> None:
        """Log initialization of an entity with consistent format.

        Args:
            entity_name: Name of the entity being initialized
            additional_info: Additional information to log
        """
        message = f"Initializing {self.__class__.__name__} for '{entity_name}'"
        if additional_info:
            message += f" - {additional_info}"
        self.logger.debug(message)

    def log_config_loaded(self, config: dict, entity_name: str = "") -> None:
        """Log configuration loading with smart summarization.

        Args:
            config: Configuration dictionary that was loaded
            entity_name: Optional entity name for context
        """
        entity_part = f" for '{entity_name}'" if entity_name else ""

        # Use ConfigSummarizer for smart logging
        summary = ConfigSummarizer.summarize(config)
        self.logger.debug(
            f"Loaded {self.__class__.__name__} configuration{entity_part}: {summary}"
        )

        # Log full config at TRACE level
        if self.logger.isEnabledFor(TRACE):
            full_config = ConfigSummarizer.get_full_config(config)
            self.logger.trace(f"Full configuration{entity_part}:\n{full_config}")

    def log_config(self, config: Dict[str, Any], level: int = logging.DEBUG) -> None:
        """Smart config logging with summarization.

        Args:
            config: Configuration dictionary to log
            level: Log level for the summary
        """
        summary = ConfigSummarizer.summarize(config)
        self.logger.log(level, summary)

        # Log full config at TRACE level
        if self.logger.isEnabledFor(TRACE):
            sanitized = ConfigSummarizer.get_full_config(config)
            self.logger.trace(f"Full configuration:\n{sanitized}")

    def log_with_context(self, level: int, msg: str, **context) -> None:
        """Log with additional context that can be filtered.

        Args:
            level: Logging level
            msg: Message to log
            **context: Additional context parameters
        """
        if self._should_log_with_context(level, context):
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            self.logger.log(level, f"{msg} [{context_str}]")

    def _should_log_with_context(self, level: int, context: Dict[str, Any]) -> bool:
        """Determine if message should be logged based on context.

        Args:
            level: Logging level
            context: Context dictionary

        Returns:
            bool: True if message should be logged
        """
        # Skip no-op operations
        if context.get("operation") == "no-op":
            return False

        # Skip empty commands
        command = context.get("command", "")
        if command in [
            "",
            "No commands",
            "No pre-run commands",
            "No post-run commands",
            "No compile commands",
            "No post-compile commands",
        ]:
            return False

        # Always log errors and warnings
        if level >= logging.WARNING:
            return True

        # Apply context-based filtering
        return True

    def log_operation_start(self, operation: str, **kwargs) -> None:
        """Log the start of an operation.

        Args:
            operation: Name of the operation starting
            **kwargs: Additional context to include in the log
        """
        # Filter out verbose kwargs at INFO level
        if self.logger.isEnabledFor(logging.INFO):
            filtered_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k in ["name", "type", "count", "target"]
            }
            context = f" with {filtered_kwargs}" if filtered_kwargs else ""
            self.logger.info(f"Starting {operation}{context}")

        # Log full context at DEBUG level
        if kwargs and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Full context for {operation}: {kwargs}")

    def log_operation_complete(self, operation: str, **kwargs) -> None:
        """Log the completion of an operation.

        Args:
            operation: Name of the operation completed
            **kwargs: Additional context to include in the log
        """
        # Filter out verbose kwargs at INFO level
        if self.logger.isEnabledFor(logging.INFO):
            filtered_kwargs = {
                k: v
                for k, v in kwargs.items()
                if k in ["name", "duration", "result", "count"]
            }
            context = f" with {filtered_kwargs}" if filtered_kwargs else ""
            self.logger.info(f"Completed {operation}{context}")

        # Log full context at DEBUG level
        if kwargs and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Full context for completed {operation}: {kwargs}")

    def log_operation_failed(self, operation: str, error: Exception, **kwargs) -> None:
        """Log the failure of an operation.

        Args:
            operation: Name of the operation that failed
            error: Exception that caused the failure
            **kwargs: Additional context to include in the log
        """
        context = f" with {kwargs}" if kwargs else ""
        self.logger.error(f"Failed {operation}{context}: {error}", exc_info=True)
