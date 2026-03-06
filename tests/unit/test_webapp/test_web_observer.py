"""Tests for WebObserver."""

import threading

import pytest

from panther.core.events.base.event_base import BaseEvent, EventType
from panther.webapp.services.web_observer import WebObserver


class _TestEvent(BaseEvent):
    """Concrete event for testing."""

    pass


def _make_event(name="test_event", entity_id="e1", data=None):
    return _TestEvent(name, EventType.TEST, entity_id, data or {})


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
