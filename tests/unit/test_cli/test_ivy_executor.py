"""Tests for the IvyExecutor Docker/host/compose execution layer."""

import pytest

pytest.importorskip("panther_ivy.api", reason="panther_ivy package not installed")

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from api.types import CommandResult, ExecutionResult

from panther.cli_click.commands.ivy_executor import (
    CONTAINER_BASE_PATH,
    ExecutionTarget,
    IvyExecutor,
)


class TestExecutionTargetResolution:
    @patch("panther.cli_click.commands.ivy_executor.shutil.which")
    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_resolve_docker_when_image_exists(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0)
        executor = IvyExecutor(target="auto")
        assert executor.resolve_target() == ExecutionTarget.DOCKER

    @patch("panther.cli_click.commands.ivy_executor.shutil.which")
    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_resolve_host_when_no_docker_but_ivyc(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=1)  # docker inspect fails
        mock_which.return_value = "/usr/bin/ivyc"
        executor = IvyExecutor(target="auto")
        assert executor.resolve_target() == ExecutionTarget.HOST

    @patch("panther.cli_click.commands.ivy_executor.shutil.which")
    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_resolve_raises_when_nothing_available(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=1)
        mock_which.return_value = None
        executor = IvyExecutor(target="auto")
        with pytest.raises(RuntimeError, match="No execution target"):
            executor.resolve_target()

    def test_explicit_docker_target(self):
        executor = IvyExecutor(target="docker")
        assert executor.resolve_target() == ExecutionTarget.DOCKER

    def test_explicit_host_target(self):
        executor = IvyExecutor(target="host")
        assert executor.resolve_target() == ExecutionTarget.HOST


class TestVolumeMappingComputation:
    def test_compute_volume_mounts_standard_path(self):
        executor = IvyExecutor(target="docker")
        ivy_file = Path(
            "/home/user/panther_ivy/protocol-testing/quic/" "quic_tests/test.ivy"
        )
        mounts = executor._compute_volume_mounts(ivy_file)
        assert any("/opt/panther_ivy/protocol-testing" in v for v in mounts.values())

    def test_compute_host_to_container_path(self):
        executor = IvyExecutor(target="docker")
        host_path = Path(
            "/home/user/panther_ivy/protocol-testing/quic/" "quic_tests/test.ivy"
        )
        container_path = executor._host_to_container_path(host_path)
        assert container_path.startswith("/opt/panther_ivy/protocol-testing")
        assert "quic" in container_path


class TestCommandExecution:
    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_execute_on_host(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
        executor = IvyExecutor(target="host")
        cmd = CommandResult(
            commands=["echo hello"],
            environment={"FOO": "bar"},
            working_dir="/tmp",
        )
        result = executor.execute(cmd)
        assert isinstance(result, ExecutionResult)
        assert result.exit_code == 0
        assert result.target == "host"

    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_execute_on_docker(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="compiled\n", stderr="")
        executor = IvyExecutor(target="docker")
        executor._ivy_file = Path("protocol-testing/quic/quic_tests/test.ivy")
        cmd = CommandResult(
            commands=["ivyc target=test test.ivy"],
            environment={},
            working_dir="/opt/panther_ivy/protocol-testing/quic/quic_tests",
        )
        result = executor.execute(cmd)
        assert result.exit_code == 0
        assert result.target == "docker"


class TestComposeExecution:
    def test_explicit_compose_target(self):
        executor = IvyExecutor(target="compose")
        assert executor.resolve_target() == ExecutionTarget.COMPOSE

    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_compose_uses_docker_compose_exec(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
        executor = IvyExecutor(target="compose")
        executor._compose_service = "ivy_server"
        cmd = CommandResult(
            commands=["echo hello"],
            environment={"FOO": "bar"},
            working_dir="/opt/panther_ivy/protocol-testing",
        )
        result = executor.execute(cmd)
        assert result.exit_code == 0
        assert result.target == "compose"
        # Verify docker compose exec was called
        call_args = mock_run.call_args
        docker_cmd = call_args[0][0]
        assert "docker" in docker_cmd
        assert "compose" in docker_cmd
        assert "exec" in docker_cmd

    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_compose_resolves_service_name(self, mock_run):
        """Auto-detect should find service with 'ivy' in name."""
        # First call: docker compose ps
        ps_output = json.dumps(
            [
                {"Name": "project-ivy_server-1", "Service": "ivy_server"},
            ]
        )
        # Second call: actual exec
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=ps_output, stderr=""),
            MagicMock(returncode=0, stdout="ok\n", stderr=""),
        ]
        executor = IvyExecutor(target="compose")
        # No explicit service set, should auto-detect
        cmd = CommandResult(
            commands=["echo hello"],
            environment={},
            working_dir="/tmp",
        )
        result = executor.execute(cmd)
        assert result.exit_code == 0

    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_compose_with_explicit_service_name(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
        executor = IvyExecutor(target="compose")
        executor._compose_service = "my_custom_ivy"
        cmd = CommandResult(
            commands=["echo hello"],
            environment={},
            working_dir="/tmp",
        )
        result = executor.execute(cmd)
        call_args = mock_run.call_args
        docker_cmd = call_args[0][0]
        assert "my_custom_ivy" in docker_cmd

    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_compose_auto_detect_finds_running_service(self, mock_run):
        ps_output = json.dumps(
            [
                {"Name": "project-ivy_server-1", "Service": "ivy_server"},
                {"Name": "project-picoquic-1", "Service": "picoquic"},
            ]
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=ps_output, stderr="")
        executor = IvyExecutor(target="compose")
        service = executor._find_compose_service()
        assert service == "ivy_server"

    @patch("panther.cli_click.commands.ivy_executor.subprocess.run")
    def test_compose_auto_detect_raises_when_no_service(self, mock_run):
        ps_output = json.dumps(
            [
                {"Name": "project-picoquic-1", "Service": "picoquic"},
            ]
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=ps_output, stderr="")
        executor = IvyExecutor(target="compose")
        with pytest.raises(RuntimeError, match="No.*ivy.*service"):
            executor._find_compose_service()

    def test_compose_get_base_path_returns_container_path(self):
        executor = IvyExecutor(target="compose")
        assert executor.get_base_path() == CONTAINER_BASE_PATH
