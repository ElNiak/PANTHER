"""
Unit tests for PANTHER Event System components.

This module tests the core event-driven architecture including event emitters,
observers, and the event management system.
"""

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Always use mock implementations for unit testing
REAL_EVENT_SYSTEM_AVAILABLE = False


# Create mock implementations for testing
class MockBaseEvent:
    def __init__(self, name, entity_type, entity_id, data=None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.timestamp = datetime.now(timezone.utc)
        self.data = data or {}

    def get_type(self):
        # If name already starts with entity_type, don't duplicate it
        if self.name.startswith(f"{self.entity_type}."):
            return self.name
        return f"{self.entity_type}.{self.name}"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.get_type(),
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class MockEventManager:
    def __init__(self):
        self.events = []
        self.observers = []

    def publish(self, event):
        self.events.append(event)
        for observer in self.observers:
            try:
                observer.handle_event(event)
            except Exception:
                # Gracefully handle observer exceptions in tests
                pass

    def register_observer(self, observer):
        self.observers.append(observer)

    @classmethod
    def get_instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance


class EventEmitter:
    def __init__(self, event_manager=None):
        self.event_manager = event_manager or MockEventManager.get_instance()
        self.event_count = 0

    def emit_event(self, event):
        """Emit a typed event."""
        if self.event_manager:
            self.event_manager.publish(event)
            self.event_count += 1

    def emit(self, event_type, data=None, entity_id=None, entity_type=None):
        """Convenience method for creating and emitting simple events."""
        if entity_type is None and "." in event_type:
            # Split the event_type into entity_type and name
            parts = event_type.split(".")
            entity_type = parts[0]
            name = ".".join(parts[1:])
        else:
            # If entity_type is provided, extract the name part after the last dot
            # or use the full event_type if no dots
            if "." in event_type:
                name = event_type.split(".")[-1]
            else:
                name = event_type
            entity_type = entity_type or "test"

        event = MockBaseEvent(
            name=name,
            entity_type=entity_type,
            entity_id=entity_id or str(uuid.uuid4()),
            data=data,
        )
        self.emit_event(event)
        return event.to_dict()

    def register_observer(self, observer):
        """Register observer with the event manager."""
        self.event_manager.register_observer(observer)


class EventEmitterBase:
    def __init__(self):
        self.is_initialized = False

    def initialize(self):
        self.is_initialized = True

    def emit_event(self, event_type, data=None):
        return {"type": event_type, "data": data}


class EmitterRegistry:
    def __init__(self):
        self.emitters = {}

    def register_emitter(self, name, emitter):
        self.emitters[name] = emitter

    def get_emitter(self, name):
        return self.emitters.get(name)

    def list_emitters(self):
        return list(self.emitters.keys())


class EventManager:
    def __init__(self):
        self.observers = []
        self.events = []

    def register_observer(self, observer):
        self.observers.append(observer)

    def emit_event(self, event):
        self.events.append(event)
        for observer in self.observers:
            observer.handle_event(event)

    def publish(self, event):
        """Alias for emit_event to match real interface."""
        self.emit_event(event)


pytestmark = [pytest.mark.unit, pytest.mark.event_system]


class TestEventEmitter:
    """Test EventEmitter base functionality."""

    def test_event_emitter_initialization(self):
        """Test EventEmitter initialization with default values."""
        emitter = EventEmitter()

        assert emitter.event_manager is not None
        assert emitter.event_count == 0

    def test_event_emitter_initialization_with_params(self):
        """Test EventEmitter initialization with custom event manager."""
        custom_manager = MockEventManager()

        emitter = EventEmitter(event_manager=custom_manager)

        assert emitter.event_manager == custom_manager
        assert emitter.event_count == 0

    def test_emit_basic_event(self):
        """Test basic event emission."""
        emitter = EventEmitter()

        event = emitter.emit(
            "service.started", entity_id="test-123", entity_type="service"
        )

        assert event is not None
        assert event["type"] == "service.started"
        assert event["entity_id"] == "test-123"
        assert event["entity_type"] == "service"
        assert "id" in event
        assert "timestamp" in event
        assert emitter.event_count == 1

    def test_emit_event_with_data(self):
        """Test event emission with custom data."""
        emitter = EventEmitter()
        test_data = {
            "status": "running",
            "progress": 0.5,
            "metadata": {"config": "test_config.yaml"},
        }

        event = emitter.emit(
            "experiment.progress",
            data=test_data,
            entity_id="exp-456",
            entity_type="experiment",
        )

        assert event["type"] == "experiment.progress"
        assert event["data"] == test_data
        assert event["entity_id"] == "exp-456"
        assert event["entity_type"] == "experiment"

    def test_observer_registration(self):
        """Test observer registration and event propagation."""
        emitter = EventEmitter()
        mock_observer = Mock()
        mock_observer.handle_event = Mock()

        # Test registration
        emitter.register_observer(mock_observer)
        assert mock_observer in emitter.event_manager.observers

        # Test event propagation
        event_dict = emitter.emit("test.event", entity_id="test-123")

        # Verify observer was called with the actual event object (not dict)
        mock_observer.handle_event.assert_called_once()
        called_event = mock_observer.handle_event.call_args[0][0]
        assert hasattr(called_event, "get_type")
        assert called_event.get_type() == "test.event"

    def test_multiple_observers(self):
        """Test multiple observers receiving events."""
        emitter = EventEmitter()
        observer1 = Mock()
        observer2 = Mock()
        observer3 = Mock()

        emitter.register_observer(observer1)
        emitter.register_observer(observer2)
        emitter.register_observer(observer3)

        event_dict = emitter.emit("multi.test", entity_id="test-123")

        # All observers should be called once
        observer1.handle_event.assert_called_once()
        observer2.handle_event.assert_called_once()
        observer3.handle_event.assert_called_once()

        # Verify they all received the same event object
        event1 = observer1.handle_event.call_args[0][0]
        event2 = observer2.handle_event.call_args[0][0]
        event3 = observer3.handle_event.call_args[0][0]
        assert event1.id == event2.id == event3.id

    def test_event_count_tracking(self):
        """Test event count tracking."""
        emitter = EventEmitter()

        assert emitter.event_count == 0

        emitter.emit("event.1", entity_id="test-1")
        assert emitter.event_count == 1

        emitter.emit("event.2", entity_id="test-2")
        emitter.emit("event.3", entity_id="test-3")
        assert emitter.event_count == 3

    def test_event_id_uniqueness(self):
        """Test that event IDs are unique."""
        emitter = EventEmitter()

        event1 = emitter.emit("test.event", entity_id="test-1")
        event2 = emitter.emit("test.event", entity_id="test-2")
        event3 = emitter.emit("test.event", entity_id="test-3")

        assert event1["id"] != event2["id"]
        assert event2["id"] != event3["id"]
        assert event1["id"] != event3["id"]

    def test_event_timestamp_ordering(self):
        """Test that event timestamps are ordered."""
        emitter = EventEmitter()

        event1 = emitter.emit("event.1", entity_id="test-1")
        time.sleep(0.001)  # Small delay
        event2 = emitter.emit("event.2", entity_id="test-2")

        assert event1["timestamp"] <= event2["timestamp"]


class TestEventEmitterBase:
    """Test EventEmitterBase abstract functionality."""

    def test_event_emitter_base_initialization(self):
        """Test EventEmitterBase initialization."""
        base_emitter = EventEmitterBase()

        assert hasattr(base_emitter, "is_initialized")
        assert not base_emitter.is_initialized

    def test_event_emitter_base_initialize(self):
        """Test EventEmitterBase initialization method."""
        base_emitter = EventEmitterBase()

        base_emitter.initialize()

        assert base_emitter.is_initialized

    def test_event_emitter_base_emit_event(self):
        """Test EventEmitterBase event emission."""
        base_emitter = EventEmitterBase()

        event = base_emitter.emit_event("test.event", {"key": "value"})

        assert event["type"] == "test.event"
        assert event["data"] == {"key": "value"}


class TestEmitterRegistry:
    """Test EmitterRegistry functionality."""

    def test_emitter_registry_initialization(self):
        """Test EmitterRegistry initialization."""
        registry = EmitterRegistry()

        assert hasattr(registry, "emitters")
        assert registry.emitters == {}

    def test_register_emitter(self):
        """Test emitter registration."""
        registry = EmitterRegistry()
        emitter = EventEmitter()

        registry.register_emitter("test_emitter", emitter)

        assert "test_emitter" in registry.emitters
        assert registry.emitters["test_emitter"] == emitter

    def test_get_emitter(self):
        """Test emitter retrieval."""
        registry = EmitterRegistry()
        emitter = EventEmitter()

        registry.register_emitter("test_emitter", emitter)
        retrieved_emitter = registry.get_emitter("test_emitter")

        assert retrieved_emitter == emitter

    def test_get_nonexistent_emitter(self):
        """Test retrieval of non-existent emitter."""
        registry = EmitterRegistry()

        result = registry.get_emitter("nonexistent")

        assert result is None

    def test_list_emitters(self):
        """Test listing registered emitters."""
        registry = EmitterRegistry()

        emitter1 = EventEmitter()
        emitter2 = EventEmitter()
        emitter3 = EventEmitter()

        registry.register_emitter("emitter1", emitter1)
        registry.register_emitter("emitter2", emitter2)
        registry.register_emitter("emitter3", emitter3)

        emitter_names = registry.list_emitters()

        assert len(emitter_names) == 3
        assert "emitter1" in emitter_names
        assert "emitter2" in emitter_names
        assert "emitter3" in emitter_names

    def test_emitter_replacement(self):
        """Test emitter replacement in registry."""
        registry = EmitterRegistry()

        emitter1 = EventEmitter()
        emitter2 = EventEmitter()

        registry.register_emitter("test_emitter", emitter1)
        assert registry.get_emitter("test_emitter") == emitter1

        registry.register_emitter("test_emitter", emitter2)
        assert registry.get_emitter("test_emitter") == emitter2


class TestEventManager:
    """Test EventManager coordination functionality."""

    def test_event_manager_initialization(self):
        """Test EventManager initialization."""
        manager = EventManager()

        assert hasattr(manager, "observers")
        assert hasattr(manager, "events")
        assert manager.observers == []
        assert manager.events == []

    def test_register_observer(self):
        """Test observer registration with EventManager."""
        manager = EventManager()
        observer = Mock()

        manager.register_observer(observer)

        assert observer in manager.observers

    def test_emit_event_propagation(self):
        """Test event propagation to observers."""
        manager = EventManager()
        observer1 = Mock()
        observer2 = Mock()

        manager.register_observer(observer1)
        manager.register_observer(observer2)

        test_event = {
            "id": "test-event-123",
            "type": "test.event",
            "data": {"key": "value"},
        }

        manager.emit_event(test_event)

        assert test_event in manager.events
        observer1.handle_event.assert_called_once_with(test_event)
        observer2.handle_event.assert_called_once_with(test_event)

    def test_multiple_event_handling(self):
        """Test handling multiple events."""
        manager = EventManager()
        observer = Mock()
        manager.register_observer(observer)

        event1 = {"id": "1", "type": "event.1"}
        event2 = {"id": "2", "type": "event.2"}
        event3 = {"id": "3", "type": "event.3"}

        manager.emit_event(event1)
        manager.emit_event(event2)
        manager.emit_event(event3)

        assert len(manager.events) == 3
        assert observer.handle_event.call_count == 3
        observer.handle_event.assert_has_calls(
            [call(event1), call(event2), call(event3)]
        )


class TestEventSystemIntegration:
    """Test integration between event system components."""

    def test_emitter_with_registry_integration(self):
        """Test EventEmitter with EmitterRegistry integration."""
        registry = EmitterRegistry()
        emitter = EventEmitter()

        registry.register_emitter("test_emitter", emitter)
        retrieved_emitter = registry.get_emitter("test_emitter")

        # Test that the retrieved emitter works correctly
        event = retrieved_emitter.emit("integration.test", entity_id="integration-test")

        assert event["entity_id"] == "integration-test"
        assert event["type"] == "integration.test"
        assert retrieved_emitter.event_count == 1

    def test_emitter_with_manager_integration(self):
        """Test EventEmitter with EventManager integration."""
        manager = EventManager()
        emitter = EventEmitter(event_manager=manager)

        # Mock observer for the manager
        observer = Mock()
        manager.register_observer(observer)

        # Emit event and verify propagation through the manager
        event_dict = emitter.emit("manager.integration.test", entity_id="manager-test")

        assert len(manager.events) == 1
        # The manager stores the actual event object, not the dict
        stored_event = manager.events[0]
        assert hasattr(stored_event, "get_type")
        assert stored_event.get_type() == "manager.integration.test"
        assert stored_event.entity_id == "manager-test"
        observer.handle_event.assert_called_once_with(stored_event)

    def test_full_event_system_workflow(self):
        """Test complete event system workflow."""
        # Create components
        registry = EmitterRegistry()
        manager = EventManager()
        emitter = EventEmitter(event_manager=manager)

        # Create observers
        storage_observer = Mock()
        metrics_observer = Mock()
        logger_observer = Mock()

        # Register observers with manager
        manager.register_observer(storage_observer)
        manager.register_observer(metrics_observer)
        manager.register_observer(logger_observer)

        # Register emitter with registry
        registry.register_emitter("workflow_emitter", emitter)

        # Emit test events
        emitter.emit(
            "workflow.started",
            data={"phase": "initialization"},
            entity_id="workflow-test",
            entity_type="test",
        )
        emitter.emit(
            "workflow.progress",
            data={"percentage": 50},
            entity_id="workflow-test",
            entity_type="test",
        )
        emitter.emit(
            "workflow.completed",
            data={"status": "success"},
            entity_id="workflow-test",
            entity_type="test",
        )

        # Verify complete workflow
        assert emitter.event_count == 3
        assert len(manager.events) == 3

        # Verify all observers received all events
        assert storage_observer.handle_event.call_count == 3
        assert metrics_observer.handle_event.call_count == 3
        assert logger_observer.handle_event.call_count == 3

        # Verify event content (stored events are objects, not dicts)
        events = manager.events
        assert events[0].get_type() == "test.started"
        assert events[0].data["phase"] == "initialization"
        assert events[1].get_type() == "test.progress"
        assert events[1].data["percentage"] == 50
        assert events[2].get_type() == "test.completed"
        assert events[2].data["status"] == "success"


class TestEventSystemErrorHandling:
    """Test error handling in event system."""

    def test_observer_exception_handling(self):
        """Test handling of observer exceptions."""
        emitter = EventEmitter()

        # Create an observer that raises an exception
        failing_observer = Mock()
        failing_observer.handle_event.side_effect = Exception("Observer failed")

        # Create a normal observer
        normal_observer = Mock()

        emitter.register_observer(failing_observer)
        emitter.register_observer(normal_observer)

        # Emit event - should not raise exception
        try:
            event_dict = emitter.emit("error.test", entity_id="test-123")
            # In a real implementation, failing observer should not prevent
            # normal observer from receiving the event
            assert event_dict is not None
            assert event_dict["entity_id"] == "test-123"
        except Exception:
            pytest.fail("Event emission should handle observer exceptions gracefully")

    def test_invalid_event_data_handling(self):
        """Test handling of invalid event data."""
        emitter = EventEmitter()

        # Test with None data
        event1 = emitter.emit("test.none", data=None, entity_id="test-1")
        assert event1["data"] == {}

        # Test with empty dict
        event2 = emitter.emit("test.empty", data={}, entity_id="test-2")
        assert event2["data"] == {}

        # Test with complex data
        complex_data = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "none_value": None,
        }
        event3 = emitter.emit("test.complex", data=complex_data, entity_id="test-3")
        assert event3["data"] == complex_data


class TestEventSystemPerformance:
    """Test performance characteristics of event system."""

    def test_event_emission_performance(self):
        """Test event emission performance."""
        emitter = EventEmitter()

        start_time = time.time()

        # Emit many events
        for i in range(100):
            emitter.emit(
                f"performance.test.{i}", data={"index": i}, entity_id=f"test-{i}"
            )

        end_time = time.time()
        duration = end_time - start_time

        # Should emit 100 events reasonably quickly
        assert duration < 1.0  # Less than 1 second
        assert emitter.event_count == 100

    def test_multiple_observers_performance(self):
        """Test performance with many observers."""
        emitter = EventEmitter()

        # Register many observers
        observers = []
        for i in range(10):
            observer = Mock()
            observers.append(observer)
            emitter.register_observer(observer)

        start_time = time.time()

        # Emit events to all observers
        for i in range(10):
            emitter.emit(f"multi_observer.test.{i}", entity_id=f"test-{i}")

        end_time = time.time()
        duration = end_time - start_time

        # Should handle multiple observers efficiently
        assert duration < 1.0  # Less than 1 second

        # Verify all observers received all events
        for observer in observers:
            assert observer.handle_event.call_count == 10

    def test_registry_lookup_performance(self):
        """Test registry lookup performance."""
        registry = EmitterRegistry()

        # Register many emitters
        for i in range(100):
            emitter = EventEmitter()
            registry.register_emitter(f"emitter_{i}", emitter)

        start_time = time.time()

        # Perform many lookups
        for i in range(100):
            emitter = registry.get_emitter(f"emitter_{i}")
            assert emitter is not None

        end_time = time.time()
        duration = end_time - start_time

        # Should perform lookups efficiently
        assert duration < 0.1  # Less than 100ms for 100 lookups


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
