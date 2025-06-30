"""PANTHER utilities package.

This package contains utility functions and classes for the PANTHER framework.
"""

# Import key modules for easier access
# Note: docker_builder imports are handled separately to avoid circular imports


from ..command_processor.mixins.event_mixin import CommandEventMixin

# Docker mixins are imported directly to avoid circular imports
# from ..docker_builder.docker_operations_mixin import DockerOperationsMixin
# from ..docker_builder.service_manager_docker_mixin import ServiceManagerDockerMixin
# from ..exceptions.error_handler_mixin import ErrorHandlerMixin  # Import directly to avoid circular imports
# Template renderers moved to avoid circular import - import directly from panther.core.template.template_renderer
# from ..template.template_renderer import ServiceTemplateRenderer, TemplateRenderer
from .config_summarizer import (
    ConfigSummarizer,
    log_omega_config_full,
    log_omega_config_summary,
)
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
# CommandBuilder moved to avoid circular import - import directly from panther.core.command_processor.builders

# Define the public API
__all__ = [
    # "TemplateRenderer",  # Import directly from panther.core.template.template_renderer
    # "ServiceTemplateRenderer",  # Import directly from panther.core.template.template_renderer
    "LoggerMixin",
    "LoggerFactory",
    "FeatureLoggerMixin",
    "get_feature_logger",
    "ConfigSummarizer",
    "log_omega_config_summary",
    "log_omega_config_full",
    "feature_registry",
    "register_feature",
    "register_module_feature",
    "detect_module_feature",
    "feature_logger",
    "CommandEventMixin",
    # "ServiceManagerDockerMixin",  # Import directly to avoid circular imports
    # "DockerOperationsMixin",      # Import directly to avoid circular imports
    # "ExecutionEnvironmentMixin",
    # "EnvironmentPluginMixin",
    # "ErrorHandlerMixin",  # Import directly to avoid circular imports
]
