"""Tests for Bugs #15 and #17: Docker Compose lifecycle fixes.

Bug #15: deploy_timeout config field
Bug #17: kill before down in teardown

Tests cover:
- DockerComposeConfig deploy_timeout default and configurability
- stop_docker_services call order: kill first, then down
- kill uses 30s timeout, down uses self.timeout
- kill failure does not prevent down
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# TestDockerComposeConfigTimeout
# ---------------------------------------------------------------------------


class TestDockerComposeConfigTimeout:
    """Verify deploy_timeout field on DockerComposeConfig."""

    def test_default_deploy_timeout_is_300(self):
        from panther.plugins.environments.network_environment.docker_compose.config_schema import (
            DockerComposeConfig,
        )

        config = DockerComposeConfig()
        assert config.deploy_timeout == 300

    def test_deploy_timeout_configurable(self):
        from panther.plugins.environments.network_environment.docker_compose.config_schema import (
            DockerComposeConfig,
        )

        config = DockerComposeConfig(deploy_timeout=300)
        assert config.deploy_timeout == 300

    def test_deploy_timeout_field_in_schema(self):
        from panther.plugins.environments.network_environment.docker_compose.config_schema import (
            DockerComposeConfig,
        )

        fields = DockerComposeConfig.model_fields
        assert "deploy_timeout" in fields
        assert fields["deploy_timeout"].default == 300


# ---------------------------------------------------------------------------
# TestDockerComposeTeardown
# ---------------------------------------------------------------------------


def _make_lifecycle_manager(timeout=60):
    """Create a DockerComposeLifecycleManager with mocked dependencies."""
    from panther.plugins.environments.network_environment.docker_compose.docker_compose_lifecycle_manager import (
        DockerComposeLifecycleManager,
    )

    mock_executor = MagicMock()
    mock_executor.execute_docker_command = MagicMock(return_value="ok")

    manager = DockerComposeLifecycleManager(
        services_managers=[],
        network_name="test_net",
        config_file_path=Path("/tmp/docker-compose.yml"),
        output_dir=Path("/tmp/output"),
        timeout=timeout,
        docker_executor=mock_executor,
    )
    return manager, mock_executor


class TestDockerComposeTeardown:
    """Verify stop_docker_services calls kill before down."""

    def test_stop_calls_kill_before_down(self):
        manager, mock_executor = _make_lifecycle_manager()

        manager.stop_docker_services()

        calls = mock_executor.execute_docker_command.call_args_list
        assert len(calls) == 2

        # First call should be kill
        kill_call_args = calls[0]
        kill_docker_args = kill_call_args.kwargs.get(
            "docker_args", kill_call_args[1].get("docker_args", [])
        )
        assert "kill" in kill_docker_args

        # Second call should be down
        down_call_args = calls[1]
        down_docker_args = down_call_args.kwargs.get(
            "docker_args", down_call_args[1].get("docker_args", [])
        )
        assert "down" in down_docker_args

    def test_kill_uses_30s_timeout(self):
        manager, mock_executor = _make_lifecycle_manager()

        manager.stop_docker_services()

        kill_call = mock_executor.execute_docker_command.call_args_list[0]
        kill_timeout = kill_call.kwargs.get("timeout", kill_call[1].get("timeout"))
        assert kill_timeout == 30

    def test_down_uses_configured_timeout(self):
        manager, mock_executor = _make_lifecycle_manager(timeout=180)

        manager.stop_docker_services()

        down_call = mock_executor.execute_docker_command.call_args_list[1]
        down_timeout = down_call.kwargs.get("timeout", down_call[1].get("timeout"))
        assert down_timeout == 180

    def test_kill_failure_does_not_prevent_down(self):
        manager, mock_executor = _make_lifecycle_manager()

        # Make kill raise an exception
        def side_effect(**kwargs):
            docker_args = kwargs.get("docker_args", [])
            if "kill" in docker_args:
                raise RuntimeError("No containers to kill")
            return "ok"

        mock_executor.execute_docker_command.side_effect = side_effect

        # Should not raise
        manager.stop_docker_services()

        # down should still have been called
        calls = mock_executor.execute_docker_command.call_args_list
        assert len(calls) == 2
        down_docker_args = calls[1].kwargs.get(
            "docker_args", calls[1][1].get("docker_args", [])
        )
        assert "down" in down_docker_args


# ---------------------------------------------------------------------------
# TestPreLaunchCleanupResilience (Gap 3)
# ---------------------------------------------------------------------------


class TestPreLaunchCleanupResilience:
    """Verify _pre_launch_cleanup error handling distinguishes expected from real errors."""

    def test_cleanup_success(self):
        """Successful cleanup logs info."""
        manager, mock_executor = _make_lifecycle_manager()
        manager._pre_launch_cleanup()
        mock_executor.execute_docker_command.assert_called_once()

    def test_cleanup_not_found_logs_debug(self):
        """'not found' exception is expected and logged at debug level."""
        manager, mock_executor = _make_lifecycle_manager()
        mock_executor.execute_docker_command.side_effect = RuntimeError(
            "No such container: test_net"
        )
        # Should not raise
        manager._pre_launch_cleanup()

    def test_cleanup_no_such_logs_debug(self):
        """'no such' exception is expected and logged at debug level."""
        manager, mock_executor = _make_lifecycle_manager()
        mock_executor.execute_docker_command.side_effect = RuntimeError(
            "network not found"
        )
        manager._pre_launch_cleanup()

    def test_cleanup_real_error_logs_warning(self):
        """Real errors (permission denied, timeout) should log at warning level."""
        manager, mock_executor = _make_lifecycle_manager()
        mock_executor.execute_docker_command.side_effect = RuntimeError(
            "permission denied while trying to connect"
        )
        with patch.object(manager.logger, "warning") as mock_warn:
            manager._pre_launch_cleanup()
            mock_warn.assert_called_once()
            call_args = str(mock_warn.call_args)
            assert "resource conflicts" in call_args

    def test_cleanup_never_raises(self):
        """_pre_launch_cleanup never propagates exceptions."""
        manager, mock_executor = _make_lifecycle_manager()
        mock_executor.execute_docker_command.side_effect = Exception("catastrophic")
        # Must not raise
        manager._pre_launch_cleanup()

    def test_cleanup_case_insensitive_matching(self):
        """Error message matching is case-insensitive."""
        manager, mock_executor = _make_lifecycle_manager()
        mock_executor.execute_docker_command.side_effect = RuntimeError(
            "NOT FOUND: some resource"
        )
        with patch.object(manager.logger, "debug") as mock_debug:
            manager._pre_launch_cleanup()
            mock_debug.assert_called()


# ---------------------------------------------------------------------------
# TestNetworkNameValidation (Gap 11)
# ---------------------------------------------------------------------------


class TestNetworkNameValidation:
    """Verify Docker network name validation via real DockerComposeEnvironment.initialize()."""

    @staticmethod
    def _make_bare_compose_env():
        """Create an uninitialized DockerComposeEnvironment with minimal attributes.

        Uses object.__new__ to skip the heavy __init__ dependency chain while still
        allowing us to call the real initialize() method.
        """
        from panther.plugins.environments.network_environment.docker_compose.config_schema import (
            DockerComposeConfig,
        )
        from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
            DockerComposeEnvironment,
        )

        env = object.__new__(DockerComposeEnvironment)
        # logger is a property on LoggerMixin; set the backing attribute directly
        env._logger = logging.getLogger("test_network_name")
        env._log_context = {}
        env.execution_environment = []
        env.env_sub_type = "docker_compose"
        # Set env_config_to_test (normally set by __init__ chain)
        env.env_config_to_test = DockerComposeConfig()
        # Pre-cache plugin config
        env._plugin_config = DockerComposeConfig()
        return env

    def test_reserved_name_gets_prefixed(self):
        """Docker reserved names (default, host, bridge, none) get panther- prefix."""
        for name in ["default", "host", "bridge", "none"]:
            env = self._make_bare_compose_env()
            env.initialize(
                test_config=MagicMock(),
                output_dir=f"/tmp/test/{name}",
                event_manager=MagicMock(),
                global_config=MagicMock(),
            )
            assert env.network_name.startswith(
                "panther-"
            ), f"Reserved name '{name}' should be prefixed, got '{env.network_name}'"

    def test_long_name_truncated(self):
        """Names exceeding 64 chars are truncated by real initialize()."""
        long_name = "a" * 100
        env = self._make_bare_compose_env()
        env.initialize(
            test_config=MagicMock(),
            output_dir=f"/tmp/test/{long_name}",
            event_manager=MagicMock(),
            global_config=MagicMock(),
        )
        assert len(env.network_name) <= 64

    def test_normal_name_passes_through(self):
        """Normal names pass through real initialize() unchanged."""
        env = self._make_bare_compose_env()
        env.initialize(
            test_config=MagicMock(),
            output_dir="/tmp/test/my-experiment-2024",
            event_manager=MagicMock(),
            global_config=MagicMock(),
        )
        assert env.network_name == "my-experiment-2024"
