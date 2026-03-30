"""Event stream recorder that writes events as JSONL to the structured log file.

EventStreamRecorder observes all PANTHER events and appends each one to the
same ``structured.jsonl`` file used by StructuredJsonFormatter. This
interleaves event records with log records chronologically, giving a single
unified timeline of everything that happened during an experiment.

Event records use ``"source": "event"`` (vs ``"source": "logging"`` for log
records) so consumers can distinguish them.

Thread safety: all writes are delegated to a centralized
:class:`~panther.core.utils.jsonl_writer.JsonlWriter` which serializes
access through a single lock.
"""

import json
import logging
from datetime import timezone
from typing import Any, Dict

from panther.core.events.base.event_base import BaseEvent
from panther.core.observer.base.typed_observer_interface import ITypedObserver
from panther.core.utils.jsonl_writer import JsonlWriter
from panther.core.utils.log_context import get_log_context


class EventStreamRecorder(ITypedObserver):
    """Observer that serializes every event to the structured JSONL file.

    Each event is converted to a JSON object matching the schema used by
    StructuredJsonFormatter, with ``"source": "event"`` and ``"level": "EVENT"``
    to distinguish it from log records.

    All writes are delegated to a shared :class:`JsonlWriter` so that log
    records, event records, and metric records are serialized through the
    same lock and file handle.

    Args:
        writer: The centralized :class:`JsonlWriter` for the structured
            JSONL file.
    """

    # Custom log level for events (between INFO=20 and WARNING=30)
    EVENT_LEVEL = 25

    def __init__(self, writer: JsonlWriter):
        """Initialize EventStreamRecorder.

        Args:
            writer: Shared :class:`JsonlWriter` instance.
        """
        super().__init__()
        self._writer = writer
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def output_path(self):
        """Return the path of the underlying JSONL writer."""
        return self._writer.path

    def on_event(self, event: BaseEvent) -> bool:
        """Serialize an event to the structured JSONL file.

        Converts the event to the shared JSONL schema and writes it via
        the centralized :class:`JsonlWriter`. The current LogContext is
        merged into the record so that context fields propagate to
        events as well.

        Args:
            event: The event to record.

        Returns:
            True on success, False if writing failed.
        """
        if self._is_duplicate(event):
            return True

        try:
            record = self._event_to_jsonl_record(event)
            line = json.dumps(record, default=str)
            self._writer.write_line(line)
            return True
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.warning(
                "EventStreamRecorder failed to write event %s: %s. Structured log may be incomplete.",
                getattr(event, "id", "?"),
                exc,
            )
            return False

    def _event_to_jsonl_record(self, event: BaseEvent) -> Dict[str, Any]:
        """Convert a BaseEvent into the structured JSONL schema.

        The schema mirrors StructuredJsonFormatter output but uses
        ``"source": "event"`` and includes event-specific fields
        (event_id, event_type, entity_type, entity_id).

        Context fields (experiment_id, test_id, service_id, phase) are
        read from the current LogContext so that events emitted inside
        a ``log_context()`` block automatically inherit the context.

        Args:
            event: The event to convert.

        Returns:
            Dictionary ready for JSON serialization.
        """
        ctx = get_log_context()
        event_dict = event.to_dict()

        # Build the event timestamp in UTC ISO-8601
        ts = event.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts_iso = ts.isoformat(timespec="microseconds")

        record: Dict[str, Any] = {
            "ts": ts_iso,
            "level": "EVENT",
            "level_num": self.EVENT_LEVEL,
            "source": "event",
            "event_id": event_dict.get("id"),
            "event_type": event_dict.get("type"),
            "entity_type": event_dict.get("entity_type"),
            "entity_id": event_dict.get("entity_id"),
            # Context fields from LogContext (may be None)
            "experiment_id": ctx.experiment_id,
            "test_id": ctx.test_id,
            "service_id": ctx.service_id,
            "phase": ctx.phase,
            # Human-readable summary
            "message": str(event),
            # Full event payload
            "data": event_dict.get("data"),
        }

        # Strip None values for compactness (matching StructuredJsonFormatter)
        record = {k: v for k, v in record.items() if v is not None}

        return record

    def is_interested(self, event_type: str) -> bool:  # noqa: ARG002
        """Accept all event types for recording.

        Args:
            event_type: Event type string (unused — records everything).

        Returns:
            Always True.
        """
        return True

    def get_priority(self) -> int:
        """Return priority 10 -- above default (0) but below business observers (50).

        Returns:
            Priority value of 10.
        """
        return 10
