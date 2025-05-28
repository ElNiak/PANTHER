"""PANTHER configuration package.

This package contains configuration management for the PANTHER framework.
"""

# Import key modules for easier access
from . import config_manager
from . import config_experiment_schema
from . import config_global_schema
from . import plugin_params

# Define the public API
__all__ = [
    "config_manager",
    "config_experiment_schema",
    "config_global_schema",
    "plugin_params"
]