"""Configuration system components — validators and builders.

Components are lazy-imported to avoid circular dependencies.

Validators:
    ``ConfigValidator``        — orchestrates Pydantic + business rules
    ``SchemaValidator``        — JSON Schema validation
    ``BusinessRulesValidator`` — domain-specific rules

Builders (dict → model):
    ``ExperimentBuilder``  — builds ExperimentConfig from raw dict
    ``ServiceBuilder``     — builds ServiceConfig with plugin resolution
    ``GlobalConfigBuilder``— builds GlobalConfig with defaults
"""

# pylint: disable-next=undefined-variable  # Variables defined dynamically via __getattr__
__all__ = [
    # Validators
    "ConfigValidator",
    "SchemaValidator",
    "BusinessRulesValidator",
    # Builders
    "ExperimentBuilder",
    "ServiceBuilder",
    "GlobalConfigBuilder",
]


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    # Validators
    if name == "ConfigValidator":
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

    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
