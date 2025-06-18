"""
Feature-aware logging mixin for PANTHER components.

This module provides the FeatureLoggerMixin class that enables components
to use feature-specific logging levels automatically.
"""

import logging
from typing import Optional

from .logger_factory import LoggerFactory


class FeatureLoggerMixin:
    """
    Mixin class that provides feature-aware logging capabilities.

    This mixin automatically detects the appropriate feature for a component
    and configures logging accordingly.
    """

    def __init_logger__(self, feature: Optional[str] = None):
        """
        Initialize the logger for this component.

        Args:
            feature: Optional explicit feature name. If not provided,
                    will be auto-detected from class name.
        """
        # Get class name for logger identification
        class_name = self.__class__.__name__
        module_name = self.__class__.__module__

        # Create logger name from module and class
        logger_name = f"{module_name}.{class_name}"

        # Auto-detect feature if not provided
        if not feature:
            feature = self._auto_detect_feature()

        # Get feature-aware logger
        self._logger = (
            LoggerFactory.get_feature_logger(logger_name, feature)
            if feature
            else LoggerFactory.get_logger(logger_name)
        )

        # Store feature for debugging
        self._feature = feature

    @property
    def logger(self):
        """Get the logger instance."""
        if not hasattr(self, "_logger") or self._logger is None:
            self.__init_logger__()
        return self._logger

    def _auto_detect_feature(self) -> Optional[str]:
        """
        Auto-detect the appropriate feature for this component.

        Returns:
            Detected feature name or None if no match found
        """
        class_name = self.__class__.__name__.lower()
        module_name = self.__class__.__module__.lower()

        # Check class name patterns first
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
            "execution_environments": [
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

        # Check patterns against class and module names
        for feature, patterns in feature_patterns.items():
            for pattern in patterns:
                if pattern in class_name or pattern in module_name:
                    return feature

        return None

    def log_with_feature(self, level: str, message: str, *args, **kwargs):
        """
        Log a message with explicit feature context.

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
        """
        Get the effective feature for this component.

        Returns:
            Feature name or None if no feature detected
        """
        return getattr(self, "_feature", None)

    def update_feature_level(self, level: str):
        """
        Update the logging level for this component's feature.

        Args:
            level: New logging level (DEBUG, INFO, etc.)
        """
        if hasattr(self, "_feature") and self._feature:
            LoggerFactory.update_feature_level(self._feature, level)

            # Reinitialize logger with new level
            self.__init_logger__(self._feature)


def get_feature_logger(name: str, feature: str):
    """
    Convenience function to get a feature-aware logger.

    Args:
        name: Logger name
        feature: Feature name

    Returns:
        Configured logger instance
    """
    return LoggerFactory.get_feature_logger(name, feature)


def auto_detect_feature_from_name(name: str) -> Optional[str]:
    """
    Auto-detect feature from a name string.

    Args:
        name: Name to analyze (class name, module name, etc.)

    Returns:
        Detected feature or None
    """
    name_lower = name.lower()

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
        "execution_environments": [
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
            if pattern in name_lower:
                return feature

    return None
