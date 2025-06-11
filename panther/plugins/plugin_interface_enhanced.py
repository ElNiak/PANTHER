"""
Enhanced Plugin Interface Module

This module defines the enhanced plugin interface for PANTHER framework's
event-driven plugin architecture. It builds on the existing IPlugin interface
and adds event handling capabilities.
"""

from abc import abstractmethod
import logging
from typing import Any

from panther.plugins.plugin_interface import IPlugin
from panther.core.events import BaseEvent as Event


class IPantherPlugin(IPlugin):
    """
    Enhanced plugin interface with event support.

    This interface builds on the basic IPlugin interface and adds event
    handling capabilities, lifecycle management, and configuration options.

    Plugins implementing this interface:
    1. Can subscribe to specific events by event type
    2. Can process events through the handle_event method
    3. Can emit events through the provided event_emitter
    4. Support standard lifecycle operations (initialize, shutdown)
    """

    def __init__(self, plugin_id: str = None, name: str = None):
        """
        Initialize a new plugin instance.

        Args:
            plugin_id: Optional unique identifier for this plugin instance
            name: Optional human-readable name for this plugin
        """
        super().__init__()
        self.plugin_id = plugin_id or self.__class__.__name__
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"Plugin:{self.name}")
        self.event_emitter = None
        self.config = {}
        self.is_initialized = False

    def set_event_emitter(self, event_emitter):
        """
        Set the event emitter for this plugin.

        Args:
            event_emitter: The event emitter instance
        """
        self.event_emitter = event_emitter
        self.logger.debug("Event emitter set on plugin %s", self.name)

    def get_supported_events(self) -> list[str]:
        """
        Get the event types this plugin is interested in.

        Returns:
            List of event types the plugin wants to receive
        """
        # Default implementation returns empty list
        # Override this in your plugin to specify events of interest
        return []

    @abstractmethod
    def handle_event(self, event: Event) -> None:
        """
        Handle an event sent to this plugin.

        Args:
            event: The event to handle
        """
        pass

    def initialize(self, config: dict[str, Any] | None = None) -> bool:
        """
        Initialize the plugin with configuration.

        This method is called during plugin loading to perform any
        setup operations needed before the plugin can be used.

        Args:
            config: Configuration dictionary for this plugin

        Returns:
            bool: True if initialization successful, False otherwise
        """
        self.config = config or {}
        self.is_initialized = True
        return True

    def shutdown(self) -> bool:
        """
        Perform cleanup operations when shutting down the plugin.

        Returns:
            bool: True if shutdown successful, False otherwise
        """
        self.is_initialized = False
        return True

    def emit_event(self, event: Event) -> None:
        """
        Emit an event using the plugin's event emitter.

        Args:
            event: The event to emit
        """
        if self.event_emitter:
            self.event_emitter.emit_event(event)
        else:
            self.logger.warning("Attempted to emit event but no event_emitter is set")
