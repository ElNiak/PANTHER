"""Tests for panther build-metrics CLI commands."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from panther.cli.commands.build_metrics import build_metrics


@pytest.mark.unit
class TestBuildMetricsListCommand:
    """Tests for build-metrics list command."""

    def test_list_no_records(self):
        """List command with no records shows appropriate message."""
        runner = CliRunner()
        with patch(
            "panther.cli.commands.build_metrics._get_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.read_records.return_value = []
            mock_get_storage.return_value = mock_storage

            result = runner.invoke(build_metrics, ["list"])
            assert result.exit_code == 0
            assert "No metrics records found" in result.output

    def test_list_respects_limit(self):
        """List command passes limit to storage."""
        runner = CliRunner()
        with patch(
            "panther.cli.commands.build_metrics._get_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.read_records.return_value = []
            mock_get_storage.return_value = mock_storage

            result = runner.invoke(build_metrics, ["list", "--limit", "5"])
            assert result.exit_code == 0
            mock_storage.read_records.assert_called_once_with(limit=5)


@pytest.mark.unit
class TestBuildMetricsShowCommand:
    """Tests for build-metrics show command."""

    def test_show_nonexistent_record(self):
        """Show command with nonexistent ID shows error."""
        runner = CliRunner()
        with patch(
            "panther.cli.commands.build_metrics._get_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.get_record_by_id.return_value = None
            mock_get_storage.return_value = mock_storage

            result = runner.invoke(build_metrics, ["show", "nonexistent-id"])
            assert result.exit_code == 0
            assert "No record found" in result.output


@pytest.mark.unit
class TestBuildMetricsExportCommand:
    """Tests for build-metrics export command."""

    def test_export_writes_json(self, tmp_path):
        """Export command writes valid JSON to file."""
        runner = CliRunner()
        output_file = tmp_path / "export.json"
        with patch(
            "panther.cli.commands.build_metrics._get_storage"
        ) as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.read_records.return_value = [
                {"run_id": "test-1", "type": "tests", "metrics": {"duration": 10.0}}
            ]
            mock_get_storage.return_value = mock_storage

            result = runner.invoke(
                build_metrics, ["export", "--output", str(output_file)]
            )
            assert result.exit_code == 0
            assert output_file.exists()
            data = json.loads(output_file.read_text())
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["run_id"] == "test-1"
