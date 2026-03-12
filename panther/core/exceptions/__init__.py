"""PANTHER exceptions package.

This package contains exception classes used throughout the PANTHER framework.

Exception Hierarchy::

    Exception
    ├── PantherException                          (fast_fail.py)
    │   ├── DockerBuildException
    │   ├── PluginLoadException
    │   │   ├── EnvironmentPluginNotFound
    │   │   ├── ServicePluginNotFound
    │   │   └── TesterPluginNotFound
    │   ├── ServiceStartException
    │   ├── DockerComposeException
    │   ├── NetworkSetupException
    │   ├── PortConflictException
    │   ├── IvyCompilationException
    │   ├── ResourceExhaustionException
    │   ├── CertificateException
    │   ├── ConfigurationException                (field-level)
    │   ├── TimeoutCascadeException
    │   ├── AuthenticationException
    │   ├── CriticalAssertionException
    │   ├── DependencyException
    │   ├── ErrorCascadeException
    │   ├── PantherExperimentError                (experiment_exceptions.py)
    │   │   ├── ExperimentInitializationError
    │   │   ├── TestCaseInitializationError
    │   │   ├── TestExecutionError
    │   │   ├── ConfigurationError                (experiment-level)
    │   │   └── PluginValidationError
    │   └── NetworkResolutionException            (network_resolution_exceptions.py)
    │       ├── PlaceholderParsingException
    │       ├── ServiceResolutionException
    │       ├── EnvironmentResolutionException
    │       ├── PlaceholderValidationException
    │       └── NetworkDiscoveryException

ConfigurationException vs ConfigurationError:
    Use ``ConfigurationException`` (fast_fail.py, severity HIGH) for
    single-field / single-file validation errors during config parsing.
    Use ``ConfigurationError`` (experiment_exceptions.py, severity CRITICAL)
    when the overall experiment config is invalid and execution cannot proceed.
"""

# Import exceptions for easier access
from .EnvironmentPluginNotFound import EnvironmentPluginNotFound
from .fast_fail import (
    ErrorCategory,
    ErrorSeverity,
    PantherException,
    PluginLoadException,
)
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
    "PluginLoadException",
    "ErrorCategory",
    "ErrorSeverity",
    "NetworkResolutionException",
    "PlaceholderParsingException",
    "ServiceResolutionException",
    "EnvironmentResolutionException",
    "PlaceholderValidationException",
    "NetworkDiscoveryException",
]
