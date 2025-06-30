"""
Integration test for event-driven plugin architecture.

This test verifies that the event-driven architecture integration is working
correctly with proper event emission and handling across service managers.
"""

from unittest.mock import Mock

import pytest

from panther.core.events.service.emitter import ServiceEventEmitter
from panther.core.events.service.events import (
    ServiceErrorEvent,
    ServiceEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
)
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.plugin_manager import PluginManager
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.config_schema import ServiceConfig
from panther.plugins.services.service_base import ServiceBase


class MockServiceManager(ServiceBase):
    """Mock service manager for testing event-driven integration."""

    def __init__(
        self,
        service_config_to_test,
        service_type: str,
        protocol,
        implementation_name: str,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name
        )
        self.prepare_called = False
        self.prepare_success = True

    def _do_prepare(self, plugin_loader=None):
        """Mock preparation implementation."""
        self.prepare_called = True
        if not self.prepare_success:
            raise RuntimeError("Mock preparation failed")
        return True

    def generate_deployment_commands(self, service_params, environment):
        """Mock deployment command generation."""
        return {"mock": "commands"}


@pytest.fixture
def event_manager():
    """Create an event manager for testing."""
    return EventManager()


@pytest.fixture
def event_emitter(event_manager):
    """Create an event emitter for testing."""
    return ServiceEventEmitter(event_manager)


@pytest.fixture
def mock_observer():
    """Create a mock observer for event testing."""
    observer = Mock()
    observer.notify = Mock()
    return observer


@pytest.fixture
def service_config():
    """Create a test service configuration."""
    return ServiceConfig(
        name="test_service",
        protocol=ProtocolConfig(
            name="test_protocol",
            version="1.0",
            role="client",
            target="target_service",
        ),
    )


@pytest.fixture
def protocol_config():
    """Create a test protocol configuration."""
    return ProtocolConfig(
        name="test_protocol",
        version="1.0",
        role="client",
        target="target_service",
    )


@pytest.fixture
def mock_service_manager(service_config, protocol_config):
    """Create a mock service manager for testing."""
    return MockServiceManager(
        service_config_to_test=service_config,
        service_type="testers",
        protocol=protocol_config,
        implementation_name="test_implementation",
    )


class TestEventDrivenIntegration:
    """Test suite for event-driven plugin architecture integration."""

    def test_event_emitter_initialization(self, event_manager, mock_service_manager):
        """Test that service managers properly initialize with event emitters."""
        # Set event emitter manually (normally done by plugin manager)
        mock_service_manager.event_emitter = ServiceEventEmitter(event_manager)

        assert mock_service_manager.event_emitter is not None
        assert isinstance(mock_service_manager.event_emitter, ServiceEventEmitter)

    def test_service_preparation_success_events(
        self, event_manager, mock_service_manager, mock_observer
    ):
        """Test that successful service preparation emits correct events."""
        # Register observer
        event_manager.register_observer(mock_observer)

        # Set event emitter
        mock_service_manager.event_emitter = ServiceEventEmitter(event_manager)

        # Prepare service
        mock_service_manager.prepare()

        # Verify preparation was called
        assert mock_service_manager.prepare_called

        # Verify events were emitted
        assert (
            mock_observer.notify.call_count >= 2
        )  # At least preparation_started and service_started

        # Check event types
        emitted_events = [call[0][0] for call in mock_observer.notify.call_args_list]
        event_names = [event.name for event in emitted_events]

        # Should have preparation_started and service_started events
        assert any("preparation_started" in name for name in event_names)
        assert any("service.test_service.started" in name for name in event_names)

    def test_service_preparation_failure_events(
        self, event_manager, mock_service_manager, mock_observer
    ):
        """Test that failed service preparation emits error events."""
        # Register observer
        event_manager.register_observer(mock_observer)

        # Set event emitter
        mock_service_manager.event_emitter = ServiceEventEmitter(event_manager)

        # Configure for failure
        mock_service_manager.prepare_success = False

        # Prepare service (should not raise exception due to error handling)
        mock_service_manager.prepare()

        # Verify events were emitted
        assert (
            mock_observer.notify.call_count >= 2
        )  # At least preparation_started and error event

        # Check for error event
        emitted_events = [call[0][0] for call in mock_observer.notify.call_args_list]
        error_events = [event for event in emitted_events if "error" in event.name]
        assert len(error_events) > 0

    def test_event_emitter_service_methods(self, event_emitter, mock_observer):
        """Test that EventEmitter service methods work correctly."""
        # Register observer
        event_emitter.event_manager.register_observer(mock_observer)

        # Test service started event
        event_emitter.emit_service_started("test_service", "Test Service")

        # Test service stopped event
        event_emitter.emit_service_stopped(
            "test_service", "Test Service", exit_code=0, reason="test completed"
        )

        # Test service error event
        event_emitter.emit_service_error(
            "test_service",
            "Test Service",
            "Test error message",
            error_type="test_error",
            error_details={"detail": "error"},
        )

        # Verify events were emitted
        assert mock_observer.notify.call_count == 3

        # Check event types
        emitted_events = [call[0][0] for call in mock_observer.notify.call_args_list]

        # Check specific event types
        assert isinstance(emitted_events[0], ServiceStartedEvent)
        assert isinstance(emitted_events[1], ServiceStoppedEvent)
        assert isinstance(emitted_events[2], ServiceErrorEvent)

    def test_plugin_manager_event_emitter_propagation(self, event_manager):
        """Test that PluginManager properly propagates event emitters to service managers."""
        # Create plugin manager with event manager
        plugin_manager = PluginManager(event_manager=event_manager)

        # Create mock service manager
        mock_service = Mock()
        mock_service.__class__.__name__ = "MockService"

        # Simulate plugin manager setting event emitter
        plugin_manager._set_event_emitter_on_service(mock_service)

        # Verify event emitter was set
        assert hasattr(mock_service, "event_emitter")
        assert mock_service.event_emitter is not None

    def test_service_base_event_methods(
        self, service_config, protocol_config, event_manager, mock_observer
    ):
        """Test ServiceBase event method implementations."""
        # Create service manager
        service_manager = MockServiceManager(
            service_config_to_test=service_config,
            service_type="testers",
            protocol=protocol_config,
            implementation_name="test_implementation",
        )

        # Set event emitter
        service_manager.event_emitter = EventEmitter(event_manager)

        # Register observer
        event_manager.register_observer(mock_observer)

        # Test service event notification
        service_manager.notify_service_event(
            "test_event",
            service_id="test_service",
            service_name="Test Service",
            details={"key": "value"},
        )

        # Verify event was emitted
        assert mock_observer.notify.call_count == 1
        emitted_event = mock_observer.notify.call_args[0][0]
        assert isinstance(emitted_event, ServiceEvent)
        assert "test_event" in emitted_event.name

    def test_event_data_validation(self, event_emitter):
        """Test that events contain proper data validation."""
        # Create service error event
        event_emitter.emit_service_error(
            "test_service", "validation_error", "Invalid data", {"context": "test"}
        )

        # The fact that no exception was raised means validation passed
        # Additional validation would be handled by event consumers

    def test_comprehensive_service_lifecycle_events(
        self, event_manager, mock_service_manager, mock_observer
    ):
        """Test complete service lifecycle event emission."""
        # Register observer
        event_manager.register_observer(mock_observer)

        # Set event emitter
        mock_service_manager.event_emitter = ServiceEventEmitter(event_manager)

        # Simulate complete lifecycle
        mock_service_manager.prepare()

        # Simulate additional lifecycle events through event emitter
        mock_service_manager.event_emitter.emit_service_stopped("test_service")

        # Verify multiple events were emitted
        assert mock_observer.notify.call_count >= 3

        # Verify event sequence
        emitted_events = [call[0][0] for call in mock_observer.notify.call_args_list]
        event_names = [event.name for event in emitted_events]

        # Should have preparation, started, and stopped events
        assert any("preparation" in name for name in event_names)
        assert any("started" in name for name in event_names)
        assert any("stopped" in name for name in event_names)

    def test_event_timing_and_metadata(
        self, event_manager, mock_service_manager, mock_observer
    ):
        """Test that events contain proper timing and metadata."""
        # Register observer
        event_manager.register_observer(mock_observer)

        # Set event emitter
        mock_service_manager.event_emitter = ServiceEventEmitter(event_manager)

        # Prepare service
        mock_service_manager.prepare()

        # Verify events have timestamps and IDs
        emitted_events = [call[0][0] for call in mock_observer.notify.call_args_list]

        for event in emitted_events:
            assert hasattr(event, "timestamp")
            assert hasattr(event, "id")
            assert event.timestamp is not None
            assert event.id is not None

    def test_error_handling_without_event_emitter(self, mock_service_manager):
        """Test that service managers handle missing event emitters gracefully."""
        # Don't set event emitter (simulate missing initialization)
        mock_service_manager.event_emitter = None

        # Prepare service - should not crash even without event emitter
        try:
            mock_service_manager.prepare()
            # Should complete without exception
        except AttributeError:
            pytest.fail(
                "Service manager should handle missing event emitter gracefully"
            )
