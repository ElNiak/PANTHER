"""PANTHER Configuration System.

Hierarchical, plugin-based configuration management with Pydantic v2 validation
and Pydantic type safety.

Key Principles:
    - Plugin-based schemas: each plugin contributes config via ``config_schema.py``
    - Dynamic validation: schemas merged at runtime and validated with Pydantic
    - Type safety: strong typing with Pydantic-based configuration models
    - Extensibility: new plugins automatically extend the configuration space

Architecture::

    YAML Input
        |
        v
    ConfigLoadingMixin --> YAMLLoader
        |
        v
    Environment Variable Resolution
        |
        v
    Plugin Schema Discovery & Merge
        |
        v
    Schema Validation --> Business Rules --> Auto-Fix
        |
        v
    Validated Configuration (cached)

Core Components:
    ConfigurationManager
        Central orchestrator using 8 mixin composition:
        ConfigLoadingMixin, ValidationOperationsMixin,
        ConfigOperationsMixin, EnvironmentHandlingMixin,
        PluginManagementMixin, CachingMixin,
        StateManagementMixin, LoggingFeaturesMixin.

    BaseConfig (``core/base.py``)
        Pure Pydantic v2 base providing type-safe validation and serialization.

    Type-Safe Models (``core/models/``)
        ExperimentConfig, ServiceConfig, GlobalConfig,
        EnvironmentConfig, and plugin-specific schemas.

Configuration Structure (YAML)::

    logging:
      level: INFO
    tests:
      - name: "Test Name"
        network_environment:
          type: docker_compose
        services:
          server:
            implementation:
              name: picoquic
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
"""

# Define the public API - but use lazy imports to avoid circular dependencies
# pylint: disable-next=undefined-variable  # Variables defined dynamically via __getattr__
__all__ = [
    # Primary configuration system exports
    "ConfigurationManager",
    "core",
    "load_experiment",
    # Configuration models
    "BaseConfig",
    "ExperimentConfig",
    "GlobalConfig",
    "BaseObserverConfig",
    "ServiceConfig",
    "TestConfig",
]


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    # Primary configuration system imports
    if name == "ConfigurationManager":
        from .core.manager import (  # pylint: disable=import-outside-toplevel
            ConfigurationManager,
        )

        return ConfigurationManager
    elif name == "core":
        from . import core  # pylint: disable=import-outside-toplevel

        return core
    # Configuration model imports
    elif name == "BaseConfig":
        from .core.base import BaseConfig  # pylint: disable=import-outside-toplevel

        return BaseConfig
    elif name == "ExperimentConfig":
        from .core.models import (  # pylint: disable=import-outside-toplevel
            ExperimentConfig,
        )

        return ExperimentConfig
    elif name == "GlobalConfig":
        from .core.models import GlobalConfig  # pylint: disable=import-outside-toplevel

        return GlobalConfig
    elif name == "BaseObserverConfig":
        from .core.models import (  # pylint: disable=import-outside-toplevel
            BaseObserverConfig,
        )

        return BaseObserverConfig
    elif name == "ServiceConfig":
        from .core.models import (  # pylint: disable=import-outside-toplevel
            ServiceConfig,
        )

        return ServiceConfig
    elif name == "TestConfig":
        from .core.models import TestConfig  # pylint: disable=import-outside-toplevel

        return TestConfig
    elif name == "load_experiment":
        from .core.manager import (  # pylint: disable=import-outside-toplevel
            load_experiment,
        )

        return load_experiment
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
