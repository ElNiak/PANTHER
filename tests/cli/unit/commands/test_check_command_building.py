"""Tests for check command building logic."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from panther.cli.core.main import cli

pytestmark = pytest.mark.unit


class TestCheckCommandBuilding:
    """Test that check command builds correct subprocess commands."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_subprocess(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="All done!", stderr=""
            )
            yield mock_run

    def test_format_check_builds_correct_command(
        self, cli_runner, mock_subprocess, tmp_path
    ):
        """Format check-only should produce ['black', '--check', <path>]."""
        result = cli_runner.invoke(cli, ["check", "--format", "--path", str(tmp_path)])
        assert result.exception is None, f"Crashed: {result.exception}"
        assert mock_subprocess.called, "subprocess.run was never reached"
        cmd = mock_subprocess.call_args[0][0]
        assert cmd == ["black", "--check", str(tmp_path)]

    def test_format_fix_builds_correct_command(
        self, cli_runner, mock_subprocess, tmp_path
    ):
        """Format fix mode should produce ['black', <path>] with no empty string."""
        result = cli_runner.invoke(
            cli, ["check", "--format", "--fix", "--path", str(tmp_path)]
        )
        assert result.exception is None, f"Crashed: {result.exception}"
        assert mock_subprocess.called, "subprocess.run was never reached"
        cmd = mock_subprocess.call_args[0][0]
        assert cmd == ["black", str(tmp_path)]

    def test_imports_check_builds_correct_command(
        self, cli_runner, mock_subprocess, tmp_path
    ):
        """Imports check-only should produce ['isort', '--check-only', <path>]."""
        result = cli_runner.invoke(cli, ["check", "--imports", "--path", str(tmp_path)])
        assert result.exception is None, f"Crashed: {result.exception}"
        assert mock_subprocess.called
        cmd = mock_subprocess.call_args[0][0]
        assert cmd == ["isort", "--check-only", str(tmp_path)]

    def test_imports_fix_builds_correct_command(
        self, cli_runner, mock_subprocess, tmp_path
    ):
        """Imports fix mode should produce ['isort', <path>]."""
        result = cli_runner.invoke(
            cli, ["check", "--imports", "--fix", "--path", str(tmp_path)]
        )
        assert result.exception is None, f"Crashed: {result.exception}"
        assert mock_subprocess.called
        cmd = mock_subprocess.call_args[0][0]
        assert cmd == ["isort", str(tmp_path)]
