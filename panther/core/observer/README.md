# Observer Pattern — Event-Driven Architecture 📡

**Purpose:** Decoupled communication between framework components through typed event handling
**Components:** Event management, typed observers, lifecycle notifications
**Dependencies:** Core framework, typed event system

PANTHER's observer pattern enables loose coupling between components through a modern typed event-driven system, supporting real-time monitoring and coordinated component interactions.

---

## Architecture Overview

```python
# Observer system with typed event handling
# - Publishers emit strongly-typed events
# - Observers implement specific handler methods for event types
# - Type-safe event routing with performance benefits
# - Framework lifecycle events coordinate component behavior
```

### Event Flow

1. **Observer Registration** → Observers register with EventManager
2. **Event Publishing** → Components emit typed events (e.g., TestStartedEvent)
3. **Type-Based Routing** → Events routed to specific handler methods
4. **Observer Processing** → Typed handlers process events with full type information
5. **Lifecycle Coordination** → Components coordinate through structured event flow

---

## Directory Structure

```
panther/core/observer/
├── base/                    # Base interfaces and abstractions
│   ├── observer_interface.py       # IObserver base interface
│   └── typed_observer_interface.py # ITypedObserver with typed handlers
├── impl/                    # Observer implementations
│   ├── experiment_observer.py # Core experiment coordinator
│   ├── logger_observer.py     # Event logging with debug features
│   ├── metrics_observer.py    # Metrics collection and monitoring
│   ├── storage_observer.py    # Event persistence and results
│   ├── plugin_observer.py     # Plugin event distribution
│   └── gui/                   # GUI observer (future work)
│       └── gui_observer.py
├── factory/                 # Observer creation and configuration
│   ├── observer_factory.py    # Core factory class
│   ├── factory_builders.py    # Specialized builder methods
│   └── factory_config.py      # Configuration loading
├── management/              # Event and results management
│   ├── event_manager.py       # Event distribution system
│   └── results_manager.py     # Test results handling
├── plugins/                 # Plugin observer infrastructure
│   ├── plugin_interface.py
│   ├── plugin_observer_factory.py
│   └── plugin_registry.py
└── utils/                   # Utility modules
    └── event_colors.py        # Terminal color formatting
```

---

## Core Components

### Typed Observer Interface

**Location:** `base/typed_observer_interface.py`

The modern observer interface with typed event handlers:

```python
class ITypedObserver(IObserver):
    """Observer with typed event handler methods"""

    # Experiment lifecycle handlers
    def on_experiment_initialized(self, event: ExperimentInitializedEvent) -> bool:
        return True

    # Test execution handlers
    def on_test_execution_started(self, event: TestExecutionStartedEvent) -> bool:
        return True

    # Service management handlers
    def on_service_started(self, event: ServiceStartedEvent) -> bool:
        return True

    # ... specific handlers for all event types
```

### Event Management System

**Location:** `management/event_manager.py`

Central hub for event distribution:

```python
class EventManager:
    """Manages observer registration and event distribution"""

    def register_observer(
        self,
        observer: IObserver,
        event_types: list[type[BaseEvent]] | None = None,
        priority: int = 0
    ):
        """Register observer with optional event type filtering"""

    def publish_event(self, event: BaseEvent):
        """Publish typed event to registered observers"""
```

### Observer Implementations

#### ExperimentObserver
**Location:** `impl/experiment_observer.py`
- Central coordinator for experiment workflow
- Tracks experiment state and progress
- Manages test execution lifecycle

#### LoggerObserver
**Location:** `impl/logger_observer.py`
- Event logging with color-coded output
- Includes debug observer functionality
- Configurable log levels and formatting

#### MetricsObserver
**Location:** `impl/metrics_observer.py`
- Real-time metrics collection
- Resource monitoring integration
- Performance statistics aggregation

#### StorageObserver
**Location:** `impl/storage_observer.py`
- Event persistence to disk
- Results management integration
- Batch processing for efficiency

---

## Factory System

### Observer Creation

The factory system provides multiple ways to create observers:

```python
# Using specialized builders
logger = create_logger(
    name="my_logger",
    log_level="DEBUG",
    enable_colors=True
)

metrics = create_metrics(
    name="my_metrics",
    collect_system_metrics=True,
    publish_interval=30
)

# Using generic factory
factory = get_observer_factory()
observer = factory.create_observer("storage", name="my_storage")

# Creating default set
observers = create_default_observer_set(config)
```

### Configuration Loading

Load observer configurations from YAML:

```yaml
# observer_config.yaml
observers:
  - class_path: panther.core.observer.impl.logger_observer.LoggerObserver
    enabled: true
    priority: 100
    params:
      log_level: DEBUG
      enable_colors: true

  - class_path: panther.core.observer.impl.metrics_observer.MetricsObserver
    enabled: true
    priority: 50
    params:
      collect_system_metrics: true
```

```python
# Load configuration
load_observer_config("observer_config.yaml")
```

---

## Creating Custom Observers

### Typed Observer Pattern

```python
from panther.core.observer import ITypedObserver
from panther.core.events import TestExecutionStartedEvent, TestCompletedEvent

class MyCustomObserver(ITypedObserver):
    """Custom observer with typed event handlers"""

    def __init__(self):
        super().__init__()
        self.test_count = 0

    def on_test_execution_started(self, event: TestExecutionStartedEvent) -> bool:
        """Handle test start with full type information"""
        self.test_count += 1
        print(f"Test {event.test_name} starting (#{self.test_count})")
        return True

    def on_test_completed(self, event: TestCompletedEvent) -> bool:
        """Handle test completion"""
        duration = event.duration_seconds
        print(f"Test {event.test_name} completed in {duration}s")
        return True
```

### Registration and Usage

```python
# Create and register observer
observer = MyCustomObserver()
event_manager = EventManager()
event_manager.register_observer(observer)

# Observer automatically receives typed events
# No string parsing or type checking needed!
```

---

## Event Types and Handlers

The typed event system provides specific events for each entity:

### Experiment Events
- `ExperimentInitializedEvent` → `on_experiment_initialized()`
- `ExperimentExecutionStartedEvent` → `on_experiment_execution_started()`
- `ExperimentCompletedEvent` → `on_experiment_completed()`

### Test Events
- `TestCreatedEvent` → `on_test_created()`
- `TestExecutionStartedEvent` → `on_test_execution_started()`
- `TestCompletedEvent` → `on_test_completed()`

### Service Events
- `ServiceCreatedEvent` → `on_service_created()`
- `ServiceStartedEvent` → `on_service_started()`
- `ServiceStoppedEvent` → `on_service_stopped()`

### Environment Events
- `EnvironmentSetupStartedEvent` → `on_environment_setup_started()`
- `EnvironmentReadyEvent` → `on_environment_ready()`
- `EnvironmentTeardownCompletedEvent` → `on_environment_teardown_completed()`

---

## Benefits of Typed Observer System

1. **Type Safety**: Full IDE support with autocomplete and type checking
2. **Performance**: Direct method dispatch instead of string parsing
3. **Clarity**: Clear method signatures show exactly what data is available
4. **Maintainability**: Easy to add new event types without breaking existing code
5. **Debugging**: Stack traces show exact handler methods

---

## Migration from Legacy Observers

If you have legacy observers using string-based events:

```python
# Old pattern
def on_event(self, event):
    if event.name == "test.started":
        # Handle test start

# New pattern
def on_test_execution_started(self, event: TestExecutionStartedEvent) -> bool:
    # Handle test start with typed event
    return True
```

Simply implement the typed handler methods for the events you care about. The base `ITypedObserver` class handles routing automatically.

---

## Best Practices

1. **Use Typed Handlers**: Always prefer typed event handlers over generic `on_event`
2. **Return Boolean**: Handler methods should return `True` to continue propagation
3. **Handle Errors**: Wrap handler logic in try-except to prevent observer failures
4. **Minimal Processing**: Keep handlers fast to avoid blocking event flow
5. **Use Factory**: Leverage the factory system for consistent observer creation

---

## Future Enhancements

- **GUI Observer**: Full implementation for real-time UI updates
- **Remote Observers**: Network-based event distribution
- **Event Replay**: Record and replay event streams
- **Advanced Filtering**: Complex event filtering rules
- **Performance Metrics**: Built-in observer performance monitoring