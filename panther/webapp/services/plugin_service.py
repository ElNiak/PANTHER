"""Service layer for plugin discovery and browsing."""

import logging

logger = logging.getLogger(__name__)


class PluginService:
    """Thin wrapper around PANTHER's PluginManager for web usage.

    Returns PluginMetadata dataclass instances from
    panther.plugins.core.structures.plugin_metadata
    (fields: name, type, version, description, supported_protocols,
    capabilities, tags, status, path; methods: .to_dict()).
    """

    def __init__(self):  # noqa: D107
        self._plugins_cache = None

    def list_plugins(self):
        """Return all discovered plugins as PluginMetadata instances.

        Falls back to an empty list if plugin discovery fails.
        """
        if self._plugins_cache is not None:
            return self._plugins_cache

        try:
            from panther.plugins.plugin_manager import PluginManager

            pm = PluginManager()
            discovered = pm.discover_plugins()
            self._plugins_cache = list(discovered.values())
        except Exception as e:
            logger.warning("Failed to discover plugins: %s", e)
            self._plugins_cache = []

        return self._plugins_cache

    def get_plugin_detail(self, name: str):
        """Get a single PluginMetadata by name, or None."""
        for p in self.list_plugins():
            if p.name == name:
                return p
        return None

    def get_plugin_manifest(self, name: str):
        """Get full PluginManifest for a plugin, or None.

        Uses the decorator registry (``get_decorated_plugins``) which
        stores the ORIGINAL manifests with all fields intact (license,
        homepage, config_schema, config_model, etc.).  The plugin_catalog
        stores re-created manifests that lose these fields.
        """
        try:
            from panther.plugins.plugin_manager import PluginManager

            # Ensure plugins are imported and decorators have run
            pm = PluginManager()
            pm.discover_plugins()

            from panther.plugins.core.plugin_decorators import get_decorated_plugins

            for _plugin_id, (_cls, manifest) in get_decorated_plugins().items():
                if manifest.name == name:
                    return manifest
        except Exception as e:
            logger.warning("Failed to get plugin manifest for %s: %s", name, e)
        return None
