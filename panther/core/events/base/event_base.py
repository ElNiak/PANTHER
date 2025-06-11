"""
Base Event Classes

This module defines the base event classes used across all entity types in PANTHER.
"""

from abc import ABC
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class EventType(Enum):
    """Enumeration of core event types."""

    EXPERIMENT = "experiment"
    TEST = "test"
    SERVICE = "service"
    ENVIRONMENT = "environment"
    SYSTEM = "system"
    METRICS = "metrics"
    STEP = "step"
    ASSERTION = "assertion"
    PLUGIN = "plugin"


class BaseEvent(ABC):
    """
    Base event class for all system events.

    Provides common functionality for all events including unique identification,
    timestamps, and basic data management.
    """

    def __init__(
        self, name: str, entity_type: EventType, entity_id: str, data: dict[str, Any] | None = None
    ):
        """
        Initialize a base event.

        Args:
            name: Event name/identifier
            entity_type: Type of entity this event relates to
            entity_id: Unique identifier of the entity
            data: Additional event data
        """
        self.id = str(uuid.uuid4())
        self.name = name
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.timestamp = datetime.now()
        self.data = data or {}

    def get_type(self) -> str:
        """Get the event type identifier."""
        return f"{self.entity_type.value}.{self.name}"

    def get_entity_id(self) -> str:
        """Get the entity identifier this event relates to."""
        return self.entity_id

    def get_timestamp(self) -> datetime:
        """Get the event timestamp."""
        return self.timestamp

    def get_data(self) -> dict[str, Any]:
        """Get the event data."""
        return self.data.copy()

    def add_data(self, key: str, value: Any) -> None:
        """Add additional data to the event."""
        self.data[key] = value

    def __str__(self) -> str:
        return f"{self.get_type()}({self.entity_id}) at {self.timestamp.isoformat()}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.get_type()}({self.entity_id})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.get_type(),
            "entity_type": self.entity_type.value,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }

    def validate(self) -> bool:
        """
        Validate event data.

        Base implementation validates required fields.
        Subclasses should override for specific validation.
        """
        return (
            self.name is not None
            and self.entity_type is not None
            and self.entity_id is not None
            and self.timestamp is not None
        )
