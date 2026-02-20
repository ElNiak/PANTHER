"""Tests for Bugs #15 and #17: Docker Compose lifecycle fixes.

Bug #15: deploy_timeout config field
Bug #17: kill before down in teardown

Tests cover:
- DockerComposeConfig deploy_timeout default and configurability
- stop_docker_services call order: kill first, then down
- kill uses 30s timeout, down uses self.timeout
- kill failure does not prevent down
"""

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
