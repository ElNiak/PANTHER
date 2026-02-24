"""Unit tests for Shadow NS ShadowSimulationMonitor."""

import os
import threading
import time
from enum import Enum
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.network_environment.base_environment_monitor import (
    ServiceHealthState,
)
from panther.plugins.environments.network_environment.shadow_ns.shadow_ns import (
    ShadowNsEnvironment,
)
from panther.plugins.environments.network_environment.shadow_ns.shadow_simulation_monitor import (
    ShadowSimulationMonitor,
    ShadowSimulationState,
)


class TestShadowSimulationMonitor:
    """Test suite for ShadowSimulationMonitor class."""

    @pytest.fixture
    def mock_shadow_env(self):
        """Create a mock ShadowNsEnvironment."""
        env = Mock(spec=ShadowNsEnvironment)
        env.logger = Mock()
        env.env_name = "test_shadow_env"
        env.simulation_duration = "300s"
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
    def monitor(self, mock_shadow_env, mock_config):
        """Create a ShadowSimulationMonitor instance."""
        return ShadowSimulationMonitor(mock_shadow_env, mock_config)

    def test_monitor_initialization(self, monitor, mock_shadow_env):
        """Test monitor initialization."""
        assert monitor.shadow_env == mock_shadow_env
        # The actual implementation uses ServiceHealthState.STARTING, not ShadowSimulationState.INITIALIZING
        assert monitor.simulation_state == ServiceHealthState.STARTING
        assert monitor.failure_count == 0
        assert monitor.expected_duration == "300s"
        assert monitor.monitoring_active is False
        assert monitor.monitor_thread is None
        assert monitor.shadow_process is None

    def test_start_monitoring(self, monitor):
        """Test starting the monitoring thread."""
        mock_process = Mock()
        mock_process.poll = Mock(return_value=None)  # Process is running

        monitor.start_monitoring(mock_process, "/path/to/output.log")

        assert monitor.monitoring_active is True
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        assert monitor.monitor_thread.daemon is True
        assert monitor.shadow_process == mock_process
        assert monitor.shadow_output_file == "/path/to/output.log"
        assert monitor.simulation_start_time is not None

        # Clean up
        monitor.stop_monitoring()

    def test_stop_monitoring(self, monitor):
        """Test stopping the monitoring thread."""
        monitor.start_monitoring(None, None)
        time.sleep(0.05)  # Let it start

        # Save reference before stop (base class sets monitor_thread to None)
        thread_ref = monitor.monitor_thread

        monitor.stop_monitoring()

        assert monitor.monitoring_active is False
        # Base class sets monitor_thread to None after stop
        # Give thread time to stop and verify via our saved reference
        time.sleep(0.2)
        assert not thread_ref.is_alive()

    def test_double_start_monitoring(self, monitor):
        """Test that starting monitoring twice doesn't create multiple threads."""
        monitor.start_monitoring(None, None)
        first_thread = monitor.monitor_thread

        monitor.start_monitoring(None, None)
        second_thread = monitor.monitor_thread

        assert first_thread is second_thread

        # Clean up
        monitor.stop_monitoring()

    def test_parse_duration(self, monitor):
        """Test duration string parsing."""
        assert monitor._parse_duration("300s") == 300.0
        assert monitor._parse_duration("5m") == 300.0
        assert monitor._parse_duration("2h") == 7200.0
        assert monitor._parse_duration("100") == 100.0
        assert monitor._parse_duration(300) == 300.0
        assert monitor._parse_duration(300.5) == 300.5

    def test_process_termination_success(self, monitor):
        """Test handling successful process termination."""
        monitor.simulation_state = ServiceHealthState.RUNNING

        monitor._handle_process_termination(0)

        assert monitor.simulation_state == ServiceHealthState.COMPLETED
        assert monitor.monitoring_active is False
        monitor.shadow_env.request_early_termination.assert_not_called()

    def test_process_termination_failure(self, monitor):
        """Test handling failed process termination."""
        monitor.simulation_state = ServiceHealthState.RUNNING
        # Pre-set failure_count so that _handle_failure reaches the threshold
        # (_handle_failure increments first, then checks >= threshold)
        monitor.failure_count = monitor.config.failure_threshold_count - 1
        # start_time is needed by _trigger_early_termination
        monitor.start_time = time.time()

        monitor._handle_process_termination(1)

        assert monitor.simulation_state == ServiceHealthState.FAILED
        assert monitor.monitoring_active is False
        monitor.shadow_env.request_early_termination.assert_called_once()
        args = monitor.shadow_env.request_early_termination.call_args[0]
        assert "Shadow process exited with code 1" in args[0]

    def test_simulation_progress_check_with_errors(self, monitor, tmp_path):
        """Test checking simulation progress with error detection."""
        # Create temporary log file
        log_file = tmp_path / "shadow.log"
        log_content = """
[INFO] Starting simulation
[INFO] Loading topology
[ERROR] Failed to initialize network
[CRITICAL] Simulation aborted
"""
        log_file.write_text(log_content)

        monitor.shadow_output_file = str(log_file)
        monitor.simulation_state = ServiceHealthState.STARTING

        monitor._check_simulation_progress()

        assert monitor.failure_count >= 2  # Both ERROR and CRITICAL lines

    def test_simulation_progress_check_completion(self, monitor, tmp_path):
        """Test detecting simulation completion."""
        # Create temporary log file
        log_file = tmp_path / "shadow.log"
        log_content = """
[INFO] Starting simulation
[INFO] Running simulation
[INFO] Simulation complete
"""
        log_file.write_text(log_content)

        monitor.shadow_output_file = str(log_file)
        monitor.simulation_state = ServiceHealthState.RUNNING

        monitor._check_simulation_progress()

        assert monitor.simulation_state == ServiceHealthState.COMPLETED
        assert monitor.monitoring_active is False

    def test_simulation_progress_state_transition(self, monitor, tmp_path):
        """Test simulation state transitions."""
        # Create temporary log file
        log_file = tmp_path / "shadow.log"
        log_content = """
[INFO] Initializing
[INFO] Starting simulation
[INFO] Network configured
"""
        log_file.write_text(log_content)

        monitor.shadow_output_file = str(log_file)
        monitor.simulation_state = ServiceHealthState.STARTING

        monitor._check_simulation_progress()

        assert monitor.simulation_state == ServiceHealthState.RUNNING

    def test_timeout_detection(self, monitor):
        """Test simulation timeout detection."""
        # Set simulation start time to past
        monitor.simulation_start_time = time.time() - 500  # 500 seconds ago
        monitor.expected_duration = "300s"  # 5 minutes expected

        # Mock process still running
        mock_process = Mock()
        mock_process.poll = Mock(return_value=None)
        monitor.shadow_process = mock_process

        # _check_health is the actual method name (not _check_simulation_health)
        monitor._check_health()

        # Should increment failure count due to timeout
        assert monitor.failure_count >= 1

        # Check multiple times to exceed threshold
        monitor._check_health()
        monitor._check_health()

        # Should trigger termination
        monitor.shadow_env.request_early_termination.assert_called()
        args = monitor.shadow_env.request_early_termination.call_args[0]
        assert "timeout" in args[0].lower() or "failed" in args[0].lower()

    def test_monitor_thread_exception_handling(self, monitor, mock_config):
        """Test that monitor thread handles exceptions gracefully."""
        mock_config.monitoring_interval_seconds = 0.01

        # Make _check_health raise an exception
        monitor._check_health = Mock(side_effect=Exception("Test exception"))

        monitor.start_monitoring(None, None)
        time.sleep(0.1)  # Let it run a few iterations

        # Thread should still be alive despite exceptions
        assert monitor.monitor_thread.is_alive()

        # Logger should have logged the error (base class uses self.logger)
        monitor.logger.error.assert_called()

        # Clean up
        monitor.stop_monitoring()

    def test_monitoring_stops_after_termination(self, monitor):
        """Test that monitoring stops after triggering termination."""
        monitor.failure_count = monitor.config.failure_threshold_count

        monitor._trigger_early_termination("Test termination")

        # Monitoring should be inactive after termination
        assert monitor.monitoring_active is False

    def test_thread_safety(self, monitor):
        """Test thread-safe access to simulation state."""
        monitor.start_monitoring(None, None)

        # Simulate concurrent access
        def read_state():
            for _ in range(10):
                _ = monitor.simulation_state
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


class TestShadowNsEnvironmentMonitoring:
    """Test suite for ShadowNsEnvironment monitoring integration."""

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        return Mock()

    @pytest.fixture
    def env_config(self):
        """Create environment configuration."""
        config = Mock(spec=EnvironmentConfig)
        config.type = "shadow_ns"
        config.enable_background_monitoring = True
        config.monitoring_interval_seconds = 0.1
        config.failure_threshold_count = 2
        config.allow_partial_deployment = False
        config.critical_services = []
        # Add Shadow-specific config
        config.shadow = {"duration": "300s", "topology": "simple"}
        return config

    @pytest.fixture
    def shadow_env(self, env_config, mock_event_manager, tmp_path):
        """Create a ShadowNsEnvironment instance."""
        env = ShadowNsEnvironment(
            env_config_to_test=env_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="shadow_ns",
            event_manager=mock_event_manager,
        )
        # Mock Docker operations
        env.execute_with_logging = Mock()
        env.execute_command = Mock()
        env.execute_docker_command = Mock()
        env.monitor_docker_container = Mock(return_value=True)
        env._monitor_simulation = Mock(return_value=True)
        return env

    def test_deploy_services_blocking_mode(self, shadow_env, env_config):
        """Test deploy_services in blocking mode."""
        env_config.enable_background_monitoring = False

        # Mock service managers
        mock_service = Mock()
        mock_service.service_name = "test_service"
        shadow_env.services_managers = [mock_service]

        result = shadow_env.deploy_services()

        assert result is True
        assert not hasattr(shadow_env, "background_monitor")
        # Should use blocking monitoring
        shadow_env.monitor_docker_container.assert_called()
        shadow_env._monitor_simulation.assert_called()

    def test_deploy_services_non_blocking_mode(self, shadow_env, env_config):
        """Test deploy_services in non-blocking mode."""
        env_config.enable_background_monitoring = True

        # Mock service managers
        mock_service = Mock()
        mock_service.service_name = "test_service"
        shadow_env.services_managers = [mock_service]

        # Mock container as running
        shadow_env.execute_docker_command = Mock(
            return_value=Mock(stdout="container_id_123", stderr="")
        )

        # Mock register_service_outputs to avoid iterating Mock output patterns
        shadow_env.register_service_outputs = Mock()

        # Ensure output_dir is a Path (source code uses / operator on it)
        shadow_env.output_dir = Path(shadow_env.output_dir)

        # Create output directory for Shadow
        shadow_results_dir = shadow_env.output_dir / "shadow-results"
        shadow_results_dir.mkdir(parents=True, exist_ok=True)

        result = shadow_env.deploy_services()

        assert result is True
        assert hasattr(shadow_env, "background_monitor")
        assert shadow_env.background_monitor.monitoring_active is True

        # Clean up
        shadow_env.background_monitor.stop_monitoring()

    def test_teardown_stops_monitoring(self, shadow_env):
        """Test that teardown stops background monitoring."""
        # Start monitoring
        mock_monitor = Mock()
        mock_monitor.stop_monitoring = Mock()
        shadow_env.background_monitor = mock_monitor

        # Mock other teardown operations
        shadow_env._collect_shadow_results = Mock()
        shadow_env.safe_docker_cleanup = Mock()
        shadow_env._wait_for_simulation_completion = Mock()
        shadow_env._perform_final_output_registration = Mock()
        # Mock network_name attribute used in cleanup
        shadow_env.network_name = "test_network"

        shadow_env._teardown_environment()

        # background_monitor is set to None after stop, so check saved reference
        mock_monitor.stop_monitoring.assert_called_once()

    def test_early_termination_integration(self, shadow_env):
        """Test early termination request integration."""
        reason = "Simulation failure"
        details = {"state": "failed"}

        shadow_env.request_early_termination(reason, details)

        assert shadow_env._early_termination_requested is True
        assert shadow_env._early_termination_reason == reason
        assert shadow_env._early_termination_details == details

        # Check should_terminate_early
        assert shadow_env.should_terminate_early() is True

    def test_shadow_config_parsing(self, shadow_env, env_config):
        """Test Shadow-specific configuration parsing."""
        config = shadow_env._get_shadow_config()

        assert config["duration"] == "300s"
        assert config["topology"] == "simple"
        assert shadow_env.simulation_duration == "300s"
        assert shadow_env.network_topology == "simple"

    def test_prepare_shadow_services(self, shadow_env):
        """Test preparing service configurations for Shadow."""
        # Mock service managers
        mock_service1 = Mock()
        mock_service1.service_name = "server"
        mock_service1.implementation_type = "iut"
        mock_service1.protocol_name = "quic"
        mock_service1.role = "server"
        mock_service1.run_cmd = {}
        mock_service1.get_run_command = Mock(return_value="./server -p 4443")
        mock_service1.get_output_file_paths = Mock(return_value={})
        mock_service1.get_standard_redirections = Mock(return_value={})

        mock_service2 = Mock()
        mock_service2.service_name = "client"
        mock_service2.implementation_type = "iut"
        mock_service2.protocol_name = "quic"
        mock_service2.role = "client"
        mock_service2.run_cmd = {}
        mock_service2.get_run_command = Mock(return_value="./client localhost:4443")
        mock_service2.get_output_file_paths = Mock(return_value={})
        mock_service2.get_standard_redirections = Mock(return_value={})

        shadow_env.services_managers = [mock_service1, mock_service2]

        services = shadow_env._prepare_shadow_services()

        assert len(services) == 2
        assert services[0]["name"] == "server"
        assert services[1]["name"] == "client"

    def test_deploy_services_container_fails_to_start(self, shadow_env, env_config):
        """Test deploy_services when container fails to start."""
        env_config.enable_background_monitoring = True

        # Mock container as not running
        shadow_env.execute_docker_command = Mock(
            return_value=Mock(stdout="", stderr="Error: container failed to start")
        )

        result = shadow_env._deploy_services_non_blocking()

        assert result is False
        assert not hasattr(shadow_env, "background_monitor")
