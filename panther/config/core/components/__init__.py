"""Configuration system components."""

# pylint: disable-next=undefined-variable  # Variables defined dynamically via __getattr__
__all__ = [
    # Loaders
    "YAMLLoader",
    "VersionLoader",
    "CompositeLoader",
    "PluginConfigLoader",
    # Validators
    "ConfigValidator",
    "SchemaValidator",
    "BusinessRulesValidator",
    "CompatibilityValidator",
    # Builders
    "ExperimentBuilder",
    "ServiceBuilder",
    "GlobalConfigBuilder",
    # Merger
    "ConfigMerger",
    "MergeContext",
    "MergeStrategy",
    "ConflictResolver",
]


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    # Loaders
    if name == "YAMLLoader":
        from .loaders import YAMLLoader  # pylint: disable=import-outside-toplevel

        return YAMLLoader
    elif name == "VersionLoader":
        from .loaders import VersionLoader  # pylint: disable=import-outside-toplevel

        return VersionLoader
    elif name == "CompositeLoader":
        from .loaders import CompositeLoader  # pylint: disable=import-outside-toplevel

        return CompositeLoader
    elif name == "PluginConfigLoader":
        from .loaders import (  # pylint: disable=import-outside-toplevel
            PluginConfigLoader,
        )

        return PluginConfigLoader

    # Validators
    elif name == "ConfigValidator":
        from .validators import (  # pylint: disable=import-outside-toplevel
            ConfigValidator,
        )

        return ConfigValidator
    elif name == "SchemaValidator":
        from .validators import (  # pylint: disable=import-outside-toplevel
            SchemaValidator,
        )

        return SchemaValidator
    elif name == "BusinessRulesValidator":
        from .validators import (  # pylint: disable=import-outside-toplevel
            BusinessRulesValidator,
        )

        return BusinessRulesValidator
    elif name == "CompatibilityValidator":
        from .validators import (  # pylint: disable=import-outside-toplevel
            CompatibilityValidator,
        )

        return CompatibilityValidator

    # Builders
    elif name == "ExperimentBuilder":
        from .builders import (  # pylint: disable=import-outside-toplevel
            ExperimentBuilder,
        )

        return ExperimentBuilder
    elif name == "ServiceBuilder":
        from .builders import ServiceBuilder  # pylint: disable=import-outside-toplevel

        return ServiceBuilder
    elif name == "GlobalConfigBuilder":
        from .builders import (  # pylint: disable=import-outside-toplevel
            GlobalConfigBuilder,
        )

        return GlobalConfigBuilder

    # Merger
    elif name == "ConfigMerger":
        from .merger import ConfigMerger  # pylint: disable=import-outside-toplevel

        return ConfigMerger
    elif name == "MergeContext":
        from .merger import MergeContext  # pylint: disable=import-outside-toplevel

        return MergeContext
    elif name == "MergeStrategy":
        from .merger import MergeStrategy  # pylint: disable=import-outside-toplevel

        return MergeStrategy
    elif name == "ConflictResolver":
        from .merger import ConflictResolver  # pylint: disable=import-outside-toplevel

        return ConflictResolver

    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
