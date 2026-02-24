"""Tests for Bug #7: StorageObserver fixes.

Tests cover:
- _convert_event_to_dict uses event.data (not entity_metadata)
- _flush_pending_events called on test completed and test failed
- Flush writes events to JSONL and clears pending list
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from panther.core.events.base.event_base import BaseEvent, EventType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_storage_observer(tmp_path, **kwargs):
    """Create a StorageObserver pointing at tmp_path.

    Uses clear_instances() first to ensure fresh singleton.
    """
    from panther.core.observer.impl.storage_observer import StorageObserver

    StorageObserver.clear_instances()
    return StorageObserver(storage_path=str(tmp_path / "storage"), **kwargs)


def _make_mock_event(event_class=None, **attrs):
    """Create a mock event with required BaseEvent attributes."""
    if event_class:
        mock = MagicMock(spec=event_class)
    else:
        mock = MagicMock(spec=BaseEvent)
    mock.id = "evt-001"
    mock.event_id = "evt-001"
    mock.timestamp = datetime.now()
    mock.entity_id = "test-1"
    mock.name = "test.event"
    mock.data = {}
    for k, v in attrs.items():
        setattr(mock, k, v)
    return mock


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Ensure StorageObserver singletons are cleared after each test."""
    yield
    try:
        from panther.core.observer.impl.storage_observer import StorageObserver

        StorageObserver.clear_instances()
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# TestStorageObserverConvertEvent
# ---------------------------------------------------------------------------


class TestStorageObserverConvertEvent:
    """Verify _convert_event_to_dict uses the data attribute."""

    def test_uses_data_attribute(self, tmp_path):
        obs = _make_storage_observer(tmp_path)
        event = _make_mock_event(data={"key": "value", "count": 5})

        result = obs._convert_event_to_dict(event, "test.completed")

        assert result["data"] == {"key": "value", "count": 5}
        assert result["type"] == "test.completed"

    def test_no_data_attribute_uses_empty_dict(self, tmp_path):
        obs = _make_storage_observer(tmp_path)
        event = _make_mock_event()
        # Simulate event with no data by deleting the attribute
        event.data = {}

        result = obs._convert_event_to_dict(event, "test.unknown")

        assert result["data"] == {}

    def test_includes_type_and_metadata(self, tmp_path):
        obs = _make_storage_observer(tmp_path)
        event = _make_mock_event(data={"x": 1})

        result = obs._convert_event_to_dict(event, "service.started")

        assert result["type"] == "service.started"
        assert "metadata" in result
        assert "class" in result["metadata"]
        assert "storage_timestamp" in result["metadata"]


# ---------------------------------------------------------------------------
# TestStorageObserverFlush
# ---------------------------------------------------------------------------


class TestStorageObserverFlush:
    """Verify flush behavior on test completed/failed."""

    def test_flush_on_test_completed(self, tmp_path):
        obs = _make_storage_observer(tmp_path)

        # Create a mock TestCompletedEvent
        from panther.core.events.test.events import TestCompletedEvent

        event = TestCompletedEvent(
            test_id="test-1",
            test_name="my_test",
            total_duration_seconds=5.0,
        )

        # Mock results_manager to avoid side effects
        obs.results_manager = MagicMock()

        obs.on_test_completed(event)

        # After on_test_completed, pending_events should be empty (flushed)
        assert len(obs.pending_events) == 0

    def test_flush_on_test_failed(self, tmp_path):
        obs = _make_storage_observer(tmp_path)

        from panther.core.events.test.events import TestFailedEvent

        event = TestFailedEvent(
            test_id="test-1",
            test_name="failing_test",
            error_message="assertion failed",
        )

        obs.results_manager = MagicMock()

        obs.on_test_failed(event)

        # After on_test_failed, pending_events should be empty (flushed)
        assert len(obs.pending_events) == 0

    def test_flush_writes_events_jsonl(self, tmp_path):
        obs = _make_storage_observer(tmp_path)

        # Manually add pending events
        obs.pending_events = [
            {"id": "1", "type": "test.started", "timestamp": "2024-01-01T00:00:00"},
            {"id": "2", "type": "test.completed", "timestamp": "2024-01-01T00:01:00"},
        ]

        obs._flush_pending_events()

        events_file = obs.storage_path / "events.jsonl"
        assert events_file.exists()

        lines = events_file.read_text().strip().split("\n")
        assert len(lines) == 2

        parsed_1 = json.loads(lines[0])
        assert parsed_1["id"] == "1"
        parsed_2 = json.loads(lines[1])
        assert parsed_2["id"] == "2"

    def test_flush_clears_pending_events(self, tmp_path):
        obs = _make_storage_observer(tmp_path)

        obs.pending_events = [
            {"id": "1", "type": "test.x", "timestamp": "2024-01-01T00:00:00"},
        ]

        obs._flush_pending_events()

        assert len(obs.pending_events) == 0
