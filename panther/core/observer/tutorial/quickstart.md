# Observer System Quickstart

This tutorial demonstrates how to create and use observers to monitor events in PANTHER's testing framework.

## Basic Observer Creation

### Step 1: Create Your First Observer

```python
from panther.core.observer.base.observer_interface import IObserver
from panther.core.events.base.event_base import BaseEvent

class MyFirstObserver(IObserver):
    """Simple observer that logs events to console."""

    def __init__(self):
        super().__init__()
        self.event_count = 0

    def is_interested(self, event_type: str) -> bool:
        """Only process test-related events."""
        return event_type.startswith("test.")

    def on_event(self, event: BaseEvent):
        """Process incoming events."""
        # Check for duplicates
        if event.uuid in self.processed_events_uuids:
            return

        # Process the event
        print(f"📅 {event.timestamp}")
        print(f"🎯 Event: {event.event_type}")
        print(f"🏷️  Entity: {event.entity_type}:{event.entity_id}")
        print(f"🆔 UUID: {event.uuid}")
        print("---")

        # Mark as processed
        self.processed_events_uuids.append(event.uuid)
        self.event_count += 1

# Test the observer
observer = MyFirstObserver()

# Simulate an event (normally events come from emitters)
from panther.core.events.test.events import TestStartedEvent
from datetime import datetime

event = TestStartedEvent(
    entity_id="test-001",
    test_name="Connection Test",
    start_time=datetime.now()
)

# Check interest and process
if observer.is_interested(event.event_type.value):
    observer.on_event(event)

print(f"Total events processed: {observer.event_count}")
```

### Step 2: Create a Specialized Observer

```python
from typing import Dict, Any
import json

class TestMetricsObserver(IObserver):
    """Observer that collects test performance metrics."""

    def __init__(self):
        super().__init__()
        self.test_metrics = {}
        self.test_start_times = {}

    def is_interested(self, event_type: str) -> bool:
        """Track test start and completion events."""
        return event_type in [
            "test.started",
            "test.completed",
            "test.failed"
        ]

    def on_event(self, event: BaseEvent):
        """Collect test metrics from events."""
        if event.uuid in self.processed_events_uuids:
            return

        entity_id = event.entity_id

        if event.event_type.value == "test.started":
            self.test_start_times[entity_id] = event.timestamp
            self.test_metrics[entity_id] = {
                "name": getattr(event, 'test_name', 'Unknown'),
                "status": "running",
                "start_time": event.timestamp.isoformat()
            }

        elif event.event_type.value in ["test.completed", "test.failed"]:
            if entity_id in self.test_start_times:
                duration = (event.timestamp - self.test_start_times[entity_id]).total_seconds()
                self.test_metrics[entity_id].update({
                    "status": "completed" if event.event_type.value == "test.completed" else "failed",
                    "end_time": event.timestamp.isoformat(),
                    "duration_seconds": duration
                })

                if hasattr(event, 'error_message'):
                    self.test_metrics[entity_id]["error"] = event.error_message

        self.processed_events_uuids.append(event.uuid)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected test metrics."""
        total_tests = len(self.test_metrics)
        completed = sum(1 for m in self.test_metrics.values() if m["status"] == "completed")
        failed = sum(1 for m in self.test_metrics.values() if m["status"] == "failed")
        running = sum(1 for m in self.test_metrics.values() if m["status"] == "running")

        durations = [m.get("duration_seconds", 0) for m in self.test_metrics.values()
                    if "duration_seconds" in m]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_tests": total_tests,
            "completed": completed,
            "failed": failed,
            "running": running,
            "average_duration": avg_duration,
            "tests": self.test_metrics
        }

    def export_metrics(self, filename: str):
        """Export metrics to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.get_metrics_summary(), f, indent=2)

# Test the metrics observer
metrics_observer = TestMetricsObserver()

# Simulate test lifecycle
test_events = [
    TestStartedEvent(entity_id="test-001", test_name="HTTP Test", start_time=datetime.now()),
    TestCompletedEvent(entity_id="test-001", test_name="HTTP Test",
                      end_time=datetime.now(), duration=2.5),
    TestStartedEvent(entity_id="test-002", test_name="HTTPS Test", start_time=datetime.now()),
    TestFailedEvent(entity_id="test-002", test_name="HTTPS Test",
                   failure_time=datetime.now(), error_message="Connection timeout")
]

for event in test_events:
    if metrics_observer.is_interested(event.event_type.value):
        metrics_observer.on_event(event)

# View metrics
summary = metrics_observer.get_metrics_summary()
print(json.dumps(summary, indent=2))
```

## Using the Observer Factory

### Step 3: Factory-Based Observer Creation

```python
from panther.core.observer.factory.observer_factory import get_observer_factory

# Get the global factory instance
factory = get_observer_factory()

# Create built-in observers with configuration
logger_observer = factory.create_observer("logger", {
    "level": "INFO",
    "colored": True,
    "format": "detailed"
})

metrics_observer = factory.create_observer("metrics", {
    "interval": 1.0,
    "metrics": ["cpu", "memory"],
    "storage": "memory"
})

storage_observer = factory.create_observer("storage", {
    "backend": "file",
    "file_path": "test_events.jsonl",
    "compression": True
})

print("Created observers:")
print(f"- Logger: {type(logger_observer).__name__}")
print(f"- Metrics: {type(metrics_observer).__name__}")
print(f"- Storage: {type(storage_observer).__name__}")
```

### Step 4: Register Custom Observer with Factory

```python
# Register our custom observer type
factory.register_observer_type(
    name="test_metrics",
    class_type=TestMetricsObserver,
    config_schema={
        "export_file": str,
        "auto_export": bool
    }
)

# Now create via factory
custom_observer = factory.create_observer("test_metrics", {
    "export_file": "custom_metrics.json",
    "auto_export": True
})

print(f"Created custom observer: {type(custom_observer).__name__}")
```

## Working with Event Manager

### Step 5: Complete Observer Integration

```python
from panther.core.observer.management.event_manager import EventManager

# Create event manager
event_manager = EventManager()

# Create and register observers
observers = [
    factory.create_observer("logger", {"level": "INFO"}),
    TestMetricsObserver(),
    factory.create_observer("storage", {"backend": "file", "file_path": "events.log"})
]

for observer in observers:
    event_manager.register_observer(observer)

print(f"Registered {len(observers)} observers")

# Emit events through manager (normally done by emitters)
test_events = [
    TestStartedEvent(entity_id="integration-test", test_name="Full Integration",
                    start_time=datetime.now()),
]

for event in test_events:
    event_manager.emit_event(event)

print("Events emitted to all interested observers")

# Get observer processing stats
registered = event_manager.get_registered_observers()
print(f"Total registered observers: {len(registered)}")
```

## Advanced Observer Patterns

### Step 6: Filtered Observer

```python
class FilteredTestObserver(IObserver):
    """Observer with advanced filtering capabilities."""

    def __init__(self, entity_filter=None, test_name_pattern=None):
        super().__init__()
        self.entity_filter = entity_filter or []
        self.test_name_pattern = test_name_pattern
        self.filtered_events = []

    def is_interested(self, event_type: str) -> bool:
        """Filter by event type."""
        return event_type.startswith("test.")

    def on_event(self, event: BaseEvent):
        """Apply additional filtering logic."""
        if event.uuid in self.processed_events_uuids:
            return

        # Entity filtering
        if self.entity_filter and event.entity_id not in self.entity_filter:
            return

        # Test name pattern filtering
        if self.test_name_pattern and hasattr(event, 'test_name'):
            if self.test_name_pattern.lower() not in event.test_name.lower():
                return

        # Process filtered event
        self.filtered_events.append({
            "event_type": event.event_type.value,
            "entity_id": event.entity_id,
            "timestamp": event.timestamp.isoformat(),
            "test_name": getattr(event, 'test_name', 'N/A')
        })

        self.processed_events_uuids.append(event.uuid)

    def get_filtered_events(self):
        """Get events that passed filters."""
        return self.filtered_events

# Use filtered observer
filtered_observer = FilteredTestObserver(
    entity_filter=["critical-test-001", "critical-test-002"],
    test_name_pattern="critical"
)

event_manager.register_observer(filtered_observer)
```

### Step 7: Async Observer (Advanced)

```python
import asyncio
from typing import List

class AsyncLoggerObserver(IObserver):
    """Observer that processes events asynchronously."""

    def __init__(self):
        super().__init__()
        self.event_queue = asyncio.Queue()
        self.processing_task = None
        self.processed_count = 0

    async def start_processing(self):
        """Start async event processing loop."""
        self.processing_task = asyncio.create_task(self._process_events())

    async def stop_processing(self):
        """Stop async processing gracefully."""
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

    def is_interested(self, event_type: str) -> bool:
        return True  # Process all events

    def on_event(self, event: BaseEvent):
        """Queue event for async processing."""
        if event.uuid not in self.processed_events_uuids:
            # Non-blocking queue operation
            try:
                self.event_queue.put_nowait(event)
            except asyncio.QueueFull:
                print(f"Warning: Event queue full, dropping event {event.uuid}")

    async def _process_events(self):
        """Async event processing loop."""
        while True:
            try:
                event = await self.event_queue.get()
                await self._process_event_async(event)
                self.processed_events_uuids.append(event.uuid)
                self.processed_count += 1
                self.event_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing event: {e}")

    async def _process_event_async(self, event: BaseEvent):
        """Async event processing - simulate I/O work."""
        # Simulate async logging to external service
        await asyncio.sleep(0.1)
        print(f"[ASYNC] Processed {event.event_type} for {event.entity_id}")

# Use async observer (in async context)
async def demo_async_observer():
    async_observer = AsyncLoggerObserver()
    await async_observer.start_processing()

    try:
        # Process some events
        events = [
            TestStartedEvent(entity_id=f"async-test-{i}",
                           test_name=f"Async Test {i}",
                           start_time=datetime.now())
            for i in range(5)
        ]

        for event in events:
            async_observer.on_event(event)

        # Wait for processing to complete
        await async_observer.event_queue.join()
        print(f"Processed {async_observer.processed_count} events asynchronously")

    finally:
        await async_observer.stop_processing()

# Run async demo (uncomment to test)
# asyncio.run(demo_async_observer())
```

## Observer Configuration with YAML

### Step 8: Configuration-Driven Observers

```python
# Create config file: observer_config.yaml
yaml_config = """
observers:
  - type: logger
    enabled: true
    config:
      level: DEBUG
      colored: true
      format: detailed

  - type: test_metrics
    enabled: true
    config:
      export_file: test_results.json
      auto_export: true

  - type: storage
    enabled: true
    config:
      backend: file
      file_path: panther_events.jsonl
      compression: true
      retention_days: 7
"""

# Save config to file
with open("observer_config.yaml", "w") as f:
    f.write(yaml_config)

# Load observers from config
from panther.core.observer.factory.factory_config import load_observer_config

observers = load_observer_config("observer_config.yaml")
print(f"Loaded {len(observers)} observers from config")

# Register all loaded observers
for observer in observers:
    event_manager.register_observer(observer)
```

## Testing Your Observers

### Step 9: Observer Testing Patterns

```python
import unittest
from unittest.mock import Mock

class TestMyObserver(unittest.TestCase):
    """Test suite for custom observers."""

    def setUp(self):
        self.observer = TestMetricsObserver()

    def test_interest_filtering(self):
        """Test event type interest filtering."""
        self.assertTrue(self.observer.is_interested("test.started"))
        self.assertTrue(self.observer.is_interested("test.completed"))
        self.assertFalse(self.observer.is_interested("service.started"))

    def test_event_processing(self):
        """Test basic event processing."""
        event = TestStartedEvent(
            entity_id="test-123",
            test_name="Unit Test",
            start_time=datetime.now()
        )

        self.observer.on_event(event)

        self.assertIn("test-123", self.observer.test_metrics)
        self.assertEqual(self.observer.test_metrics["test-123"]["status"], "running")

    def test_duplicate_prevention(self):
        """Test duplicate event prevention."""
        event = TestStartedEvent(
            entity_id="test-123",
            test_name="Duplicate Test",
            start_time=datetime.now()
        )

        # Process same event twice
        self.observer.on_event(event)
        initial_count = len(self.observer.test_metrics)

        self.observer.on_event(event)  # Duplicate
        final_count = len(self.observer.test_metrics)

        self.assertEqual(initial_count, final_count)

    def test_metrics_calculation(self):
        """Test metrics calculation accuracy."""
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=5)

        start_event = TestStartedEvent(
            entity_id="test-duration",
            test_name="Duration Test",
            start_time=start_time
        )

        complete_event = TestCompletedEvent(
            entity_id="test-duration",
            test_name="Duration Test",
            end_time=end_time,
            duration=5.0
        )

        self.observer.on_event(start_event)
        self.observer.on_event(complete_event)

        summary = self.observer.get_metrics_summary()
        self.assertEqual(summary["total_tests"], 1)
        self.assertEqual(summary["completed"], 1)
        self.assertAlmostEqual(summary["average_duration"], 5.0, places=1)

# Run tests
if __name__ == "__main__":
    unittest.main()
```

## Best Practices

### Observer Design Guidelines

1. **Interest Filtering**: Always implement `is_interested()` efficiently
2. **Duplicate Handling**: Check `processed_events_uuids` in `on_event()`
3. **Error Handling**: Wrap processing logic in try-catch blocks
4. **Resource Management**: Clean up resources in destructor/cleanup methods
5. **Thread Safety**: Use locks for shared state in multi-threaded environments

### Performance Tips

1. **Batch Processing**: Process multiple events together when possible
2. **Async I/O**: Use async observers for I/O-bound operations
3. **Memory Management**: Limit size of `processed_events_uuids` list
4. **Selective Filtering**: Filter events as early as possible
5. **Lazy Evaluation**: Defer expensive calculations until needed

### Testing Strategies

1. **Unit Tests**: Test individual observer methods
2. **Integration Tests**: Test with real event manager
3. **Performance Tests**: Measure processing throughput
4. **Error Tests**: Verify graceful error handling
5. **Configuration Tests**: Test factory creation with various configs

This tutorial covers the essential patterns for creating and using observers in PANTHER. See the API reference for complete details on all observer types and advanced configuration options.
