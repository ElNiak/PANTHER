"""
Enhanced Plugin Interface Module

This module defines the core interfaces for all plugin types in the enhanced plugin architecture.
"""

from abc import ABC, abstractmethod
from typing import Any

from panther.core.observer.events import Event


class IPantherPlugin(ABC):
    """
    Base interface for all PANTHER plugins with standardized lifecycle methods.

    This interface defines the common methods that all plugins must implement,
    ensuring a consistent plugin lifecycle and event handling capability.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the plugin.

        This method is called when the plugin is first loaded. It should perform
        any setup needed for the plugin to function, but should not start any
        long-running operations.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def start(self) -> bool:
        """
        Start the plugin.

        This method is called when the plugin should begin its primary operations.
        It may start long-running processes, establish connections, etc.

        Returns:
            bool: True if startup was successful, False otherwise
        """
        pass

    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the plugin.

        This method is called when the plugin should cease operations. It should
        cleanly shut down any processes, close connections, etc.

        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """
        Get the current status of the plugin.

        Returns:
            Dict[str, Any]: Dictionary containing status information
        """
        pass

    @abstractmethod
    def configure(self, config: dict[str, Any]) -> bool:
        """
        Configure the plugin with the provided configuration.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        pass

    @abstractmethod
    def handle_event(self, event: Event) -> None:
        """
        Handle an incoming event.

        This method is called when an event the plugin is subscribed to occurs.
        Plugins should process the event and take appropriate action.

        Args:
            event: The event to handle
        """
        pass

    @abstractmethod
    def get_subscribed_events(self) -> list[str]:
        """
        Get the list of event types this plugin is interested in.

        Returns:
            List[str]: List of event type identifiers
        """
        pass


class IPluginRegistry(ABC):
    """
    Interface for the plugin registry.

    The plugin registry is responsible for managing plugins and routing events
    between them.
    """

    @abstractmethod
    def register_plugin(self, plugin_id: str, plugin: IPantherPlugin) -> bool:
        """
        Register a plugin with the registry.

        Args:
            plugin_id: Unique identifier for the plugin
            plugin: Plugin instance to register

        Returns:
            bool: True if registration was successful, False otherwise
        """
        pass

    @abstractmethod
    def unregister_plugin(self, plugin_id: str) -> bool:
        """
        Unregister a plugin from the registry.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_plugin(self, plugin_id: str) -> IPantherPlugin | None:
        """
        Get a plugin by ID.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            Optional[IPantherPlugin]: The plugin if found, None otherwise
        """
        pass

    @abstractmethod
    def get_plugin_status(self, plugin_id: str) -> dict[str, Any]:
        """
        Get the status of a plugin.

        Args:
            plugin_id: Unique identifier for the plugin

        Returns:
            Dict[str, Any]: Dictionary containing plugin status
        """
        pass

    @abstractmethod
    def get_all_plugins(self) -> dict[str, IPantherPlugin]:
        """
        Get all registered plugins.

        Returns:
            Dict[str, IPantherPlugin]: Dictionary mapping plugin IDs to plugin instances
        """
        pass

    @abstractmethod
    def dispatch_event(self, event: Event) -> None:
        """
        Dispatch an event to all subscribed plugins.

        Args:
            event: The event to dispatch
        """
        pass

    @abstractmethod
    def subscribe_to_event(self, plugin_id: str, event_type: str) -> None:
        """
        Subscribe a plugin to an event type.

        Args:
            plugin_id: Unique identifier for the plugin
            event_type: Event type to subscribe to
        """
        pass

    @abstractmethod
    def unsubscribe_from_event(self, plugin_id: str, event_type: str) -> None:
        """
        Unsubscribe a plugin from an event type.

        Args:
            plugin_id: Unique identifier for the plugin
            event_type: Event type to unsubscribe from
        """
        pass

    @abstractmethod
    def get_plugins_for_event(self, event_type: str) -> list[str]:
        """
        Get the IDs of plugins subscribed to an event type.

        Args:
            event_type: Event type to check

        Returns:
            List[str]: List of plugin IDs
        """
        pass
