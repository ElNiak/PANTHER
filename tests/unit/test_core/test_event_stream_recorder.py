"""Unit tests for EventStreamRecorder."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from panther.core.events.base.event_base import BaseEvent, EventType
from panther.core.observer.impl.event_stream_recorder import EventStreamRecorder
from panther.core.utils.log_context import log_context

# -- Concrete event subclass for tests (BaseEvent is abstract) ----------------


class _TestEvent(BaseEvent):
    """Minimal concrete BaseEvent for testing."""

    pass


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture()
def tmp_jsonl(tmp_path):
    """Return a fresh path for a structured.jsonl file."""
    return tmp_path / "structured.jsonl"


@pytest.fixture()
def recorder(tmp_jsonl):
    """Return an EventStreamRecorder wired to the tmp path."""
    return EventStreamRecorder(output_path=tmp_jsonl)


def _read_records(path: Path):
    """Read all JSONL records from a file."""
    records = []
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


# -- Tests -------------------------------------------------------------------


@pytest.mark.unit
class TestEventStreamRecorderBasics:
    """Basic write and schema tests."""

    def test_writes_event_to_file(self, recorder, tmp_jsonl):
        """A single event is appended as one JSONL line."""
        event = _TestEvent("started", EventType.TEST, "t1")
        result = recorder.on_event(event)

        assert result is True
        records = _read_records(tmp_jsonl)
        assert len(records) == 1

    def test_record_schema(self, recorder, tmp_jsonl):
        """Verify the JSONL record has the expected top-level keys."""
        event = _TestEvent("execution_started", EventType.TEST, "t1", {"k": "v"})
        recorder.on_event(event)

        record = _read_records(tmp_jsonl)[0]
        assert record["source"] == "event"
        assert record["level"] == "EVENT"
        assert record["level_num"] == 25
        assert record["event_type"] == "test.execution_started"
        assert record["entity_type"] == "test"
        assert record["entity_id"] == "t1"
        assert "ts" in record
        assert "event_id" in record
        assert "message" in record
        assert record["data"] == {"k": "v"}

    def test_null_values_stripped(self, recorder, tmp_jsonl):
        """None-valued context fields are omitted for compactness."""
        event = _TestEvent("started", EventType.TEST, "t1")
        recorder.on_event(event)

        record = _read_records(tmp_jsonl)[0]
        # experiment_id, test_id, service_id, phase should all be absent
        assert "experiment_id" not in record
        assert "test_id" not in record
        assert "service_id" not in record
        assert "phase" not in record

    def test_multiple_events_appended(self, recorder, tmp_jsonl):
        """Multiple events are appended as separate lines."""
        for i in range(5):
            event = _TestEvent(f"step_{i}", EventType.STEP, f"s{i}")
            recorder.on_event(event)

        records = _read_records(tmp_jsonl)
        assert len(records) == 5
        names = [r["event_type"] for r in records]
        assert names == [f"step.step_{i}" for i in range(5)]


@pytest.mark.unit
class TestEventStreamRecorderContext:
    """Verify LogContext fields propagate to event records."""

    def test_context_fields_propagated(self, recorder, tmp_jsonl):
        """log_context() fields appear in the event record."""
        with log_context(experiment_id="exp-1", test_id="t-42", phase="init"):
            event = _TestEvent("created", EventType.TEST, "t-42")
            recorder.on_event(event)

        record = _read_records(tmp_jsonl)[0]
        assert record["experiment_id"] == "exp-1"
        assert record["test_id"] == "t-42"
        assert record["phase"] == "init"

    def test_nested_context(self, recorder, tmp_jsonl):
        """Inner log_context overrides outer for the same key."""
        with log_context(experiment_id="exp-1", phase="init"):
            with log_context(phase="deploy", service_id="svc-a"):
                event = _TestEvent("started", EventType.SERVICE, "svc-a")
                recorder.on_event(event)

        record = _read_records(tmp_jsonl)[0]
        assert record["experiment_id"] == "exp-1"
        assert record["phase"] == "deploy"
        assert record["service_id"] == "svc-a"


@pytest.mark.unit
class TestEventStreamRecorderDeduplication:
    """Events with the same content-based UUID are written only once."""

    def test_duplicate_events_skipped(self, recorder, tmp_jsonl):
        """Sending the same event twice results in only one JSONL line."""
        event = _TestEvent("started", EventType.TEST, "t1", {"k": "v"})
        recorder.on_event(event)
        recorder.on_event(event)  # same object, same id

        records = _read_records(tmp_jsonl)
        assert len(records) == 1


@pytest.mark.unit
class TestEventStreamRecorderThreadSafety:
    """Concurrent writes do not interleave or corrupt the file."""

    def test_concurrent_writes(self, tmp_jsonl):
        """Multiple threads writing simultaneously produce valid JSONL."""
        recorder = EventStreamRecorder(output_path=tmp_jsonl)
        barrier = threading.Barrier(4)

        def _write_events(thread_id):
            barrier.wait()
            for i in range(20):
                event = _TestEvent(
                    f"event_{i}",
                    EventType.TEST,
                    f"thread_{thread_id}_{i}",
                    use_content_uuid=False,
                )
                recorder.on_event(event)

        threads = [threading.Thread(target=_write_events, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        records = _read_records(tmp_jsonl)
        assert len(records) == 80  # 4 threads * 20 events


@pytest.mark.unit
class TestEventStreamRecorderPriority:
    """Observer priority and interest."""

    def test_low_priority(self, recorder):
        """Recorder priority is low (10) so business observers run first."""
        assert recorder.get_priority() == 10

    def test_interested_in_all(self, recorder):
        """Recorder is interested in all event types."""
        assert recorder.is_interested("test.started") is True
        assert recorder.is_interested("experiment.completed") is True
        assert recorder.is_interested("") is True


@pytest.mark.unit
class TestEventStreamRecorderErrorHandling:
    """Graceful handling of write failures."""

    def test_write_failure_returns_false(self, recorder, tmp_jsonl):
        """If the file cannot be opened, on_event returns False."""
        # Make the output path a directory so open() fails
        tmp_jsonl.mkdir(parents=True, exist_ok=True)
        event = _TestEvent("started", EventType.TEST, "t1")
        result = recorder.on_event(event)
        assert result is False

    def test_timestamp_without_timezone(self, recorder, tmp_jsonl):
        """Events with naive timestamps are handled without error."""
        event = _TestEvent("started", EventType.TEST, "t1")
        event.timestamp = datetime(2025, 1, 1, 12, 0, 0)  # naive
        result = recorder.on_event(event)
        assert result is True

        record = _read_records(tmp_jsonl)[0]
        assert "ts" in record
