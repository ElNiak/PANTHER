# Events Module Developer Guide

## Development Environment Setup

### Prerequisites
- Python 3.8+ with type checking support
- Poetry or pip for dependency management
- pytest for testing
- mypy for static type checking

### Installation
```bash
# Install development dependencies
pip install -e ".[dev]"

# Install type checking tools
pip install mypy pytest-cov

# Verify installation
python -c "from panther.core.events import BaseEvent; print('Events module ready')"
```

### IDE Configuration
Configure your IDE for optimal development:

**VS Code**
```json
{
    "python.linting.mypyEnabled": true,
    "python.linting.enabled": true,
    "python.testing.pytestEnabled": true
}
```

**PyCharm**
- Enable type checking inspections
- Configure pytest as test runner
- Set up auto-formatting with Black

## Development Workflow

### Creating New Event Types

#### 1. Define Event Enum
```python
# In events.py
class MyEventType(Enum):
    MY_EVENT_STARTED = "my_event.started"
    MY_EVENT_COMPLETED = "my_event.completed"
    MY_EVENT_FAILED = "my_event.failed"
```

#### 2. Create Event Classes
```python
@dataclass(frozen=True)
class MyEvent(BaseEvent):
    """Base class for my domain events.

    Requires:
        entity_type is set to appropriate domain
        event_type is from MyEventType enum

    Ensures:
        Immutable event structure
        Content-based UUID generation
        Timestamp preservation
    """

    def __post_init__(self):
        super().__post_init__()
        # Domain-specific validation

@dataclass(frozen=True)
class MyEventStartedEvent(MyEvent):
    """Event emitted when my operation starts.

    Args:
        entity_id: Unique identifier for the entity
        context: Additional context information

    Example:
        >>> event = MyEventStartedEvent(
        ...     entity_id="test-123",
        ...     context={"param": "value"}
        ... )
        >>> assert event.event_type == MyEventType.MY_EVENT_STARTED
    """
    context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, 'event_type', MyEventType.MY_EVENT_STARTED)
        super().__post_init__()
```

#### 3. Create State Manager
```python
class MyState(Enum):
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    FAILED = "failed"

class MyStateManager(StateManager[MyState]):
    """Manages state transitions for my domain entities."""

    def __init__(self):
        transitions = {
            MyState.INACTIVE: [MyState.STARTING],
            MyState.STARTING: [MyState.ACTIVE, MyState.FAILED],
            MyState.ACTIVE: [MyState.FAILED],
            MyState.FAILED: []
        }
        super().__init__(MyState.INACTIVE, transitions)
```

#### 4. Create Event Emitter
```python
class MyEventEmitter(EntityEventEmitterBase[MyEventType]):
    """Emits events for my domain entities."""

    def __init__(self, entity_id: str):
        super().__init__(entity_id, "my_domain")

    def emit_started(self, context: Dict[str, Any] = None):
        """Emit event when operation starts.

        Args:
            context: Additional context for the event

        Example:
            >>> emitter = MyEventEmitter("entity-123")
            >>> emitter.emit_started({"param": "value"})
        """
        event = MyEventStartedEvent(
            entity_id=self.entity_id,
            context=context or {}
        )
        self.emit_event(event)
```

### Testing Guidelines

#### Unit Tests
```python
# test_my_events.py
import pytest
from panther.core.events.my.events import MyEventStartedEvent, MyEventType

def test_my_event_creation():
    """Test basic event creation and properties."""
    event = MyEventStartedEvent(
        entity_id="test-123",
        context={"key": "value"}
    )

    assert event.entity_id == "test-123"
    assert event.event_type == MyEventType.MY_EVENT_STARTED
    assert event.context["key"] == "value"
    assert event.uuid  # Should have generated UUID

def test_my_event_immutability():
    """Test that events cannot be modified after creation."""
    event = MyEventStartedEvent(entity_id="test-123")

    with pytest.raises(FrozenInstanceError):
        event.entity_id = "modified"

def test_my_event_deduplication():
    """Test content-based UUID generation for deduplication."""
    event1 = MyEventStartedEvent(entity_id="test-123", context={"a": 1})
    event2 = MyEventStartedEvent(entity_id="test-123", context={"a": 1})

    assert event1.uuid == event2.uuid  # Same content = same UUID
```

#### Integration Tests
```python
def test_my_event_emitter_integration():
    """Test event emitter with real observer."""
    from panther.core.observer.management.event_manager import get_event_manager

    events_received = []

    class TestObserver:
        def on_event(self, event):
            events_received.append(event)

        def is_interested(self, event_type: str) -> bool:
            return event_type.startswith("my_event.")

    manager = get_event_manager()
    observer = TestObserver()
    manager.register_observer(observer)

    emitter = MyEventEmitter("test-entity")
    emitter.emit_started({"test": True})

    assert len(events_received) == 1
    assert events_received[0].entity_id == "test-entity"
```

### Debugging Events

#### Enable Debug Logging
```python
import logging
logging.getLogger('panther.core.events').setLevel(logging.DEBUG)
```

#### Event Inspector Utility
```python
def inspect_event(event: BaseEvent):
    """Debug utility to inspect event properties."""
    print(f"Event Type: {event.event_type}")
    print(f"Entity: {event.entity_type}:{event.entity_id}")
    print(f"UUID: {event.uuid}")
    print(f"Timestamp: {event.timestamp}")
    print(f"Data: {event.__dict__}")
```

#### Event Tracing
```python
class EventTracer:
    """Utility to trace event flow through the system."""

    def __init__(self):
        self.events = []

    def trace_event(self, event: BaseEvent):
        self.events.append({
            'timestamp': event.timestamp,
            'type': event.event_type,
            'entity': f"{event.entity_type}:{event.entity_id}",
            'uuid': event.uuid
        })

    def print_trace(self):
        for event in sorted(self.events, key=lambda e: e['timestamp']):
            print(f"{event['timestamp']} - {event['type']} - {event['entity']}")
```

## Quality Assurance

### Code Standards
- All events must inherit from domain base classes
- Use dataclass with frozen=True for immutability
- Include comprehensive docstrings with Args/Returns
- Add type hints for all parameters and return values

### Testing Requirements
- Unit tests for all event classes
- Integration tests for emitters and state managers
- Property-based tests for UUID generation
- Performance tests for high-volume scenarios

### Documentation Standards
- Module docstrings following Google style
- Example usage in all public APIs
- Pre/post-conditions for complex operations
- Complexity notes for performance-critical code

## Performance Guidelines

### Event Design
- Use __slots__ in event classes for memory efficiency
- Minimize data copying in event creation
- Prefer enums over strings for event types
- Design for immutability to enable caching

### Emission Patterns
- Batch related events when possible
- Use async emission for I/O bound operations
- Implement event filtering at source when feasible
- Consider event sampling for high-frequency events

### Memory Management
- Events are automatically garbage collected
- UUID strings are interned for deduplication
- State managers use weak references where appropriate
- Event history has configurable retention policies

## Common Patterns

### Error Event Pattern
```python
@dataclass(frozen=True)
class MyEventFailedEvent(MyEvent):
    """Event for operation failures with error details."""
    error_message: str
    error_type: str
    stack_trace: Optional[str] = None

    def __post_init__(self):
        object.__setattr__(self, 'event_type', MyEventType.MY_EVENT_FAILED)
        super().__post_init__()
```

### Progress Event Pattern
```python
@dataclass(frozen=True)
class MyEventProgressEvent(MyEvent):
    """Event for operation progress updates."""
    progress_percent: float
    current_step: str
    total_steps: int

    def __post_init__(self):
        object.__setattr__(self, 'event_type', MyEventType.MY_EVENT_PROGRESS)
        super().__post_init__()
```

### Batch Event Pattern
```python
@dataclass(frozen=True)
class MyBatchEvent(MyEvent):
    """Event containing multiple related items."""
    items: List[Dict[str, Any]]
    batch_id: str

    def __post_init__(self):
        object.__setattr__(self, 'event_type', MyEventType.MY_BATCH_COMPLETE)
        super().__post_init__()
```

## Troubleshooting

### Common Issues

**Events not appearing in observers**
- Check observer interest filtering
- Verify event manager registration
- Confirm event type enum values

**Memory usage growing**
- Check for observer reference leaks
- Review event retention policies
- Monitor UUID deduplication effectiveness

**Performance degradation**
- Profile event creation overhead
- Analyze observer processing times
- Check for synchronous I/O in event handlers

### Debug Commands
```bash
# Run tests with coverage
pytest --cov=panther.core.events tests/unit/test_events/

# Type check the module
mypy panther/core/events/

# Profile event creation
python -m cProfile -s cumulative test_event_performance.py

# Validate event schemas
python scripts/validate_event_schemas.py
```
