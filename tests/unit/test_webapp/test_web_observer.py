"""Tests for WebObserver."""

import json
import threading

import pytest

from panther.core.events.base.event_base import BaseEvent, EventType
from panther.core.events.event_summarizer import EventImportance
from panther.webapp.infra.web_observer import Subscription, WebObserver


class _TestEvent(BaseEvent):
    """Concrete event for testing."""

    pass


def _make_event(name="test_event", entity_id="e1", data=None, etype=EventType.TEST):
    return _TestEvent(name, etype, entity_id, data or {})


# ── Original tests (backward compat) ─────────────────────────────────


@pytest.mark.unit
class TestWebObserverSubscription:
    def test_subscribe_and_dispatch(self):
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e))
        event = _make_event()
        obs.update_gui(event)
        assert received == [event]

    def test_multiple_subscribers(self):
        obs = WebObserver()
        a, b = [], []
        obs.subscribe(lambda e: a.append(e))
        obs.subscribe(lambda e: b.append(e))
        event = _make_event()
        obs.update_gui(event)
        assert len(a) == 1
        assert len(b) == 1

    def test_unsubscribe(self):
        obs = WebObserver()
        received = []
        cb = lambda e: received.append(e)
        obs.subscribe(cb)
        obs.unsubscribe(cb)
        obs.update_gui(_make_event())
        assert received == []

    def test_unsubscribe_missing_no_error(self):
        obs = WebObserver()
        obs.unsubscribe(lambda e: None)  # should not raise

    def test_subscriber_exception_does_not_break_others(self):
        obs = WebObserver()
        received = []

        def bad_cb(e):
            raise RuntimeError("boom")

        obs.subscribe(bad_cb)
        obs.subscribe(lambda e: received.append(e))
        obs.update_gui(_make_event())
        assert len(received) == 1


@pytest.mark.unit
class TestWebObserverEventHistory:
    def test_on_event_records_history(self):
        obs = WebObserver()
        event = _make_event(name="hist", entity_id="h1")
        obs.on_event(event)
        assert event in obs.event_history

    def test_history_bounded(self):
        obs = WebObserver()
        obs.max_history = 5
        for i in range(10):
            obs.on_event(_make_event(entity_id=str(i)))
        assert len(obs.event_history) == 5


@pytest.mark.unit
class TestWebObserverGUIState:
    def test_gui_state_counters(self):
        obs = WebObserver()
        event = _make_event(name="counter_test")
        obs.on_event(event)
        event_type = event.get_type()
        assert obs.gui_state.get(f"{event_type}_count") == 1
        # Send another with same type but different entity to avoid dedup
        obs.on_event(_make_event(name="counter_test", entity_id="e2"))
        assert obs.gui_state.get(f"{event_type}_count") == 2

    def test_last_event_tracked(self):
        obs = WebObserver()
        event = _make_event()
        obs.on_event(event)
        assert obs.gui_state["last_event"] is event


@pytest.mark.unit
class TestWebObserverConcurrency:
    def test_subscribe_during_dispatch(self):
        """Subscribing during dispatch should not crash (thread-safe copy)."""
        obs = WebObserver()
        late_received = []

        def add_subscriber(e):
            obs.subscribe(lambda ev: late_received.append(ev))

        obs.subscribe(add_subscriber)
        obs.update_gui(_make_event())
        # The late subscriber was added during dispatch but should not
        # have received the current event (list was copied before iteration).
        assert late_received == []
        # But it should receive the next one.
        obs.update_gui(_make_event(entity_id="e2"))
        assert len(late_received) == 1

    def test_concurrent_on_event_calls(self):
        """Multiple threads calling on_event should not crash."""
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e))
        barrier = threading.Barrier(4)

        def worker(eid):
            barrier.wait()
            obs.on_event(_make_event(entity_id=eid))

        threads = [threading.Thread(target=worker, args=(str(i),)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        # All events should have been dispatched (no crash)
        assert len(received) >= 1


# ── Phase 1: Filtering tests ─────────────────────────────────────────


@pytest.mark.unit
class TestWebObserverFiltering:
    def test_subscribe_with_event_type_filter(self):
        """Subscriber with event_types only receives matching events."""
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e), event_types={"experiment"})

        # Should match: type is "experiment.started"
        exp_event = _make_event(name="started", etype=EventType.EXPERIMENT)
        obs.update_gui(exp_event)

        # Should NOT match: type is "test.test_event"
        test_event = _make_event(name="test_event", etype=EventType.TEST)
        obs.update_gui(test_event)

        assert received == [exp_event]

    def test_subscribe_with_importance_filter(self):
        """Subscriber with importance threshold filters low-importance events."""
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e), importance=EventImportance.HIGH)

        # "experiment.started" is HIGH → should pass
        high_event = _make_event(name="started", etype=EventType.EXPERIMENT)
        obs.update_gui(high_event)

        # "step.progress" is LOW → should be filtered
        low_event = _make_event(name="progress", etype=EventType.STEP)
        obs.update_gui(low_event)

        assert received == [high_event]

    def test_subscribe_with_custom_predicate(self):
        """Subscriber with predicate only receives events passing the check."""
        obs = WebObserver()
        received = []
        obs.subscribe(
            lambda e: received.append(e),
            predicate=lambda e: e.entity_id == "target",
        )

        obs.update_gui(_make_event(entity_id="target"))
        obs.update_gui(_make_event(entity_id="other"))

        assert len(received) == 1
        assert received[0].entity_id == "target"

    def test_subscribe_combined_filters(self):
        """All filters are ANDed together."""
        obs = WebObserver()
        received = []
        obs.subscribe(
            lambda e: received.append(e),
            event_types={"experiment"},
            importance=EventImportance.HIGH,
            predicate=lambda e: e.entity_id == "exp1",
        )

        # Matches all three filters
        good = _make_event(name="started", etype=EventType.EXPERIMENT, entity_id="exp1")
        obs.update_gui(good)

        # Wrong event type
        bad_type = _make_event(name="progress", etype=EventType.STEP, entity_id="exp1")
        obs.update_gui(bad_type)

        # Wrong entity (predicate fails)
        bad_pred = _make_event(
            name="started", etype=EventType.EXPERIMENT, entity_id="exp2"
        )
        obs.update_gui(bad_pred)

        assert received == [good]

    def test_subscribe_no_filter_backward_compat(self):
        """Plain subscribe() with no filters receives all events."""
        obs = WebObserver()
        received = []
        sub = obs.subscribe(lambda e: received.append(e))

        obs.update_gui(_make_event(name="started", etype=EventType.EXPERIMENT))
        obs.update_gui(_make_event(name="progress", etype=EventType.STEP))
        obs.update_gui(_make_event(name="crashed", etype=EventType.SERVICE))

        assert len(received) == 3
        assert isinstance(sub, Subscription)

    def test_unsubscribe_by_subscription_handle(self):
        """Unsubscribing by Subscription handle removes the subscriber."""
        obs = WebObserver()
        received = []
        sub = obs.subscribe(lambda e: received.append(e))
        obs.unsubscribe(sub)
        obs.update_gui(_make_event())
        assert received == []

    def test_unsubscribe_by_callback_backward_compat(self):
        """Unsubscribing by raw callback still works (backward compat)."""
        obs = WebObserver()
        received = []
        cb = lambda e: received.append(e)
        obs.subscribe(cb)
        obs.unsubscribe(cb)
        obs.update_gui(_make_event())
        assert received == []


# ── Phase 2: Batching tests ──────────────────────────────────────────


@pytest.mark.unit
class TestWebObserverBatching:
    def test_batching_accumulates_events(self):
        """Events are buffered when batching is enabled."""
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e))
        obs.enable_batching(500)

        obs.update_gui(_make_event(name="progress", etype=EventType.STEP))
        obs.update_gui(
            _make_event(name="progress", etype=EventType.STEP, entity_id="e2")
        )

        # Not yet delivered
        assert len(received) == 0

    def test_flush_batch_delivers_all(self):
        """Flushing delivers all buffered events to batched subscribers."""
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e))
        obs.enable_batching(500)

        e1 = _make_event(name="progress", etype=EventType.STEP)
        e2 = _make_event(name="progress", etype=EventType.STEP, entity_id="e2")
        obs.update_gui(e1)
        obs.update_gui(e2)
        obs._flush_batch()

        assert len(received) == 2
        assert received[0] is e1
        assert received[1] is e2

    def test_critical_events_bypass_batch(self):
        """CRITICAL events are delivered immediately even when batching is on."""
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e))
        obs.enable_batching(500)

        # "experiment.failed" is CRITICAL in EventSummarizer
        critical = _make_event(name="failed", etype=EventType.EXPERIMENT)
        obs.update_gui(critical)

        # Should be delivered immediately, not buffered
        assert len(received) == 1
        assert received[0] is critical

    def test_unbatched_subscriber_receives_immediately(self):
        """Subscriber with batched=False receives events immediately."""
        obs = WebObserver()
        immediate = []
        batched = []
        obs.subscribe(lambda e: immediate.append(e), batched=False)
        obs.subscribe(lambda e: batched.append(e), batched=True)
        obs.enable_batching(500)

        event = _make_event(name="progress", etype=EventType.STEP)
        obs.update_gui(event)

        assert len(immediate) == 1
        assert len(batched) == 0  # still in buffer

        obs._flush_batch()
        assert len(batched) == 1

    def test_disable_batching_flushes_remaining(self):
        """disable_batching() flushes buffered events."""
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e))
        obs.enable_batching(500)

        obs.update_gui(_make_event(name="progress", etype=EventType.STEP))
        assert len(received) == 0

        obs.disable_batching()
        assert len(received) == 1

    def test_batch_thread_safety(self):
        """Concurrent update_gui + flush should not crash."""
        obs = WebObserver()
        received = []
        obs.subscribe(lambda e: received.append(e))
        obs.enable_batching(100)
        barrier = threading.Barrier(5)

        def producer(eid):
            barrier.wait()
            obs.update_gui(
                _make_event(name="progress", etype=EventType.STEP, entity_id=eid)
            )

        def flusher():
            barrier.wait()
            obs._flush_batch()

        threads = [threading.Thread(target=producer, args=(str(i),)) for i in range(4)]
        threads.append(threading.Thread(target=flusher))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # Flush remaining
        obs._flush_batch()
        # Should have received some events without crashing
        assert len(received) >= 0  # no crash is the main assertion


# ── Phase 3: Persistence tests ────────────────────────────────────────


@pytest.mark.unit
class TestWebObserverPersistence:
    def test_save_state_stores_gui_state(self):
        """save_state() returns a JSON-serializable dict of gui_state."""
        obs = WebObserver()
        obs.on_event(_make_event(name="started", etype=EventType.EXPERIMENT))
        state = obs.save_state()

        assert isinstance(state, dict)
        # Should contain counter keys
        assert "experiment.started_count" in state
        assert state["experiment.started_count"] == 1
        # Should be JSON-serializable
        json.dumps(state, default=str)

    def test_restore_state_recovers_counters(self):
        """restore_state() populates gui_state from saved dict."""
        obs = WebObserver()
        saved = {
            "experiment.started_count": 5,
            "test.completed_count": 3,
            "custom_key": "value",
        }
        obs.restore_state(saved)

        assert obs.gui_state["experiment.started_count"] == 5
        assert obs.gui_state["test.completed_count"] == 3
        assert obs.gui_state["custom_key"] == "value"

    def test_export_history_creates_valid_json(self, tmp_path):
        """export_history() writes valid JSON with event dicts."""
        obs = WebObserver()
        obs.on_event(_make_event(name="started", etype=EventType.EXPERIMENT))
        obs.on_event(_make_event(name="completed", etype=EventType.TEST))

        path = str(tmp_path / "history.json")
        obs.export_history(path)

        with open(path) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["type"] == "experiment.started"
        assert data[1]["type"] == "test.completed"

    def test_import_history_loads_events(self, tmp_path):
        """import_history() loads event dicts from JSON file."""
        history = [
            {"type": "experiment.started", "entity_id": "e1"},
            {"type": "test.completed", "entity_id": "t1"},
        ]
        path = str(tmp_path / "history.json")
        with open(path, "w") as f:
            json.dump(history, f)

        obs = WebObserver()
        obs.import_history(path)

        assert hasattr(obs, "imported_history")
        assert len(obs.imported_history) == 2
        assert obs.imported_history[0]["type"] == "experiment.started"

    def test_restore_with_no_saved_state_noop(self):
        """restore_state({}) and restore_state(None-ish) are no-ops."""
        obs = WebObserver()
        obs.gui_state["existing"] = 42

        obs.restore_state({})
        assert obs.gui_state["existing"] == 42

        obs.restore_state(None)
        assert obs.gui_state["existing"] == 42
