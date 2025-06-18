"""PANTHER utilities package.

This package contains utility functions and classes for the PANTHER framework.
"""

# Import key modules for easier access
# Note: docker_builder imports are handled separately to avoid circular imports

from ...plugins.environments.environment_utils import (
    EnvironmentPluginMixin,
    ExecutionEnvironmentMixin,
)
from ..command_processor.command_event_mixin import CommandEventMixin

# Docker mixins are imported directly to avoid circular imports
# from ..docker_builder.docker_operations_mixin import DockerOperationsMixin
# from ..docker_builder.service_manager_docker_mixin import ServiceManagerDockerMixin
# from ..exceptions.error_handler_mixin import ErrorHandlerMixin  # Import directly to avoid circular imports
from ..template.template_renderer import ServiceTemplateRenderer, TemplateRenderer
from .config_summarizer import ConfigSummarizer
from .feature_logger_mixin import FeatureLoggerMixin, get_feature_logger
from .feature_registry import (
    detect_module_feature,
    feature_logger,
    feature_registry,
    register_feature,
    register_module_feature,
)
from .logger_factory import LoggerFactory
from .logging_mixin import LoggerMixin

# Import new utilities
# CommandBuilder moved to avoid circular import - import directly from panther.core.command_processor.command_builder

# Define the public API
__all__ = [
    "TemplateRenderer",
    "ServiceTemplateRenderer",
    "LoggerMixin",
    "LoggerFactory",
    "FeatureLoggerMixin",
    "get_feature_logger",
    "ConfigSummarizer",
    "feature_registry",
    "register_feature",
    "register_module_feature",
    "detect_module_feature",
    "feature_logger",
    "CommandEventMixin",
    # "ServiceManagerDockerMixin",  # Import directly to avoid circular imports
    # "DockerOperationsMixin",      # Import directly to avoid circular imports
    "ExecutionEnvironmentMixin",
    "EnvironmentPluginMixin",
    # "ErrorHandlerMixin",  # Import directly to avoid circular imports
]
