"""Tests for plugins validate path type handling."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from panther.cli.core.main import cli

pytestmark = pytest.mark.unit


class TestPluginsValidatePathConversion:
    """Test that validate converts Click's str path to Path."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_validate_converts_str_to_path(self, cli_runner, tmp_path):
        """Validate must convert Click's str to Path before calling .is_dir()."""
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "test_plugin.py").write_text("# plugin file")

        result = cli_runner.invoke(cli, ["plugins", "validate", str(plugin_dir)])
        assert result.exception is None or not isinstance(
            result.exception, AttributeError
        ), f"AttributeError crash: {result.exception}"
        assert "PANTHER Plugin Validator" in result.output

    def test_validate_handles_file_path(self, cli_runner, tmp_path):
        """Validate should work with a single file path."""
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text("class MyPlugin: pass")

        result = cli_runner.invoke(cli, ["plugins", "validate", str(plugin_file)])
        assert result.exception is None or not isinstance(
            result.exception, AttributeError
        ), f"AttributeError crash: {result.exception}"

    def test_validate_rejects_nonexistent_path(self, cli_runner):
        """Click should reject nonexistent paths before function runs."""
        result = cli_runner.invoke(cli, ["plugins", "validate", "/nonexistent/path"])
        assert result.exit_code != 0
