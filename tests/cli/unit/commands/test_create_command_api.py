"""Tests for create command API parameter correctness."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from panther.cli.core.main import cli

pytestmark = pytest.mark.unit


class TestCreateCommandAPI:
    """Test that create commands pass correct parameters to creator functions."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_create_plugin_does_not_pass_force_overwrite(self, cli_runner):
        """create_plugin() does not accept force_overwrite; verify it is not passed."""
        with patch(
            "panther.tools.plugins.plugin_creator.create_plugin", return_value=True
        ) as mock_create:
            result = cli_runner.invoke(
                cli,
                [
                    "create",
                    "plugin",
                    "service",
                    "test_plugin",
                ],
            )
            assert (
                mock_create.called
            ), f"create_plugin was not called; output: {result.output}"
            args, kwargs = mock_create.call_args
            assert (
                "force_overwrite" not in kwargs
            ), "force_overwrite should not be passed to create_plugin()"
            assert "in_development_mode" in kwargs
            assert "create_subplugins" in kwargs

    def test_create_subplugin_does_not_pass_force_overwrite(self, cli_runner):
        """create_subplugin() does not accept force_overwrite; verify it is not passed."""
        with patch(
            "panther.tools.plugins.plugin_creator.create_subplugin", return_value=True
        ) as mock_create:
            result = cli_runner.invoke(
                cli,
                ["create", "subplugin", "service", "picoquic", "test_sub"],
            )
            assert (
                mock_create.called
            ), f"create_subplugin was not called; output: {result.output}"
            args, kwargs = mock_create.call_args
            assert (
                "force_overwrite" not in kwargs
            ), "force_overwrite should not be passed to create_subplugin()"
            assert "in_development_mode" in kwargs
