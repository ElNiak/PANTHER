"""PANTHER plugins package.

This package contains all plugins for the PANTHER framework.
"""

# Define the public API - but use lazy imports to avoid circular dependencies
__all__ = [
    "plugin_interface",
    "plugin_manager",
    "plugin_manager",
]


def __getattr__(name):
    """Lazy import implementation to avoid circular imports."""
    if name == "plugin_interface":
        from . import plugin_interface

        return plugin_interface
    elif name == "plugin_manager":
        from . import plugin_manager

    elif name == "plugin_manager":
        from . import plugin_manager

        return plugin_manager
    elif name == "plugin_creator":
        from ..tools.plugins import plugin_creator

        return plugin_creator
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
