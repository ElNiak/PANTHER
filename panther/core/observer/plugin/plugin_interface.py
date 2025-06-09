"""
Plugin Observer Interface Module

This module defines interfaces for plugin-based observers in the PANTHER framework.
"""

import logging
from abc import abstractmethod
from collections import defaultdict

from panther.core.observer.core.observer_interface import IObserver
from panther.core.observer.events import Event


class IPluginObserver(IObserver):
    """
    Interface for plugin-based observers.

    Plugin observers are dynamically generated based on plugin interfaces and
    can automatically handle events relevant to specific plugins.
    """

    def __init__(self):
        """Initialize the plugin observer with logging and plugin tracking."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        # Map plugin IDs to their interested event types
        self.plugin_events: dict[str, set[str]] = defaultdict(set)
        # Map event types to interested plugin IDs
        self.event_plugins: dict[str, set[str]] = defaultdict(set)

    @abstractmethod
    def register_plugin_events(self, plugin_id: str, event_types: list[str]) -> None:
        """
        Register event types that a plugin is interested in.

        Args:
            plugin_id: Unique identifier for the plugin
            event_types: List of event types the plugin is interested in
        """
        pass

    @abstractmethod
    def unregister_plugin(self, plugin_id: str) -> None:
        """
        Unregister a plugin and its event interests.

        Args:
            plugin_id: Unique identifier for the plugin
        """
        pass

    @abstractmethod
    def get_plugin_events(self, plugin_id: str) -> list[str]:
        """
        Get the event types a plugin is interested in.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            List of event types the plugin is interested in
        """
        pass

    @abstractmethod
    def get_plugins_for_event(self, event_type: str) -> list[str]:
        """
        Get plugins interested in a specific event type.

        Args:
            event_type: The event type to check

        Returns:
            List of plugin IDs interested in this event type
        """
        pass


class PluginObserver(IPluginObserver):
    """
    Concrete implementation of the plugin observer interface.

    This class provides a complete implementation for managing plugin-based
    event subscriptions and notifications.
    """

    def __init__(self):
        """Initialize the plugin observer."""
        super().__init__()

    def register_plugin_events(self, plugin_id: str, event_types: list[str]) -> None:
        """
        Register event types that a plugin is interested in.

        Args:
            plugin_id: Unique identifier for the plugin
            event_types: List of event types the plugin is interested in
        """
        self.logger.debug(f"Registering plugin '{plugin_id}' for events: {event_types}")

        # Add events to plugin's interest list
        self.plugin_events[plugin_id].update(event_types)

        # Add plugin to each event's plugin list
        for event_type in event_types:
            self.event_plugins[event_type].add(plugin_id)

    def unregister_plugin(self, plugin_id: str) -> None:
        """
        Unregister a plugin and its event interests.

        Args:
            plugin_id: Unique identifier for the plugin
        """
        self.logger.debug(f"Unregistering plugin '{plugin_id}'")

        # Get events this plugin was interested in
        interested_events = self.plugin_events.get(plugin_id, set())

        # Remove plugin from event mappings
        for event_type in interested_events:
            self.event_plugins[event_type].discard(plugin_id)
            # Clean up empty event mappings
            if not self.event_plugins[event_type]:
                del self.event_plugins[event_type]

        # Remove plugin's event interests
        if plugin_id in self.plugin_events:
            del self.plugin_events[plugin_id]

    def get_plugin_events(self, plugin_id: str) -> list[str]:
        """
        Get the event types a plugin is interested in.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            List of event types the plugin is interested in
        """
        return list(self.plugin_events.get(plugin_id, set()))

    def get_plugins_for_event(self, event_type: str) -> list[str]:
        """
        Get plugins interested in a specific event type.

        Args:
            event_type: The event type to check

        Returns:
            List of plugin IDs interested in this event type
        """
        return list(self.event_plugins.get(event_type, set()))

    def on_event(self, event: Event) -> None:
        """
        Handle an event by notifying interested plugins.

        Args:
            event: The event to handle
        """
        event_type = event.get_type()
        interested_plugins = self.get_plugins_for_event(event_type)

        if interested_plugins:
            self.logger.debug(f"Event '{event_type}' interests plugins: {interested_plugins}")
            # This is where you would notify the actual plugin instances
            # The specific implementation depends on your plugin system
            self._notify_plugins(event, interested_plugins)

    def _notify_plugins(self, event: Event, plugin_ids: list[str]) -> None:
        """
        Notify specific plugins about an event.

        This method should be overridden by concrete implementations
        to handle the actual plugin notification mechanism.

        Args:
            event: The event to send to plugins
            plugin_ids: List of plugin IDs to notify
        """
        # Default implementation just logs the notification
        for plugin_id in plugin_ids:
            self.logger.info(f"Notifying plugin '{plugin_id}' about event '{event.get_type()}'")

    def get_registered_plugins(self) -> list[str]:
        """
        Get a list of all registered plugin IDs.

        Returns:
            List of registered plugin IDs
        """
        return list(self.plugin_events.keys())

    def get_event_types(self) -> list[str]:
        """
        Get a list of all event types that have interested plugins.

        Returns:
            List of event types with registered plugins
        """
        return list(self.event_plugins.keys())
