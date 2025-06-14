"""
Event Observer Plugin Module

This module provides a base class for plugins that observe events in the system.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from panther.core.events.base.event_base import BaseEvent as Event


class EventObserverPlugin(ABC):
    """
    Base class for plugins that want to observe events.

    To create a plugin that observes events:
    1. Inherit from this class
    2. Define EVENT_TYPES class variable with list of event types to observe
    3. Implement on_event() method
    4. Optionally implement on_event_X methods for specific event types

    Example:
    ```python
    class MyEventPlugin(EventObserverPlugin):
        EVENT_TYPES = ["test.started", "test.completed"]

        def on_event(self, event):
            # Handle any event
            pass

        def on_event_test_started(self, event):
            # Handle only test_started events
            pass
    ```
    """

    # List of event types this plugin is interested in
    # Override in subclasses
    EVENT_TYPES: list[str] = []

    def __init__(self):
        """Initialize the event observer plugin."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.plugin_id = f"{self.__class__.__module__}.{self.__class__.__name__}"
        self.event_history: list[Event] = []
        self.max_history = 100

    @abstractmethod
    def on_event(self, event: Event) -> None:
        """
        Handle an event.

        This method is called for any event type that this plugin is registered to observe.

        Args:
            event: The event to handle
        """
        # Store event in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history :]

        # Log the event
        self.logger.debug(f"Plugin {self.plugin_id} received event: {event.get_type()}")

        # Try to call specific event handler if it exists
        event_type = event.get_type()
        handler_name = f"on_event_{event_type.replace('.', '_')}"

        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            if callable(handler):
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(
                        f"Error in specific event handler {handler_name}: {e}"
                    )

    def is_interested(self, event_type: str) -> bool:
        """
        Check if this plugin is interested in an event type.

        Args:
            event_type: The event type to check

        Returns:
            True if the plugin is interested in this event type, False otherwise
        """
        # Check if event type is in the plugin's interest list
        if event_type in self.EVENT_TYPES:
            return True

        # Check if there's a specific handler method for this event type
        handler_name = f"on_event_{event_type.replace('.', '_')}"
        return hasattr(self, handler_name)

    def get_event_types(self) -> list[str]:
        """
        Get the list of event types this plugin is interested in.

        Returns:
            List of event types this plugin observes
        """
        return self.EVENT_TYPES.copy()

    def get_plugin_id(self) -> str:
        """
        Get the unique identifier for this plugin.

        Returns:
            The plugin ID
        """
        return self.plugin_id

    def get_event_history(
        self, event_type: str = None, limit: int = None
    ) -> list[Event]:
        """
        Get the event history for this plugin.

        Args:
            event_type: Filter by this event type, or None for all events
            limit: Maximum number of events to return

        Returns:
            List of events this plugin has received
        """
        events = self.event_history

        if event_type:
            events = [e for e in events if e.get_type() == event_type]

        if limit:
            events = events[-limit:]

        return events

    def get_plugin_info(self) -> dict[str, Any]:
        """
        Get information about this plugin.

        Returns:
            Dictionary containing plugin information
        """
        return {
            "id": self.plugin_id,
            "class": self.__class__.__name__,
            "module": self.__class__.__module__,
            "event_types": self.get_event_types(),
            "events_received": len(self.event_history),
        }
