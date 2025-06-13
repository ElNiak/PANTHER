"""
Base Event Emitter

This module provides a base class for all event emitters to reduce code duplication.
"""

from typing import TYPE_CHECKING, TypeVar
from abc import ABC

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_base import BaseEvent

EventType = TypeVar("EventType", bound=BaseEvent)


class EventEmitterBase(ABC):
    """
    Base class for all event emitters.

    This class provides common functionality for event emission,
    reducing duplication across specific emitter implementations.
    """

    def __init__(self, event_manager: "EventManager", entity_id: str = None):
        """
        Initialize the base event emitter.

        Args:
            event_manager: Event manager to emit events through
            entity_id: Optional ID of the entity this emitter handles
        """
        self.event_manager = event_manager
        self.entity_id = entity_id

    def _emit_event(self, event: BaseEvent) -> None:
        """
        Emit an event through the event manager.

        Args:
            event: Event to emit
        """
        self.event_manager.notify(event)

    def _create_and_emit_event(self, event_class: type[EventType], **kwargs) -> None:
        """
        Create and emit an event with the given parameters.

        Args:
            event_class: Class of the event to create
            **kwargs: Keyword arguments to pass to the event constructor
        """
        # Add entity_id if it's provided and not already in kwargs
        if self.entity_id is not None and "entity_id" not in kwargs:
            # Try common entity ID field names
            for field_name in ["experiment_id", "service_id", "test_id", "plugin_id"]:
                # Check if the event class has dataclass fields or constructor parameters
                if (
                    hasattr(event_class, "__dataclass_fields__")
                    and field_name in event_class.__dataclass_fields__
                ):
                    kwargs[field_name] = self.entity_id
                    break
                # For non-dataclass events, try to inspect constructor
                elif hasattr(event_class, "__init__"):
                    import inspect

                    try:
                        sig = inspect.signature(event_class.__init__)
                        if field_name in sig.parameters:
                            kwargs[field_name] = self.entity_id
                            break
                    except (ValueError, TypeError):
                        # If inspection fails, continue to next field name
                        continue

        event = event_class(**kwargs)
        self._emit_event(event)

    def _validate_required_fields(self, **kwargs) -> None:
        """
        Validate that required fields are provided.

        Args:
            **kwargs: Fields to validate

        Raises:
            ValueError: If required fields are missing
        """
        missing_fields = [key for key, value in kwargs.items() if value is None]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")


class EntityEventEmitterBase(EventEmitterBase):
    """
    Base class for entity-specific event emitters.

    This class extends EventEmitterBase for emitters that are tied to
    a specific entity (experiment, service, test, etc.).
    """

    def __init__(self, event_manager: "EventManager", entity_id: str, entity_type: str):
        """
        Initialize the entity event emitter.

        Args:
            event_manager: Event manager to emit events through
            entity_id: ID of the entity this emitter handles
            entity_type: Type of entity (for logging/debugging)
        """
        super().__init__(event_manager, entity_id)
        self.entity_type = entity_type

    def _create_and_emit_entity_event(self, event_class: type[EventType], **kwargs) -> None:
        """
        Create and emit an entity-specific event.

        Args:
            event_class: Class of the event to create
            **kwargs: Keyword arguments to pass to the event constructor
        """
        # Ensure entity_id is always included
        entity_id_field = f"{self.entity_type}_id"
        if entity_id_field not in kwargs:
            kwargs[entity_id_field] = self.entity_id

        self._create_and_emit_event(event_class, **kwargs)
