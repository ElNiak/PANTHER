"""Integration tests for early termination feature with non-blocking monitoring."""

import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.impl.experiment_observer import ExperimentObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.test_cases.test_case_impl import TestCase
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.network_environment.base_environment_monitor import (
    ServiceHealthState,
)
from panther.plugins.environments.network_environment.docker_compose.background_service_monitor import (
    BackgroundServiceMonitor,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)

pytestmark = pytest.mark.integration


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
            env_type="network_environment",
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

        monitor.start_monitoring()
        assert monitor.monitoring_active
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()

        monitor.stop_monitoring()
        assert not monitor.monitoring_active
        assert monitor.monitor_thread is None

    def test_service_failure_detection(self, docker_compose_env, mock_env_config):
        """Test that service failures are detected and trigger early termination."""
        services = ["failing_service"]
        monitor = BackgroundServiceMonitor(
            docker_compose_env, services, mock_env_config
        )

        docker_compose_env.execute_docker_command = Mock(return_value=Mock(stdout=""))

        monitor.start_monitoring()

        deadline = time.time() + 10
        while time.time() < deadline:
            if docker_compose_env._early_termination_requested:
                break
            time.sleep(0.2)

        assert monitor.service_states["failing_service"] == ServiceHealthState.FAILED
        assert (
            monitor.failure_counts["failing_service"]
            >= mock_env_config.failure_threshold_count
        )
        assert docker_compose_env._early_termination_requested
        assert docker_compose_env._early_termination_reason is not None

        monitor.stop_monitoring()

    def test_critical_service_triggers_termination(
        self, docker_compose_env, mock_env_config
    ):
        """Test that critical service failure triggers immediate termination."""
        services = ["critical_service", "normal_service"]
        monitor = BackgroundServiceMonitor(
            docker_compose_env, services, mock_env_config
        )

        def mock_docker_command(docker_args=None, check=True, timeout=None):
            result = Mock()
            if docker_args and any("critical_service" in str(a) for a in docker_args):
                result.stdout = ""
            else:
                result.stdout = "abc123"
            return result

        docker_compose_env.execute_docker_command = Mock(
            side_effect=mock_docker_command
        )

        monitor.start_monitoring()

        deadline = time.time() + 10
        while time.time() < deadline:
            if docker_compose_env._early_termination_requested:
                break
            time.sleep(0.2)

        assert docker_compose_env._early_termination_requested
        assert docker_compose_env._early_termination_reason is not None

        monitor.stop_monitoring()

    def test_deploy_services_monitoring(self, docker_compose_env, mock_env_config):
        """Test deploy_services_monitoring returns True (monitoring started via events)."""
        result = docker_compose_env.deploy_services_monitoring()
        assert result is True

    def test_monitoring_not_active_before_deployment_event(
        self, docker_compose_env, mock_env_config
    ):
        """Test that monitoring is not active until deployment_completed event fires."""
        assert not hasattr(docker_compose_env, "background_monitor") or (
            docker_compose_env.background_monitor is None
            if hasattr(docker_compose_env, "background_monitor")
            else True
        )

    def test_experiment_observer_handles_environment_errors(self):
        """Test that ExperimentObserver properly handles environment error events."""
        observer = ExperimentObserver(
            name="test_observer", track_timing=False, track_steps=False
        )

        from panther.core.events.environment.events import EnvironmentEvent

        error_event = EnvironmentEvent.error(
            environment_id="test_env",
            environment_name="test",
            environment_type="docker_compose",
            error_message="Experiment finished early: Service failure",
            error_type="early_termination",
        )

        result = observer.on_event(error_event)

        assert result is True
        assert observer.experiment_finished_early is True
        assert observer._termination_reason is not None
        assert "Service failure" in observer._termination_reason

    def test_test_case_checks_early_termination(self):
        """Test that TestCase properly checks for early termination during step execution."""
        mock_steps = MagicMock()
        mock_steps.wait = 10

        test_config = MagicMock()
        test_config.name = "test_early_termination"
        test_config.steps = mock_steps
        test_config.services = {}
        test_config.fast_fail_enabled = None
        test_config.network_environment = MagicMock()
        test_config.execution_environment = []
        test_config.description = "Early termination test"

        global_config = MagicMock()
        global_config.logging.level.name = "INFO"
        global_config.logging.format = "%(message)s"

        plugin_manager = Mock()
        import tempfile

        experiment_dir = Path(tempfile.mkdtemp())

        with (
            patch("panther.core.test_cases.test_case_impl.EmitterRegistry") as mock_er,
            patch(
                "panther.core.test_cases.base.test_case_base.EventManager"
            ) as mock_em,
        ):
            mock_event_manager = Mock()
            mock_em.get_instance.return_value = mock_event_manager
            mock_em.return_value = mock_event_manager

            mock_emitter_registry = Mock()
            mock_er.return_value = mock_emitter_registry
            mock_emitter_registry.get_test_emitter = Mock(return_value=Mock())
            mock_emitter_registry.service_emitter = Mock()
            mock_emitter_registry.environment_emitter = Mock()
            mock_emitter_registry.step_emitter = Mock()
            mock_emitter_registry.experiment_emitter = Mock()
            mock_emitter_registry.assertion_emitter = Mock()
            mock_emitter_registry.metrics_emitter = Mock()
            mock_emitter_registry.get_emitter = Mock(return_value=None)

            test_case = TestCase(
                test_config=test_config,
                global_config=global_config,
                plugin_manager=plugin_manager,
                experiment_dir=experiment_dir,
            )

            mock_env_manager = Mock()
            mock_env_manager.should_terminate_early = Mock(return_value=True)
            test_case.environment_plugin_manager = [mock_env_manager]

            mock_observer = Mock()
            mock_observer.should_terminate_early = Mock(return_value=False)
            mock_event_manager.get_observer_by_type = Mock(return_value=mock_observer)
            test_case.event_manager = mock_event_manager

            test_case.step_emitter = Mock()
            test_case.experiment_emitter = Mock()

            test_case.execute_steps()

            assert mock_env_manager.should_terminate_early.called

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

        def mock_docker_command(docker_args=None, check=True, timeout=None):
            nonlocal health_check_count
            health_check_count += 1
            result = Mock()
            # Fail after a few checks to simulate service failure
            result.stdout = "abc123" if health_check_count < 3 else ""
            return result

        docker_compose_env.execute_docker_command = Mock(
            side_effect=mock_docker_command
        )

        # Deploy with monitoring enabled
        result = docker_compose_env.deploy_services_monitoring()
        assert result is True

        # Manually start monitoring (normally triggered by deployment_completed event)
        monitor = BackgroundServiceMonitor(
            docker_compose_env, services, mock_env_config
        )
        docker_compose_env.background_monitor = monitor
        monitor.start_monitoring()

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
