# Observer Module Developer Guide

## Development Environment Setup

### Prerequisites
- Python 3.8+ with asyncio support
- Poetry or pip for dependency management
- pytest-asyncio for testing async components
- mypy for type checking

### Installation
```bash
# Install development dependencies
pip install -e ".[dev]"

# Install testing tools
pip install pytest-asyncio pytest-mock

# Verify installation
python -c "from panther.core.observer import IObserver; print('Observer module ready')"
```

### IDE Configuration
Configure your IDE for observer development:

**VS Code**
```json
{
    "python.linting.mypyEnabled": true,
    "python.testing.pytestArgs": ["--asyncio-mode=auto"],
    "python.testing.pytestEnabled": true
}
```

## Development Workflow

### Creating Custom Observers

#### 1. Basic Observer Implementation
```python
from panther.core.observer.base.observer_interface import IObserver
from panther.core.events.base.event_base import BaseEvent

class MyCustomObserver(IObserver):
    """Custom observer for domain-specific event handling.

    Requires:
        Event filtering through is_interested()
        Thread-safe event processing

    Ensures:
        No duplicate event processing
        Graceful error handling
        Resource cleanup
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__()
        self.config = config or {}
        self.processed_count = 0

    def is_interested(self, event_type: str) -> bool:
        """Check if observer handles this event type.

        Args:
            event_type: Type string to check interest for

        Returns:
            True if observer should process this event type

        Example:
            >>> observer = MyCustomObserver()
            >>> observer.is_interested("test.started")
            True
        """
        return event_type.startswith("test.")

    def on_event(self, event: BaseEvent):
        """Process received event.

        Args:
            event: Event to process

        Requires:
            Event UUID not in processed_events_uuids

        Ensures:
            Event UUID added to processed_events_uuids
            Processed count incremented

        Example:
            >>> observer = MyCustomObserver()
            >>> event = TestStartedEvent(entity_id="test-123")
            >>> observer.on_event(event)
            >>> assert observer.processed_count == 1
        """
        if event.uuid in self.processed_events_uuids:
            return  # Skip duplicate

        try:
            self._process_event(event)
            self.processed_events_uuids.append(event.uuid)
            self.processed_count += 1
        except Exception as e:
            self._handle_error(event, e)

    def _process_event(self, event: BaseEvent):
        """Override this method for custom event processing."""
        pass

    def _handle_error(self, event: BaseEvent, error: Exception):
        """Handle processing errors gracefully."""
        print(f"Error processing {event.event_type}: {error}")
```

#### 2. Typed Observer Implementation
```python
from panther.core.observer.base.typed_observer_interface import ITypedObserver
from panther.core.events.test.events import TestEvent

class MyTypedObserver(ITypedObserver[TestEvent]):
    """Type-safe observer for specific event types.

    Provides compile-time type checking for event handling.
    """

    def on_event(self, event: TestEvent):
        """Process test events with type safety.

        Args:
            event: Typed test event
        """
        match event.event_type:
            case "test.started":
                self._handle_test_started(event)
            case "test.completed":
                self._handle_test_completed(event)
            case _:
                self._handle_unknown_event(event)

    def _handle_test_started(self, event: TestEvent):
        """Handle test start events."""
        pass

    def _handle_test_completed(self, event: TestEvent):
        """Handle test completion events."""
        pass
```

#### 3. Plugin Observer Implementation
```python
from panther.core.observer.base.observer_plugin_interface import IPluginObserver
from panther.core.events.plugin.events import PluginEvent

class MyPluginObserver(IPluginObserver):
    """Observer that responds to plugin lifecycle events."""

    def get_supported_events(self) -> List[str]:
        """Return list of supported event types.

        Returns:
            List of event type strings this observer handles
        """
        return [
            "plugin.loaded",
            "plugin.started",
            "plugin.stopped",
            "plugin.error"
        ]

    def handle_plugin_event(self, event: PluginEvent):
        """Handle plugin-specific events.

        Args:
            event: Plugin lifecycle event
        """
        if event.event_type == "plugin.loaded":
            self._on_plugin_loaded(event)
        elif event.event_type == "plugin.error":
            self._on_plugin_error(event)
```

### Observer Factory Integration

#### 1. Register Custom Observer
```python
from panther.core.observer.factory.observer_factory import get_observer_factory

def register_my_observer():
    """Register custom observer with factory."""
    factory = get_observer_factory()

    factory.register_observer_type(
        "my_custom",
        MyCustomObserver,
        config_schema={
            "enabled": bool,
            "filter_patterns": list,
            "output_format": str
        }
    )

# Register during application startup
register_my_observer()
```

#### 2. Configuration-Driven Creation
```yaml
# config/observers.yaml
observers:
  - type: my_custom
    enabled: true
    config:
      filter_patterns: ["test.*", "experiment.*"]
      output_format: "json"
```

```python
def load_observers_from_config():
    """Load observers from configuration file."""
    from panther.core.observer.factory.factory_config import load_observer_config

    observers = load_observer_config("config/observers.yaml")
    return observers
```

### Testing Guidelines

#### Unit Tests for Observers
```python
import pytest
from unittest.mock import Mock
from panther.core.events.test.events import TestStartedEvent

class TestMyCustomObserver:
    """Test suite for MyCustomObserver."""

    def test_interest_filtering(self):
        """Test event type interest filtering."""
        observer = MyCustomObserver()

        assert observer.is_interested("test.started")
        assert observer.is_interested("test.completed")
        assert not observer.is_interested("metrics.collected")

    def test_event_processing(self):
        """Test basic event processing."""
        observer = MyCustomObserver()
        event = TestStartedEvent(entity_id="test-123")

        observer.on_event(event)

        assert observer.processed_count == 1
        assert event.uuid in observer.processed_events_uuids

    def test_duplicate_prevention(self):
        """Test duplicate event prevention."""
        observer = MyCustomObserver()
        event = TestStartedEvent(entity_id="test-123")

        # Process same event twice
        observer.on_event(event)
        observer.on_event(event)

        assert observer.processed_count == 1  # Only processed once

    def test_error_handling(self):
        """Test graceful error handling."""
        observer = MyCustomObserver()
        observer._process_event = Mock(side_effect=Exception("Test error"))

        event = TestStartedEvent(entity_id="test-123")

        # Should not raise exception
        observer.on_event(event)

        assert observer.processed_count == 0  # Not incremented on error
```

#### Integration Tests
```python
import pytest
from panther.core.observer.management.event_manager import EventManager

@pytest.fixture
def event_manager():
    """Create event manager for testing."""
    return EventManager()

def test_observer_registration(event_manager):
    """Test observer registration and event routing."""
    observer = MyCustomObserver()
    event_manager.register_observer(observer)

    # Emit test event
    event = TestStartedEvent(entity_id="integration-test")
    event_manager.emit_event(event)

    assert observer.processed_count == 1

def test_multiple_observers(event_manager):
    """Test multiple observers receiving same event."""
    observer1 = MyCustomObserver()
    observer2 = MyCustomObserver()

    event_manager.register_observer(observer1)
    event_manager.register_observer(observer2)

    event = TestStartedEvent(entity_id="multi-test")
    event_manager.emit_event(event)

    assert observer1.processed_count == 1
    assert observer2.processed_count == 1
```

### Async Observer Development

#### Async Observer Implementation
```python
import asyncio
from panther.core.observer.base.observer_interface import IObserver

class MyAsyncObserver(IObserver):
    """Async observer for I/O bound operations."""

    def __init__(self):
        super().__init__()
        self.queue = asyncio.Queue()
        self.processor_task = None

    async def start_processing(self):
        """Start async event processing loop."""
        self.processor_task = asyncio.create_task(self._process_events())

    async def stop_processing(self):
        """Stop async processing and cleanup."""
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass

    def on_event(self, event: BaseEvent):
        """Queue event for async processing."""
        if event.uuid not in self.processed_events_uuids:
            asyncio.create_task(self.queue.put(event))

    async def _process_events(self):
        """Async event processing loop."""
        while True:
            try:
                event = await self.queue.get()
                await self._process_event_async(event)
                self.processed_events_uuids.append(event.uuid)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in async processing: {e}")

    async def _process_event_async(self, event: BaseEvent):
        """Override for async event processing."""
        # Example: async I/O operation
        await asyncio.sleep(0.1)  # Simulate async work
```

#### Testing Async Observers
```python
@pytest.mark.asyncio
async def test_async_observer():
    """Test async observer functionality."""
    observer = MyAsyncObserver()
    await observer.start_processing()

    try:
        event = TestStartedEvent(entity_id="async-test")
        observer.on_event(event)

        # Wait for processing
        await observer.queue.join()

        assert event.uuid in observer.processed_events_uuids
    finally:
        await observer.stop_processing()
```

## Performance Optimization

### Observer Performance Guidelines

#### Efficient Interest Filtering
```python
class OptimizedObserver(IObserver):
    """Observer with optimized interest filtering."""

    def __init__(self, event_prefixes: Set[str]):
        super().__init__()
        self.event_prefixes = event_prefixes

    def is_interested(self, event_type: str) -> bool:
        """Fast prefix-based filtering.

        O(1) lookup instead of string operations.
        """
        return any(event_type.startswith(prefix) for prefix in self.event_prefixes)
```

#### Batch Processing Pattern
```python
class BatchingObserver(IObserver):
    """Observer that processes events in batches."""

    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        super().__init__()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.event_batch = []
        self.last_flush = time.time()

    def on_event(self, event: BaseEvent):
        """Add event to batch for processing."""
        self.event_batch.append(event)

        if (len(self.event_batch) >= self.batch_size or
            time.time() - self.last_flush > self.flush_interval):
            self._flush_batch()

    def _flush_batch(self):
        """Process accumulated events in batch."""
        if not self.event_batch:
            return

        try:
            self._process_batch(self.event_batch)
            self.processed_events_uuids.extend(e.uuid for e in self.event_batch)
        finally:
            self.event_batch.clear()
            self.last_flush = time.time()
```

### Memory Management

#### Observer Lifecycle Management
```python
class ManagedObserver(IObserver):
    """Observer with automatic resource management."""

    def __init__(self, max_processed_events: int = 10000):
        super().__init__()
        self.max_processed_events = max_processed_events

    def on_event(self, event: BaseEvent):
        """Process event with memory management."""
        super().on_event(event)

        # Prevent unlimited growth of processed events list
        if len(self.processed_events_uuids) > self.max_processed_events:
            # Keep only recent half
            self.processed_events_uuids = self.processed_events_uuids[-self.max_processed_events//2:]

    def cleanup(self):
        """Cleanup observer resources."""
        self.processed_events_uuids.clear()
```

## Debugging and Troubleshooting

### Observer Debug Utilities

#### Debug Observer
```python
class DebugObserver(IObserver):
    """Observer that logs detailed processing information."""

    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger or logging.getLogger(__name__)
        self.processing_times = {}

    def on_event(self, event: BaseEvent):
        """Process event with detailed logging."""
        start_time = time.time()

        self.logger.debug(f"Processing event: {event.event_type} - {event.uuid}")

        try:
            super().on_event(event)
            processing_time = time.time() - start_time
            self.processing_times[event.event_type] = processing_time

            self.logger.debug(f"Processed in {processing_time:.3f}s")
        except Exception as e:
            self.logger.error(f"Error processing event {event.uuid}: {e}")
            raise
```

#### Performance Profiler
```python
class ProfilingObserver(IObserver):
    """Observer that profiles event processing performance."""

    def __init__(self):
        super().__init__()
        self.stats = {
            'total_events': 0,
            'processing_times': [],
            'error_count': 0,
            'events_by_type': defaultdict(int)
        }

    def on_event(self, event: BaseEvent):
        """Profile event processing."""
        start_time = time.perf_counter()

        try:
            super().on_event(event)
            processing_time = time.perf_counter() - start_time

            self.stats['total_events'] += 1
            self.stats['processing_times'].append(processing_time)
            self.stats['events_by_type'][event.event_type] += 1

        except Exception as e:
            self.stats['error_count'] += 1
            raise

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance statistics report."""
        if not self.stats['processing_times']:
            return {}

        times = self.stats['processing_times']
        return {
            'total_events': self.stats['total_events'],
            'avg_processing_time': statistics.mean(times),
            'median_processing_time': statistics.median(times),
            'max_processing_time': max(times),
            'error_rate': self.stats['error_count'] / self.stats['total_events'],
            'events_by_type': dict(self.stats['events_by_type'])
        }
```

### Common Issues and Solutions

#### Issue: Observer Not Receiving Events
```python
def debug_observer_registration():
    """Debug observer registration issues."""
    from panther.core.observer.management.event_manager import get_event_manager

    manager = get_event_manager()
    observers = manager.get_registered_observers()

    print(f"Registered observers: {len(observers)}")
    for i, observer in enumerate(observers):
        print(f"  {i}: {type(observer).__name__}")

        # Test interest filtering
        test_events = ["test.started", "metrics.collected", "error.occurred"]
        for event_type in test_events:
            interested = observer.is_interested(event_type)
            print(f"    {event_type}: {interested}")
```

#### Issue: Memory Leaks
```python
def check_observer_memory():
    """Check for observer memory issues."""
    import psutil
    import gc

    process = psutil.Process()

    print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB")
    print(f"Open file descriptors: {process.num_fds()}")

    # Check for observer objects
    observer_objects = [obj for obj in gc.get_objects() if isinstance(obj, IObserver)]
    print(f"Observer objects in memory: {len(observer_objects)}")

    # Check processed events list sizes
    for observer in observer_objects:
        events_count = len(observer.processed_events_uuids)
        print(f"  {type(observer).__name__}: {events_count} processed events")
```

#### Issue: Performance Degradation
```bash
# Profile observer performance
python -m cProfile -s cumulative -o observer_profile.prof test_observer_performance.py

# Analyze profile results
python -c "
import pstats
stats = pstats.Stats('observer_profile.prof')
stats.sort_stats('cumulative').print_stats(20)
"

# Memory profiling
python -m memory_profiler observer_memory_test.py
```

## Quality Checklist

### Code Quality
- [ ] Observer implements IObserver interface correctly
- [ ] Proper error handling and logging
- [ ] Thread-safe implementation if needed
- [ ] Resource cleanup in destructor/cleanup methods
- [ ] Type hints for all methods and parameters

### Testing Coverage
- [ ] Unit tests for all observer methods
- [ ] Integration tests with event manager
- [ ] Error condition testing
- [ ] Performance/load testing for high-volume scenarios
- [ ] Memory leak testing for long-running observers

### Documentation
- [ ] Class and method docstrings with Args/Returns
- [ ] Usage examples in docstrings
- [ ] Configuration documentation
- [ ] Performance characteristics documented
- [ ] Error handling behavior documented
