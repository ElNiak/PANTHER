# Task 10: Extract Event Types to panther-types

## Goal
Extract `BaseEvent`, `EventType`, `create_content_based_uuid`, `create_event_signature` from `event_base.py` and `BaseState`, `StateTransition`, `StateManager` from `state_base.py` into panther-types.

## Prerequisites
- Task 06 completed (package scaffolded)

## Source Files
- `panther/core/events/base/event_base.py` (246 lines) - self-contained, no panther imports
- `panther/core/events/base/state_base.py` (182 lines) - self-contained, no panther imports

## Context
Both files are fully self-contained with only stdlib imports (hashlib, uuid, datetime, enum, abc, logging). They form the event system foundation and are needed by panther_web for event streaming.

## Steps

### Step 1: Create panther_types/events/base.py

Read the full source of `event_base.py` and copy everything:

```python
# packages/panther-types/panther_types/events/base.py
"""Event system base types.

Provides the foundation for PANTHER's event-driven architecture:
- BaseEvent: Abstract base class for all events
- EventType: Enum for event categories
- Utility functions for event deduplication
"""
```

Copy from `panther/core/events/base/event_base.py`:
- `create_content_based_uuid()` function (lines 15-33)
- `create_event_signature()` function (lines 36-59)
- `EventType` enum (lines 62-73)
- `BaseEvent` class (lines 76-245)

All imports are stdlib only: `hashlib`, `uuid`, `abc`, `datetime`, `enum`, `typing`.

### Step 2: Create panther_types/events/state.py

Read the full source of `state_base.py` and copy everything:

```python
# packages/panther-types/panther_types/events/state.py
"""State management types.

Provides base classes for entity state management with allowed transitions,
history tracking, and state validation.
"""
```

Copy from `panther/core/events/base/state_base.py`:
- `BaseState` enum class (lines 14-24)
- `StateTransition` class (lines 27-45)
- `StateManager` ABC (lines 48-181)

All imports are stdlib only: `logging`, `abc`, `datetime`, `enum`, `typing`.

### Step 3: Update __init__.py

```python
# packages/panther-types/panther_types/events/__init__.py
"""Event system base types."""
from panther_types.events.base import (
    BaseEvent,
    EventType,
    create_content_based_uuid,
    create_event_signature,
)
from panther_types.events.state import BaseState, StateManager, StateTransition

__all__ = [
    "BaseEvent",
    "EventType",
    "create_content_based_uuid",
    "create_event_signature",
    "BaseState",
    "StateManager",
    "StateTransition",
]
```

### Step 4: Write tests

```python
# packages/panther-types/tests/test_events.py
"""Tests for event base types."""
from datetime import datetime
from enum import Enum

from panther_types.events.base import (
    BaseEvent,
    EventType,
    create_content_based_uuid,
    create_event_signature,
)
from panther_types.events.state import BaseState, StateManager, StateTransition


class TestEventType:
    def test_values(self):
        assert EventType.EXPERIMENT is not None
        assert EventType.TEST is not None
        assert EventType.SERVICE is not None
        assert EventType.SYSTEM is not None

    def test_is_enum(self):
        assert isinstance(EventType.EXPERIMENT, EventType)


class TestCreateContentBasedUuid:
    def test_deterministic(self):
        uuid1 = create_content_based_uuid("same content")
        uuid2 = create_content_based_uuid("same content")
        assert uuid1 == uuid2

    def test_different_content(self):
        uuid1 = create_content_based_uuid("content a")
        uuid2 = create_content_based_uuid("content b")
        assert uuid1 != uuid2


class TestCreateEventSignature:
    def test_creates_signature(self):
        sig = create_event_signature("test_event", "test", "test-1")
        assert isinstance(sig, str)
        assert len(sig) > 0


class ConcreteEvent(BaseEvent):
    """Concrete event for testing."""

    def __init__(self, name="test", **kwargs):
        super().__init__(
            name=name,
            event_type=EventType.TEST,
            entity_type="test",
            entity_id="test-1",
            **kwargs
        )


class TestBaseEvent:
    def test_create(self):
        e = ConcreteEvent()
        assert e.get_type() == EventType.TEST

    def test_has_timestamp(self):
        e = ConcreteEvent()
        ts = e.get_timestamp()
        assert isinstance(ts, datetime)

    def test_has_event_id(self):
        e = ConcreteEvent()
        assert e.event_id is not None
        assert len(e.event_id) > 0

    def test_to_dict(self):
        e = ConcreteEvent()
        d = e.to_dict()
        assert "event_type" in d
        assert "timestamp" in d

    def test_add_data(self):
        e = ConcreteEvent()
        e.add_data("key", "value")
        assert e.get_data().get("key") == "value"

    def test_duplicate_detection(self):
        e1 = ConcreteEvent(name="same")
        e2 = ConcreteEvent(name="same")
        # Events with same content should be detected as duplicates
        assert e1.is_duplicate_of(e2)


class TestState(BaseState):
    """Concrete state for testing."""
    INIT = "init"
    RUNNING = "running"
    DONE = "done"


class ConcreteStateManager(StateManager):
    """Concrete state manager for testing."""

    def _define_allowed_transitions(self):
        return {
            TestState.INIT: {TestState.RUNNING},
            TestState.RUNNING: {TestState.DONE},
            TestState.DONE: set(),
        }


class TestStateTransition:
    def test_create(self):
        t = StateTransition(
            from_state=TestState.INIT,
            to_state=TestState.RUNNING,
            reason="starting"
        )
        assert str(t) is not None


class TestStateManager:
    def test_initial_state(self):
        mgr = ConcreteStateManager(entity_id="test-1", initial_state=TestState.INIT)
        assert mgr.get_current_state() == TestState.INIT

    def test_transition(self):
        mgr = ConcreteStateManager(entity_id="test-1", initial_state=TestState.INIT)
        mgr.transition_to(TestState.RUNNING, reason="go")
        assert mgr.get_current_state() == TestState.RUNNING

    def test_invalid_transition(self):
        mgr = ConcreteStateManager(entity_id="test-1", initial_state=TestState.INIT)
        # INIT -> DONE is not allowed
        try:
            mgr.transition_to(TestState.DONE, reason="skip")
            assert False, "Should have raised"
        except (ValueError, Exception):
            pass

    def test_history(self):
        mgr = ConcreteStateManager(entity_id="test-1", initial_state=TestState.INIT)
        mgr.transition_to(TestState.RUNNING, reason="go")
        history = mgr.get_state_history()
        assert len(history) >= 1

    def test_can_transition_to(self):
        mgr = ConcreteStateManager(entity_id="test-1", initial_state=TestState.INIT)
        assert mgr.can_transition_to(TestState.RUNNING) is True
        assert mgr.can_transition_to(TestState.DONE) is False
```

## Verification
```bash
cd packages/panther-types
pytest tests/test_events.py -v
```

## Important Notes
- Both source files are self-contained with zero panther imports. This is the cleanest extraction in Phase 2.
- `BaseEvent.__init__` generates UUIDs. Verify the UUID generation logic matches the source.
- `StateManager._define_allowed_transitions()` is abstract - verify the abc pattern.
- `BaseState` is an abstract Enum base class. Check if it uses `Enum` or `str, Enum`.

## Commit Message
```
feat(panther-types): extract event and state management types

Move BaseEvent, EventType, BaseState, StateTransition, and StateManager
from panther/core/events/base/ into panther-types. These are the
foundation for PANTHER's event-driven architecture.
```

## Files Modified
- `packages/panther-types/panther_types/events/base.py` (new)
- `packages/panther-types/panther_types/events/state.py` (new)
- `packages/panther-types/panther_types/events/__init__.py` (updated)
- `packages/panther-types/tests/test_events.py` (new)
