# Events Module API Reference

## Core Classes

### BaseEvent

```python
class BaseEvent(ABC)
```

Foundation class for all events in the PANTHER framework.

**Description:** Provides immutable event structure with content-based UUID generation for deduplication, timestamp tracking, and entity identification.

**Attributes:**
- `entity_type: str` - Type of entity that generated the event
- `entity_id: str` - Unique identifier for the entity
- `event_type: EventType` - Specific event type from domain enum
- `uuid: str` - Content-based UUID for deduplication
- `timestamp: datetime` - Event creation timestamp

**Methods:**

#### `__post_init__()`
Initializes UUID and timestamp after dataclass creation.

**Requires:**
- `entity_type` and `entity_id` must be set
- `event_type` must be from valid enum

**Ensures:**
- UUID generated from event content
- Timestamp set to current time
- Event marked as frozen/immutable

**Example:**
```python
@dataclass(frozen=True)
class CustomEvent(BaseEvent):
    data: Dict[str, Any]

    def __post_init__(self):
        object.__setattr__(self, 'event_type', CustomEventType.CREATED)
        super().__post_init__()

event = CustomEvent(
    entity_type="test",
    entity_id="test-123",
    data={"key": "value"}
)
```

**Complexity:** O(1) for UUID generation, O(n) for content hashing where n is serialized event size.

---

### EventEmitterBase

```python
class EventEmitterBase(ABC)
```

Abstract base class for domain-specific event emitters.

**Description:** Provides event emission coordination with observer notification and optional event persistence.

**Type Parameters:**
- `TEventType` - Enum type for domain-specific events

**Attributes:**
- `entity_id: str` - Entity identifier for emitted events
- `entity_type: str` - Entity type for emitted events

**Methods:**

#### `emit_event(event: BaseEvent) -> None`
Emit event to registered observers.

**Args:**
- `event: BaseEvent` - Event to emit

**Requires:**
- Event must have valid UUID and timestamp
- Event entity_id must match emitter entity_id

**Ensures:**
- All interested observers receive event
- Event logged if logging enabled
- Event persisted if persistence enabled

**Example:**
```python
class TestEmitter(EventEmitterBase[TestEventType]):
    def emit_started(self):
        event = TestStartedEvent(
            entity_id=self.entity_id,
            start_time=datetime.now()
        )
        self.emit_event(event)
```

#### `register_observer(observer: IObserver) -> None`
Register observer for event notifications.

**Args:**
- `observer: IObserver` - Observer to register

**Ensures:**
- Observer receives future events if interested
- Observer added to internal registry

---

### StateManager

```python
class StateManager(Generic[TState])
```

Manages state transitions for domain entities.

**Description:** Enforces valid state transitions and tracks entity lifecycle with event emission on state changes.

**Type Parameters:**
- `TState` - Enum type for domain-specific states

**Attributes:**
- `current_state: TState` - Current entity state
- `initial_state: TState` - Starting state for entity
- `valid_transitions: Dict[TState, List[TState]]` - Allowed state transitions

**Methods:**

#### `transition_to(new_state: TState) -> bool`
Attempt to transition to new state.

**Args:**
- `new_state: TState` - Target state

**Returns:**
- `bool` - True if transition successful, False if invalid

**Requires:**
- `new_state` must be in valid transitions for current state

**Ensures:**
- Current state updated if transition valid
- State change event emitted
- Transition logged

**Example:**
```python
class TestState(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"

manager = StateManager(
    initial_state=TestState.CREATED,
    valid_transitions={
        TestState.CREATED: [TestState.RUNNING],
        TestState.RUNNING: [TestState.COMPLETED]
    }
)

success = manager.transition_to(TestState.RUNNING)  # True
success = manager.transition_to(TestState.CREATED)  # False
```

**Complexity:** O(1) for transition validation and execution.

---

## Domain Event Classes

### Test Events

#### TestEvent

```python
@dataclass(frozen=True)
class TestEvent(BaseEvent)
```

Base class for all test-related events.

**Attributes:**
- `test_name: str` - Human-readable test name
- `test_config: Dict[str, Any]` - Test configuration parameters

#### TestStartedEvent

```python
@dataclass(frozen=True)
class TestStartedEvent(TestEvent)
```

Event emitted when test execution begins.

**Attributes:**
- `start_time: datetime` - Test execution start time
- `environment_id: str` - Execution environment identifier

**Example:**
```python
event = TestStartedEvent(
    entity_id="test-123",
    test_name="QUIC Connection Test",
    test_config={"timeout": 30},
    start_time=datetime.now(),
    environment_id="env-456"
)
```

#### TestCompletedEvent

```python
@dataclass(frozen=True)
class TestCompletedEvent(TestEvent)
```

Event emitted when test execution completes successfully.

**Attributes:**
- `end_time: datetime` - Test completion time
- `duration: float` - Test execution duration in seconds
- `result_summary: Dict[str, Any]` - Test result summary

#### TestFailedEvent

```python
@dataclass(frozen=True)
class TestFailedEvent(TestEvent)
```

Event emitted when test execution fails.

**Attributes:**
- `end_time: datetime` - Test failure time
- `error_message: str` - Failure description
- `error_type: str` - Error classification
- `stack_trace: Optional[str]` - Exception stack trace

---

### Service Events

#### ServiceEvent

```python
@dataclass(frozen=True)
class ServiceEvent(BaseEvent)
```

Base class for service lifecycle events.

**Attributes:**
- `service_name: str` - Service identifier
- `service_type: str` - Service category (e.g., "docker", "native")

#### ServiceStartedEvent

```python
@dataclass(frozen=True)
class ServiceStartedEvent(ServiceEvent)
```

Event emitted when service starts successfully.

**Attributes:**
- `start_time: datetime` - Service start time
- `pid: Optional[int]` - Process ID if applicable
- `endpoint: Optional[str]` - Service endpoint URL

#### ServiceHealthCheckPassedEvent

```python
@dataclass(frozen=True)
class ServiceHealthCheckPassedEvent(ServiceEvent)
```

Event emitted when service health check succeeds.

**Attributes:**
- `check_time: datetime` - Health check timestamp
- `response_time: float` - Health check response time
- `health_data: Dict[str, Any]` - Health status details

---

### Metrics Events

#### MetricsEvent

```python
@dataclass(frozen=True)
class MetricsEvent(BaseEvent)
```

Base class for metrics collection events.

**Attributes:**
- `metric_name: str` - Metric identifier
- `metric_type: str` - Metric category

#### MetricCollectedEvent

```python
@dataclass(frozen=True)
class MetricCollectedEvent(MetricsEvent)
```

Event emitted when metric data is collected.

**Attributes:**
- `value: float` - Metric value
- `unit: str` - Measurement unit
- `tags: Dict[str, str]` - Metric tags/labels
- `collection_time: datetime` - Collection timestamp

**Example:**
```python
event = MetricCollectedEvent(
    entity_id="system-metrics",
    metric_name="cpu_usage_percent",
    metric_type="system",
    value=75.5,
    unit="percent",
    tags={"host": "test-01", "core": "0"},
    collection_time=datetime.now()
)
```

---

## Utility Functions

### create_content_based_uuid

```python
def create_content_based_uuid(content: str) -> str
```

Generate deterministic UUID from content for deduplication.

**Args:**
- `content: str` - String content to generate UUID from

**Returns:**
- `str` - Deterministic UUID string

**Description:** Uses UUID5 with PANTHER namespace to ensure identical content always produces the same UUID, enabling reliable duplicate detection.

**Example:**
```python
uuid1 = create_content_based_uuid("test-event-data")
uuid2 = create_content_based_uuid("test-event-data")
assert uuid1 == uuid2  # Same content = same UUID
```

### create_event_signature

```python
def create_event_signature(
    name: str,
    entity_type: str,
    entity_id: str,
    data: Dict[str, Any] = None
) -> str
```

Create signature string for event deduplication.

**Args:**
- `name: str` - Event name
- `entity_type: str` - Event entity type
- `entity_id: str` - Entity identifier
- `data: Dict[str, Any]` - Optional event data

**Returns:**
- `str` - String signature for the event

**Description:** Creates deterministic signature from core event properties for efficient duplicate detection.

**Example:**
```python
signature = create_event_signature(
    name="test.started",
    entity_type="test",
    entity_id="test-123",
    data={"config": "value"}
)
```

---

## Enums

### Event Type Enums

Each domain defines event types through enums:

#### TestEventType

```python
class TestEventType(Enum):
    TEST_CREATED = "test.created"
    TEST_SETUP_STARTED = "test.setup.started"
    TEST_SETUP_COMPLETED = "test.setup.completed"
    TEST_SETUP_FAILED = "test.setup.failed"
    TEST_EXECUTION_STARTED = "test.execution.started"
    TEST_EXECUTION_COMPLETED = "test.execution.completed"
    TEST_EXECUTION_FAILED = "test.execution.failed"
    TEST_COMPLETED = "test.completed"
    TEST_FAILED = "test.failed"
```

#### ServiceEventType

```python
class ServiceEventType(Enum):
    SERVICE_CREATED = "service.created"
    SERVICE_STARTED = "service.started"
    SERVICE_READY = "service.ready"
    SERVICE_HEALTH_CHECK_PASSED = "service.health_check.passed"
    SERVICE_HEALTH_CHECK_FAILED = "service.health_check.failed"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_ERROR = "service.error"
    SERVICE_DESTROYED = "service.destroyed"
```

#### MetricsEventType

```python
class MetricsEventType(Enum):
    METRIC_COLLECTED = "metrics.collected"
    RESOURCE_METRIC = "metrics.resource"
    TIMING_METRIC = "metrics.timing"
    COUNTER_METRIC = "metrics.counter"
    METRICS_SUMMARY = "metrics.summary"
```

---

## Error Handling

### Event Creation Errors

**ValidationError:** Thrown when event data fails validation
- Invalid entity_id format
- Missing required fields
- Invalid enum values

**Example:**
```python
try:
    event = TestEvent(entity_id="", test_name="Test")  # Invalid empty ID
except ValidationError as e:
    print(f"Event validation failed: {e}")
```

### Event Processing Errors

**EventProcessingError:** Thrown during event emission or handling
- Observer processing failures
- Serialization errors
- Network communication failures

**Example:**
```python
try:
    emitter.emit_event(event)
except EventProcessingError as e:
    print(f"Failed to process event: {e}")
```

---

## Performance Notes

### Memory Usage
- Events use `__slots__` for reduced memory footprint
- UUID strings are interned for deduplication efficiency
- State managers use weak references to prevent memory leaks

### Processing Speed
- Event type filtering: O(1) with enum comparisons
- UUID generation: O(n) where n is serialized content size
- State transitions: O(1) for validation and execution

### Concurrency
- Events are immutable and thread-safe
- State managers use locks for atomic transitions
- Event emitters support concurrent observer notification

### Scalability
- Content-based deduplication handles high event volumes
- Batch processing available for metrics events
- Observer interest filtering reduces processing overhead by 60-80%
