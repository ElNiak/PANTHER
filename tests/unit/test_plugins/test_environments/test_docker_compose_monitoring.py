"""Unit tests for Docker Compose BackgroundServiceMonitor."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    BackgroundServiceMonitor,
    DockerComposeEnvironment,
    ServiceHealthState,
)


class TestBackgroundServiceMonitor:
    """Test suite for BackgroundServiceMonitor class."""

    @pytest.fixture
    def mock_docker_env(self):
        """Create a mock DockerComposeEnvironment."""
        env = Mock(spec=DockerComposeEnvironment)
        env.logger = Mock()
        env._is_service_ready = Mock(return_value=True)
        env.request_early_termination = Mock()
        return env

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=EnvironmentConfig)
        config.monitoring_interval_seconds = 0.1  # Fast for testing
        config.failure_threshold_count = 2
        config.critical_services = ["critical_service"]
        config.allow_partial_deployment = False
        return config

    @pytest.fixture
    def monitor(self, mock_docker_env, mock_config):
        """Create a BackgroundServiceMonitor instance."""
        services = ["service1", "service2", "critical_service"]
        return BackgroundServiceMonitor(mock_docker_env, services, mock_config)

    def test_monitor_initialization(self, monitor):
        """Test monitor initialization."""
        assert monitor.monitoring_active is False
        assert monitor.monitor_thread is None
        assert len(monitor.services) == 3
        assert all(
            monitor.service_states[s] == ServiceHealthState.STARTING
            for s in monitor.services
        )
        assert all(monitor.failure_counts[s] == 0 for s in monitor.services)

    def test_start_monitoring(self, monitor):
        """Test starting the monitoring thread."""
        monitor.start_monitoring()

        assert monitor.monitoring_active is True
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        assert monitor.monitor_thread.daemon is True

        # Clean up
        monitor.stop_monitoring()

    def test_stop_monitoring(self, monitor):
        """Test stopping the monitoring thread."""
        monitor.start_monitoring()
        time.sleep(0.05)  # Let it start

        monitor.stop_monitoring()

        assert monitor.monitoring_active is False
        # Give thread time to stop
        time.sleep(0.2)
        assert not monitor.monitor_thread.is_alive()

    def test_double_start_monitoring(self, monitor):
        """Test that starting monitoring twice doesn't create multiple threads."""
        monitor.start_monitoring()
        first_thread = monitor.monitor_thread

        monitor.start_monitoring()
        second_thread = monitor.monitor_thread

        assert first_thread is second_thread

        # Clean up
        monitor.stop_monitoring()

    def test_service_health_check_all_healthy(self, monitor):
        """Test health checking when all services are healthy."""
        monitor.docker_compose_env._is_service_ready.return_value = True

        monitor._check_all_services()

        # All services should be ready
        assert all(
            monitor.service_states[s] == ServiceHealthState.READY
            for s in monitor.services
        )
        assert all(monitor.failure_counts[s] == 0 for s in monitor.services)

        # No early termination should be triggered
        monitor.docker_compose_env.request_early_termination.assert_not_called()

    def test_service_failure_detection(self, monitor):
        """Test detection of service failures."""

        # Make service1 unhealthy
        def mock_is_ready(service_name):
            return service_name != "service1"

        monitor.docker_compose_env._is_service_ready.side_effect = mock_is_ready

        # First check - failure count increases
        monitor._check_all_services()
        assert monitor.failure_counts["service1"] == 1
        assert monitor.service_states["service1"] == ServiceHealthState.FAILING

        # Second check - reaches threshold
        monitor._check_all_services()
        assert monitor.failure_counts["service1"] == 2
        assert monitor.service_states["service1"] == ServiceHealthState.FAILED

        # Early termination should be triggered
        monitor.docker_compose_env.request_early_termination.assert_called_once()
        args = monitor.docker_compose_env.request_early_termination.call_args[0]
        assert "service1" in args[0]
        assert args[1]["failed_service"] == "service1"

    def test_critical_service_failure(self, monitor):
        """Test that critical service failure triggers immediate termination."""

        # Make critical_service unhealthy
        def mock_is_ready(service_name):
            return service_name != "critical_service"

        monitor.docker_compose_env._is_service_ready.side_effect = mock_is_ready

        # Check services twice to reach threshold
        monitor._check_all_services()
        monitor._check_all_services()

        # Should trigger termination
        assert monitor.service_states["critical_service"] == ServiceHealthState.FAILED
        monitor.docker_compose_env.request_early_termination.assert_called_once()

        # Verify it's because of critical service
        args = monitor.docker_compose_env.request_early_termination.call_args[0]
        assert "critical_service" in args[0]

    def test_partial_deployment_allowed(self, monitor, mock_config):
        """Test behavior when partial deployment is allowed."""
        mock_config.allow_partial_deployment = True
        mock_config.critical_services = []

        # Make only one service fail
        def mock_is_ready(service_name):
            return service_name != "service1"

        monitor.docker_compose_env._is_service_ready.side_effect = mock_is_ready

        # Check twice to reach threshold
        monitor._check_all_services()
        monitor._check_all_services()

        # Should not terminate with only one failure
        monitor.docker_compose_env.request_early_termination.assert_not_called()

        # Make majority fail
        def mock_is_ready_majority_fail(service_name):
            return service_name == "service1"

        monitor.docker_compose_env._is_service_ready.side_effect = (
            mock_is_ready_majority_fail
        )

        # Check twice more
        monitor._check_all_services()
        monitor._check_all_services()

        # Now should terminate (more than half failed)
        monitor.docker_compose_env.request_early_termination.assert_called_once()

    def test_service_recovery(self, monitor):
        """Test that services can recover from failing state."""
        # Make service1 unhealthy initially
        monitor.docker_compose_env._is_service_ready.return_value = False

        monitor._check_all_services()
        assert monitor.failure_counts["service1"] == 1
        assert monitor.service_states["service1"] == ServiceHealthState.FAILING

        # Service recovers
        monitor.docker_compose_env._is_service_ready.return_value = True

        monitor._check_all_services()
        assert monitor.failure_counts["service1"] == 0  # Reset
        assert monitor.service_states["service1"] == ServiceHealthState.READY

    def test_monitor_thread_exception_handling(self, monitor, mock_config):
        """Test that monitor thread handles exceptions gracefully."""
        mock_config.monitoring_interval_seconds = 0.01

        # Make _check_all_services raise an exception
        monitor._check_all_services = Mock(side_effect=Exception("Test exception"))

        monitor.start_monitoring()
        time.sleep(0.1)  # Let it run a few iterations

        # Thread should still be alive despite exceptions
        assert monitor.monitor_thread.is_alive()

        # Clean up
        monitor.stop_monitoring()

    def test_monitoring_stops_after_termination(self, monitor):
        """Test that monitoring stops after triggering termination."""
        # Make all services fail
        monitor.docker_compose_env._is_service_ready.return_value = False

        # Check twice to trigger termination
        monitor._check_all_services()
        monitor._check_all_services()

        # Monitoring should be inactive after termination
        assert monitor.monitoring_active is False

    def test_thread_safety(self, monitor):
        """Test thread-safe access to service states."""
        monitor.start_monitoring()

        # Simulate concurrent access
        def read_states():
            for _ in range(10):
                _ = monitor.service_states.copy()
                time.sleep(0.01)

        threads = [threading.Thread(target=read_states) for _ in range(3)]
        for t in threads:
            t.start()

        # Let monitoring run concurrently
        time.sleep(0.2)

        for t in threads:
            t.join()

        # Should complete without deadlock
        monitor.stop_monitoring()

        # Verify lock is not held
        assert monitor.lock.acquire(blocking=False)
        monitor.lock.release()


class TestDockerComposeEnvironmentMonitoring:
    """Test suite for DockerComposeEnvironment monitoring integration."""

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        return Mock()

    @pytest.fixture
    def env_config(self):
        """Create environment configuration."""
        config = Mock(spec=EnvironmentConfig)
        config.type = "docker_compose"
        config.enable_background_monitoring = True
        config.monitoring_interval_seconds = 0.1
        config.failure_threshold_count = 2
        config.allow_partial_deployment = False
        config.critical_services = []
        return config

    @pytest.fixture
    def docker_env(self, env_config, mock_event_manager, tmp_path):
        """Create a DockerComposeEnvironment instance."""
        env = DockerComposeEnvironment(
            env_config_to_test=env_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="docker_compose",
            event_manager=mock_event_manager,
        )
        # Mock Docker operations
        env.execute_with_logging = Mock()
        env.execute_command = Mock()
        env.execute_docker_command = Mock()
        env._is_service_ready = Mock(return_value=True)
        return env

    def test_deploy_services_blocking_mode(self, docker_env, env_config):
        """Test deploy_services in blocking mode."""
        env_config.enable_background_monitoring = False

        # Mock service managers
        mock_service = Mock()
        mock_service.service_name = "test_service"
        docker_env.services_managers = [mock_service]

        # Mock monitoring method
        docker_env._monitor_single_service = Mock(return_value=True)

        with patch("concurrent.futures.ThreadPoolExecutor"):
            result = docker_env.deploy_services()

        assert result is True
        assert not hasattr(docker_env, "background_monitor")

    def test_deploy_services_non_blocking_mode(self, docker_env, env_config):
        """Test deploy_services in non-blocking mode."""
        env_config.enable_background_monitoring = True

        # Mock service managers
        mock_service = Mock()
        mock_service.service_name = "test_service"
        docker_env.services_managers = [mock_service]

        # Mock service ready check
        docker_env._is_service_ready = Mock(return_value=False)

        result = docker_env.deploy_services()

        assert result is True
        assert hasattr(docker_env, "background_monitor")
        assert docker_env.background_monitor.monitoring_active is True

        # Clean up
        docker_env.background_monitor.stop_monitoring()

    def test_teardown_stops_monitoring(self, docker_env):
        """Test that teardown stops background monitoring."""
        # Start monitoring
        docker_env.background_monitor = Mock()
        docker_env.background_monitor.stop_monitoring = Mock()

        # Mock other teardown operations
        docker_env._register_all_service_outputs = Mock()
        docker_env.collect_outputs = Mock(return_value={})

        docker_env._teardown_environment()

        docker_env.background_monitor.stop_monitoring.assert_called_once()

    def test_early_termination_integration(self, docker_env):
        """Test early termination request integration."""
        reason = "Service failure"
        details = {"service": "test_service"}

        docker_env.request_early_termination(reason, details)

        assert docker_env._early_termination_requested is True
        assert docker_env._early_termination_reason == reason
        assert docker_env._early_termination_details == details

        # Check should_terminate_early
        assert docker_env.should_terminate_early() is True
