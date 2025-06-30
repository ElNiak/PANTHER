"""PANTHER configuration package.

This package contains configuration management for the PANTHER framework.

The package provides a unified configuration system based on ConfigurationManager.
"""

# Define the public API - but use lazy imports to avoid circular dependencies
# pylint: disable-next=undefined-variable  # Variables defined dynamically via __getattr__
__all__ = [
    # Primary configuration system exports
    "ConfigurationManager",
    "core",
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
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
