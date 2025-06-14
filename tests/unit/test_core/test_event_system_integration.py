"""Tests for the new event-driven architecture integration."""
from unittest.mock import Mock, patch

import pytest

from panther.core.events.experiment.events import ExperimentEvent
from panther.core.events.service.events import ServiceEvent
from panther.core.events.test.events import TestEvent

pytestmark = [pytest.mark.unit, pytest.mark.event_system]


class TestEventSystemIntegration:
    """Test the integration of the new event-driven architecture."""

    def test_experiment_event_creation(self, mock_event_manager):
        """Test that experiment events are created correctly."""
        event = ExperimentEvent.create_started("test_experiment")

        assert event.event_type == "experiment.started"
        assert event.data["experiment_name"] == "test_experiment"
        assert "timestamp" in event.data
        assert "uuid" in event.data

    def test_service_event_creation(self, mock_event_manager):
        """Test that service events are created correctly."""
        event = ServiceEvent.create_deployed("test_service", {"config": "test"})

        assert event.event_type == "service.deployed"
        assert event.data["service_name"] == "test_service"
        assert event.data["metadata"]["config"] == "test"

    def test_test_event_creation(self, mock_event_manager):
        """Test that test events are created correctly."""
        event = TestEvent.create_completed("test_case", True, {"result": "success"})

        assert event.event_type == "test.completed"
        assert event.data["test_name"] == "test_case"
        assert event.data["success"] is True
        assert event.data["result_data"]["result"] == "success"

    @patch("panther.core.observer.management.event_manager.EventManager")
    def test_event_propagation(self, mock_manager_class):
        """Test that events are properly propagated through the system."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        # Simulate event emission
        event = ExperimentEvent.create_started("test_experiment")
        mock_manager.emit_event(event)

        # Verify the event was emitted
        mock_manager.emit_event.assert_called_once_with(event)

    def test_event_observer_integration(self, mock_event_manager):
        """Test that observers are properly integrated with events."""
        # Create mock observers
        mock_logger_observer = Mock()
        mock_metrics_observer = Mock()

        mock_event_manager.add_observer(mock_logger_observer)
        mock_event_manager.add_observer(mock_metrics_observer)

        # Create and emit an event
        event = ServiceEvent.create_deployed("test_service", {})
        mock_event_manager.emit_event(event)

        # Verify observers were notified
        mock_event_manager.add_observer.assert_any_call(mock_logger_observer)
        mock_event_manager.add_observer.assert_any_call(mock_metrics_observer)
        mock_event_manager.emit_event.assert_called_with(event)


@pytest.mark.integration
class TestEventCommandProcessorIntegration:
    """Test integration between event system and command processor."""

    def test_command_generation_events(
        self, mock_event_manager, mock_command_processor
    ):
        """Test that command generation emits appropriate events."""
        # Mock command generation
        mock_command_processor.generate_commands.return_value = {
            "run_cmd": {"command_binary": "test", "command_args": "--test"}
        }

        # Simulate command generation with event emission
        commands = mock_command_processor.generate_commands("test_service")

        # Verify command generation was called
        mock_command_processor.generate_commands.assert_called_once_with("test_service")
        assert commands["run_cmd"]["command_binary"] == "test"

    def test_command_validation_events(
        self, mock_event_manager, mock_command_processor
    ):
        """Test that command validation emits events."""
        # Mock validation
        mock_command_processor.validate_command.return_value = True

        test_command = {"command_binary": "test", "timeout": 60}
        result = mock_command_processor.validate_command(test_command)

        mock_command_processor.validate_command.assert_called_once_with(test_command)
        assert result is True
