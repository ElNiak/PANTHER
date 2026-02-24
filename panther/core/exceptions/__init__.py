"""PANTHER exceptions package.

This package contains exception classes used throughout the PANTHER framework.

Exception Naming: ConfigurationException vs ConfigurationError
==============================================================

Two similarly named exception classes exist for configuration-related failures.
They serve different purposes and should not be used interchangeably.

ConfigurationException (fast_fail.py)
-------------------------------------
- **When to use**: For config validation and parsing errors caught by the
  fast-fail framework. Raised when a specific config file, field, or value
  fails validation during initial parsing or schema checks.
- **Severity**: HIGH (ErrorSeverity.HIGH) -- the current operation must stop,
  but it does not necessarily terminate the entire process.
- **Category**: ErrorCategory.CONFIGURATION
- **Constructor**: ``ConfigurationException(message, config_file, field, validation_error)``
- **Parent**: PantherException (directly)
- **Typical callers**: Config loaders, YAML/OmegaConf parsers, Pydantic
  validators invoked during startup.

ConfigurationError (experiment_exceptions.py)
---------------------------------------------
- **When to use**: For experiment-level configuration issues that prevent an
  experiment from executing. Raised when the overall experiment config is
  structurally invalid, has missing required sections, or contains
  contradictory settings that make experiment execution impossible.
- **Severity**: CRITICAL (ErrorSeverity.CRITICAL) -- config errors at this
  level prevent execution entirely.
- **Category**: ErrorCategory.CONFIGURATION (inherited via PantherExperimentError)
- **Constructor**: ``ConfigurationError(message, config_field=None, config_value=None, context=None)``
- **Parent**: PantherExperimentError -> PantherException
- **Typical callers**: ExperimentManager initialization, test-case setup,
  plugin validation during experiment assembly.

Rule of thumb: if you are validating a single field or file, use
``ConfigurationException``. If the experiment cannot run because of a
config-level problem, use ``ConfigurationError``.
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
