"""Typed Pydantic configuration models for PANTHER.

Model hierarchy — all classes inherit from ``BaseConfig``
(``panther.config.core.base``)::

    BaseConfig
    │
    ├── Global settings
    │   GlobalConfig, LoggingConfig, FeatureLogLevelsConfig, PathsConfig,
    │   DockerConfig, DockerUserMappingConfig, ServiceDockerOverrideConfig,
    │   ProgressConfig, FastFailConfig, MetricsConfig
    │
    ├── Experiment structure
    │   ExperimentConfig → TestConfig → ServiceConfig
    │   StepsConfig, ExperimentMetadata
    │
    ├── Service details
    │   ServiceConfig, ImplementationConfig, ProtocolConfig, NetworkConfig,
    │   Parameter, VersionBase (plain BaseModel — not part of config tree)
    │
    ├── Environments
    │   EnvironmentConfig → NetworkEnvironmentConfig, ExecutionEnvironmentConfig
    │
    └── Observers
        ObserversConfig, BaseObserverConfig → Logger/Metrics/Storage/Experiment

Import guide:
    Prefer importing from this module (``panther.config.core.models``)
    rather than individual sub-modules.
"""

from ..base import BaseConfig
from .environment import (
    EnvironmentConfig,
    ExecutionEnvironmentConfig,
    NetworkEnvironmentConfig,
)
from .experiment import ExperimentConfig, ExperimentMetadata, StepsConfig, TestConfig
from .global_config import (
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
    ServiceDockerOverrideConfig,
    resolve_docker_build_config,
)
from .observer import (
    BaseObserverConfig,
    ExperimentObserverConfig,
    LoggerObserverConfig,
    MetricsObserverConfig,
    ObserversConfig,
    StorageObserverConfig,
)
from .service import (
    ImplementationConfig,
    ImplementationType,
    NetworkConfig,
    Parameter,
    ProtocolConfig,
    ProtocolRole,
    ServiceConfig,
    VersionBase,
)

# Protocol migration completed - RoleEnum removed, use ProtocolRole instead

__all__ = [
    # Base
    "BaseConfig",
    # Global Config
    "GlobalConfig",
    "LoggingConfig",
    "LoggingLevel",
    "FeatureLogLevelsConfig",
    "PathsConfig",
    "DockerConfig",
    "DockerUserMappingConfig",
    "ServiceDockerOverrideConfig",
    "resolve_docker_build_config",
    "ProgressConfig",
    "FastFailConfig",
    "MetricsConfig",
    # Observer Config
    "ObserversConfig",
    "BaseObserverConfig",
    "LoggerObserverConfig",
    "MetricsObserverConfig",
    "StorageObserverConfig",
    "ExperimentObserverConfig",
    # Experiment Config
    "ExperimentConfig",
    "ExperimentMetadata",
    "TestConfig",
    "StepsConfig",
    # Service Config
    "ServiceConfig",
    "ImplementationConfig",
    "ImplementationType",
    "Parameter",
    "ProtocolConfig",
    "ProtocolRole",
    "NetworkConfig",
    "VersionBase",
    # Environment Config
    "EnvironmentConfig",
    "NetworkEnvironmentConfig",
    "ExecutionEnvironmentConfig",
]
