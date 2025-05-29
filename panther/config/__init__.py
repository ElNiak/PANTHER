"""PANTHER configuration package.

This package contains configuration management for the PANTHER framework.
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    "config_manager",
    "config_experiment_schema",
    "config_global_schema",
    "plugin_params",
]


def __getattr__(name):
    """Lazy import implementation to avoid circular imports."""
    if name == "config_manager":
        from . import config_manager

        return config_manager
    elif name == "config_experiment_schema":
        from . import config_experiment_schema

        return config_experiment_schema
    elif name == "config_global_schema":
        from . import config_global_schema

        return config_global_schema
    elif name == "plugin_params":
        from . import plugin_params

        return plugin_params
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
