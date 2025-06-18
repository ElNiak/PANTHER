"""Base event emitter for unified event emission."""

from typing import Optional

from panther.core.events.base.event_base import BaseEvent
from panther.core.observer.management.event_manager import EventManager


class EventEmitter:
    """Base class for emitting typed events in a unified way."""

    def __init__(self, event_manager: Optional[EventManager] = None):
        """Initialize the event emitter.

        Args:
            event_manager: Optional event manager for handling events
        """
        self.event_manager = event_manager or EventManager.get_instance()

    def emit_event(self, event: BaseEvent) -> None:
        """Emit a typed event.

        Args:
            event: The typed event to emit
        """
        if self.event_manager:
            self.event_manager.publish(event)
