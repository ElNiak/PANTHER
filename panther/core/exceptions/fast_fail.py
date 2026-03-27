"""Fast-fail exception handling for PANTHER.

This module provides immediate termination on critical errors to prevent
wasted resources and improve user experience.
"""

import logging
import threading
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


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
    SECURITY = "security"
    TEST_FRAMEWORK = "test_framework"
    TEST_EXECUTION = "test_execution"
    DEPENDENCY = "dependency"
    CASCADE = "cascade"


class PantherException(Exception):
    """Base exception for all PANTHER errors with severity tracking."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity,
        category: ErrorCategory,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize PANTHER exception with severity and category."""
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
        """Initialize Docker build exception."""
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
        """Initialize plugin load exception."""
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
        """Initialize service start exception."""
        context = {"service_name": service_name}
        super().__init__(message, severity, ErrorCategory.SERVICE_START, context)


class DockerComposeException(PantherException):
    """Docker Compose execution failure - typically unrecoverable."""

    def __init__(
        self,
        message: str,
        command: str,
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ):
        """Initialize Docker Compose exception."""
        context = {
            "command": command,
            "returncode": returncode,
            "stdout": stdout[:500] if stdout else "",  # Truncate for logging
            "stderr": stderr[:500] if stderr else "",
        }
        super().__init__(
            message, ErrorSeverity.CRITICAL, ErrorCategory.DOCKER_RUNTIME, context
        )


class NetworkSetupException(PantherException):
    """Network initialization or setup failure."""

    def __init__(self, message: str, network_type: str, details: str):
        """Initialize network setup exception."""
        context = {
            "network_type": network_type,
            "details": details,
        }
        super().__init__(
            message, ErrorSeverity.CRITICAL, ErrorCategory.NETWORK_SETUP, context
        )


class PortConflictException(PantherException):
    """Port binding conflict detected."""

    def __init__(self, message: str, port: int, service: str):
        """Initialize port conflict exception."""
        context = {
            "port": port,
            "service": service,
        }
        super().__init__(
            message, ErrorSeverity.HIGH, ErrorCategory.NETWORK_SETUP, context
        )


class IvyCompilationException(PantherException):
    """Ivy test compilation failure."""

    def __init__(self, message: str, test_name: str, output: str, exit_code: int):
        """Initialize Ivy compilation exception."""
        context = {
            "test_name": test_name,
            "compilation_output": output[:500],  # Truncate
            "exit_code": exit_code,
        }
        super().__init__(
            message, ErrorSeverity.CRITICAL, ErrorCategory.TEST_FRAMEWORK, context
        )


class ResourceExhaustionException(PantherException):
    """System resource exhaustion."""

    def __init__(
        self, message: str, resource_type: str, available: float, required: float
    ):
        """Initialize resource exhaustion exception."""
        context = {
            "resource_type": resource_type,
            "available": available,
            "required": required,
        }
        super().__init__(
            message, ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE, context
        )


class CertificateException(PantherException):
    """Certificate generation or validation failure."""

    def __init__(self, message: str, cert_path: str, error: str):
        """Initialize certificate exception."""
        context = {"cert_path": cert_path, "error": error}
        super().__init__(
            message, ErrorSeverity.CRITICAL, ErrorCategory.SECURITY, context
        )


class ConfigurationException(PantherException):
    """Configuration validation or parsing error."""

    def __init__(
        self, message: str, config_file: str, field: str, validation_error: str
    ):
        """Initialize configuration exception."""
        context = {
            "config_file": config_file,
            "field": field,
            "validation_error": validation_error,
        }
        super().__init__(
            message, ErrorSeverity.HIGH, ErrorCategory.CONFIGURATION, context
        )


class TimeoutCascadeException(PantherException):
    """Multiple consecutive timeouts detected."""

    def __init__(self, message: str, count: int, services: List[str]):
        """Initialize timeout cascade exception."""
        context = {"timeout_count": count, "affected_services": services}
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.CASCADE, context)


class AuthenticationException(PantherException):
    """Authentication or authorization failure."""

    def __init__(self, message: str, auth_type: str, service: str):
        """Initialize authentication exception."""
        context = {"auth_type": auth_type, "service": service}
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.SECURITY, context)


class CriticalAssertionException(PantherException):
    """Critical test assertion failure."""

    def __init__(self, message: str, assertion_type: str, expected: Any, actual: Any):
        """Initialize critical assertion exception."""
        context = {
            "assertion_type": assertion_type,
            "expected": str(expected),
            "actual": str(actual),
        }
        super().__init__(
            message, ErrorSeverity.HIGH, ErrorCategory.TEST_EXECUTION, context
        )


class DependencyException(PantherException):
    """Dependency resolution or version mismatch."""

    def __init__(
        self,
        message: str,
        dependency: str,
        required_version: str,
        found_version: Optional[str] = None,
    ):
        """Initialize dependency exception."""
        context = {
            "dependency": dependency,
            "required_version": required_version,
            "found_version": found_version or "not found",
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.DEPENDENCY, context)


class ErrorCascadeException(PantherException):
    """Multiple errors of same type in succession."""

    def __init__(self, message: str, error_type: str, error_count: int, threshold: int):
        """Initialize error cascade exception."""
        context = {
            "error_type": error_type,
            "error_count": error_count,
            "threshold": threshold,
        }
        super().__init__(message, ErrorSeverity.HIGH, ErrorCategory.CASCADE, context)


class FastFailHandler:
    """Enhanced handler for fast-fail behavior in PANTHER with cascade detection."""

    def __init__(self, enabled: bool = True, logger: Optional[logging.Logger] = None):
        """Initialize fast-fail handler."""
        self.enabled = enabled
        self.logger = logger or logging.getLogger(__name__)
        self._lock = threading.Lock()
        self.error_count = 0
        self.critical_error: Optional[PantherException] = None

        # Error history tracking with timestamps
        self.error_history: List[Tuple[datetime, PantherException]] = []

        # Cascade thresholds for different error categories
        self.cascade_thresholds = {
            ErrorCategory.TIMEOUT: 3,
            ErrorCategory.DOCKER_RUNTIME: 2,
            ErrorCategory.SERVICE_START: 3,
            ErrorCategory.NETWORK_SETUP: 2,
            ErrorCategory.COMMAND_EXECUTION: 5,
            ErrorCategory.TEST_EXECUTION: 4,
        }

        # Time window for cascade detection (in seconds)
        self.cascade_time_window = 300  # 5 minutes

    def handle_error(self, error: Exception, raise_on_critical: bool = True) -> bool:
        """Handle an error and determine if execution should continue.

        Args:
            error: The error to handle
            raise_on_critical: Whether to re-raise critical errors

        Returns:
            bool: True if execution should continue, False otherwise

        Raises:
            PantherException: If error is critical and raise_on_critical is True
        """
        # Convert regular exceptions to PantherException if needed
        if not isinstance(error, PantherException):
            error = PantherException(
                str(error), ErrorSeverity.MEDIUM, ErrorCategory.COMMAND_EXECUTION
            )

        with self._lock:
            self.error_count += 1
            self.error_history.append((datetime.now(), error))
            # Trim old entries from history (keep last 100)
            if len(self.error_history) > 100:
                self.error_history = self.error_history[-100:]

        # Check for cascade
        cascade_error = self.detect_cascade(error)
        if cascade_error:
            # Log cascade detection
            self.logger.critical(
                f"ERROR CASCADE DETECTED: {self._format_error(cascade_error)}"
            )
            # Upgrade severity if cascade detected
            if error.severity != ErrorSeverity.CRITICAL:
                error = cascade_error

        # Log the error with appropriate level
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(self._format_error(error))
            with self._lock:
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

    def detect_cascade(
        self, error: PantherException
    ) -> Optional[ErrorCascadeException]:
        """Detect if we're in an error cascade situation.

        Args:
            error: The current error to check

        Returns:
            ErrorCascadeException if cascade detected, None otherwise
        """
        # Check recent errors of same category
        current_time = datetime.now()
        with self._lock:
            history_snapshot = list(self.error_history[-10:])
        recent_errors = [
            e
            for t, e in history_snapshot
            if e.category == error.category
            and (current_time - t).total_seconds() < self.cascade_time_window
        ]

        threshold = self.cascade_thresholds.get(error.category, 5)
        if len(recent_errors) >= threshold:
            return ErrorCascadeException(
                f"Cascade detected: {len(recent_errors)} {error.category.value} errors in {self.cascade_time_window}s",
                error.category.value,
                len(recent_errors),
                threshold,
            )
        return None

    def get_error_patterns(self) -> Dict[ErrorCategory, List[Tuple[datetime, int]]]:
        """Analyze error patterns and return statistics by category.

        Returns:
            Dict mapping error categories to list of (timestamp, count) tuples
        """
        patterns: Dict[ErrorCategory, List[tuple[datetime, int]]] = {}

        # Group errors by category and time windows
        for category in ErrorCategory:
            category_errors = [
                (t, e) for t, e in self.error_history if e.category == category
            ]
            if not category_errors:
                continue

            # Create time-windowed counts
            windows = []
            window_start = category_errors[0][0]
            window_count = 0

            for timestamp, _ in category_errors:
                if (timestamp - window_start).total_seconds() <= 60:  # 1-minute windows
                    window_count += 1
                else:
                    windows.append((window_start, window_count))
                    window_start = timestamp
                    window_count = 1

            if window_count > 0:
                windows.append((window_start, window_count))

            patterns[category] = windows

        return patterns

    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of all errors encountered.

        Returns:
            Dict containing error statistics and patterns
        """
        summary = {
            "total_errors": self.error_count,
            "critical_error": str(self.critical_error) if self.critical_error else None,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recent_errors": [],
            "cascades_detected": [],
        }

        # Count by category
        for _, error in self.error_history:
            cat = error.category.value
            sev = error.severity.name

            summary["errors_by_category"][cat] = (
                summary["errors_by_category"].get(cat, 0) + 1
            )
            summary["errors_by_severity"][sev] = (
                summary["errors_by_severity"].get(sev, 0) + 1
            )

        # Recent errors (last 10)
        for timestamp, error in self.error_history[-10:]:
            summary["recent_errors"].append(
                {
                    "timestamp": timestamp.isoformat(),
                    "category": error.category.value,
                    "severity": error.severity.name,
                    "message": str(error),
                }
            )

        # Check for cascades in each category
        for category in ErrorCategory:
            recent_category_errors = [
                (t, e) for t, e in self.error_history[-20:] if e.category == category
            ]

            if len(recent_category_errors) >= self.cascade_thresholds.get(category, 5):
                summary["cascades_detected"].append(
                    {
                        "category": category.value,
                        "count": len(recent_category_errors),
                        "threshold": self.cascade_thresholds.get(category, 5),
                    }
                )

        return summary

    def clear_history(self) -> None:
        """Clear error history and reset counters."""
        with self._lock:
            self.error_history.clear()
            self.error_count = 0
            self.critical_error = None

    def set_cascade_threshold(self, category: ErrorCategory, threshold: int) -> None:
        """Set custom cascade threshold for a specific error category.

        Args:
            category: The error category to configure
            threshold: Number of errors before cascade is detected
        """
        self.cascade_thresholds[category] = threshold

    def get_cascade_risk(self, category: ErrorCategory) -> float:
        """Calculate the risk of cascade for a given category.

        Args:
            category: The error category to check

        Returns:
            float: Risk score between 0.0 and 1.0
        """
        recent_errors = [
            e
            for t, e in self.error_history[-20:]
            if e.category == category
            and (datetime.now() - t).total_seconds() < self.cascade_time_window
        ]

        threshold = self.cascade_thresholds.get(category, 5)
        risk = len(recent_errors) / threshold

        return min(1.0, risk)

    def _format_error(self, error: PantherException) -> str:
        """Format error for logging."""
        context_str = ", ".join(f"{k}={v}" for k, v in error.context.items())
        return (
            f"[{error.category.value.upper()}] "
            f"{error.severity.name}: {error} "
            f"({context_str})"
        )

    def check_critical(self) -> None:
        """Check if a critical error occurred and raise it."""
        if self.critical_error and self.enabled:
            raise self.critical_error
