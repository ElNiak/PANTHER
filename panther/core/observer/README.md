# Observer Pattern — Event-Driven Architecture 📡

**Purpose:** Decoupled communication between framework components
**Components:** Event management, observers, lifecycle notifications
**Dependencies:** Core framework, logging system

PANTHER's observer pattern enables loose coupling between components through event-driven communication, supporting real-time monitoring and coordinated component interactions.

---

## Architecture Overview

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/observer/
# Event-based communication system
# - Publishers emit events without knowing subscribers
# - Observers react to events they're interested in
# - Framework lifecycle events coordinate component behavior
```

### Event Flow

1. **Event Registration** → Components register as observers for specific events
2. **Event Publishing** → Framework components emit events at key moments
3. **Event Distribution** → Event manager notifies all registered observers
4. **Observer Reaction** → Observers process events and potentially emit new ones
5. **Lifecycle Coordination** → Framework components coordinate through events

---

## Core Components

### Event Management System

**Location:** `panther/core/observer/`

The observer system manages event subscription and distribution:

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/observer/
class EventManager:
    """Central event coordination and distribution"""

    def register_observer(self, event_type: str, observer: Observer):
        """Register an observer for specific event types"""

    def publish_event(self, event: Event):
        """Publish event to all registered observers"""

    def unregister_observer(self, event_type: str, observer: Observer):
        """Remove observer registration"""
```

### Logger Observer

**Location:** `panther/core/observer/logger_observer.py`

Built-in observer for experiment lifecycle logging:

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/observer/logger_observer.py
class LoggerObserver:
    """Observer that logs framework events for debugging and monitoring"""

    def on_experiment_started(self, event):
        """Log experiment initialization"""

    def on_test_case_started(self, event):
        """Log individual test case execution"""

    def on_plugin_loaded(self, event):
        """Log plugin loading and initialization"""
```

---

## Event Types

### Framework Lifecycle Events

**Experiment Level:**

- `experiment.started` — Experiment initialization begins
- `experiment.configured` — Configuration loading completed
- `experiment.finished` — Experiment execution completed
- `experiment.error` — Experiment encountered fatal error

**Test Case Level:**

- `test_case.started` — Individual test case begins
- `test_case.setup_complete` — Test environment ready
- `test_case.execution_started` — Test execution phase begins
- `test_case.results_collected` — Test outputs gathered
- `test_case.finished` — Test case completed
- `test_case.error` — Test case failed or encountered error

### Plugin Events

**Plugin Lifecycle:**

- `plugin.discovered` — Plugin found during discovery
- `plugin.loaded` — Plugin successfully imported
- `plugin.initialized` — Plugin setup completed
- `plugin.error` — Plugin initialization or execution failed

**Service Events:**

- `service.starting` — Service initialization begins
- `service.ready` — Service available for testing
- `service.stopping` — Service shutdown initiated
- `service.stopped` — Service cleanup completed

### Environment Events

**Network Environment:**

- `network.setup_started` — Network environment creation begins
- `network.ready` — Network infrastructure available
- `network.teardown_started` — Network cleanup begins
- `network.teardown_complete` — Network resources released

**Execution Environment:**

- `execution.environment_ready` — Execution context prepared
- `execution.environment_error` — Environment setup failed

---

## Usage Patterns

### Creating Custom Observers

```python
from panther.core.observer.base_observer import Observer

class CustomMonitoringObserver(Observer):
    """Custom observer for experiment monitoring"""

    def __init__(self):
        self.test_metrics = {}

    def on_test_case_started(self, event):
        """Track test case start times"""
        self.test_metrics[event.test_name] = {
            'start_time': event.timestamp,
            'status': 'running'
        }

    def on_test_case_finished(self, event):
        """Calculate test duration and status"""
        if event.test_name in self.test_metrics:
            self.test_metrics[event.test_name].update({
                'end_time': event.timestamp,
                'duration': event.timestamp - self.test_metrics[event.test_name]['start_time'],
                'status': 'completed' if event.success else 'failed'
            })
```

### Registering Observers

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/experiment_manager.py
# Register observers during experiment initialization
event_manager = EventManager()
logger_observer = LoggerObserver()
custom_observer = CustomMonitoringObserver()

event_manager.register_observer("test_case.*", logger_observer)
event_manager.register_observer("test_case.*", custom_observer)
```

### Publishing Events

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/test_cases/test_case_impl.py
# Emit events at key points in test execution
def execute(self):
    # Notify test case start
    self.event_manager.publish_event(TestCaseStartedEvent(
        test_name=self.name,
        timestamp=datetime.now(),
        configuration=self.config
    ))

    try:
        # Execute test logic
        result = self._run_test()

        # Notify successful completion
        self.event_manager.publish_event(TestCaseFinishedEvent(
            test_name=self.name,
            timestamp=datetime.now(),
            success=True,
            result=result
        ))
    except Exception as e:
        # Notify error
        self.event_manager.publish_event(TestCaseErrorEvent(
            test_name=self.name,
            timestamp=datetime.now(),
            error=str(e)
        ))
```

---

## Integration Points

### With Experiment Engine

The experiment manager uses events to coordinate component interactions:

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/experiment_manager.py
def run_tests(self):
    """Execute tests with event coordination"""
    self.event_manager.publish_event(ExperimentStartedEvent())

    for test_case in self.test_cases:
        # Events coordinate setup, execution, and cleanup
        test_case.execute()  # Emits test case lifecycle events

    self.event_manager.publish_event(ExperimentFinishedEvent())
```

### With Plugin System

Plugins can both observe and emit events:

```python
# Plugin implementations can observe framework events
class PluginImplementation:
    def __init__(self, event_manager):
        self.event_manager = event_manager
        event_manager.register_observer("service.ready", self.on_service_ready)

    def on_service_ready(self, event):
        """React to service availability"""
        if event.service_name == self.target_service:
            self.start_interaction()
```

### With Results System

Results collection can be event-driven:

```python
# filepath: /Users/elniak/Documents/Project/PANTHER/panther/core/results/result_collector.py
class ResultCollector(Observer):
    """Collect results based on test case events"""

    def on_test_case_finished(self, event):
        """Automatically collect results when test completes"""
        self.collect_test_artifacts(event.test_name)
        self.validate_results(event.result)
```

---

## Real-Time Monitoring

### Progress Tracking

```python
class ProgressObserver(Observer):
    """Track experiment progress in real-time"""

    def __init__(self):
        self.total_tests = 0
        self.completed_tests = 0
        self.failed_tests = 0

    def on_experiment_started(self, event):
        self.total_tests = len(event.test_cases)
        print(f"Starting experiment with {self.total_tests} tests")

    def on_test_case_finished(self, event):
        self.completed_tests += 1
        if not event.success:
            self.failed_tests += 1

        progress = (self.completed_tests / self.total_tests) * 100
        print(f"Progress: {progress:.1f}% ({self.completed_tests}/{self.total_tests})")
```

### Metrics Collection

```python
class MetricsObserver(Observer):
    """Collect performance and execution metrics"""

    def on_test_case_started(self, event):
        self.start_time = time.time()

    def on_test_case_finished(self, event):
        duration = time.time() - self.start_time
        self.metrics.append({
            'test_name': event.test_name,
            'duration': duration,
            'success': event.success
        })
```

---

## Extending the Observer System

### Custom Event Types

Define events for domain-specific needs:

```python
@dataclass
class CustomProtocolEvent:
    """Custom event for protocol-specific notifications"""
    protocol: str
    message_type: str
    payload: dict
    timestamp: datetime
```

### Asynchronous Observers

For I/O intensive operations:

```python
import asyncio

class AsyncObserver(Observer):
    """Observer with asynchronous event processing"""

    async def on_event_async(self, event):
        """Process events asynchronously"""
        await self.perform_io_operation(event)

    def on_event(self, event):
        """Synchronous wrapper that schedules async processing"""
        asyncio.create_task(self.on_event_async(event))
```

### Debugging Observer Issues

- Enable event logging to trace event flow
- Check observer registration timing
- Verify event type matching (wildcards vs. specific types)
- Monitor for observer exceptions that could break event chains

---

**Related Documentation:**

- [Experiment Engine](panther/core/EXPERIMENT_ENGINE.md) — How events coordinate experiment execution
- [Plugin Development](panther/plugins/development.md) — Integrating events in plugins
