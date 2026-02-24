"""Configuration manager mixins for modular functionality.

This package implements a mixin-based architecture that decomposes the
``ConfigurationManager`` into independently testable units, each owning a
single configuration concern. The canonical composition order used by
``panther.config.core.manager.ConfigurationManager`` is::

    class ConfigurationManager(
        ConfigLoadingMixin,          # 1. Core file/dict/env loading
        EnvironmentHandlingMixin,    # 2. ${VAR} interpolation & env mappings
        ValidationOperationsMixin,   # 3. Multi-stage validation pipeline
        ConfigOperationsMixin,       # 4. Merging, field ops, MergeStrategy
        CachingMixin,                # 5. TTL-based caching & cache stats
        LoggingFeaturesMixin,        # 6. Feature-level log configuration
        PluginManagementMixin,       # 7. Plugin directory/tester management
        StateManagementMixin,        # 8. Health checks & state persistence
        ErrorHandlerMixin,           # 9. Error handling (from panther.core)
    ):
        ...

MRO (Method Resolution Order) notes
    All mixins inherit from ``LoggerMixin`` (via ``panther.core.utils``), so
    Python's C3 linearisation resolves ``super().__init__()`` chains
    correctly as long as every mixin calls ``super().__init__()``.

    The ordering above is significant:

    * ``ConfigLoadingMixin`` must precede ``EnvironmentHandlingMixin`` so that
      raw YAML loading is available before environment interpolation runs.
    * ``ValidationOperationsMixin`` comes after loading/environment mixins so
      that validation operates on fully resolved configs.
    * ``CachingMixin`` defines ``__init__`` that initialises cache state; it
      must appear before ``StateManagementMixin`` so cache stats are available
      in health checks.
    * ``ErrorHandlerMixin`` is last because it provides a catch-all error
      boundary used by all other mixins.

Mixin responsibilities
    ``ConfigLoadingMixin``
        Loading from YAML files, JSON, dictionaries, and OmegaConf DictConfig.
        Hot-reload support and format detection.

    ``EnvironmentHandlingMixin``
        Resolving ``${VAR}`` / ``${VAR:default}`` placeholders. Mapping
        well-known ``PANTHER_*`` environment variables to config paths.

    ``ValidationOperationsMixin``
        Schema validation via Pydantic, business-rule validation, auto-fix
        suggestions, and validation result reporting.

    ``ConfigOperationsMixin``
        Deep/shallow merge via ``MergeStrategy``, conflict resolution via
        ``ConflictResolution``, dot-notation field access, and config
        transformation helpers.

    ``CachingMixin``
        In-memory caches for loaded experiments, validation results, plugin
        schemas, and version data. Tracks cache hit/miss counts.

    ``LoggingFeaturesMixin``
        Maps per-feature log level overrides (e.g., ``docker_build: DEBUG``)
        from ``LoggingConfig`` to the logging subsystem.

    ``PluginManagementMixin``
        Copies external tester plugin directories into the PANTHER plugin
        tree and manages plugin file lifecycle.

    ``StateManagementMixin``
        Health-check reporting, config state persistence to disk, and
        resource lifecycle management.
"""

from .caching import CachingMixin
from .config_loading import ConfigLoadingMixin
from .config_operations import ConfigOperationsMixin
from .environment_handling import EnvironmentHandlingMixin
from .logging_features import LoggingFeaturesMixin
from .plugin_management import PluginManagementMixin
from .state_management import StateManagementMixin
from .validation_ops import ValidationOperationsMixin

__all__ = [
    "CachingMixin",
    "ConfigLoadingMixin",
    "ConfigOperationsMixin",
    "EnvironmentHandlingMixin",
    "LoggingFeaturesMixin",
    "PluginManagementMixin",
    "StateManagementMixin",
    "ValidationOperationsMixin",
]
