"""PANTHER configuration package.

This package contains configuration management for the PANTHER framework.

The package provides both legacy and new unified configuration systems:
- Legacy: config_manager, config_*_schema modules (for backward compatibility)
- New: core.* modules with unified ConfigurationManager and Pydantic models
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    # Legacy exports (for backward compatibility)
    "config_manager",
    "config_experiment_schema",
    "config_global_schema",
    "config_observer_schema",
    "ConfigLoader",
    # New unified configuration system exports
    "core",
    "ConfigurationManager",
    "BaseConfig",
    "ExperimentConfig",
    "GlobalConfig",
    "ObserverConfig",
    "ServiceConfig",
    "TestConfig",
]


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    # Legacy imports
    if name == "config_manager":
        from . import config_manager  # pylint: disable=import-outside-toplevel

        return config_manager
    elif name == "config_experiment_schema":
        from . import (  # pylint: disable=import-outside-toplevel
            config_experiment_schema,
        )

        return config_experiment_schema
    elif name == "config_global_schema":
        from . import config_global_schema  # pylint: disable=import-outside-toplevel

        return config_global_schema
    elif name == "config_observer_schema":
        from . import config_observer_schema  # pylint: disable=import-outside-toplevel

        return config_observer_schema
    elif name == "ConfigLoader":
        from .config_manager import ConfigLoader  # pylint: disable=import-outside-toplevel

        return ConfigLoader
    # New unified configuration system imports
    elif name == "core":
        from . import core  # pylint: disable=import-outside-toplevel

        return core
    elif name == "ConfigurationManager":
        from .core.manager import (  # pylint: disable=import-outside-toplevel
            ConfigurationManager,
        )

        return ConfigurationManager
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
    elif name == "ObserverConfig":
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
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
