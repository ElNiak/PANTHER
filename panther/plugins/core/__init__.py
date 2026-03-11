"""Plugin core components — discovery, metadata, and factory utilities.

Provides the internal machinery that the unified
`PluginManager` relies on.

Architecture::

    PluginDiscovery       ← scans packages for @register_plugin decorators
    PluginFactory         ← instantiates plugins from metadata + config
    PluginMetadata        ← runtime metadata envelope
    PluginManifest        ← on-disk manifest for installed plugins
    PluginStatus          ← lifecycle state enum

See Also:
    `panther.plugins.plugin_interface`
        ``IPlugin`` abstract base class.
    `panther.plugins.plugin_manager`
        Singleton plugin manager using these components.
"""

from .plugin_discovery import PluginDiscovery
from .plugin_factory import PluginFactory
from .structures.plugin_manifest import PluginManifest
from .structures.plugin_metadata import PluginMetadata, PluginStatus

__all__ = [
    "PluginMetadata",
    "PluginStatus",
    "PluginManifest",
    "PluginFactory",
    "PluginDiscovery",
]
