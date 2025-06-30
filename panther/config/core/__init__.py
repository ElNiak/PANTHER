"""Core configuration system for PANTHER.

This module provides the primary configuration management system using
Pydantic models and OmegaConf for advanced configuration handling.
"""

# pylint: disable-next=undefined-variable  # Variables defined dynamically via __getattr__
__all__ = [
    "BaseConfig",
    "ConfigurationManager",
    "get_config_manager",
    "load_experiment",
    "validate_service",
    "discover_versions",
]


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    if name == "BaseConfig":
        from .base import BaseConfig  # pylint: disable=import-outside-toplevel

        return BaseConfig
    elif name == "ConfigurationManager":
        from .manager import (  # pylint: disable=import-outside-toplevel
            ConfigurationManager,
        )

        return ConfigurationManager
    elif name == "get_config_manager":
        from .manager import (  # pylint: disable=import-outside-toplevel
            get_config_manager,
        )

        return get_config_manager
    elif name == "load_experiment":
        from .manager import load_experiment  # pylint: disable=import-outside-toplevel

        return load_experiment
    elif name == "validate_service":
        from .manager import validate_service  # pylint: disable=import-outside-toplevel

        return validate_service
    elif name == "discover_versions":
        from .manager import (  # pylint: disable=import-outside-toplevel
            discover_versions,
        )

        return discover_versions
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
