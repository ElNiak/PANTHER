"""Core configuration system for PANTHER.

This package provides the primary configuration management system using
Pydantic v2 models for type-safe configuration handling.

Architecture at a Glance
========================

Validator System
----------------
``config.core.components.field_coercion``
    **Standalone coercion function** for imperative use: ``validate_integer_field()``.

``config.core.validators.pydantic_factories``
    **Pydantic validator factory functions** returning closures for
    ``@field_validator`` decorators: ``create_enum_validator()``,
    ``create_time_string_validator()``, and pre-configured helpers
    like ``protocol_role_validator``.

Mixin-Based ConfigurationManager
---------------------------------
``ConfigurationManager`` (in ``manager.py``) is composed from four mixins
plus ``ErrorHandlerMixin``, each owning a single concern.  See
``config.core.mixins.__init__`` for the canonical composition order and
MRO constraints.

Key mixins: ``ConfigLoadingMixin``, ``EnvironmentHandlingMixin``,
``ValidationOperationsMixin``, ``CachingMixin``.

Key Entry Points
----------------
- ``panther.config.core.manager.ConfigurationManager`` -- primary API
- ``panther.config.core.base.BaseConfig`` -- pure Pydantic v2 base for all config models
- ``panther.config.core.components`` -- validators and builders
- ``panther.config.core.models`` -- typed Pydantic configuration models
- ``panther.config.core.validators`` -- Pydantic validator factories
- ``panther.config.core.mixins`` -- composable manager capabilities
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
