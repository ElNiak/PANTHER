"""Unit tests for BaseNetworkEnvironment early termination functionality."""

from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class ConcreteNetworkEnvironment(BaseNetworkEnvironment):
    """Concrete implementation for testing abstract BaseNetworkEnvironment."""

    def generate_environment_services(self, paths, timestamp):
        pass

    def prepare_environment(self):
        return True

    def launch_environment_services(self):
        pass

    def deploy_services(self):
        return True

    def setup_environment(
        self,
        services_managers: List[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: Optional["PluginManager"],
        execution_environment: List[IExecutionEnvironment],
    ):
        return True

    def teardown_environment(self):
        pass

    def _do_setup_environment(self, *args, **kwargs):
        return True

    def _do_deploy_services(self):
        pass

    def _do_teardown_environment(self):
        pass


class TestBaseNetworkEnvironmentEarlyTermination:
    """Test suite for BaseNetworkEnvironment early termination functionality."""

    @pytest.fixture
    def mock_event_manager(self):
        """Create a mock event manager."""
        manager = Mock(spec=EventManager)
        manager.emit_event = Mock()
        return manager

    @pytest.fixture
    def mock_config(self):
        """Create a mock environment configuration."""
        config = Mock(spec=EnvironmentConfig)
        config.type = "test_network"
        config.enable_background_monitoring = True
        config.monitoring_interval_seconds = 5
        config.failure_threshold_count = 3
        return config

    @pytest.fixture
    def base_env(self, mock_config, mock_event_manager, tmp_path):
        """Create a concrete BaseNetworkEnvironment instance for testing."""
        env = ConcreteNetworkEnvironment(
            env_config_to_test=mock_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="test",
            event_manager=mock_event_manager,
        )
        return env

    def test_initial_termination_state(self, base_env):
        """Test initial early termination state."""
        assert base_env._early_termination_requested is False
        assert base_env._early_termination_reason is None
        assert base_env._early_termination_details is None

    def test_request_early_termination(self, base_env):
        """Test requesting early termination."""
        reason = "Service failure detected"
        details = {
            "failed_service": "test_service",
            "failure_count": 3,
            "error_type": "connection_refused",
        }

        base_env.request_early_termination(reason, details)

        assert base_env._early_termination_requested is True
        assert base_env._early_termination_reason == reason
        assert base_env._early_termination_details == details

    def test_should_terminate_early(self, base_env):
        """Test should_terminate_early method."""
        # Initially should return False
        assert base_env.should_terminate_early() is False

        # Request termination
        base_env.request_early_termination("Test reason", {})

        # Now should return True
        assert base_env.should_terminate_early() is True

    def test_get_termination_reason(self, base_env):
        """Test getting termination reason and details."""
        # Initially should return None
        reason, details = base_env.get_termination_reason()
        assert reason is None
        assert details is None

        # Request termination with reason and details
        test_reason = "Critical service failure"
        test_details = {"service": "critical_service", "exit_code": 1}
        base_env.request_early_termination(test_reason, test_details)

        # Should return the reason and details
        reason, details = base_env.get_termination_reason()
        assert reason == test_reason
        assert details == test_details

    def test_multiple_termination_requests(self, base_env):
        """Test that only the first termination request is recorded."""
        # First request
        base_env.request_early_termination("First reason", {"first": True})

        # Second request
        base_env.request_early_termination("Second reason", {"second": True})

        # Should keep the first reason
        reason, details = base_env.get_termination_reason()
        assert reason == "First reason"
        assert details == {"first": True}

    def test_termination_with_empty_details(self, base_env):
        """Test termination request with empty or None details."""
        base_env.request_early_termination("Reason without details", None)

        assert base_env._early_termination_requested is True
        assert base_env._early_termination_reason == "Reason without details"
        assert base_env._early_termination_details is None

        reason, details = base_env.get_termination_reason()
        assert reason == "Reason without details"
        assert details is None

    def test_termination_logging(self, base_env):
        """Test that termination requests are logged."""
        reason = "Test termination"
        details = {"test": "data"}

        with patch.object(base_env.logger, "warning") as mock_logger:
            base_env.request_early_termination(reason, details)

            mock_logger.assert_called_once()
            log_args = mock_logger.call_args[0]
            assert "Early termination requested" in log_args[0]
            assert reason in str(log_args)

    def test_termination_state_isolation(
        self, mock_config, mock_event_manager, tmp_path
    ):
        """Test that termination state is isolated between instances."""
        # Create two separate environment instances
        env1 = ConcreteNetworkEnvironment(
            env_config_to_test=mock_config,
            output_dir=str(tmp_path / "env1"),
            env_type="network",
            env_sub_type="test1",
            event_manager=mock_event_manager,
        )

        env2 = ConcreteNetworkEnvironment(
            env_config_to_test=mock_config,
            output_dir=str(tmp_path / "env2"),
            env_type="network",
            env_sub_type="test2",
            event_manager=mock_event_manager,
        )

        # Request termination on env1
        env1.request_early_termination("Env1 failure", {"env": 1})

        # env1 should be terminated
        assert env1.should_terminate_early() is True

        # env2 should not be affected
        assert env2.should_terminate_early() is False

        # Request termination on env2
        env2.request_early_termination("Env2 failure", {"env": 2})

        # Both should now be terminated with their own reasons
        reason1, details1 = env1.get_termination_reason()
        reason2, details2 = env2.get_termination_reason()

        assert reason1 == "Env1 failure"
        assert details1 == {"env": 1}
        assert reason2 == "Env2 failure"
        assert details2 == {"env": 2}

    def test_inheritance_preservation(self, mock_config, mock_event_manager, tmp_path):
        """Test that early termination methods work correctly in inherited classes."""
        # Import one of the actual implementations
        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            DockerComposeEnvironment,
        )

        docker_env = DockerComposeEnvironment(
            env_config_to_test=mock_config,
            output_dir=str(tmp_path),
            env_type="network",
            env_sub_type="docker_compose",
            event_manager=mock_event_manager,
        )

        # Should have the early termination methods
        assert hasattr(docker_env, "request_early_termination")
        assert hasattr(docker_env, "should_terminate_early")
        assert hasattr(docker_env, "get_termination_reason")

        # Should work correctly
        docker_env.request_early_termination("Docker failure", {"container": "test"})
        assert docker_env.should_terminate_early() is True

        reason, details = docker_env.get_termination_reason()
        assert reason == "Docker failure"
        assert details == {"container": "test"}
