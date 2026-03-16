"""Utilities Module - Cross-Cutting Concerns for PANTHER.

Shared utilities used across the framework: logging, configuration
summarization, and feature registration.

Utility Groups:
    Logging:
        - `LoggerMixin` -- adds ``self.logger`` to any class
        - `LoggerFactory` -- standardized logger creation
        - `get_feature_logger()` -- feature-scoped logger factory function
        - `ConsoleFormatter` -- context-aware console formatter with banners

    Configuration:
        - `ConfigSummarizer` -- compact config display
        - `log_omega_config_summary()` -- summarize OmegaConf to log
        - `log_omega_config_full()` -- full config dump

    Feature Registration:
        - `register_feature()` / `register_module_feature()` -- declare features
        - `detect_module_feature()` -- runtime feature detection
        - ``feature_registry`` -- global feature catalog

See Also:
    `panther.core.command_processor` -- CommandEventMixin re-exported here
    `panther.core.template` -- template utilities (imported separately to avoid circular deps)
"""

# Import key modules for easier access
# Note: docker_builder imports are handled separately to avoid circular imports


from ..command_processor.mixins.event_mixin import CommandEventMixin
from .config_summarizer import (
    ConfigSummarizer,
    log_omega_config_full,
    log_omega_config_summary,
)
from .console_formatter import ConsoleFormatter
from .feature_logger_mixin import get_feature_logger
from .feature_registry import (
    detect_module_feature,
    feature_logger,
    feature_registry,
    register_feature,
    register_module_feature,
)
from .format_utils import compute_duration, format_json
from .logger_factory import LoggerFactory
from .logging_mixin import LoggerMixin

# Define the public API
__all__ = [
    "LoggerMixin",
    "LoggerFactory",
    "ConsoleFormatter",
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
    "format_json",
    "compute_duration",
]
