"""Unit tests for Docker Compose BackgroundServiceMonitor."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.core.test_cases.execution import test_executor as _executor_mod
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.network_environment.base_environment_monitor import (
    ServiceHealthState,
)
from panther.plugins.environments.network_environment.docker_compose import (
    docker_compose as _dc_mod,
)
from panther.plugins.environments.network_environment.docker_compose.background_service_monitor import (
    BackgroundServiceMonitor,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)

pytestmark = pytest.mark.unit


class TestBackgroundServiceMonitor:
    """Test suite for BackgroundServiceMonitor class."""

    @pytest.fixture
    def mock_docker_env(self):
        """Create a mock DockerComposeEnvironment."""
        env = Mock(spec=DockerComposeEnvironment)
        env.logger = Mock()
        env.env_name = "test-env"
        env.request_early_termination = Mock()
        # Mock execute_docker_command used by _is_service_ready_with_timeout
        mock_result = Mock()
        mock_result.stdout = "container_id_123\n"
        env.execute_docker_command = Mock(return_value=mock_result)
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
        # stop_monitoring() sets monitor_thread to None after joining
        assert monitor.monitor_thread is None

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
        # Mock _is_service_ready_with_timeout to return True for all services
        monitor._is_service_ready_with_timeout = Mock(return_value=True)

        monitor._check_health()

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
        def mock_is_ready(service_name, timeout=10.0):
            return service_name != "service1"

        monitor._is_service_ready_with_timeout = Mock(side_effect=mock_is_ready)

        # First check - per-service failure count increases
        monitor._check_health()
        assert monitor.failure_counts["service1"] == 1
        assert monitor.service_states["service1"] == ServiceHealthState.FAILING

        # Second check - per-service count reaches threshold (2), state becomes FAILED,
        # and _handle_failure is called once (global failure_count becomes 1)
        monitor._check_health()
        assert monitor.failure_counts["service1"] == 2
        assert monitor.service_states["service1"] == ServiceHealthState.FAILED

        # Third check - _handle_failure called again (global failure_count reaches 2),
        # which meets the threshold and triggers _should_terminate -> termination
        monitor._check_health()

        # Early termination should now be triggered via base class _trigger_early_termination
        monitor.docker_compose_env.request_early_termination.assert_called_once()
        args = monitor.docker_compose_env.request_early_termination.call_args[0]
        # First arg is the reason string (contains monitor name and failure info)
        assert "service1" in args[0]
        # Second arg is the details dict from _get_termination_details
        details = args[1]
        assert "failed_services" in details
        assert "service1" in details["failed_services"]

    def test_critical_service_failure(self, monitor):
        """Test that critical service failure triggers termination."""

        # Make critical_service unhealthy
        def mock_is_ready(service_name, timeout=10.0):
            return service_name != "critical_service"

        monitor._is_service_ready_with_timeout = Mock(side_effect=mock_is_ready)

        # First check: per-service failure count = 1 (below threshold)
        monitor._check_health()
        # Second check: per-service count reaches threshold (2), calls _handle_failure
        # (global failure_count becomes 1, below global threshold of 2)
        monitor._check_health()
        assert monitor.service_states["critical_service"] == ServiceHealthState.FAILED

        # Third check: _handle_failure called again, global failure_count reaches 2,
        # meets threshold -> _should_terminate -> termination
        monitor._check_health()

        monitor.docker_compose_env.request_early_termination.assert_called_once()

        # Verify the reason mentions the critical service
        args = monitor.docker_compose_env.request_early_termination.call_args[0]
        assert "critical_service" in args[0]

    def test_partial_deployment_allowed(self, monitor, mock_config):
        """Test behavior when partial deployment is allowed."""
        mock_config.allow_partial_deployment = True
        mock_config.critical_services = []

        # Make only one service fail
        def mock_is_ready(service_name, timeout=10.0):
            return service_name != "service1"

        monitor._is_service_ready_with_timeout = Mock(side_effect=mock_is_ready)

        # Check twice to reach threshold
        monitor._check_health()
        monitor._check_health()

        # _should_terminate returns False when allow_partial_deployment is True,
        # no critical services, and fewer than half the services have failed.
        # Since only 1 of 3 services failed, should not terminate.
        monitor.docker_compose_env.request_early_termination.assert_not_called()

        # Now make majority fail (service2 and critical_service fail, only service1 healthy)
        def mock_is_ready_majority_fail(service_name, timeout=10.0):
            return service_name == "service1"

        monitor._is_service_ready_with_timeout = Mock(
            side_effect=mock_is_ready_majority_fail
        )

        # Reset failure counts for service2 and critical_service so they start fresh
        monitor.failure_counts["service2"] = 0
        monitor.failure_counts["critical_service"] = 0
        monitor.service_states["service2"] = ServiceHealthState.STARTING
        monitor.service_states["critical_service"] = ServiceHealthState.STARTING

        # Check twice more to reach threshold for service2 and critical_service
        monitor._check_health()
        monitor._check_health()

        # Now should terminate (more than half failed: service2 + critical_service = 2 out of 3)
        monitor.docker_compose_env.request_early_termination.assert_called_once()

    def test_service_recovery(self, monitor):
        """Test that services can recover from failing state."""
        # Make all services unhealthy initially
        monitor._is_service_ready_with_timeout = Mock(return_value=False)

        monitor._check_health()
        assert monitor.failure_counts["service1"] == 1
        assert monitor.service_states["service1"] == ServiceHealthState.FAILING

        # Service recovers
        monitor._is_service_ready_with_timeout = Mock(return_value=True)

        monitor._check_health()
        assert monitor.failure_counts["service1"] == 0  # Reset
        assert monitor.service_states["service1"] == ServiceHealthState.READY

    def test_monitor_thread_exception_handling(self, monitor, mock_config):
        """Test that monitor thread handles exceptions gracefully."""
        mock_config.monitoring_interval_seconds = 0.01

        # Make _check_health raise an exception
        monitor._check_health = Mock(side_effect=Exception("Test exception"))

        monitor.start_monitoring()
        time.sleep(0.1)  # Let it run a few iterations

        # Thread should still be alive despite exceptions
        assert monitor.monitor_thread.is_alive()

        # Clean up
        monitor.stop_monitoring()

    def test_monitoring_stops_after_termination(self, monitor):
        """Test that monitoring stops after triggering termination."""
        # Make all services fail
        monitor._is_service_ready_with_timeout = Mock(return_value=False)

        # Check twice to trigger termination
        monitor._check_health()
        monitor._check_health()

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
        """Create a DockerComposeEnvironment instance with mocked internals."""
        with (
            patch.object(_dc_mod, "TemplateRenderer"),
            patch.object(_dc_mod, "DockerComposeNetworkResolver"),
            patch.object(_dc_mod, "DockerComposePortManager"),
            patch.object(_dc_mod, "DockerComposeOutputManager"),
        ):
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

    def test_deploy_services_monitoring_returns_true(self, docker_env, env_config):
        """Test deploy_services_monitoring returns True."""
        result = docker_env.deploy_services_monitoring()
        assert result is True

    def test_remove_service_monitoring_stops_monitor(self, docker_env):
        """Test remove_service_monitoring stops and clears background monitor."""
        mock_monitor = Mock()
        mock_monitor.stop_monitoring = Mock()
        docker_env.background_monitor = mock_monitor

        docker_env.remove_service_monitoring()

        mock_monitor.stop_monitoring.assert_called_once()
        assert docker_env.background_monitor is None

    def test_remove_service_monitoring_noop_when_no_monitor(self, docker_env):
        """Test remove_service_monitoring is a no-op when no monitor exists."""
        # No background_monitor attribute set -- should not raise
        docker_env.remove_service_monitoring()

    def test_teardown_stops_monitoring(self, docker_env):
        """Test that _teardown_environment stops background monitoring."""
        docker_env.background_monitor = Mock()
        docker_env.background_monitor.stop_monitoring = Mock()

        # Mock other teardown dependencies
        docker_env.output_manager = Mock()
        docker_env.services_managers = []
        docker_env.rendered_services_network_config_file_path = "/nonexistent/path"

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

    def test_monitor_is_told_which_services_are_testers(self, docker_env):
        """Only the services whose manager answers is_tester() are passed as testers."""
        tester = Mock(service_name="ivy_tester")
        tester.is_tester = Mock(return_value=True)
        iut = Mock(service_name="frr_server")
        iut.is_tester = Mock(return_value=False)
        docker_env.services_managers = [tester, iut]
        docker_env.config = Mock()
        docker_env.background_monitor = None

        with patch.object(_dc_mod, "BackgroundServiceMonitor") as monitor_cls:
            docker_env._start_background_monitoring_after_deployment()

        kwargs = monitor_cls.call_args.kwargs
        assert kwargs["services"] == ["ivy_tester", "frr_server"]
        assert kwargs["testers"] == ["ivy_tester"]
        monitor_cls.return_value.start_monitoring.assert_called_once()


def _docker_stub(stopped):
    """Build an execute_docker_command stand-in.

    Args:
        stopped: Container name -> the ``inspect`` output (status and exit code)
            of a container that is no longer running; every other container runs.

    Returns:
        A callable with execute_docker_command's signature.
    """

    def run(docker_args, check=False, timeout=None):
        result = Mock()
        if docker_args[0] == "ps":
            # Matches both the anchored name and the legacy <network>_<name>_1 form
            running = not any(name in docker_args[-1] for name in stopped)
            result.stdout = "container_id\n" if running else ""
        else:
            result.stdout = (
                f"{stopped[docker_args[-1]]}\n" if docker_args[-1] in stopped else ""
            )
        return result

    return run


class TestTesterExitEndsTheWait:
    """A tester's exit ends the wait as a completion; any other exit is a failure."""

    @pytest.fixture
    def config(self):
        """Monitoring configuration with a threshold above one check."""
        config = Mock(spec=EnvironmentConfig)
        config.monitoring_interval_seconds = 0.05
        config.failure_threshold_count = 3
        config.critical_services = []
        config.allow_partial_deployment = False
        return config

    @pytest.fixture
    def env(self):
        """A Docker Compose environment double."""
        env = Mock(spec=DockerComposeEnvironment)
        env.logger = Mock()
        env.env_name = "test-env"
        env.network_name = "test-net"
        env.request_early_termination = Mock()
        return env

    def test_tester_exit_ends_the_wait_at_the_first_check(self, env, config):
        """An exited tester requests the end at once, with its exit code and no failure."""
        env.execute_docker_command = Mock(
            side_effect=_docker_stub({"ivy_tester": "exited 0"})
        )
        monitor = BackgroundServiceMonitor(
            env, ["ivy_tester", "frr_server"], config, testers=["ivy_tester"]
        )

        monitor._check_health()

        env.request_early_termination.assert_called_once()
        reason, details = env.request_early_termination.call_args[0]
        assert reason == "Tester 'ivy_tester' exited (code 0)"
        assert details["tester"] == "ivy_tester"
        assert details["exit_code"] == 0
        assert monitor.failure_counts["ivy_tester"] == 0
        assert monitor.service_states["ivy_tester"] != ServiceHealthState.FAILED
        assert monitor.monitoring_active is False
        env.logger.error.assert_not_called()

    def test_iut_exit_keeps_the_failure_path(self, env, config):
        """An exited IUT is counted as a failure and does not end the wait at once."""
        env.execute_docker_command = Mock(
            side_effect=_docker_stub({"frr_server": "exited 1"})
        )
        monitor = BackgroundServiceMonitor(
            env, ["ivy_tester", "frr_server"], config, testers=["ivy_tester"]
        )

        monitor._check_health()

        env.request_early_termination.assert_not_called()
        assert monitor.failure_counts["frr_server"] == 1
        assert monitor.service_states["frr_server"] == ServiceHealthState.FAILING

    @pytest.mark.parametrize("inspect_output", ["created 0", "restarting 1"])
    def test_tester_not_running_but_not_exited_keeps_the_failure_path(
        self, env, config, inspect_output
    ):
        """A tester that is not running but has not exited is counted as a failure."""
        env.execute_docker_command = Mock(
            side_effect=_docker_stub({"ivy_tester": inspect_output})
        )
        monitor = BackgroundServiceMonitor(
            env, ["ivy_tester"], config, testers=["ivy_tester"]
        )

        monitor._check_health()

        env.request_early_termination.assert_not_called()
        assert monitor.failure_counts["ivy_tester"] == 1

    def test_tester_with_no_container_keeps_the_failure_path(self, env, config):
        """A tester whose state cannot be read is counted as a failure."""

        def run(docker_args, check=False, timeout=None):
            return Mock(stdout="")

        env.execute_docker_command = Mock(side_effect=run)
        monitor = BackgroundServiceMonitor(
            env, ["ivy_tester"], config, testers=["ivy_tester"]
        )

        monitor._check_health()

        env.request_early_termination.assert_not_called()
        assert monitor.failure_counts["ivy_tester"] == 1

    def test_long_wait_ends_within_one_slice_of_the_tester_exit(self, config):
        """The executor's wait ends one slice after a running monitor sees the exit."""

        class ClockedEnvironment:
            """An environment whose tester container exits at a set time."""

            logger = Mock()
            env_name = "clocked"
            network_name = "clocked-net"

            def __init__(self, tester_exits_after):
                self.exit_at = time.monotonic() + tester_exits_after
                self.reasons = []

            def execute_docker_command(self, docker_args, check=False, timeout=None):
                exited = time.monotonic() >= self.exit_at
                state = {"ivy_tester": "exited 0"} if exited else {}
                return _docker_stub(state)(docker_args, check, timeout)

            def request_early_termination(self, reason, details=None):
                self.reasons.append(reason)

            def should_terminate_early(self):
                return bool(self.reasons)

        env = ClockedEnvironment(tester_exits_after=0.3)
        monitor = BackgroundServiceMonitor(
            env, ["ivy_tester"], config, testers=["ivy_tester"]
        )
        test_case = Mock()
        test_case.environment_plugin_manager = [env]
        executor = _executor_mod.TestExecutor(test_case)

        monitor.start_monitoring()
        started = time.monotonic()
        try:
            executor._check_early_exit({"type": "wait", "duration": 30}, None)
        finally:
            monitor.stop_monitoring()
        elapsed = time.monotonic() - started

        assert env.reasons == ["Tester 'ivy_tester' exited (code 0)"]
        assert elapsed < 0.3 + 1.0 + 0.7  # the exit, one slice, scheduling slack
