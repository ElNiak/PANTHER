"""Plugin Observer Module.

This module provides a concrete implementation of the PluginManager interface
to facilitate event delivery to plugins in the PANTHER framework.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Set

from panther.core.events.base.event_base import BaseEvent as Event
from panther.core.observer.base.observer_interface import IObserver
from panther.plugins.plugin_interface import IPlugin


class PluginObserver(IObserver):
    """Concrete implementation of IPluginObserver that manages event interests.

    Manages event interests for plugins and delivers events to interested plugins.

    This observer serves as a bridge between the event system and plugins,
    ensuring that plugins only receive events they are interested in.
    """

    def __init__(self, event_manager=None):
        """Initialize the plugin observer.

        Args:
            event_manager: Optional event manager for plugin events
        """
        self.logger = logging.getLogger("PluginObserver")
        self.event_manager = event_manager
        # Map plugin IDs to plugin instances
        self.plugins: Dict[str, IPlugin] = {}
        # Map plugin IDs to their event interests
        self.plugin_interests: Dict[str, Set[str]] = defaultdict(set)
        # Map event types to interested plugin IDs
        self.event_subscribers: Dict[str, Set[str]] = defaultdict(set)

    def register_plugin(self, plugin: IPlugin) -> None:
        """Register a plugin with the observer.

        Args:
            plugin: The plugin instance to register
        """
        plugin_id = plugin.plugin_id
        self.plugins[plugin_id] = plugin

        # Register the plugin's event interests
        event_types = plugin.get_supported_events()
        if event_types:
            self.register_plugin_events(plugin_id, event_types)

        self.logger.debug(
            "Registered plugin '%s' with %d event interests",
            plugin.name,
            len(event_types),
        )

    def register_plugin_events(self, plugin_id: str, event_types: List[str]) -> None:
        """Register event types that a plugin is interested in.

        Args:
            plugin_id: Unique identifier for the plugin
            event_types: List of event types the plugin is interested in
        """
        if plugin_id not in self.plugins:
            self.logger.warning(
                "Attempted to register events for unknown plugin ID: %s", plugin_id
            )
            return

        for event_type in event_types:
            self.plugin_interests[plugin_id].add(event_type)
            self.event_subscribers[event_type].add(plugin_id)

        self.logger.debug(
            "Registered plugin '%s' for events: %s", plugin_id, ", ".join(event_types)
        )

    def unregister_plugin(self, plugin_id: str) -> None:
        """Unregister a plugin and its event interests.

        Args:
            plugin_id: Unique identifier for the plugin
        """
        if plugin_id not in self.plugins:
            return

        # Remove from event subscriptions
        for event_type in list(self.plugin_interests.get(plugin_id, [])):
            if plugin_id in self.event_subscribers.get(event_type, set()):
                self.event_subscribers[event_type].remove(plugin_id)

        # Clean up empty event subscriber entries
        for event_type in list(self.event_subscribers.keys()):
            if not self.event_subscribers[event_type]:
                del self.event_subscribers[event_type]

        # Remove plugin interests
        if plugin_id in self.plugin_interests:
            del self.plugin_interests[plugin_id]

        # Remove plugin instance
        if plugin_id in self.plugins:
            del self.plugins[plugin_id]

        self.logger.debug("Unregistered plugin '%s'", plugin_id)

    def get_plugin_events(self, plugin_id: str) -> List[str]:
        """Get the event types a plugin is interested in.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            List of event types the plugin is interested in
        """
        return list(self.plugin_interests.get(plugin_id, []))

    def get_plugins_for_event(self, event_type: str) -> List[str]:
        """Get plugins interested in a specific event type.

        Args:
            event_type: The event type to check

        Returns:
            List of plugin IDs interested in this event type
        """
        # Direct matches for this exact event type
        matches = set(self.event_subscribers.get(event_type, []))

        # Also check for parent event types using dot notation hierarchy
        parts = event_type.split(".")
        for i in range(1, len(parts)):
            parent_type = ".".join(parts[:-i])
            matches.update(self.event_subscribers.get(parent_type, []))

        return list(matches)

    def is_interested(self, event_type: str) -> bool:
        """Check if any plugin is interested in this event type.

        Args:
            event_type: The event type to check

        Returns:
            True if at least one plugin is interested in this event type
        """
        if self.get_plugins_for_event(event_type):
            return True

        return False

    def on_event(self, event: Event) -> None:
        """Handle an event by routing it to interested plugins.

        Args:
            event: The event to handle
        """
        event_type = event.get_type()

        # Find interested plugins
        plugin_ids = self.get_plugins_for_event(event_type)
        if not plugin_ids:
            return

        for plugin_id in plugin_ids:
            plugin = self.plugins.get(plugin_id)
            if not plugin:
                continue

            try:
                plugin.handle_event(event)
            except Exception as e:
                self.logger.error(
                    "Error in plugin '%s' handling event '%s': %s",
                    plugin.name,
                    event_type,
                    str(e),
                    exc_info=True,
                )
