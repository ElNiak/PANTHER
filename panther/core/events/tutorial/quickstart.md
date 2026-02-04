# Events System Quickstart

This tutorial walks through creating and using events in PANTHER's testing framework.

## Basic Event Creation

### Step 1: Create Your First Event

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from panther.core.events.base.event_base import BaseEvent

# Define event types for your domain
class MyTestEventType(Enum):
    TEST_STARTED = "my_test.started"
    TEST_COMPLETED = "my_test.completed"

# Create event class
@dataclass(frozen=True)
class MyTestStartedEvent(BaseEvent):
    """Event when a custom test starts."""
    test_name: str
    start_time: datetime

    def __post_init__(self):
        object.__setattr__(self, 'event_type', MyTestEventType.TEST_STARTED)
        super().__post_init__()

# Create an event
event = MyTestStartedEvent(
    entity_type="custom_test",
    entity_id="test-001",
    test_name="Connection Test",
    start_time=datetime.now()
)

print(f"Created event: {event.event_type}")
print(f"Event UUID: {event.uuid}")
```

### Step 2: Create an Event Emitter

```python
from panther.core.events.base.event_emitter_base import EntityEventEmitterBase

class MyTestEmitter(EntityEventEmitterBase[MyTestEventType]):
    """Emitter for custom test events."""

    def __init__(self, test_id: str):
        super().__init__(test_id, "custom_test")

    def emit_test_started(self, test_name: str):
        """Emit test started event."""
        event = MyTestStartedEvent(
            entity_id=self.entity_id,
            test_name=test_name,
            start_time=datetime.now()
        )
        self.emit_event(event)

    def emit_test_completed(self, test_name: str, duration: float):
        """Emit test completed event."""
        event = MyTestCompletedEvent(
            entity_id=self.entity_id,
            test_name=test_name,
            end_time=datetime.now(),
            duration=duration
        )
        self.emit_event(event)

# Use the emitter
emitter = MyTestEmitter("test-001")
emitter.emit_test_started("Connection Test")
```

## Working with State Management

### Step 3: Create State Manager

```python
from enum import Enum
from panther.core.events.base.state_base import StateManager

class MyTestState(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# Define valid state transitions
transitions = {
    MyTestState.CREATED: [MyTestState.RUNNING],
    MyTestState.RUNNING: [MyTestState.COMPLETED, MyTestState.FAILED],
    MyTestState.COMPLETED: [],  # Terminal state
    MyTestState.FAILED: []      # Terminal state
}

# Create state manager
state_manager = StateManager(
    initial_state=MyTestState.CREATED,
    valid_transitions=transitions
)

# Try state transitions
print(f"Initial state: {state_manager.current_state}")

success = state_manager.transition_to(MyTestState.RUNNING)
print(f"Transition to RUNNING: {success}")  # True

success = state_manager.transition_to(MyTestState.CREATED)
print(f"Invalid transition back: {success}")  # False

success = state_manager.transition_to(MyTestState.COMPLETED)
print(f"Transition to COMPLETED: {success}")  # True
```

## Creating Complete Event Workflow

### Step 4: Complete Test Example

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any
from panther.core.events.base.event_base import BaseEvent
from panther.core.events.base.event_emitter_base import EntityEventEmitterBase

# Complete event type definition
class QuickTestEventType(Enum):
    TEST_CREATED = "quick_test.created"
    TEST_STARTED = "quick_test.started"
    TEST_COMPLETED = "quick_test.completed"
    TEST_FAILED = "quick_test.failed"

# Event classes
@dataclass(frozen=True)
class QuickTestEvent(BaseEvent):
    """Base event for quick test tutorial."""
    test_name: str
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class QuickTestCreatedEvent(QuickTestEvent):
    """Event when test is created."""
    creation_time: datetime

    def __post_init__(self):
        object.__setattr__(self, 'event_type', QuickTestEventType.TEST_CREATED)
        super().__post_init__()

@dataclass(frozen=True)
class QuickTestStartedEvent(QuickTestEvent):
    """Event when test execution starts."""
    start_time: datetime

    def __post_init__(self):
        object.__setattr__(self, 'event_type', QuickTestEventType.TEST_STARTED)
        super().__post_init__()

@dataclass(frozen=True)
class QuickTestCompletedEvent(QuickTestEvent):
    """Event when test completes successfully."""
    end_time: datetime
    duration: float
    results: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, 'event_type', QuickTestEventType.TEST_COMPLETED)
        super().__post_init__()

@dataclass(frozen=True)
class QuickTestFailedEvent(QuickTestEvent):
    """Event when test fails."""
    failure_time: datetime
    error_message: str
    error_type: str = "unknown"

    def __post_init__(self):
        object.__setattr__(self, 'event_type', QuickTestEventType.TEST_FAILED)
        super().__post_init__()

# Complete emitter
class QuickTestEmitter(EntityEventEmitterBase[QuickTestEventType]):
    """Complete emitter for tutorial test events."""

    def __init__(self, test_id: str):
        super().__init__(test_id, "quick_test")
        self.start_time = None

    def emit_created(self, test_name: str, config: Dict[str, Any] = None):
        """Emit test created event."""
        event = QuickTestCreatedEvent(
            entity_id=self.entity_id,
            test_name=test_name,
            config=config or {},
            creation_time=datetime.now()
        )
        self.emit_event(event)

    def emit_started(self, test_name: str, config: Dict[str, Any] = None):
        """Emit test started event."""
        self.start_time = datetime.now()
        event = QuickTestStartedEvent(
            entity_id=self.entity_id,
            test_name=test_name,
            config=config or {},
            start_time=self.start_time
        )
        self.emit_event(event)

    def emit_completed(self, test_name: str, results: Dict[str, Any] = None):
        """Emit test completed event."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds() if self.start_time else 0

        event = QuickTestCompletedEvent(
            entity_id=self.entity_id,
            test_name=test_name,
            config={},
            end_time=end_time,
            duration=duration,
            results=results or {}
        )
        self.emit_event(event)

    def emit_failed(self, test_name: str, error_message: str, error_type: str = "unknown"):
        """Emit test failed event."""
        event = QuickTestFailedEvent(
            entity_id=self.entity_id,
            test_name=test_name,
            config={},
            failure_time=datetime.now(),
            error_message=error_message,
            error_type=error_type
        )
        self.emit_event(event)

# Run complete example
def run_test_workflow():
    """Run a complete test workflow with events."""
    emitter = QuickTestEmitter("tutorial-test-001")

    # Test lifecycle
    print("=== Starting Test Lifecycle ===")

    # 1. Create test
    emitter.emit_created("Tutorial Connection Test", {
        "timeout": 30,
        "retry_count": 3
    })
    print("✓ Test created")

    # 2. Start test
    emitter.emit_started("Tutorial Connection Test", {
        "timeout": 30,
        "retry_count": 3
    })
    print("✓ Test started")

    # Simulate test execution
    import time
    time.sleep(1)  # Simulate test work

    # 3. Complete test (or fail)
    import random
    if random.choice([True, False]):
        emitter.emit_completed("Tutorial Connection Test", {
            "packets_sent": 100,
            "packets_received": 98,
            "success_rate": 0.98
        })
        print("✓ Test completed successfully")
    else:
        emitter.emit_failed("Tutorial Connection Test",
                          "Connection timeout after 30 seconds",
                          "timeout_error")
        print("✗ Test failed")

# Run the example
if __name__ == "__main__":
    run_test_workflow()
```

## Event Deduplication Example

### Step 5: Understanding Event Deduplication

```python
from panther.core.events.base.event_base import create_content_based_uuid

# Create identical events
event1 = QuickTestStartedEvent(
    entity_id="test-123",
    test_name="Dedup Test",
    config={"param": "value"},
    start_time=datetime(2025, 1, 1, 12, 0, 0)
)

event2 = QuickTestStartedEvent(
    entity_id="test-123",
    test_name="Dedup Test",
    config={"param": "value"},
    start_time=datetime(2025, 1, 1, 12, 0, 0)
)

print(f"Event 1 UUID: {event1.uuid}")
print(f"Event 2 UUID: {event2.uuid}")
print(f"UUIDs match: {event1.uuid == event2.uuid}")  # True - same content

# Create different event
event3 = QuickTestStartedEvent(
    entity_id="test-456",  # Different entity_id
    test_name="Dedup Test",
    config={"param": "value"},
    start_time=datetime(2025, 1, 1, 12, 0, 0)
)

print(f"Event 3 UUID: {event3.uuid}")
print(f"Event 1 vs 3 match: {event1.uuid == event3.uuid}")  # False - different content
```

## Next Steps

### Integration with Observers

Once you've created events, you'll want to process them with observers:

```python
# See observer tutorial for processing these events
from panther.core.observer.base.observer_interface import IObserver

class TutorialObserver(IObserver):
    def is_interested(self, event_type: str) -> bool:
        return event_type.startswith("quick_test.")

    def on_event(self, event):
        print(f"Observed: {event.event_type} for {event.entity_id}")

# Register observer with event manager
# (See observer module documentation for details)
```

### Advanced Features

- **Batch Events**: Create events that contain multiple data points
- **Error Events**: Standardized error event patterns
- **Metrics Integration**: Events that trigger metrics collection
- **State Coordination**: Events that drive state machine transitions

### Best Practices

1. **Event Granularity**: Create events for meaningful state changes, not every operation
2. **Immutability**: Always use `frozen=True` dataclass for events
3. **Type Safety**: Use enums for event types to prevent typos
4. **Documentation**: Include docstrings with usage examples
5. **Testing**: Write tests for event creation and emission logic

This tutorial covers the basics of PANTHER's event system. See the full API reference for comprehensive details on all event types and advanced features.
