"""Tests for plugins params/scan metadata handling."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from panther.cli.core.main import cli
from panther.plugins.core.structures.plugin_metadata import PluginMetadata

pytestmark = pytest.mark.unit


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_plugins_dict():
    """Realistic plugins_dict as returned by discover_plugins()."""
    return {
        "picoquic": PluginMetadata(
            name="picoquic", type="iut", version="1.0.0", path=Path("/fake/picoquic")
        ),
        "aioquic": PluginMetadata(
            name="aioquic", type="iut", version="0.9.0", path=Path("/fake/aioquic")
        ),
        "ivy": PluginMetadata(
            name="ivy", type="tester", version="2.0.0", path=Path("/fake/ivy")
        ),
    }


class TestPluginsParamsMetadata:
    """Test that params command handles PluginMetadata correctly."""

    def test_params_finds_plugin_type_from_metadata(
        self, cli_runner, mock_plugins_dict
    ):
        """Params should find plugin type via PluginMetadata.type, not 'in' check."""
        mock_discovery = MagicMock()
        mock_discovery.discover_plugins.return_value = mock_plugins_dict

        with (
            patch(
                "panther.plugins.core.plugin_discovery.PluginDiscovery",
                return_value=mock_discovery,
            ),
            patch("panther.config.ConfigurationManager") as mock_config,
        ):
            mock_config.return_value.list_plugin_parameters.return_value = {
                "port": {"type": "int", "default": 4433}
            }
            result = cli_runner.invoke(cli, ["plugins", "params", "picoquic"])
            assert result.exception is None or not isinstance(
                result.exception, TypeError
            ), f"TypeError crash: {result.exception}"


class TestPluginsScanMetadata:
    """Test that scan command handles PluginMetadata correctly."""

    def test_scan_handles_plugin_metadata_dict(self, cli_runner, mock_plugins_dict):
        """Scan should handle Dict[str, PluginMetadata] without calling len() on metadata."""
        mock_discovery = MagicMock()
        mock_discovery.discover_plugins.return_value = mock_plugins_dict

        with patch(
            "panther.plugins.core.plugin_discovery.PluginDiscovery",
            return_value=mock_discovery,
        ):
            result = cli_runner.invoke(cli, ["plugins", "scan"])
            assert result.exception is None, f"Crashed: {result.exception}"
            assert result.exit_code == 0, f"Failed: {result.output}"
            assert "3 plugin(s)" in result.output

    def test_scan_groups_by_type_and_shows_versions(
        self, cli_runner, mock_plugins_dict
    ):
        """Scan should group plugins by type and display version from metadata."""
        mock_discovery = MagicMock()
        mock_discovery.discover_plugins.return_value = mock_plugins_dict

        with patch(
            "panther.plugins.core.plugin_discovery.PluginDiscovery",
            return_value=mock_discovery,
        ):
            result = cli_runner.invoke(cli, ["plugins", "scan"])
            assert result.exception is None, f"Crashed: {result.exception}"
            assert "picoquic" in result.output
            assert "v1.0.0" in result.output
            assert "ivy" in result.output
            assert "v2.0.0" in result.output
