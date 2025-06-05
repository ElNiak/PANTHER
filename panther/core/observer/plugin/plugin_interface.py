"""
Plugin Observer Interface Module

This module defines interfaces for plugin-based observers in the PANTHER framework.
"""

from abc import abstractmethod

from panther.core.observer.core.observer_interface import IObserver


class IPluginObserver(IObserver):
    """
    Interface for plugin-based observers.

    Plugin observers are dynamically generated based on plugin interfaces and
    can automatically handle events relevant to specific plugins.
    """

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
