"""
Base Event Classes

This module defines the base event classes used across all entity types in PANTHER.
"""

import hashlib
import uuid
from abc import ABC
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


def create_content_based_uuid(content: str) -> str:
    """
    Create a deterministic UUID from content for duplicate detection.

    This function generates a UUID5 based on the content, ensuring that
    identical content always produces the same UUID. This enables
    detection of duplicate events.

    Args:
        content: String content to generate UUID from

    Returns:
        Deterministic UUID string
    """
    # Use a namespace for PANTHER events
    panther_namespace = uuid.UUID(
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    )  # Standard namespace OID
    return str(uuid.uuid5(panther_namespace, content))


def create_event_signature(
    name: str, entity_type: str, entity_id: str, data: Dict[str, Any] = None
) -> str:
    """
    Create a signature string for event deduplication.

    Args:
        name: Event name
        entity_type: Event entity type
        entity_id: Entity identifier
        data: Event data dictionary

    Returns:
        String signature for the event
    """
    # Create deterministic signature from core event properties
    # Note: We exclude timestamp to allow duplicate detection of identical events
    data_str = ""
    if data:
        # Sort data keys for deterministic ordering
        sorted_data = {k: str(v) for k, v in sorted(data.items()) if k != "timestamp"}
        data_str = str(sorted_data)

    return f"{entity_type}:{name}:{entity_id}:{data_str}"


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
    Base event class for all system events in PANTHER's event-driven architecture.

    This class forms the foundation of PANTHER's event system, providing deterministic
    event identification, deduplication capabilities, and consistent event lifecycle
    management. All domain-specific events (test, service, environment, etc.) inherit
    from this base class.

    **Architecture Role:**
    - Central abstraction for all events in the system
    - Enables event deduplication through content-based UUIDs
    - Provides serialization and validation capabilities
    - Supports event tracing and debugging through signatures

    **Event Deduplication:**
    Uses UUID5 with a deterministic namespace to generate identical UUIDs for events
    with the same content, enabling sophisticated deduplication strategies in
    distributed testing environments.

    **Integration Pattern:**
    ```mermaid
    graph LR
        A[Event Producer] --> B[BaseEvent]
        B --> C[EventEmitter]
        C --> D[EventManager]
        D --> E[Observers]
    ```

    Attributes:
        id (str): Unique identifier (UUID4 or content-based UUID5)
        name (str): Event name/identifier
        entity_type (EventType): Type of entity this event relates to
        entity_id (str): Unique identifier of the entity
        timestamp (datetime): Event creation timestamp
        data (Dict[str, Any]): Additional event data
        content_signature (str, optional): Deterministic content signature for deduplication
    """

    def __init__(
        self,
        name: str,
        entity_type: EventType,
        entity_id: str,
        data: Optional[Dict[str, Any]] = None,
        use_content_uuid: bool = True,
    ):
        """
        Initialize a base event.

        Args:
            name: Event name/identifier
            entity_type: Type of entity this event relates to
            entity_id: Unique identifier of the entity
            data: Additional event data
            use_content_uuid: If True, generate deterministic UUID for duplicate detection
        """
        self.name = name
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.timestamp = datetime.now()
        self.data = data or {}

        # Generate UUID based on content for duplicate detection
        if use_content_uuid:
            # Create signature from event content (excluding timestamp)
            signature = create_event_signature(
                name=self.name,
                entity_type=self.entity_type.value,
                entity_id=self.entity_id,
                data=self.data,
            )
            self.id = create_content_based_uuid(signature)
            self.content_signature = signature
        else:
            # Fall back to random UUID (legacy behavior)
            self.id = str(uuid.uuid4())
            self.content_signature = None

    def get_type(self) -> str:
        """Get the event type identifier."""
        return f"{self.entity_type.value}.{self.name}"

    def get_entity_id(self) -> str:
        """Get the entity identifier this event relates to."""
        return self.entity_id

    def get_timestamp(self) -> datetime:
        """Get the event timestamp."""
        return self.timestamp

    def get_data(self) -> Dict[str, Any]:
        """Get the event data."""
        return self.data.copy()

    def add_data(self, key: str, value: Any) -> None:
        """Add additional data to the event."""
        self.data[key] = value

        # If using content-based UUID, regenerate it after data changes
        if hasattr(self, "content_signature") and self.content_signature is not None:
            signature = create_event_signature(
                name=self.name,
                entity_type=self.entity_type.value,
                entity_id=self.entity_id,
                data=self.data,
            )
            self.id = create_content_based_uuid(signature)
            self.content_signature = signature

    def is_duplicate_of(self, other_event: "BaseEvent") -> bool:
        """
        Check if this event is a duplicate of another event.

        Args:
            other_event: Another BaseEvent to compare with

        Returns:
            bool: True if events have the same content signature
        """
        if not isinstance(other_event, BaseEvent):
            return False

        # If both events use content-based UUIDs, compare them
        if (
            hasattr(self, "content_signature")
            and self.content_signature
            and hasattr(other_event, "content_signature")
            and other_event.content_signature
        ):
            return self.content_signature == other_event.content_signature

        # If both have same UUID (content-based), they're duplicates
        return self.id == other_event.id

    def get_content_signature(self) -> Optional[str]:
        """Get the content signature for duplicate detection."""
        return getattr(self, "content_signature", None)

    def __str__(self) -> str:
        return f"{self.get_type()}({self.entity_id}) at {self.timestamp.isoformat()}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.get_type()}({self.entity_id})>"

    def to_dict(self) -> Dict[str, Any]:
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
