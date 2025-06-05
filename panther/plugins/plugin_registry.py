"""
Enhanced Plugin Registry for event-driven architecture.
"""

import logging
from typing import Any, TypeVar
from collections.abc import Callable

T = TypeVar("T")


class EnhancedPluginRegistry:
    """
    Enhanced plugin registry that supports event-driven plugin management.

    This registry maintains information about registered plugins and their
    relationships, allowing for dynamic discovery and event propagation.

    Attributes:
        plugins (Dict): Dictionary of registered plugins by type and ID
        relationships (Dict): Tracking of relationships between plugins
        logger (logging.Logger): Logger for the registry
    """

    def __init__(self):
        """
        Initialize the enhanced plugin registry.
        """
        self.plugins: dict[str, dict[str, Any]] = {}
        self.relationships: dict[str, dict[str, dict[str, list[str]]]] = {}
        self.logger = logging.getLogger("EnhancedPluginRegistry")

    def register_plugin(self, plugin_type: str, plugin_id: str, plugin: Any) -> None:
        """
        Register a plugin with the registry.

        Args:
            plugin_type: Type of the plugin (e.g., 'service', 'environment', 'tester')
            plugin_id: Unique identifier for the plugin
            plugin: The plugin object
        """
        if plugin_type not in self.plugins:
            self.plugins[plugin_type] = {}

        # Register the plugin
        self.plugins[plugin_type][plugin_id] = plugin
        self.logger.debug("Registered %s plugin: %s", plugin_type, plugin_id)

    def unregister_plugin(self, plugin_type: str, plugin_id: str) -> None:
        """
        Unregister a plugin from the registry.

        Args:
            plugin_type: Type of the plugin
            plugin_id: ID of the plugin to unregister
        """
        if plugin_type in self.plugins and plugin_id in self.plugins[plugin_type]:
            del self.plugins[plugin_type][plugin_id]
            self.logger.debug("Unregistered %s plugin: %s", plugin_type, plugin_id)

            # Clean up any relationships
            if plugin_type in self.relationships and plugin_id in self.relationships[plugin_type]:
                del self.relationships[plugin_type][plugin_id]

    def get_plugin(self, plugin_type: str, plugin_id: str) -> Any | None:
        """
        Get a plugin from the registry.

        Args:
            plugin_type: Type of the plugin
            plugin_id: ID of the plugin

        Returns:
            The plugin object if found, None otherwise
        """
        if plugin_type in self.plugins and plugin_id in self.plugins[plugin_type]:
            return self.plugins[plugin_type][plugin_id]
        return None

    def get_plugins_by_type(self, plugin_type: str) -> dict[str, Any]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugins to retrieve

        Returns:
            Dictionary of plugins with their IDs as keys
        """
        return self.plugins.get(plugin_type, {})

    def get_all_plugins(self) -> dict[str, dict[str, Any]]:
        """
        Get all registered plugins.

        Returns:
            Dictionary of all plugins organized by type
        """
        return self.plugins

    def register_relationship(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        relationship_type: str = "depends_on",
    ) -> None:
        """
        Register a relationship between two plugins.

        Args:
            source_type: Type of the source plugin
            source_id: ID of the source plugin
            target_type: Type of the target plugin
            target_id: ID of the target plugin
            relationship_type: Type of relationship
        """
        # Ensure the source relationship structure exists
        if source_type not in self.relationships:
            self.relationships[source_type] = {}
        if source_id not in self.relationships[source_type]:
            self.relationships[source_type][source_id] = {}
        if relationship_type not in self.relationships[source_type][source_id]:
            self.relationships[source_type][source_id][relationship_type] = []

        # Add the target to the relationship
        relationship = self.relationships[source_type][source_id][relationship_type]
        target_key = f"{target_type}:{target_id}"
        if target_key not in relationship:
            relationship.append(target_key)
            self.logger.debug(
                "Registered relationship: %s.%s --%s--> %s.%s",
                source_type,
                source_id,
                relationship_type,
                target_type,
                target_id,
            )

    def get_related_plugins(
        self, plugin_type: str, plugin_id: str, relationship_type: str = "depends_on"
    ) -> list[dict[str, str]]:
        """
        Get plugins related to the specified plugin.

        Args:
            plugin_type: Type of the plugin
            plugin_id: ID of the plugin
            relationship_type: Type of relationship to check

        Returns:
            List of related plugin information (type and id)
        """
        if (
            plugin_type not in self.relationships
            or plugin_id not in self.relationships[plugin_type]
            or relationship_type not in self.relationships[plugin_type][plugin_id]
        ):
            return []

        related = []
        for target_key in self.relationships[plugin_type][plugin_id][relationship_type]:
            target_type, target_id = target_key.split(":", 1)
            related.append({"type": target_type, "id": target_id})

        return related

    def find_plugin(
        self, predicate: Callable[[Any], bool], plugin_type: str | None = None
    ) -> Any | None:
        """
        Find a plugin that matches the given predicate.

        Args:
            predicate: Function that takes a plugin and returns True if it matches
            plugin_type: Optional type to restrict the search

        Returns:
            The first matching plugin, or None if no match is found
        """
        if plugin_type:
            # Search only in the specified type
            for plugin_id, plugin in self.plugins.get(plugin_type, {}).items():
                if predicate(plugin):
                    return plugin
        else:
            # Search in all plugin types
            for type_dict in self.plugins.values():
                for plugin_id, plugin in type_dict.items():
                    if predicate(plugin):
                        return plugin
        return None

    def find_plugins(
        self, predicate: Callable[[Any], bool], plugin_type: str | None = None
    ) -> list[Any]:
        """
        Find all plugins that match the given predicate.

        Args:
            predicate: Function that takes a plugin and returns True if it matches
            plugin_type: Optional type to restrict the search

        Returns:
            List of matching plugins
        """
        matches = []
        if plugin_type:
            # Search only in the specified type
            for plugin_id, plugin in self.plugins.get(plugin_type, {}).items():
                if predicate(plugin):
                    matches.append(plugin)
        else:
            # Search in all plugin types
            for type_dict in self.plugins.values():
                for plugin_id, plugin in type_dict.items():
                    if predicate(plugin):
                        matches.append(plugin)
        return matches
