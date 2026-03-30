"""Tests for ITypedObserver dispatch routing.

Covers:
- _handler_name_for() convention-based naming
- on_event() type-based dispatch, name-based dispatch, and fallback
- on_event() deduplication via event.id
- is_interested() correctness (no false positives for short strings)
- Error handling in handlers
"""

from unittest.mock import MagicMock

import pytest

from panther.core.events.base.event_base import EventType
from panther.core.events.experiment.events import ExperimentEvent
from panther.core.events.test.events import TestCompletedEvent, TestFailedEvent
from panther.core.observer.base.typed_observer_interface import (
    ITypedObserver,
    _handler_name_for,
)


class ConcreteObserver(ITypedObserver):
    """Minimal concrete observer for testing dispatch."""

    def __init__(self):
        super().__init__()
        self.handled_events = []

    def on_test_completed(self, event):
        self.handled_events.append(("test_completed", event))
        return True

    def on_test_failed(self, event):
        self.handled_events.append(("test_failed", event))
        return True

    def on_experiment_initialized(self, event):
        self.handled_events.append(("experiment_initialized", event))
        return True


@pytest.mark.unit
class TestHandlerNameFor:
    """Tests for the _handler_name_for helper function."""

    def test_convention_fallback(self):
        """Non-overridden entries fall back to on_{prefix}_{name}."""
        result = _handler_name_for(EventType.TEST, "completed")
        assert result == "on_test_completed"

    def test_convention_fallback_experiment(self):
        """Experiment entity type uses 'experiment' prefix."""
        result = _handler_name_for(EventType.EXPERIMENT, "initialized")
        assert result == "on_experiment_initialized"

    def test_convention_fallback_service(self):
        """Service entity type uses 'service' prefix."""
        result = _handler_name_for(EventType.SERVICE, "started")
        assert result == "on_service_started"

    def test_unknown_entity_type_uses_value(self):
        """Unknown entity type falls back to its .value string."""
        result = _handler_name_for(EventType.SYSTEM, "heartbeat")
        assert result == "on_system_heartbeat"

    def test_dot_separated_name_converted_to_underscores(self):
        """Dot-separated event names should convert dots to underscores."""
        result = _handler_name_for(EventType.ENVIRONMENT, "network.setup.started")
        assert result == "on_environment_network_setup_started"


@pytest.mark.unit
class TestOnEventDispatch:
    """Tests for on_event() dispatch routing."""

    def test_type_based_dispatch(self):
        """TestCompletedEvent should route to on_test_completed via type match."""
        obs = ConcreteObserver()
        event = TestCompletedEvent(test_id="t1", test_name="test1")
        result = obs.on_event(event)
        assert result is True
        assert len(obs.handled_events) == 1
        assert obs.handled_events[0][0] == "test_completed"

    def test_type_based_dispatch_failed(self):
        """TestFailedEvent should route to on_test_failed via type match."""
        obs = ConcreteObserver()
        event = TestFailedEvent(test_id="t1", test_name="test1", error_message="err")
        result = obs.on_event(event)
        assert result is True
        assert len(obs.handled_events) == 1
        assert obs.handled_events[0][0] == "test_failed"

    def test_name_based_dispatch(self):
        """Factory-created ExperimentEvent.initialized should route via name-based dispatch."""
        obs = ConcreteObserver()
        event = ExperimentEvent.initialized("exp1", config={"key": "val"})
        result = obs.on_event(event)
        assert result is True
        assert len(obs.handled_events) == 1
        assert obs.handled_events[0][0] == "experiment_initialized"

    def test_fallback_to_unknown_event(self):
        """Events with no matching handler should fall through to on_unknown_event."""
        obs = ConcreteObserver()
        # Create a factory event with a name that has no handler on ConcreteObserver
        event = ExperimentEvent.plugin_loading_started("exp1", plugin_count=5)
        result = obs.on_event(event)
        # on_unknown_event returns True by default
        assert result is True
        # Should NOT appear in handled_events since on_unknown_event doesn't add to it
        assert len(obs.handled_events) == 0

    def test_dedup_via_event_id(self):
        """Same event dispatched twice should be deduplicated on second call."""
        obs = ConcreteObserver()
        event = TestCompletedEvent(test_id="t1", test_name="test1")
        result1 = obs.on_event(event)
        assert result1 is True
        assert len(obs.handled_events) == 1

        # Second dispatch of the same event object should be deduped
        result2 = obs.on_event(event)
        assert result2 is True
        # Handler should NOT be called again
        assert len(obs.handled_events) == 1

    def test_dedup_different_events_not_deduped(self):
        """Two different events should both be dispatched."""
        obs = ConcreteObserver()
        event1 = TestCompletedEvent(test_id="t1", test_name="test1")
        event2 = TestCompletedEvent(test_id="t2", test_name="test2")
        obs.on_event(event1)
        obs.on_event(event2)
        assert len(obs.handled_events) == 2

    def test_handler_exception_returns_false(self):
        """Handler raising an exception should cause on_event to return False."""
        obs = ConcreteObserver()
        # Replace the handler with one that raises
        obs.on_test_completed = MagicMock(side_effect=ValueError("boom"))
        obs._type_handlers[TestCompletedEvent] = obs.on_test_completed
        event = TestCompletedEvent(test_id="t1", test_name="test1")
        result = obs.on_event(event)
        assert result is False

    def test_handler_recursion_error_returns_false(self):
        """RecursionError in a handler should be caught and return False."""
        obs = ConcreteObserver()
        obs.on_test_completed = MagicMock(side_effect=RecursionError("stack overflow"))
        obs._type_handlers[TestCompletedEvent] = obs.on_test_completed
        event = TestCompletedEvent(test_id="t1", test_name="test1")
        result = obs.on_event(event)
        assert result is False


@pytest.mark.unit
class TestIsInterested:
    """Tests for is_interested() correctness."""

    def test_exact_entity_match(self):
        """Exact entity prefix like 'test' should match."""
        obs = ConcreteObserver()
        assert obs.is_interested("test") is True

    def test_entity_prefix_experiment(self):
        """'experiment' should match."""
        obs = ConcreteObserver()
        assert obs.is_interested("experiment") is True

    def test_entity_prefix_service(self):
        """'service' should match."""
        obs = ConcreteObserver()
        assert obs.is_interested("service") is True

    def test_empty_string_no_false_positive(self):
        """Empty string should NOT match (was a false positive before fix)."""
        obs = ConcreteObserver()
        assert obs.is_interested("") is False

    def test_single_char_no_false_positive(self):
        """Single character 'e' should NOT match (was a false positive before fix)."""
        obs = ConcreteObserver()
        assert obs.is_interested("e") is False

    def test_unrelated_string_returns_false(self):
        """Completely unrelated string should not match."""
        obs = ConcreteObserver()
        assert obs.is_interested("zzz_nonexistent") is False

    def test_class_name_match(self):
        """Event class name substring should still match via type handler check."""
        obs = ConcreteObserver()
        # "TestCompletedEvent" contains "testcompleted" when lowered
        assert obs.is_interested("testcompleted") is True

    def test_partial_prefix_match(self):
        """'ste' IS a prefix of 'step' so it should match via startswith."""
        obs = ConcreteObserver()
        # "ste" is a prefix of "step" -> matches via startswith
        assert obs.is_interested("ste") is True

    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        obs = ConcreteObserver()
        assert obs.is_interested("TEST") is True
        assert obs.is_interested("Experiment") is True
