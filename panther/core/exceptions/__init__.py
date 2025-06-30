"""PANTHER exceptions package.

This package contains exception classes used throughout the PANTHER framework.
"""

# Import exceptions for easier access
from .EnvironmentPluginNotFound import EnvironmentPluginNotFound
from .fast_fail import ErrorCategory, ErrorSeverity, PantherException
from .network_resolution_exceptions import (
    EnvironmentResolutionException,
    NetworkDiscoveryException,
    NetworkResolutionException,
    PlaceholderParsingException,
    PlaceholderValidationException,
    ServiceResolutionException,
)
from .ServicePluginNotFound import ServicePluginNotFound
from .TesterPluginNotFound import TesterPluginNotFound

# Define the public API
__all__ = [
    "EnvironmentPluginNotFound",
    "ServicePluginNotFound",
    "TesterPluginNotFound",
    "PantherException",
    "ErrorCategory",
    "ErrorSeverity",
    "NetworkResolutionException",
    "PlaceholderParsingException",
    "ServiceResolutionException",
    "EnvironmentResolutionException",
    "PlaceholderValidationException",
    "NetworkDiscoveryException",
]
