"""Global configuration schema for PANTHER framework.

This module provides backward compatibility imports for the legacy schema structure
while redirecting to the new unified configuration models.
"""

# Re-export from new unified models
from panther.config.core.models.global_config import (
    DockerConfig,
    DockerUserMappingConfig,
    FastFailConfig,
    FeatureLogLevelsConfig,
    GlobalConfig,
    LoggingConfig,
    LoggingLevel,
    MetricsConfig,
    PathsConfig,
    ProgressConfig,
)

# Re-export observer config
from panther.config.core.models.observer import ObserversConfig

__all__ = [
    "DockerConfig",
    "DockerUserMappingConfig",
    "FastFailConfig",
    "FeatureLogLevelsConfig",
    "GlobalConfig",
    "LoggingConfig",
    "LoggingLevel",
    "MetricsConfig",
    "ObserversConfig",
    "PathsConfig",
    "ProgressConfig",
]
