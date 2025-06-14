"""Unit tests for Localhost SingleContainerMonitor."""

import threading
import time
from enum import Enum
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import (
    ContainerState,
    LocalhostSingleContainerEnvironment,
    SingleContainerMonitor,
)


class TestSingleContainerMonitor:
    """Test suite for SingleContainerMonitor class."""

    @pytest.fixture
    def mock_localhost_env(self):
        """Create a mock LocalhostSingleContainerEnvironment."""
        env = Mock(spec=LocalhostSingleContainerEnvironment)
        env.logger = Mock()
        env.execute_docker_command = Mock()
        env.request_early_termination = Mock()
        return env

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=EnvironmentConfig)
        config.monitoring_interval_seconds = 0.1  # Fast for testing
        config.failure_threshold_count = 2
        return config

    @pytest.fixture
    def monitor(self, mock_localhost_env, mock_config):
        """Create a SingleContainerMonitor instance."""
        container_name = "test_container"
        return SingleContainerMonitor(mock_localhost_env, container_name, mock_config)

    def test_monitor_initialization(self, monitor):
        """Test monitor initialization."""
        assert monitor.container_name == "test_container"
        assert monitor.container_state == ContainerState.INITIALIZING
        assert monitor.failure_count == 0
        assert monitor.monitoring_active is False
        assert monitor.monitor_thread is None

    def test_start_monitoring(self, monitor):
        """Test starting the monitoring thread."""
        monitor.start_monitoring()

        assert monitor.monitoring_active is True
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        assert monitor.monitor_thread.daemon is True
        assert (
            monitor.monitor_thread.name == f"ContainerMonitor-{monitor.container_name}"
        )

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

    def test_container_health_check_healthy(self, monitor):
        """Test health checking when container is healthy."""
        # Mock container as running
        monitor.localhost_env.execute_docker_command.return_value = Mock(
            stdout="container_id_123\n", stderr=""
        )

        # Check health
        is_healthy = monitor._is_container_healthy()

        assert is_healthy is True

        # Verify Docker commands were called
        assert monitor.localhost_env.execute_docker_command.call_count >= 1
        first_call = monitor.localhost_env.execute_docker_command.call_args_list[0]
        assert "ps" in first_call[1]["docker_args"]
        assert f"name=^{monitor.container_name}$" in first_call[1]["docker_args"]

    def test_container_health_check_not_running(self, monitor):
        """Test health checking when container is not running."""
        # First call returns empty (container not running)
        # Second call returns exit status
        monitor.localhost_env.execute_docker_command.side_effect = [
            Mock(stdout="", stderr=""),
            Mock(stdout="Exited (1) 10 seconds ago", stderr=""),
        ]

        is_healthy = monitor._is_container_healthy()

        assert is_healthy is False
        assert monitor.localhost_env.execute_docker_command.call_count == 2

    def test_container_health_check_unhealthy_status(self, monitor):
        """Test health checking when container reports unhealthy status."""
        # Container is running but unhealthy
        monitor.localhost_env.execute_docker_command.side_effect = [
            Mock(stdout="container_id_123\n", stderr=""),  # Container is running
            Mock(stdout="unhealthy", stderr=""),  # Health status is unhealthy
        ]

        is_healthy = monitor._is_container_healthy()

        assert is_healthy is False

    def test_container_failure_detection(self, monitor):
        """Test detection of container failures."""
        # Mock container as unhealthy
        monitor._is_container_healthy = Mock(return_value=False)

        # First check - failure count increases
        monitor._check_container_health()
        assert monitor.failure_count == 1

        # Second check - reaches threshold
        monitor._check_container_health()
        assert monitor.failure_count == 2
        assert monitor.container_state == ContainerState.FAILED

        # Early termination should be triggered
        monitor.localhost_env.request_early_termination.assert_called_once()
        args = monitor.localhost_env.request_early_termination.call_args[0]
        assert "test_container" in args[0]
        assert args[1]["container_name"] == "test_container"
        assert args[1]["failure_count"] == 2

    def test_container_recovery(self, monitor):
        """Test that container can recover from failing state."""
        # Mock container as initially unhealthy
        monitor._is_container_healthy = Mock(return_value=False)

        monitor._check_container_health()
        assert monitor.failure_count == 1

        # Container recovers
        monitor._is_container_healthy = Mock(return_value=True)

        monitor._check_container_health()
        assert monitor.failure_count == 0  # Reset
        assert monitor.container_state == ContainerState.RUNNING

    def test_monitor_thread_exception_handling(self, monitor, mock_config):
        """Test that monitor thread handles exceptions gracefully."""
        mock_config.monitoring_interval_seconds = 0.01

        # Make _check_container_health raise an exception
        monitor._check_container_health = Mock(side_effect=Exception("Test exception"))

        monitor.start_monitoring()
        time.sleep(0.1)  # Let it run a few iterations

        # Thread should still be alive despite exceptions
        assert monitor.monitor_thread.is_alive()

        # Logger should have logged the error
        monitor.logger.error.assert_called()

        # Clean up
        monitor.stop_monitoring()

    def test_monitoring_stops_after_termination(self, monitor):
        """Test that monitoring stops after triggering termination."""
        # Mock container failure
        monitor._is_container_healthy = Mock(return_value=False)

        # Check twice to trigger termination
        monitor._check_container_health()
        monitor._check_container_health()

        # Monitoring should be inactive after termination
        assert monitor.monitoring_active is False

    def test_get_container_logs_on_failure(self, monitor):
        """Test that container logs are retrieved on failure."""
        # Mock container as unhealthy
        monitor._is_container_healthy = Mock(return_value=False)

        # Mock log retrieval
        monitor.localhost_env.execute_docker_command.return_value = Mock(
            stdout="Error: Service failed to start\nConnection refused", stderr=""
        )

        # Check twice to trigger failure
        monitor._check_container_health()
        monitor._check_container_health()

        # Verify logs were retrieved
        log_calls = [
            call
            for call in monitor.localhost_env.execute_docker_command.call_args_list
            if "logs" in call[1]["docker_args"]
        ]
        assert len(log_calls) > 0
        assert "--tail" in log_calls[0][1]["docker_args"]
        assert "50" in log_calls[0][1]["docker_args"]

    def test_thread_safety(self, monitor):
        """Test thread-safe access to container state."""
        monitor.start_monitoring()

        # Simulate concurrent access
        def read_state():
            for _ in range(10):
                _ = monitor.container_state
                _ = monitor.failure_count
                time.sleep(0.01)

        threads = [threading.Thread(target=read_state) for _ in range(3)]
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


class TestLocalhostSingleContainerEnvironmentMonitoring:
    """Test suite for LocalhostSingleContainerEnvironment monitoring integration."""

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        return Mock()

    @pytest.fixture
    def env_config(self):
        """Create environment configuration."""
        config = Mock(spec=EnvironmentConfig)
        config.type = "localhost_single_container"
        config.enable_background_monitoring = True
        config.monitoring_interval_seconds = 0.1
        config.failure_threshold_count = 2
        config.allow_partial_deployment = False
        config.critical_services = []
        return config

    @pytest.fixture
    def localhost_env(self, env_config, mock_event_manager, tmp_path):
        """Create a LocalhostSingleContainerEnvironment instance."""
        env = LocalhostSingleContainerEnvironment(
            env_config_to_test=env_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="localhost_single_container",
            event_manager=mock_event_manager,
        )
        # Mock Docker operations
        env.execute_with_logging = Mock()
        env.execute_command = Mock()
        env.execute_docker_command = Mock()
        return env

    def test_deploy_services_blocking_mode(self, localhost_env, env_config):
        """Test deploy_services in blocking mode."""
        env_config.enable_background_monitoring = False

        # Mock service managers
        mock_service = Mock()
        mock_service.service_name = "test_service"
        localhost_env.services_managers = [mock_service]

        # Mock monitoring methods
        localhost_env.monitor_docker_container = Mock(return_value=True)
        localhost_env._check_early_termination = Mock(return_value=False)

        result = localhost_env.deploy_services()

        assert result is True
        assert not hasattr(localhost_env, "background_monitor")

    def test_deploy_services_non_blocking_mode(self, localhost_env, env_config):
        """Test deploy_services in non-blocking mode."""
        env_config.enable_background_monitoring = True

        # Mock service managers
        mock_service = Mock()
        mock_service.service_name = "test_service"
        localhost_env.services_managers = [mock_service]

        # Mock container as running
        localhost_env.execute_docker_command = Mock(
            return_value=Mock(stdout="container_id_123", stderr="")
        )

        result = localhost_env.deploy_services()

        assert result is True
        assert hasattr(localhost_env, "background_monitor")
        assert localhost_env.background_monitor.monitoring_active is True

        # Clean up
        localhost_env.background_monitor.stop_monitoring()

    def test_teardown_stops_monitoring(self, localhost_env):
        """Test that teardown stops background monitoring."""
        # Start monitoring
        localhost_env.background_monitor = Mock()
        localhost_env.background_monitor.stop_monitoring = Mock()

        # Mock other teardown operations
        localhost_env.safe_docker_cleanup = Mock()

        localhost_env._teardown_environment()

        localhost_env.background_monitor.stop_monitoring.assert_called_once()

    def test_early_termination_integration(self, localhost_env):
        """Test early termination request integration."""
        reason = "Container failure"
        details = {"container": "test_container"}

        localhost_env.request_early_termination(reason, details)

        assert localhost_env._early_termination_requested is True
        assert localhost_env._early_termination_reason == reason
        assert localhost_env._early_termination_details == details

        # Check should_terminate_early
        assert localhost_env.should_terminate_early() is True

    def test_deploy_services_container_fails_to_start(self, localhost_env, env_config):
        """Test deploy_services when container fails to start."""
        env_config.enable_background_monitoring = True

        # Mock container as not running
        localhost_env.execute_docker_command = Mock(
            return_value=Mock(stdout="", stderr="Error: container failed to start")
        )

        result = localhost_env._deploy_services_non_blocking()

        assert result is False
        assert not hasattr(localhost_env, "background_monitor")

    def test_check_early_termination_method(self, localhost_env):
        """Test _check_early_termination method."""
        # Mock container as running
        localhost_env.execute_docker_command = Mock(
            return_value=Mock(stdout="container_id_123", stderr="")
        )

        result = localhost_env._check_early_termination()
        assert result is False

        # Mock container as exited
        localhost_env.execute_docker_command.side_effect = [
            Mock(stdout="", stderr=""),  # Not running
            Mock(stdout="Exited (1) 10 seconds ago", stderr=""),  # Exit status
        ]

        result = localhost_env._check_early_termination()
        assert result is True
