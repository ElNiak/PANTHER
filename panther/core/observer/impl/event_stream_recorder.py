"""Event stream recorder that writes events as JSONL to the structured log file.

EventStreamRecorder observes all PANTHER events and appends each one to the
same ``structured.jsonl`` file used by StructuredJsonFormatter. This
interleaves event records with log records chronologically, giving a single
unified timeline of everything that happened during an experiment.

Event records use ``"source": "event"`` (vs ``"source": "logging"`` for log
records) so consumers can distinguish them.

Thread safety: writes are protected by a threading.Lock to prevent
interleaving with concurrent log handler writes.
"""

import json
import logging
import threading
from datetime import timezone
from pathlib import Path
from typing import Any, Dict

from panther.core.events.base.event_base import BaseEvent
from panther.core.observer.base.typed_observer_interface import ITypedObserver
from panther.core.utils.log_context import get_log_context


class EventStreamRecorder(ITypedObserver):
    """Observer that serializes every event to the structured JSONL file.

    Each event is converted to a JSON object matching the schema used by
    StructuredJsonFormatter, with ``"source": "event"`` and ``"level": "EVENT"``
    to distinguish it from log records.

    The recorder shares the output file with the logging system's file handler,
    so a threading lock guards all writes.

    Args:
        output_path: Path to the structured.jsonl file.

    Attributes:
        output_path: Resolved Path to the JSONL file.
        _lock: Threading lock for file-write serialization.
    """

    # Custom log level for events (between INFO=20 and WARNING=30)
    EVENT_LEVEL = 25

    def __init__(self, output_path: str | Path):
        """Initialize EventStreamRecorder.

        Args:
            output_path: Path to the structured JSONL file.
        """
        super().__init__()
        self.output_path = Path(output_path)
        self._lock = threading.Lock()
        self.logger = logging.getLogger(self.__class__.__name__)

    def on_event(self, event: BaseEvent) -> bool:
        """Serialize an event to the structured JSONL file.

        Converts the event to the shared JSONL schema and appends it
        as a single line. The current LogContext is merged into the
        record so that context fields propagate to events as well.

        Args:
            event: The event to record.

        Returns:
            True on success, False if writing failed.
        """
        # Track processed events for deduplication
        if hasattr(event, "id"):
            if event.id in self.processed_events_uuids:
                return True
            self.processed_events_uuids.append(event.id)

        try:
            record = self._event_to_jsonl_record(event)
            line = json.dumps(record, default=str)
            with self._lock:
                with open(self.output_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
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
        """Return low priority so business observers run first.

        Returns:
            Priority value of 10 (low, runs after higher-priority observers).
        """
        return 10
