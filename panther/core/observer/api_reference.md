# Observer Module API Reference

## Core Interfaces

### IObserver

```python
class IObserver(ABC)
```

Core interface for all observer implementations in PANTHER.

**Description:** Defines the contract for event processing with deduplication protection and interest-based filtering.

**Attributes:**
- `processed_events_uuids: List[str]` - UUIDs of previously processed events

**Methods:**

#### `on_event(event: BaseEvent) -> None`
Handle an incoming event.

**Args:**
- `event: BaseEvent` - Event to process

**Requires:**
- Event must have valid UUID and timestamp
- Implementation must handle exceptions gracefully

**Ensures:**
- Event processing is idempotent
- No side effects on other observers
- Thread-safe execution

**Example:**
```python
class MyObserver(IObserver):
    def on_event(self, event: BaseEvent):
        if event.uuid in self.processed_events_uuids:
            return  # Skip duplicate

        # Process event
        self.process_event(event)
        self.processed_events_uuids.append(event.uuid)
```

#### `is_interested(event_type: str) -> bool`
Check if observer should process events of given type.

**Args:**
- `event_type: str` - Event type to check interest for

**Returns:**
- `bool` - True if observer handles this event type

**Default Implementation:** Returns True (interested in all events)

**Example:**
```python
def is_interested(self, event_type: str) -> bool:
    return event_type.startswith("test.") or event_type.startswith("metrics.")
```

**Complexity:** O(1) for simple filters, O(n) for complex pattern matching.

---

### ITypedObserver

```python
class ITypedObserver(IObserver, Generic[TEvent])
```

Type-safe observer interface for specific event types.

**Description:** Provides compile-time type checking for event handling with generic type parameters.

**Type Parameters:**
- `TEvent` - Specific event type this observer handles

**Methods:**

#### `on_event(event: TEvent) -> None`
Handle typed event with compile-time safety.

**Args:**
- `event: TEvent` - Typed event to process

**Ensures:**
- Type safety at compile time
- IDE autocomplete support
- Runtime type validation

**Example:**
```python
class TestObserver(ITypedObserver[TestEvent]):
    def on_event(self, event: TestEvent):
        # event is guaranteed to be TestEvent type
        print(f"Test {event.test_name} status: {event.event_type}")
```

---

### IPluginObserver

```python
class IPluginObserver(IObserver)
```

Interface for plugin-based observers that can be loaded dynamically.

**Description:** Extends IObserver with plugin lifecycle support and dynamic loading capabilities.

**Methods:**

#### `get_supported_events() -> List[str]`
Return list of event types this plugin observer supports.

**Returns:**
- `List[str]` - Event type strings

**Example:**
```python
def get_supported_events(self) -> List[str]:
    return [
        "plugin.loaded",
        "plugin.started",
        "plugin.stopped",
        "plugin.error"
    ]
```

#### `initialize_plugin(config: Dict[str, Any]) -> None`
Initialize plugin observer with configuration.

**Args:**
- `config: Dict[str, Any]` - Plugin configuration

**Requires:**
- Valid configuration schema
- Required dependencies available

**Ensures:**
- Plugin ready to process events
- Resources allocated and initialized

---

## Built-in Observer Implementations

### LoggerObserver

```python
class LoggerObserver(IObserver)
```

Event logging observer with color-coded output and severity indicators.

**Description:** Provides structured event logging with terminal capability detection, color schemes, and integration with TQDM progress bars.

**Attributes:**
- `logger: logging.Logger` - Python logger instance
- `colored: bool` - Enable color output
- `level: str` - Logging level (DEBUG, INFO, WARN, ERROR)
- `format: str` - Log format template

**Methods:**

#### `__init__(config: Dict[str, Any] = None)`
Initialize logger observer with configuration.

**Args:**
- `config: Dict[str, Any]` - Logger configuration

**Configuration Options:**
- `level: str` - Log level (default: "INFO")
- `colored: bool` - Color output (default: True if terminal capable)
- `format: str` - Log format (default: "detailed")
- `file_output: str` - Optional file output path

**Example:**
```python
observer = LoggerObserver({
    'level': 'DEBUG',
    'colored': True,
    'format': 'detailed',
    'file_output': '/logs/panther.log'
})
```

#### `format_event(event: BaseEvent) -> str`
Format event for logging output.

**Args:**
- `event: BaseEvent` - Event to format

**Returns:**
- `str` - Formatted log message

**Features:**
- Color coding by event severity
- Timestamp formatting
- Entity information display
- Error details inclusion

---

### MetricsObserver

```python
class MetricsObserver(IObserver)
```

Performance metrics collection and aggregation observer.

**Description:** Collects system metrics, test performance data, and resource utilization with configurable collection intervals and storage backends.

**Attributes:**
- `collector: IMetricsCollector` - Metrics collection backend
- `aggregator: MetricsAggregator` - Data aggregation engine
- `collection_interval: float` - Metrics collection frequency

**Methods:**

#### `__init__(config: Dict[str, Any] = None)`
Initialize metrics observer with configuration.

**Configuration Options:**
- `interval: float` - Collection interval in seconds (default: 1.0)
- `metrics: List[str]` - Metrics to collect (default: ["cpu", "memory", "network"])
- `storage: str` - Storage backend ("memory", "file", "database")
- `aggregation: str` - Aggregation method ("sum", "avg", "max")

#### `collect_metrics() -> MetricsSnapshot`
Collect current system metrics.

**Returns:**
- `MetricsSnapshot` - Current metrics data

**Collected Metrics:**
- CPU usage percentage
- Memory utilization
- Network I/O statistics
- Disk usage
- Test execution timings

**Example:**
```python
observer = MetricsObserver({
    'interval': 0.5,
    'metrics': ['cpu', 'memory'],
    'storage': 'file'
})

snapshot = observer.collect_metrics()
print(f"CPU: {snapshot.cpu_percent}%")
```

#### `get_aggregated_metrics(time_range: TimeRange) -> Dict[str, Any]`
Get aggregated metrics for time period.

**Args:**
- `time_range: TimeRange` - Time period for aggregation

**Returns:**
- `Dict[str, Any]` - Aggregated metrics data

---

### StorageObserver

```python
class StorageObserver(IObserver)
```

Event persistence observer for audit trails and analytics.

**Description:** Persists events to various storage backends with compression, retention policies, and query capabilities.

**Attributes:**
- `storage_backend: str` - Storage type ("file", "database", "cloud")
- `compression: bool` - Enable data compression
- `retention_days: int` - Data retention period

**Methods:**

#### `__init__(config: Dict[str, Any] = None)`
Initialize storage observer with backend configuration.

**Configuration Options:**
- `backend: str` - Storage backend type
- `connection_string: str` - Backend connection details
- `compression: bool` - Enable compression (default: True)
- `retention_days: int` - Retention period (default: 30)
- `batch_size: int` - Batch insert size (default: 100)

#### `store_event(event: BaseEvent) -> None`
Store event to configured backend.

**Args:**
- `event: BaseEvent` - Event to store

**Ensures:**
- Event persisted durably
- Compression applied if enabled
- Batch processing for efficiency

#### `query_events(criteria: QueryCriteria) -> List[BaseEvent]`
Query stored events by criteria.

**Args:**
- `criteria: QueryCriteria` - Search criteria

**Returns:**
- `List[BaseEvent]` - Matching events

**Query Options:**
- Event type filtering
- Time range selection
- Entity filtering
- Custom field matching

**Example:**
```python
criteria = QueryCriteria(
    event_types=["test.started", "test.completed"],
    time_range=TimeRange(start=yesterday, end=today),
    entity_filter={"entity_type": "test"}
)
events = observer.query_events(criteria)
```

---

### StateObserver

```python
class StateObserver(IObserver)
```

Entity state tracking and workflow coordination observer.

**Description:** Monitors entity state changes, validates transitions, and coordinates multi-step workflows with error recovery.

**Attributes:**
- `state_managers: Dict[str, StateManager]` - State managers by entity
- `workflow_tracker: WorkflowTracker` - Multi-step workflow coordination
- `transition_rules: Dict[str, Dict]` - State transition rules

**Methods:**

#### `track_entity_state(entity_id: str, initial_state: Any) -> None`
Begin tracking state for entity.

**Args:**
- `entity_id: str` - Entity to track
- `initial_state: Any` - Starting state

**Ensures:**
- State manager created for entity
- Transition rules applied
- Workflow tracking enabled

#### `get_entity_state(entity_id: str) -> Any`
Get current state for entity.

**Args:**
- `entity_id: str` - Entity identifier

**Returns:**
- Current state value

**Raises:**
- `KeyError` if entity not tracked

#### `validate_transition(entity_id: str, new_state: Any) -> bool`
Validate if state transition is allowed.

**Args:**
- `entity_id: str` - Entity identifier
- `new_state: Any` - Target state

**Returns:**
- `bool` - True if transition valid

**Example:**
```python
observer = StateObserver()
observer.track_entity_state("test-123", TestState.CREATED)

# Later, when processing test started event
valid = observer.validate_transition("test-123", TestState.RUNNING)
if valid:
    print("Transition allowed")
```

---

## Factory System

### ObserverFactory

```python
class ObserverFactory
```

Factory for creating and configuring observer instances.

**Description:** Provides standardized observer creation with configuration validation and dependency injection.

**Methods:**

#### `create_observer(observer_type: str, config: Dict[str, Any] = None) -> IObserver`
Create observer instance of specified type.

**Args:**
- `observer_type: str` - Type of observer to create
- `config: Dict[str, Any]` - Observer configuration

**Returns:**
- `IObserver` - Configured observer instance

**Supported Types:**
- "logger" - LoggerObserver
- "metrics" - MetricsObserver
- "storage" - StorageObserver
- "state" - StateObserver
- "experiment" - ExperimentObserver

**Example:**
```python
factory = ObserverFactory()
observer = factory.create_observer("logger", {
    'level': 'DEBUG',
    'colored': True
})
```

#### `register_observer_type(name: str, class_type: Type[IObserver], schema: Dict = None) -> None`
Register custom observer type with factory.

**Args:**
- `name: str` - Type name for factory
- `class_type: Type[IObserver]` - Observer class
- `schema: Dict` - Configuration schema

**Ensures:**
- Custom observer available via create_observer
- Configuration validation applied
- Type registered globally

#### `create_default_observers() -> List[IObserver]`
Create standard set of observers for typical usage.

**Returns:**
- `List[IObserver]` - Default observer instances

**Default Set:**
- LoggerObserver with INFO level
- MetricsObserver with 1-second interval
- StateObserver with workflow tracking

---

## Management Classes

### EventManager

```python
class EventManager
```

Central coordinator for event distribution to observers.

**Description:** Manages observer registration, event routing, and performance optimization with interest-based filtering.

**Attributes:**
- `observers: List[IObserver]` - Registered observers
- `event_queue: Queue` - Event processing queue
- `filtering_enabled: bool` - Interest-based filtering

**Methods:**

#### `register_observer(observer: IObserver) -> None`
Register observer for event notifications.

**Args:**
- `observer: IObserver` - Observer to register

**Ensures:**
- Observer receives future events if interested
- Observer added to routing table
- Thread-safe registration

#### `emit_event(event: BaseEvent) -> None`
Distribute event to interested observers.

**Args:**
- `event: BaseEvent` - Event to distribute

**Process:**
1. Filter observers by interest
2. Distribute to interested observers
3. Handle observer errors gracefully
4. Log distribution metrics

**Performance:** O(n) where n is number of interested observers.

#### `get_registered_observers() -> List[IObserver]`
Get list of currently registered observers.

**Returns:**
- `List[IObserver]` - Registered observers

---

### ResultsManager

```python
class ResultsManager
```

Aggregates and exports results from observer processing.

**Description:** Collects processed data from observers and provides export capabilities for CI/CD integration and analytics.

**Methods:**

#### `collect_results(observers: List[IObserver]) -> Dict[str, Any]`
Collect aggregated results from observers.

**Args:**
- `observers: List[IObserver]` - Observers to collect from

**Returns:**
- `Dict[str, Any]` - Aggregated results

**Collected Data:**
- Event processing statistics
- Performance metrics
- Error summaries
- State transition reports

#### `export_results(format: str, output_path: str) -> None`
Export collected results to file.

**Args:**
- `format: str` - Export format ("json", "xml", "csv")
- `output_path: str` - Output file path

**Supported Formats:**
- JSON - Structured data export
- XML - Enterprise integration
- CSV - Spreadsheet analysis
- YAML - Configuration-friendly

**Example:**
```python
manager = ResultsManager()
results = manager.collect_results(observers)
manager.export_results("json", "results.json")
```

---

## Plugin System

### EventObserverPlugin

```python
class EventObserverPlugin(IPluginObserver)
```

Base class for plugin-based observer implementations.

**Description:** Provides foundation for dynamically loaded observers with lifecycle management and configuration.

**Methods:**

#### `load_plugin(plugin_path: str, config: Dict[str, Any]) -> IObserver`
Load observer plugin from path.

**Args:**
- `plugin_path: str` - Path to plugin module
- `config: Dict[str, Any]` - Plugin configuration

**Returns:**
- `IObserver` - Loaded plugin instance

**Example:**
```python
plugin = EventObserverPlugin.load_plugin(
    "plugins.custom_observer",
    {"setting": "value"}
)
```

### PluginObserverFactory

```python
class PluginObserverFactory
```

Factory for dynamic plugin observer loading and management.

**Methods:**

#### `create_plugin_observer(plugin_name: str, config: Dict[str, Any]) -> IObserver`
Create observer from plugin registry.

**Args:**
- `plugin_name: str` - Registered plugin name
- `config: Dict[str, Any]` - Plugin configuration

**Returns:**
- `IObserver` - Plugin observer instance

#### `register_plugin_observer(name: str, plugin_path: str) -> None`
Register plugin observer in factory.

**Args:**
- `name: str` - Plugin name for factory
- `plugin_path: str` - Plugin module path

---

## Utility Classes

### WorkflowTracker

```python
class WorkflowTracker
```

Tracks multi-step workflow progress across observer coordination.

**Description:** Monitors complex workflows involving multiple entities and provides progress reporting with error recovery.

**Methods:**

#### `track_workflow(workflow_id: str, steps: List[str]) -> None`
Begin tracking multi-step workflow.

**Args:**
- `workflow_id: str` - Workflow identifier
- `steps: List[str]` - Workflow step names

#### `update_step_progress(workflow_id: str, step: str, status: str) -> None`
Update progress for workflow step.

**Args:**
- `workflow_id: str` - Workflow identifier
- `step: str` - Step name
- `status: str` - Step status ("started", "completed", "failed")

#### `get_workflow_status(workflow_id: str) -> WorkflowStatus`
Get current workflow status.

**Args:**
- `workflow_id: str` - Workflow identifier

**Returns:**
- `WorkflowStatus` - Current workflow state

---

## Error Handling

### Observer Exceptions

#### ObserverError

```python
class ObserverError(Exception)
```

Base exception for observer-related errors.

#### EventProcessingError

```python
class EventProcessingError(ObserverError)
```

Exception raised during event processing.

**Attributes:**
- `event: BaseEvent` - Event that caused error
- `observer: IObserver` - Observer that failed

#### ConfigurationError

```python
class ConfigurationError(ObserverError)
```

Exception raised for observer configuration issues.

**Common Causes:**
- Invalid configuration schema
- Missing required settings
- Type validation failures

---

## Performance Characteristics

### Observer Performance

**Event Filtering:**
- Interest-based filtering: O(1) with simple patterns
- Complex regex filtering: O(m) where m is pattern complexity
- Overall filtering efficiency: 60-80% reduction in processing

**Memory Usage:**
- Base observer overhead: ~1KB per observer
- Event deduplication: ~40 bytes per processed event UUID
- Metrics observer: ~100KB per hour of 1-second interval collection

**Throughput:**
- Simple observers: >10,000 events/second
- Complex observers (I/O): 100-1,000 events/second
- Batch processing: 5-10x throughput improvement

### Optimization Guidelines

**For High-Volume Scenarios:**
- Use interest filtering aggressively
- Implement batch processing where possible
- Consider async observers for I/O operations
- Monitor memory usage with long-running observers

**For Low-Latency Scenarios:**
- Minimize observer processing complexity
- Use direct observer notification
- Avoid I/O in synchronous event handling
- Profile observer performance regularly
