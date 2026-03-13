"""Integration tests for early termination feature with non-blocking monitoring."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.config.core.models.experiment import TestConfig
from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.impl.experiment_observer import ExperimentObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.test_cases.test_case_impl import TestCase
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.network_environment.base_environment_monitor import (
    ServiceHealthState,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    BackgroundServiceMonitor,
    DockerComposeEnvironment,
)


class TestEarlyTermination:
    """Test suite for early termination functionality."""

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        manager = Mock(spec=EventManager)
        manager.get_observer_by_type = Mock()
        return manager

    @pytest.fixture
    def mock_env_config(self):
        """Create a mock environment configuration with monitoring enabled."""
        config = Mock(spec=EnvironmentConfig)
        config.type = "docker_compose"
        config.enable_background_monitoring = True
        config.monitoring_interval_seconds = 1
        config.failure_threshold_count = 2
        config.allow_partial_deployment = False
        config.critical_services = ["critical_service"]
        return config

    @pytest.fixture
    def docker_compose_env(self, mock_env_config, mock_event_manager, tmp_path):
        """Create a DockerComposeEnvironment instance for testing."""
        env = DockerComposeEnvironment(
            env_config_to_test=mock_env_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="docker_compose",
            event_manager=mock_event_manager,
        )
        # Mock some methods to avoid actual Docker operations
        env.execute_with_logging = Mock()
        env.execute_command = Mock()
        env.execute_docker_command = Mock()
        env._is_service_ready = Mock(return_value=False)
        return env

    def test_background_monitor_initialization(
        self, docker_compose_env, mock_env_config
    ):
        """Test BackgroundServiceMonitor initialization."""
        services = ["service1", "service2"]
        monitor = BackgroundServiceMonitor(
            docker_compose_env, services, mock_env_config
        )

        assert monitor.docker_compose_env == docker_compose_env
        assert monitor.services == services
        assert monitor.config == mock_env_config
        assert not monitor.monitoring_active
        assert all(
            monitor.service_states[s] == ServiceHealthState.STARTING for s in services
        )
        assert all(monitor.failure_counts[s] == 0 for s in services)

    def test_background_monitor_start_stop(self, docker_compose_env, mock_env_config):
        """Test starting and stopping background monitoring."""
        services = ["service1"]
        monitor = BackgroundServiceMonitor(
            docker_compose_env, services, mock_env_config
        )

        # Start monitoring
        monitor.start_monitoring()
        assert monitor.monitoring_active
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()

        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor.monitoring_active
        # Give thread time to stop
        time.sleep(0.1)
        assert not monitor.monitor_thread.is_alive()

    def test_service_failure_detection(self, docker_compose_env, mock_env_config):
        """Test that service failures are detected and trigger early termination."""
        services = ["failing_service"]
        monitor = BackgroundServiceMonitor(
            docker_compose_env, services, mock_env_config
        )

        # Mock service as unhealthy
        docker_compose_env._is_service_ready = Mock(return_value=False)

        # Start monitoring
        monitor.start_monitoring()

        # Wait for failure threshold to be exceeded
        time.sleep(
            mock_env_config.monitoring_interval_seconds
            * (mock_env_config.failure_threshold_count + 1)
        )

        # Check that service is marked as failed
        assert monitor.service_states["failing_service"] == ServiceHealthState.FAILED
        assert (
            monitor.failure_counts["failing_service"]
            >= mock_env_config.failure_threshold_count
        )

        # Check that early termination was requested
        assert docker_compose_env._early_termination_requested
        assert docker_compose_env._early_termination_reason is not None
        assert "failing_service" in docker_compose_env._early_termination_reason

        # Stop monitoring
        monitor.stop_monitoring()

    def test_critical_service_triggers_termination(
        self, docker_compose_env, mock_env_config
    ):
        """Test that critical service failure triggers immediate termination."""
        services = ["critical_service", "normal_service"]
        monitor = BackgroundServiceMonitor(
            docker_compose_env, services, mock_env_config
        )

        # Mock critical service as unhealthy, normal as healthy
        def mock_is_ready(service_name):
            return service_name != "critical_service"

        docker_compose_env._is_service_ready = Mock(side_effect=mock_is_ready)

        # Start monitoring
        monitor.start_monitoring()

        # Wait for failure detection
        time.sleep(
            mock_env_config.monitoring_interval_seconds
            * (mock_env_config.failure_threshold_count + 1)
        )

        # Check that termination was triggered due to critical service
        assert docker_compose_env._early_termination_requested
        assert "critical_service" in docker_compose_env._early_termination_reason

        monitor.stop_monitoring()

    def test_non_blocking_deployment(self, docker_compose_env, mock_env_config):
        """Test non-blocking deployment mode."""
        # Set up service managers
        mock_service_manager = Mock()
        mock_service_manager.service_name = "test_service"
        docker_compose_env.services_managers = [mock_service_manager]

        # Mock service as initially not ready
        docker_compose_env._is_service_ready = Mock(return_value=False)

        # Deploy services in non-blocking mode
        result = docker_compose_env._deploy_services_non_blocking()

        # Should return True immediately
        assert result is True

        # Background monitor should be created and started
        assert hasattr(docker_compose_env, "background_monitor")
        assert docker_compose_env.background_monitor.monitoring_active

        # Clean up
        docker_compose_env.background_monitor.stop_monitoring()

    def test_backward_compatibility_blocking_mode(
        self, docker_compose_env, mock_env_config
    ):
        """Test backward compatibility with blocking deployment mode."""
        # Disable background monitoring
        mock_env_config.enable_background_monitoring = False

        # Set up service managers
        mock_service_manager = Mock()
        mock_service_manager.service_name = "test_service"
        docker_compose_env.services_managers = [mock_service_manager]

        # Mock service as ready
        docker_compose_env._is_service_ready = Mock(return_value=True)
        docker_compose_env._monitor_single_service = Mock(return_value=True)

        # Deploy services - should use blocking mode
        with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor:
            mock_future = Mock()
            mock_future.result = Mock(return_value=True)
            mock_executor.return_value.__enter__.return_value.submit.return_value = (
                mock_future
            )

            result = docker_compose_env.deploy_services()

        # Should use blocking deployment
        assert result is True
        assert not hasattr(docker_compose_env, "background_monitor")

    def test_experiment_observer_handles_environment_errors(self):
        """Test that ExperimentObserver properly handles environment error events."""
        observer = ExperimentObserver(
            name="test_observer", track_timing=False, track_steps=False
        )

        # Create environment error event
        from panther.core.events.environment.events import EnvironmentEvent

        error_event = EnvironmentEvent.error(
            environment_id="test_env",
            environment_name="test",
            environment_type="docker_compose",
            error_message="Experiment finished early: Service failure",
            error_type="early_termination",
        )

        # Handle the event
        result = observer.on_event(error_event)

        assert result is True
        assert observer._should_terminate_early
        assert observer.experiment_finished_early
        assert "Service failure" in observer._termination_reason

    def test_test_case_checks_early_termination(self):
        """Test that TestCase properly checks for early termination during step execution."""
        # Create mock configurations
        test_config = Mock(spec=TestConfig)
        test_config.name = "test_early_termination"
        test_config.steps = {"wait": 10}

        global_config = Mock(spec=GlobalConfig)
        global_config.logging.level.name = "INFO"
        global_config.logging.format = "%(message)s"

        plugin_manager = Mock()
        experiment_dir = Path("/tmp/test")

        # Create test case
        test_case = TestCase(
            test_config=test_config,
            global_config=global_config,
            plugin_manager=plugin_manager,
            experiment_dir=experiment_dir,
        )

        # Mock environment manager with early termination
        mock_env_manager = Mock()
        mock_env_manager.should_terminate_early = Mock(return_value=True)
        test_case.environment_plugin_manager = [mock_env_manager]

        # Mock event manager and observer
        mock_event_manager = Mock()
        mock_observer = Mock()
        mock_observer.should_terminate_early = Mock(return_value=False)
        mock_event_manager.get_observer_by_type = Mock(return_value=mock_observer)
        test_case.event_manager = mock_event_manager

        # Mock emitters
        test_case.step_emitter = Mock()
        test_case.experiment_emitter = Mock()

        # Execute steps - should terminate early
        test_case.execute_steps()

        # Verify early termination was detected
        assert mock_env_manager.should_terminate_early.called
        assert test_case.experiment_emitter.emit_finished_early.called

    @pytest.mark.requires_docker
    def test_end_to_end_early_termination(self, docker_compose_env, mock_env_config):
        """End-to-end test of early termination with real threading."""
        services = ["service1", "service2"]

        # Set up service managers
        for service in services:
            mock_manager = Mock()
            mock_manager.service_name = service
            docker_compose_env.services_managers.append(mock_manager)

        # Mock service health checks
        health_check_count = 0

        def mock_health_check(service_name):
            nonlocal health_check_count
            health_check_count += 1
            # Fail after a few checks to simulate service failure
            return health_check_count < 3

        docker_compose_env._is_service_ready = Mock(side_effect=mock_health_check)

        # Deploy with non-blocking monitoring
        result = docker_compose_env._deploy_services_non_blocking()
        assert result is True

        # Wait for service failure detection
        max_wait = 10  # seconds
        start_time = time.time()
        while (
            not docker_compose_env._early_termination_requested
            and (time.time() - start_time) < max_wait
        ):
            time.sleep(0.1)

        # Verify early termination was triggered
        assert docker_compose_env._early_termination_requested
        assert docker_compose_env._early_termination_reason is not None

        # Clean up
        if hasattr(docker_compose_env, "background_monitor"):
            docker_compose_env.background_monitor.stop_monitoring()
