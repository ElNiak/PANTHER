"""
Plugin Communicator Module

This module provides a helper class for plugin-to-plugin communication using events.
"""

from typing import Any

from panther.core.observer.plugin.plugin_events import (
    ServiceRequestEvent,
    PluginEvent,
)
from panther.plugins.enhanced_plugin_registry import EnhancedPluginRegistry


class PluginCommunicator:
    """
    Helper class for plugin communication.

    This class provides standardized methods for plugins to communicate with each other
    using events through the plugin registry.
    """

    def __init__(self, plugin_registry: EnhancedPluginRegistry):
        """
        Initialize the plugin communicator.

        Args:
            plugin_registry: Registry for plugin management and event dispatching
        """
        self.plugin_registry = plugin_registry

    def request_service(
        self, requester_id: str, service_type: str, parameters: dict[str, Any] = None
    ) -> None:
        """
        Request a service from another plugin.

        Args:
            requester_id: ID of the plugin making the request
            service_type: Type of service being requested
            parameters: Parameters for the service request
        """
        event = ServiceRequestEvent(
            requester_id=requester_id,
            service_type=service_type,
            parameters=parameters,
        )
        self.plugin_registry.dispatch_event(event)

    def send_custom_event(
        self,
        source_plugin_id: str,
        event_name: str,
        data: dict[str, Any] = None,
        target_plugin_ids: list[str] = None,
    ) -> None:
        """
        Send a custom event to other plugins.

        Args:
            source_plugin_id: ID of the plugin sending the event
            event_name: Name/type of the event
            data: Event data
            target_plugin_ids: Specific plugins to notify, or None for all relevant plugins
        """
        # Create a custom plugin event
        event = PluginEvent(event_name, source_plugin_id, data)

        if target_plugin_ids:
            # Dispatch to specific plugins
            for plugin_id in target_plugin_ids:
                plugin = self.plugin_registry.get_plugin(plugin_id)
                if plugin:
                    plugin.handle_event(event)
        else:
            # Dispatch to all subscribers
            self.plugin_registry.dispatch_event(event)

    def get_plugin_status_by_type(self, plugin_type: str) -> dict[str, dict[str, Any]]:
        """
        Get the status of all plugins of a specific type.

        Args:
            plugin_type: Type of plugins to check

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping plugin IDs to status information
        """
        plugins = self.plugin_registry.get_all_plugins()
        return {
            plugin_id: plugin.get_status()
            for plugin_id, plugin in plugins.items()
            if getattr(plugin, "plugin_type", None) == plugin_type
        }

    def get_running_services(self) -> dict[str, dict[str, Any]]:
        """
        Get information about all running services.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping service IDs to service information
        """
        services = self.get_plugin_status_by_type("service")
        return {
            plugin_id: status
            for plugin_id, status in services.items()
            if status.get("state") == "running"
        }
