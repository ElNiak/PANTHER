"""
Event Observer Plugin Module

This module provides a base class for plugins that observe events in the system.
"""

from abc import ABC, abstractmethod

from panther.core.observer.core.core_events import Event


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
        EVENT_TYPES = ["test_started", "test_completed"]

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

    @abstractmethod
    def on_event(self, event: Event) -> None:
        """
        Handle an event.

        This method is called for any event type that this plugin is registered to observe.

        Args:
            event: The event to handle
        """
        pass

    def is_interested(self, event_type: str) -> bool:
        """
        Check if this plugin is interested in an event type.

        Args:
            event_type: The event type to check

        Returns:
            True if the plugin is interested in this event type, False otherwise
        """
        return event_type in self.EVENT_TYPES or hasattr(self, f"on_event_{event_type}")
