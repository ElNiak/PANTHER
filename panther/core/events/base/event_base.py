"""Base event classes and utility functions for the PANTHER event system.

This module defines the foundational event infrastructure:

- `create_content_based_uuid()` -- Deterministic UUID5 generation for
  event deduplication across distributed test environments.
- `create_event_signature()` -- Builds a deterministic signature string
  (excluding timestamps) for duplicate detection.
- `EventType` -- Enum that partitions events by entity domain
  (experiment, test, service, environment, etc.).
- `BaseEvent` -- Abstract base for all events.  **Not a dataclass** --
  uses a standard ``__init__`` constructor.  **Not frozen/immutable** --
  ``add_data()`` mutates the data dict and regenerates the UUID.

Example:
    Basic event creation and deduplication::

        from panther.core.events.base.event_base import (
            BaseEvent, EventType, create_content_based_uuid,
        )

        e1 = BaseEvent("test.started", EventType.TEST, "t1", {"k": "v"})
        e2 = BaseEvent("test.started", EventType.TEST, "t1", {"k": "v"})
        assert e1.is_duplicate_of(e2)  # same content --> same UUID
"""

import hashlib
import uuid
from abc import ABC
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


def create_content_based_uuid(content: str) -> str:
    """Create a deterministic UUID from content for duplicate detection.

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
    """Create a deterministic signature string for event deduplication.

    Excludes timestamps so that two events with identical content but
    different creation times produce the same signature.

    Args:
        name: Event name (e.g. ``"test.execution_started"``).
        entity_type: Event entity type (e.g. ``"test"``).
        entity_id: Unique entity identifier.
        data: Optional event data dictionary.  Keys are sorted for
            deterministic ordering; the ``"timestamp"`` key is excluded.

    Returns:
        Signature in the format
        ``"{entity_type}:{name}:{entity_id}:{sorted_data}"``.
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
    """Enumeration of entity domains that events belong to.

    Each member corresponds to a sub-package under ``panther.core.events``
    that defines domain-specific event classes, emitters, and state managers.
    Used as the ``entity_type`` field on `BaseEvent` to enable O(1)
    event filtering by domain.
    """

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
    """Base event class for all system events in PANTHER.

    Foundation of the event-driven architecture, providing deterministic event
    identification, deduplication, serialization, and validation.  All
    domain-specific events (test, service, environment, etc.) inherit from
    this class.

    **Not a dataclass** -- uses a standard ``__init__``.
    **Not frozen/immutable** -- ``add_data()`` mutates data and regenerates
    the content-based UUID.

    Integration flow::

        Event Producer --> BaseEvent --> EventEmitter --> EventManager --> Observers

    Event Deduplication:
        Uses UUID5 with a deterministic namespace to generate identical UUIDs
        for events with the same content, enabling deduplication in
        distributed testing environments.  The ``content_signature`` excludes
        timestamps so identical logical events always match.

    Attributes:
        id: Unique identifier -- UUID4 (legacy) or content-based UUID5.
        name: Event name/identifier (e.g. ``"execution_started"``).
        entity_type: `EventType` enum member for domain partitioning.
        entity_id: Unique identifier of the entity this event relates to.
        timestamp: Event creation timestamp (``datetime.now()``).
        data: Additional event payload (mutable via ``add_data()``).
        content_signature: Deterministic signature for duplicate detection,
            or ``None`` when ``use_content_uuid=False``.

    Example:
        Create an event and check deduplication::

            e1 = BaseEvent("test.started", EventType.TEST, "t1", {"k": "v"})
            e2 = BaseEvent("test.started", EventType.TEST, "t1", {"k": "v"})
            assert e1.is_duplicate_of(e2)

            e1.add_data("extra", 42)   # mutates data, regenerates UUID
            assert not e1.is_duplicate_of(e2)
    """

    def __init__(
        self,
        name: str,
        entity_type: EventType,
        entity_id: str,
        data: Optional[Dict[str, Any]] = None,
        use_content_uuid: bool = True,
    ):
        """Initialize a base event.

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
        """Get the event type identifier string.

        Returns:
            Composite string in the format ``"{entity_type}.{name}"``
            (e.g. ``"test.execution_started"``).
        """
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
        """Add additional data to the event.

        Mutates ``self.data`` in place and regenerates the content-based UUID
        (if content-based deduplication is enabled).

        Args:
            key: Data key to add.
            value: Data value to store.
        """
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
        """Check if this event is a duplicate of another event.

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
        """Return human-readable string representation."""
        return f"{self.get_type()}({self.entity_id}) at {self.timestamp.isoformat()}"

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        return f"<{self.__class__.__name__}: {self.get_type()}({self.entity_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation.

        Returns:
            Dict with keys: ``id``, ``name``, ``type``, ``entity_type``,
            ``entity_id``, ``timestamp`` (ISO format), ``data``.
        """
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
        """Validate event data.

        Base implementation checks that ``name``, ``entity_type``,
        ``entity_id``, and ``timestamp`` are not ``None``.  Subclasses
        should override for domain-specific validation.

        Returns:
            ``True`` if all required fields are present.
        """
        return (
            self.name is not None
            and self.entity_type is not None
            and self.entity_id is not None
            and self.timestamp is not None
        )
