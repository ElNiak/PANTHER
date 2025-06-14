"""Unit tests for event system integration with early termination."""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from panther.core.events.environment.events import (
    EnvironmentErrorEvent,
    EnvironmentEventType,
)
from panther.core.events.experiment.events import (
    ExperimentEventType,
    ExperimentFinishedEarlyEvent,
    ExperimentServiceFailureEvent,
)
from panther.core.observer.impl.experiment_observer import ExperimentObserver
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    BackgroundServiceMonitor,
    DockerComposeEnvironment,
)


class TestEventSystemIntegration:
    """Test suite for event system integration with early termination."""

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager with event tracking."""
        manager = Mock(spec=EventManager)
        manager.emitted_events = []

        def track_event(event):
            manager.emitted_events.append(event)

        manager.emit_event = Mock(side_effect=track_event)
        manager.get_observer_by_type = Mock()
        return manager

    @pytest.fixture
    def experiment_observer(self):
        """Create an ExperimentObserver instance."""
        observer = ExperimentObserver(
            name="test_experiment_observer", track_timing=False, track_steps=False
        )
        return observer

    @pytest.fixture
    def mock_env_config(self):
        """Create a mock environment configuration."""
        config = Mock(spec=EnvironmentConfig)
        config.type = "docker_compose"
        config.enable_background_monitoring = True
        config.monitoring_interval_seconds = 0.1
        config.failure_threshold_count = 2
        config.critical_services = ["critical_service"]
        config.allow_partial_deployment = False
        return config

    def test_environment_error_event_creation(self):
        """Test EnvironmentErrorEvent creation and attributes."""
        event = EnvironmentErrorEvent(
            environment_id="env_123",
            environment_name="test_env",
            environment_type="docker_compose",
            error_message="Service failure detected",
            error_type="service_failure",
            error_details={"failed_service": "test_service"},
        )

        assert event.event_type == EnvironmentEventType.ERROR
        assert event.environment_id == "env_123"
        assert event.error_message == "Service failure detected"
        assert event.error_type == "service_failure"
        assert event.error_details == {"failed_service": "test_service"}

    def test_experiment_service_failure_event_creation(self):
        """Test ExperimentServiceFailureEvent creation and attributes."""
        event = ExperimentServiceFailureEvent(
            experiment_id="exp_123",
            test_id="test_456",
            service_name="failing_service",
            failure_reason="Connection refused",
            failure_details={"exit_code": 1, "last_log": "Error: Cannot bind to port"},
        )

        assert event.event_type == ExperimentEventType.SERVICE_FAILURE
        assert event.service_name == "failing_service"
        assert event.failure_reason == "Connection refused"
        assert event.failure_details["exit_code"] == 1

    def test_experiment_observer_handles_environment_error(self, experiment_observer):
        """Test ExperimentObserver handling of EnvironmentErrorEvent."""
        # Create an environment error event
        error_event = EnvironmentErrorEvent(
            environment_id="env_123",
            environment_name="docker_compose",
            environment_type="network",
            error_message="Experiment finished early: Service 'web' failed",
            error_type="early_termination",
        )

        # Handle the event
        result = experiment_observer.on_event(error_event)

        assert result is True
        assert experiment_observer._should_terminate_early is True
        assert experiment_observer.experiment_finished_early is True
        assert "Service 'web' failed" in experiment_observer._termination_reason

    def test_experiment_observer_handles_service_failure(self, experiment_observer):
        """Test ExperimentObserver handling of ExperimentServiceFailureEvent."""
        # Create a service failure event
        failure_event = ExperimentServiceFailureEvent(
            experiment_id="exp_123",
            test_id="test_456",
            service_name="critical_service",
            failure_reason="Health check failed",
            failure_details={"attempts": 3},
        )

        # Handle the event
        result = experiment_observer.on_event(failure_event)

        assert result is True
        assert experiment_observer._should_terminate_early is True
        assert "critical_service" in experiment_observer._termination_reason
        assert "Health check failed" in experiment_observer._termination_reason

    def test_experiment_observer_ignores_non_termination_errors(
        self, experiment_observer
    ):
        """Test that ExperimentObserver ignores non-early-termination errors."""
        # Create a regular error event (not early termination)
        error_event = EnvironmentErrorEvent(
            environment_id="env_123",
            environment_name="docker_compose",
            environment_type="network",
            error_message="Warning: Low disk space",
            error_type="warning",
        )

        # Handle the event
        result = experiment_observer.on_event(error_event)

        assert result is True
        assert experiment_observer._should_terminate_early is False
        assert experiment_observer.experiment_finished_early is False

    def test_background_monitor_emits_events_through_environment(
        self, mock_event_manager, mock_env_config, tmp_path
    ):
        """Test that BackgroundServiceMonitor triggers events through the environment."""
        # Create environment with event manager
        env = DockerComposeEnvironment(
            env_config_to_test=mock_env_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="docker_compose",
            event_manager=mock_event_manager,
        )

        # Mock Docker operations
        env._is_service_ready = Mock(return_value=False)

        # Create and start monitor
        services = ["failing_service"]
        monitor = BackgroundServiceMonitor(env, services, mock_env_config)

        # Simulate service failures
        monitor._check_all_services()
        monitor._check_all_services()  # Reach failure threshold

        # Verify early termination was requested on environment
        assert env._early_termination_requested is True
        assert "failing_service" in env._early_termination_reason

    def test_event_propagation_chain(self, mock_event_manager, experiment_observer):
        """Test the complete event propagation chain from monitor to observer."""
        # Set up event manager to return our observer
        mock_event_manager.get_observer_by_type.return_value = experiment_observer

        # Create an environment error event
        error_event = EnvironmentErrorEvent(
            environment_id="env_123",
            environment_name="test_env",
            environment_type="docker_compose",
            error_message="Experiment finished early: Critical service failed",
            error_type="early_termination",
        )

        # Simulate event emission
        mock_event_manager.emit_event(error_event)

        # Process the event through the observer
        experiment_observer.on_event(error_event)

        # Verify the chain worked
        assert len(mock_event_manager.emitted_events) == 1
        assert mock_event_manager.emitted_events[0] == error_event
        assert experiment_observer.should_terminate_early() is True

    def test_concurrent_event_handling(self, experiment_observer):
        """Test that observer handles concurrent events correctly."""
        import threading

        events_processed = []

        def emit_events():
            for i in range(5):
                event = EnvironmentErrorEvent(
                    environment_id=f"env_{i}",
                    environment_name="test_env",
                    environment_type="docker_compose",
                    error_message=f"Experiment finished early: Service {i} failed",
                    error_type="early_termination",
                )
                result = experiment_observer.on_event(event)
                if result:
                    events_processed.append(i)
                time.sleep(0.01)

        # Start multiple threads emitting events
        threads = [threading.Thread(target=emit_events) for _ in range(3)]
        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should have processed events and set termination flag
        assert len(events_processed) > 0
        assert experiment_observer.should_terminate_early() is True

    def test_event_details_preservation(self, experiment_observer):
        """Test that event details are preserved through the handling chain."""
        detailed_failure = {
            "service": "database",
            "exit_code": 1,
            "last_logs": ["Connection refused", "Shutting down"],
            "container_id": "abc123",
            "timestamp": "2024-01-01T12:00:00Z",
        }

        event = ExperimentServiceFailureEvent(
            experiment_id="exp_123",
            test_id="test_456",
            service_name="database",
            failure_reason="Database connection failed",
            failure_details=detailed_failure,
        )

        experiment_observer.on_event(event)

        # Details should be preserved in termination reason
        assert "database" in experiment_observer._termination_reason
        assert "Database connection failed" in experiment_observer._termination_reason

    def test_multiple_failure_events_first_wins(self, experiment_observer):
        """Test that only the first failure event sets the termination reason."""
        # First failure event
        event1 = ExperimentServiceFailureEvent(
            experiment_id="exp_123",
            test_id="test_456",
            service_name="service1",
            failure_reason="First failure",
            failure_details={},
        )

        # Second failure event
        event2 = ExperimentServiceFailureEvent(
            experiment_id="exp_123",
            test_id="test_456",
            service_name="service2",
            failure_reason="Second failure",
            failure_details={},
        )

        # Handle both events
        experiment_observer.on_event(event1)
        experiment_observer.on_event(event2)

        # First failure should be the termination reason
        assert "service1" in experiment_observer._termination_reason
        assert "First failure" in experiment_observer._termination_reason
        assert "service2" not in experiment_observer._termination_reason

    @pytest.mark.parametrize(
        "error_type,should_terminate",
        [
            ("early_termination", True),
            ("service_failure", True),
            ("warning", False),
            ("info", False),
            ("debug", False),
        ],
    )
    def test_error_type_handling(
        self, experiment_observer, error_type, should_terminate
    ):
        """Test that different error types are handled appropriately."""
        event = EnvironmentErrorEvent(
            environment_id="env_123",
            environment_name="test_env",
            environment_type="docker_compose",
            error_message=f"Test message for {error_type}",
            error_type=error_type,
        )

        # For early termination errors, include the expected prefix
        if error_type == "early_termination":
            event.error_message = f"Experiment finished early: {event.error_message}"

        experiment_observer.on_event(event)

        assert experiment_observer.should_terminate_early() == should_terminate
