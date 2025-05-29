"""PANTHER plugins package.

This package contains all plugins for the PANTHER framework.
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    "plugin_interface",
    "plugin_loader",
    "plugin_entry_points",
    "plugin_manager",
    "plugin_creator",
]


def __getattr__(name):
    """Lazy import implementation to avoid circular imports."""
    if name == "plugin_interface":
        from . import plugin_interface

        return plugin_interface
    elif name == "plugin_loader":
        from . import plugin_loader

        return plugin_loader
    elif name == "plugin_entry_points":
        from . import plugin_entry_points

        return plugin_entry_points
    elif name == "plugin_manager":
        from . import plugin_manager

        return plugin_manager
    elif name == "plugin_creator":
        from . import plugin_creator

        return plugin_creator
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
