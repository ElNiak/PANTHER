"""GDB debugging execution environment plugin."""

from .config_schema import GdbConfig

__all__ = ["GdbConfig"]

# GdbEnvironment is available but not imported here to avoid circular imports
# during plugin discovery. It will be discovered by the plugin system.
