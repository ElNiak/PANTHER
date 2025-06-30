"""
Network resolution exceptions for network-aware command resolution.

This module provides specific exceptions for handling network parameter
resolution failures in the placeholder system.
"""

from typing import Any, Dict, Optional

from panther.core.exceptions.fast_fail import (
    ErrorCategory,
    ErrorSeverity,
    PantherException,
)


class NetworkResolutionException(PantherException):
    """Base exception for network resolution failures."""

    def __init__(
        self,
        message: str,
        resolution_context: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
    ):
        context = {"resolution_context": resolution_context or {}}
        super().__init__(message, severity, ErrorCategory.NETWORK_SETUP, context)


class PlaceholderParsingException(NetworkResolutionException):
    """Exception raised when placeholder parsing fails."""

    def __init__(
        self,
        message: str,
        placeholder: str,
        command_template: str,
        parsing_error: Optional[str] = None,
    ):
        resolution_context = {
            "placeholder": placeholder,
            "command_template": command_template,
            "parsing_error": parsing_error,
        }
        super().__init__(
            f"Failed to parse placeholder '{placeholder}': {message}",
            resolution_context,
            ErrorSeverity.HIGH,
        )


class ServiceResolutionException(NetworkResolutionException):
    """Exception raised when service resolution fails."""

    def __init__(
        self,
        message: str,
        service_name: str,
        attribute: str,
        format_type: str,
        available_services: Optional[list] = None,
    ):
        resolution_context = {
            "service_name": service_name,
            "attribute": attribute,
            "format_type": format_type,
            "available_services": available_services or [],
        }
        super().__init__(
            f"Failed to resolve service '{service_name}': {message}",
            resolution_context,
            ErrorSeverity.HIGH,
        )


class EnvironmentResolutionException(NetworkResolutionException):
    """Exception raised when environment-specific resolution fails."""

    def __init__(
        self,
        message: str,
        environment_type: str,
        resolution_method: str,
        error_details: Optional[str] = None,
    ):
        resolution_context = {
            "environment_type": environment_type,
            "resolution_method": resolution_method,
            "error_details": error_details,
        }
        super().__init__(
            f"Environment resolution failed in {environment_type}: {message}",
            resolution_context,
            ErrorSeverity.HIGH,
        )


class PlaceholderValidationException(NetworkResolutionException):
    """Exception raised when placeholder validation fails."""

    def __init__(
        self,
        message: str,
        placeholder: str,
        validation_rule: str,
        expected_format: str,
    ):
        resolution_context = {
            "placeholder": placeholder,
            "validation_rule": validation_rule,
            "expected_format": expected_format,
        }
        super().__init__(
            f"Placeholder validation failed for '{placeholder}': {message}",
            resolution_context,
            ErrorSeverity.MEDIUM,
        )


class NetworkDiscoveryException(NetworkResolutionException):
    """Exception raised when network discovery fails."""

    def __init__(
        self,
        message: str,
        discovery_method: str,
        network_environment: str,
        discovery_error: Optional[str] = None,
    ):
        resolution_context = {
            "discovery_method": discovery_method,
            "network_environment": network_environment,
            "discovery_error": discovery_error,
        }
        super().__init__(
            f"Network discovery failed using {discovery_method}: {message}",
            resolution_context,
            ErrorSeverity.HIGH,
        )
