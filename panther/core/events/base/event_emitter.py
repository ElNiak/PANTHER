"""Base event emitter for unified event emission."""

from typing import Any
from datetime import datetime
from uuid import uuid4

from panther.core.events.base.event_base import BaseEvent
from panther.core.observer.management.event_manager import EventManager


class Event(BaseEvent):
    """Simple event class for backward compatibility."""

    def __init__(
        self,
        event_id: str,
        event_type: str,
        timestamp: datetime,
        severity: str = "info",
        data: dict[str, Any] = None,
    ):
        """Initialize a simple event.

        Args:
            event_id: Unique event identifier
            event_type: Type of the event
            timestamp: Event timestamp
            severity: Event severity level
            data: Event data
        """
        # Parse event type to extract entity type
        parts = event_type.split(".")
        entity_type_str = parts[0] if parts else "system"
        event_name = ".".join(parts[1:]) if len(parts) > 1 else event_type

        # Map string to EventType enum
        from panther.core.events.base.event_base import EventType

        entity_type_map = {
            "experiment": EventType.EXPERIMENT,
            "test": EventType.TEST,
            "service": EventType.SERVICE,
            "environment": EventType.ENVIRONMENT,
            "system": EventType.SYSTEM,
            "metrics": EventType.METRICS,
            "step": EventType.STEP,
            "assertion": EventType.ASSERTION,
            "plugin": EventType.PLUGIN,
        }
        entity_type = entity_type_map.get(entity_type_str, EventType.SYSTEM)

        super().__init__(
            name=event_name, entity_type=entity_type, entity_id=event_id, data=data or {}
        )
        self.severity = severity
        self.event_type = event_type
        self.timestamp = timestamp


class EventEmitter:
    """Base class for emitting events in a unified way."""

    def __init__(self, event_manager: EventManager | None = None):
        """Initialize the event emitter.

        Args:
            event_manager: Optional event manager for handling events
        """
        self.event_manager = event_manager or EventManager.get_instance()

    def emit(self, event_type: str, data: dict[str, Any], severity: str = "info") -> None:
        """Emit an event.

        Args:
            event_type: Type of the event
            data: Event data
            severity: Event severity level
        """
        event = Event(
            event_id=str(uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            severity=severity,
            data=data,
        )

        if self.event_manager:
            self.event_manager.publish(event)
