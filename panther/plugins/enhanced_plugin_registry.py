"""
Enhanced Plugin Registry Module

This module provides a central registry for plugin management and event dispatching.
"""

from collections import defaultdict
from typing import Any

from panther.core.observer.event_manager import EventManager
from panther.core.observer.events import Event
from panther.plugins.enhanced_plugin_interface import IPantherPlugin, IPluginRegistry


class EnhancedPluginRegistry(IPluginRegistry):
    """
    Central registry for plugin event handling and lifecycle management.

    This class maintains the registry of all plugins and manages event subscriptions
    and dispatching, acting as the central coordinator for the plugin ecosystem.
    """

    def __init__(self, event_manager: EventManager):
        """
        Initialize the plugin registry.

        Args:
            event_manager: Event manager instance to use for event propagation
        """
        self.event_manager = event_manager
        self.plugins: dict[str, IPantherPlugin] = {}
        self.event_subscriptions: dict[str, list[str]] = defaultdict(list)

    def register_plugin(self, plugin_id: str, plugin: IPantherPlugin) -> bool:
        """
        Register a plugin with the registry.

        Args:
            plugin_id: Unique identifier for the plugin
            plugin: Plugin instance to register

        Returns:
            bool: True if registration was successful, False otherwise
        """
        if plugin_id in self.plugins:
            return False

        # Register the plugin
        self.plugins[plugin_id] = plugin

        # Subscribe the plugin to its events of interest
        for event_type in plugin.get_subscribed_events():
            self.subscribe_to_event(plugin_id, event_type)

        return True

    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin from the registry.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        if plugin_id not in self.plugins:
            return False

        # Unsubscribe the plugin from all event types
        for event_type in list(self.event_subscriptions.keys()):
            if plugin_id in self.event_subscriptions[event_type]:
                self.event_subscriptions[event_type].remove(plugin_id)

        # Remove the plugin
        del self.plugins[plugin_id]

        return True

    def get_plugin(self, plugin_id: str) -> IPantherPlugin | None:
        """
        Get a plugin by ID.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            Optional[IPantherPlugin]: The plugin if found, None otherwise
        """
        return self.plugins.get(plugin_id)

    def get_plugin_status(self, plugin_id: str) -> dict[str, Any]:
        """
        Get the status of a plugin.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            Dict[str, Any]: Dictionary containing plugin status
        """
        plugin = self.get_plugin(plugin_id)
        if plugin:
            return plugin.get_status()
        return {"status": "not_found", "plugin_id": plugin_id}

    def get_all_plugins(self) -> dict[str, IPantherPlugin]:
        """
        Get all registered plugins.

        Returns:
            Dict[str, IPantherPlugin]: Dictionary mapping plugin IDs to plugin instances
        """
        return self.plugins

    def dispatch_event(self, event: Event) -> None:
        """
        Dispatch an event to all subscribed plugins.

        This method sends the event to all plugins that have subscribed to this event type.
        It also propagates the event to the central event manager.

        Args:
            event: The event to dispatch
        """
        # Get the event type
        event_type = event.get_type()

        # Propagate to the central event manager
        self.event_manager.notify(event)

        # Dispatch to subscribed plugins
        for plugin_id in self.event_subscriptions.get(event_type, []):
            plugin = self.plugins.get(plugin_id)
            if plugin:
                plugin.handle_event(event)

    def subscribe_to_event(self, plugin_id: str, event_type: str) -> None:
        """
        Subscribe a plugin to an event type.

        Args:
            plugin_id: Unique identifier for the plugin
            event_type: Event type to subscribe to
        """
        if plugin_id in self.plugins and plugin_id not in self.event_subscriptions[event_type]:
            self.event_subscriptions[event_type].append(plugin_id)

    def unsubscribe_from_event(self, plugin_id: str, event_type: str) -> None:
        """
        Unsubscribe a plugin from an event type.

        Args:
            plugin_id: Unique identifier for the plugin
            event_type: Event type to unsubscribe from
        """
        if (
            event_type in self.event_subscriptions
            and plugin_id in self.event_subscriptions[event_type]
        ):
            self.event_subscriptions[event_type].remove(plugin_id)

    def get_plugins_for_event(self, event_type: str) -> list[str]:
        """
        Get the IDs of plugins subscribed to an event type.

        Args:
            event_type: Event type to check

        Returns:
            List[str]: List of plugin IDs
        """
        return self.event_subscriptions.get(event_type, [])
