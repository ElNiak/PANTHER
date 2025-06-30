"""
Experiment-related exceptions for PANTHER.

This module provides custom exceptions for errors that occur during experiment
execution, initialization, and test case management.
"""

from typing import Any, Dict, Optional

from panther.core.exceptions.fast_fail import (
    ErrorCategory,
    ErrorSeverity,
    PantherException,
)


class PantherExperimentError(PantherException):
    """Base class for all experiment-related errors in PANTHER."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            severity=severity,
            category=ErrorCategory.CONFIGURATION,
            context=context,
        )


class ExperimentInitializationError(PantherExperimentError):
    """Error raised when experiment initialization fails."""

    def __init__(
        self,
        message: str,
        experiment_name: Optional[str] = None,
        config_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        full_context = context or {}
        if experiment_name:
            full_context["experiment_name"] = experiment_name
        if config_path:
            full_context["config_path"] = config_path

        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,  # Experiment init failure is critical
            context=full_context,
        )


class TestCaseInitializationError(PantherExperimentError):
    """Error raised when test case initialization fails."""

    def __init__(
        self,
        message: str,
        test_name: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        context: Optional[Dict[str, Any]] = None,
    ):
        full_context = context or {}
        if test_name:
            full_context["test_name"] = test_name

        super().__init__(
            message=message,
            severity=severity,
            context=full_context,
        )


class TestExecutionError(PantherExperimentError):
    """Error raised when test execution fails."""

    def __init__(
        self,
        message: str,
        test_name: Optional[str] = None,
        phase: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        context: Optional[Dict[str, Any]] = None,
    ):
        full_context = context or {}
        if test_name:
            full_context["test_name"] = test_name
        if phase:
            full_context["phase"] = phase

        super().__init__(
            message=message,
            severity=severity,
            context=full_context,
        )


class ConfigurationError(PantherExperimentError):
    """Error raised when there are issues with the experiment configuration."""

    def __init__(
        self,
        message: str,
        config_field: Optional[str] = None,
        config_value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        full_context = context or {}
        if config_field:
            full_context["config_field"] = config_field
        if config_value is not None:
            full_context["config_value"] = str(config_value)

        super().__init__(
            message=message,
            severity=ErrorSeverity.CRITICAL,  # Config errors prevent execution
            context=full_context,
        )


class PluginValidationError(PantherExperimentError):
    """Error raised when plugin validation fails."""

    def __init__(
        self,
        message: str,
        plugin_name: Optional[str] = None,
        plugin_type: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        context: Optional[Dict[str, Any]] = None,
    ):
        full_context = context or {}
        if plugin_name:
            full_context["plugin_name"] = plugin_name
        if plugin_type:
            full_context["plugin_type"] = plugin_type

        super().__init__(
            message=message,
            severity=severity,
            context=full_context,
        )
