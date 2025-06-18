"""PANTHER exceptions package.

This package contains exception classes used throughout the PANTHER framework.
"""

# Import exceptions for easier access
from .EnvironmentPluginNotFound import EnvironmentPluginNotFound
from .error_handler_mixin import ErrorHandlerMixin
from .ServicePluginNotFound import ServicePluginNotFound
from .TesterPluginNotFound import TesterPluginNotFound
from .fast_fail import PantherException, ErrorCategory, ErrorSeverity

# Define the public API
__all__ = [
    "EnvironmentPluginNotFound",
    "ServicePluginNotFound",
    "TesterPluginNotFound",
    "ErrorHandlerMixin",
    "PantherException",
    "ErrorCategory", 
    "ErrorSeverity",
]
