"""
Fast-fail exception handling for PANTHER.

This module provides immediate termination on critical errors to prevent
wasted resources and improve user experience.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """Error severity levels for fast-fail decisions."""

    CRITICAL = 4  # Immediate termination required
    HIGH = 3  # Current operation must stop
    MEDIUM = 2  # Current task fails, but experiment can continue
    LOW = 1  # Warning only, continue execution


class ErrorCategory(Enum):
    """Categories of errors for specific handling."""

    DOCKER_BUILD = "docker_build"
    DOCKER_RUNTIME = "docker_runtime"
    PLUGIN_LOAD = "plugin_load"
    SERVICE_START = "service_start"
    NETWORK_SETUP = "network_setup"
    COMMAND_EXECUTION = "command_execution"
    CONFIGURATION = "configuration"
    RESOURCE = "resource"
    TIMEOUT = "timeout"


class PantherException(Exception):
    """Base exception for all PANTHER errors with severity tracking."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.severity = severity
        self.category = category
        self.timestamp = datetime.now()
        self.context = context or {}

    def should_terminate(self) -> bool:
        """Check if this error should cause immediate termination."""
        return self.severity == ErrorSeverity.CRITICAL


class DockerBuildException(PantherException):
    """Docker build failure - typically unrecoverable."""

    def __init__(
        self,
        message: str,
        image_name: str,
        dockerfile: str,
        build_error: Optional[str] = None,
    ):
        context = {
            "image_name": image_name,
            "dockerfile": dockerfile,
            "build_error": build_error,
        }
        super().__init__(
            message, ErrorSeverity.CRITICAL, ErrorCategory.DOCKER_BUILD, context
        )


class PluginLoadException(PantherException):
    """Plugin loading failure."""

    def __init__(
        self,
        message: str,
        plugin_name: str,
        plugin_type: str,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
    ):
        context = {"plugin_name": plugin_name, "plugin_type": plugin_type}
        super().__init__(message, severity, ErrorCategory.PLUGIN_LOAD, context)


class ServiceStartException(PantherException):
    """Service startup failure."""

    def __init__(
        self,
        message: str,
        service_name: str,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
    ):
        context = {"service_name": service_name}
        super().__init__(message, severity, ErrorCategory.SERVICE_START, context)


class FastFailHandler:
    """Handler for fast-fail behavior in PANTHER."""

    def __init__(self, enabled: bool = True, logger: Optional[logging.Logger] = None):
        self.enabled = enabled
        self.logger = logger or logging.getLogger(__name__)
        self.error_count = 0
        self.critical_error: Optional[PantherException] = None

    def handle_error(self, error: Exception, raise_on_critical: bool = True) -> bool:
        """
        Handle an error and determine if execution should continue.

        Args:
            error: The error to handle
            raise_on_critical: Whether to re-raise critical errors

        Returns:
            bool: True if execution should continue, False otherwise

        Raises:
            PantherException: If error is critical and raise_on_critical is True
        """
        self.error_count += 1

        # Convert regular exceptions to PantherException if needed
        if not isinstance(error, PantherException):
            error = PantherException(
                str(error), ErrorSeverity.MEDIUM, ErrorCategory.COMMAND_EXECUTION
            )

        # Log the error with appropriate level
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(self._format_error(error))
            self.critical_error = error
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(self._format_error(error))
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(self._format_error(error))
        else:
            self.logger.info(self._format_error(error))

        # Determine action
        if not self.enabled:
            return True  # Continue if fast-fail is disabled

        if error.should_terminate():
            if raise_on_critical:
                raise error
            return False

        return error.severity.value < ErrorSeverity.HIGH.value

    def _format_error(self, error: PantherException) -> str:
        """Format error for logging."""
        context_str = ", ".join(f"{k}={v}" for k, v in error.context.items())
        return (
            f"[{error.category.value.upper()}] "
            f"{error.severity.name}: {str(error)} "
            f"({context_str})"
        )

    def check_critical(self) -> None:
        """Check if a critical error occurred and raise it."""
        if self.critical_error and self.enabled:
            raise self.critical_error
