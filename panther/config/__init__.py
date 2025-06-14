"""PANTHER configuration package.

This package contains configuration management for the PANTHER framework.
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    "config_manager",
    "config_experiment_schema",
    "config_global_schema",
    "config_observer_schema",
]


def __getattr__(name):  # pylint: disable=invalid-name
    """Lazy import implementation to avoid circular imports."""
    if name == "config_manager":
        from . import config_manager  # pylint: disable=import-outside-toplevel

        return config_manager
    elif name == "config_experiment_schema":
        from . import config_experiment_schema  # pylint: disable=import-outside-toplevel

        return config_experiment_schema
    elif name == "config_global_schema":
        from . import config_global_schema  # pylint: disable=import-outside-toplevel

        return config_global_schema
    elif name == "config_observer_schema":
        from . import config_observer_schema  # pylint: disable=import-outside-toplevel

        return config_observer_schema
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
