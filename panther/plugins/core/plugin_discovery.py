"""
Plugin Discovery Module

This module provides plugin discovery functionality for the PANTHER framework,
using the decorator registry to identify available plugins.
"""

from typing import Dict, List, Optional

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.core.structures.plugin_manifest import PluginManifest
from panther.plugins.core.structures.plugin_metadata import PluginMetadata


class PluginDiscovery(LoggerMixin):
    """
    Discovers plugins in the PANTHER framework using the decorator registry.

    This class provides a clean interface for plugin discovery, following
    the Single Responsibility Principle by focusing only on discovery logic.
    """

    def __init__(self):
        """Initialize the plugin discovery system."""
        super().__init__()
        self.discovered_plugins: Dict[str, PluginMetadata] = {}

    def discover_plugins(
        self, force_refresh: bool = False
    ) -> Dict[str, PluginMetadata]:
        """
        Discover all plugins from the decorator registry.

        Args:
            force_refresh: If True, refresh the plugin list

        Returns:
            Dictionary mapping plugin IDs to metadata
        """
        from panther.plugins.core.plugin_decorators import get_decorated_plugins

        if force_refresh or not self.discovered_plugins:
            self.discovered_plugins.clear()

            # Get all plugins from decorator registry
            decorated_plugins = get_decorated_plugins()

            for plugin_id, (plugin_class, manifest) in decorated_plugins.items():
                metadata = self._convert_manifest_to_metadata(manifest)
                if metadata:
                    self.discovered_plugins[metadata.name] = metadata
                    self.logger.debug(
                        f"Discovered plugin: {metadata.name} "
                        f"({metadata.plugin_type})"
                    )

            self.logger.info(
                f"Discovered {len(self.discovered_plugins)} plugins "
                f"from decorator registry"
            )

        return self.discovered_plugins.copy()

    def _convert_manifest_to_metadata(
        self, manifest: PluginManifest
    ) -> Optional[PluginMetadata]:
        """Convert PluginManifest from decorator to PluginMetadata."""
        try:
            return PluginMetadata(
                name=manifest.name,
                version=manifest.version,
                plugin_type=(
                    manifest.type.value
                    if hasattr(manifest.type, "value")
                    else str(manifest.type)
                ),
                supported_protocols=manifest.supported_protocols,
                implementation=getattr(manifest, "implementation", ""),
                role=getattr(manifest, "role", "both"),
                path=manifest.file_path or "",
                entry_point=manifest.entry_point,
                config_schema=manifest.config_schema,
                dependencies=manifest.dependencies,
                description=manifest.description,
                author=manifest.author,
                capabilities=manifest.capabilities,
                tags=manifest.tags,
            )
        except Exception as e:
            self.logger.error(f"Failed to convert manifest to metadata: {e}")
            return None

    def get_plugins_by_type(self, plugin_type: str) -> List[PluginMetadata]:
        """Get all discovered plugins of a specific type."""
        return [
            metadata
            for metadata in self.discovered_plugins.values()
            if metadata.plugin_type == plugin_type
        ]

    def get_plugin(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a specific plugin by name."""
        return self.discovered_plugins.get(plugin_name)

    def clear_cache(self) -> None:
        """Clear the discovery cache."""
        self.discovered_plugins.clear()
        self.logger.debug("Cleared plugin discovery cache")
