"""
Experiment-related exceptions for PANTHER.

This module provides custom exceptions for errors that occur during experiment
execution, initialization, and test case management.
"""


class PantherExperimentError(Exception):
    """Base class for all experiment-related errors in PANTHER."""

    pass


class ExperimentInitializationError(PantherExperimentError):
    """Error raised when experiment initialization fails."""

    pass


class TestCaseInitializationError(PantherExperimentError):
    """Error raised when test case initialization fails."""

    pass


class TestExecutionError(PantherExperimentError):
    """Error raised when test execution fails."""

    pass


class ConfigurationError(PantherExperimentError):
    """Error raised when there are issues with the experiment configuration."""

    pass


class PluginValidationError(PantherExperimentError):
    """Error raised when plugin validation fails."""

    pass
