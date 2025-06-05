"""
Plugin Observer Factory Module

This module provides classes and functions for automatically generating
plugin observers based on plugin interfaces.
"""

import logging
import inspect
from typing import Any

from panther.core.observer.core.core_events import Event
from panther.core.observer.plugin.plugin_interface import IPluginObserver


class PluginObserverFactory:
    """
    Factory for creating plugin observers.

    This factory automatically generates observers based on plugin interfaces
    and routes events to appropriate plugin handlers.
    """

    def __init__(self):
        """Initialize the plugin observer factory."""
        self.logger = logging.getLogger("PluginObserverFactory")
        self._plugins = {}  # plugin_id -> plugin_instance
        self._plugin_events = {}  # plugin_id -> [event_types]
        self._event_plugins = {}  # event_type -> [plugin_ids]

    def register_plugin(self, plugin_id: str, plugin: Any) -> None:
        """
        Register a plugin with the factory.

        Args:
            plugin_id: Unique identifier for the plugin
            plugin: Plugin instance
        """
        self.logger.debug(f"Registering plugin: {plugin_id}")
        self._plugins[plugin_id] = plugin

        # Extract event interests from plugin
        event_types = self._extract_event_interests(plugin)
        self._plugin_events[plugin_id] = event_types

        # Update reverse mapping
        for event_type in event_types:
            if event_type not in self._event_plugins:
                self._event_plugins[event_type] = []
            self._event_plugins[event_type].append(plugin_id)

    def unregister_plugin(self, plugin_id: str) -> None:
        """
        Unregister a plugin from the factory.

        Args:
            plugin_id: Unique identifier for the plugin
        """
        if plugin_id in self._plugins:
            self.logger.debug(f"Unregistering plugin: {plugin_id}")

            # Clean up event mappings
            event_types = self._plugin_events.get(plugin_id, [])
            for event_type in event_types:
                if event_type in self._event_plugins:
                    self._event_plugins[event_type].remove(plugin_id)

            # Clean up plugin registrations
            del self._plugins[plugin_id]
            if plugin_id in self._plugin_events:
                del self._plugin_events[plugin_id]

    def create_observer(self) -> IPluginObserver:
        """
        Create a new plugin observer.

        Returns:
            A dynamically created plugin observer instance
        """
        return _PluginObserver(self)

    def route_event(self, event: Event) -> None:
        """
        Route an event to interested plugins.

        Args:
            event: Event to route
        """
        event_type = event.get_type()
        interested_plugins = self._event_plugins.get(event_type, [])

        for plugin_id in interested_plugins:
            plugin = self._plugins.get(plugin_id)
            if plugin:
                self._handle_plugin_event(plugin, event)

    def _extract_event_interests(self, plugin: Any) -> list[str]:
        """
        Extract event interests from a plugin.

        Args:
            plugin: Plugin instance

        Returns:
            List of event types the plugin is interested in
        """
        event_types = []

        # Check for EVENT_TYPES attribute
        if hasattr(plugin, "EVENT_TYPES"):
            event_types.extend(plugin.EVENT_TYPES)

        # Check for is_interested method
        if hasattr(plugin, "is_interested") and callable(plugin.is_interested):
            # This is just registration time, actual filtering happens at runtime
            pass

        # Look for on_event_* methods
        for name, method in inspect.getmembers(plugin, inspect.ismethod):
            if name.startswith("on_event_"):
                event_type = name[9:]  # Strip 'on_event_' prefix
                event_types.append(event_type)

        return event_types

    def _handle_plugin_event(self, plugin: Any, event: Event) -> None:
        """
        Handle an event for a specific plugin.

        Args:
            plugin: Plugin instance
            event: Event to handle
        """
        event_type = event.get_type()

        # Check general event handler
        if hasattr(plugin, "on_event") and callable(plugin.on_event):
            try:
                plugin.on_event(event)
            except Exception as e:
                self.logger.error(f"Error in plugin.on_event: {str(e)}")

        # Check specific event handler
        specific_handler = f"on_event_{event_type}"
        if hasattr(plugin, specific_handler) and callable(getattr(plugin, specific_handler)):
            try:
                getattr(plugin, specific_handler)(event)
            except Exception as e:
                self.logger.error(f"Error in plugin.{specific_handler}: {str(e)}")


class _PluginObserver(IPluginObserver):
    """
    Concrete implementation of IPluginObserver.

    This class is created by the PluginObserverFactory and delegates
    event handling to the factory.
    """

    def __init__(self, factory: PluginObserverFactory):
        """
        Initialize a plugin observer.

        Args:
            factory: Reference to the factory that created this observer
        """
        self.factory = factory
        self.logger = logging.getLogger("PluginObserver")

    def on_event(self, event: Event):
        """
        Handle an event by routing it to appropriate plugins.

        Args:
            event: Event to handle
        """
        self.factory.route_event(event)

    def register_plugin_events(self, plugin_id: str, event_types: list[str]) -> None:
        """Register event types for a plugin."""
        for event_type in event_types:
            if event_type not in self.factory._event_plugins:
                self.factory._event_plugins[event_type] = []
            if plugin_id not in self.factory._event_plugins[event_type]:
                self.factory._event_plugins[event_type].append(plugin_id)

        if plugin_id not in self.factory._plugin_events:
            self.factory._plugin_events[plugin_id] = []
        self.factory._plugin_events[plugin_id].extend(event_types)

    def unregister_plugin(self, plugin_id: str) -> None:
        """Unregister a plugin."""
        self.factory.unregister_plugin(plugin_id)

    def get_plugin_events(self, plugin_id: str) -> list[str]:
        """Get events a plugin is interested in."""
        return self.factory._plugin_events.get(plugin_id, [])

    def get_plugins_for_event(self, event_type: str) -> list[str]:
        """Get plugins interested in an event type."""
        return self.factory._event_plugins.get(event_type, [])

    def is_interested(self, event_type: str) -> bool:
        """Check if any plugins are interested in an event type."""
        return event_type in self.factory._event_plugins


# Singleton factory instance for global use
_factory = PluginObserverFactory()


def create_plugin_observer() -> IPluginObserver:
    """
    Create a new plugin observer using the global factory.

    Returns:
        A plugin observer instance
    """
    return _factory.create_observer()


def register_plugin_observer(plugin_id: str, plugin: Any) -> None:
    """
    Register a plugin with the global factory.

    Args:
        plugin_id: Unique identifier for the plugin
        plugin: Plugin instance
    """
    _factory.register_plugin(plugin_id, plugin)
