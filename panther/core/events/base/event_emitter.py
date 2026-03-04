"""Simple event emitter using the EventManager singleton.

Provides :class:`EventEmitter`, a lightweight convenience class that emits
events via ``EventManager.get_instance()`` by default.  Unlike the abstract
:class:`~panther.core.events.base.event_emitter_base.EventEmitterBase`
hierarchy, this class is concrete and requires no subclassing.

Example:
    Emit an event with the default manager::

        from panther.core.events.base.event_emitter import EventEmitter
        from panther.core.events.base.event_base import BaseEvent, EventType

        emitter = EventEmitter()
        event = BaseEvent("test.started", EventType.TEST, "t1")
        emitter.emit_event(event)
"""

from typing import Optional

from panther.core.events.base.event_base import BaseEvent
from panther.core.observer.management.event_manager import EventManager


class EventEmitter:
    """Simple event emitter that uses ``EventManager.get_instance()`` as default.

    Emits events via ``event_manager.publish(event)``.  If no
    ``EventManager`` is provided at construction time, the global singleton
    is used automatically.
    """

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
