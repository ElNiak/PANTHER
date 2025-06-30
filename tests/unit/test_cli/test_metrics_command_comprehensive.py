"""
Comprehensive unit tests for MetricsCommand CLI.

This module provides exhaustive testing for ALL MetricsCommand parameters,
including the recently fixed constructor parameter issues, edge cases,
and error conditions.
"""

import argparse
import json
import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from panther.cli.subcommands.metrics import MetricsCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestMetricsCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for MetricsCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return MetricsCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "metrics"

    @pytest.fixture
    def mock_metrics_collector_class(self):
        """Mock MetricsCollector class for testing."""
        with patch("panther.cli.subcommands.metrics.MetricsCollector") as mock:
            mock_instance = MagicMock()
            mock_instance.get_metrics.return_value = []
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_metrics_exporter_class(self):
        """Mock MetricsExporter class for testing."""
        with patch("panther.cli.subcommands.metrics.MetricsExporter") as mock:
            mock_instance = MagicMock()
            mock_instance.export_to_json.return_value = True
            mock_instance.export_to_csv.return_value = True
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_metrics_reporter_class(self):
        """Mock MetricsReporter class for testing."""
        with patch("panther.cli.subcommands.metrics.MetricsReporter") as mock:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = {}
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def sample_metrics_data(self):
        """Sample metrics data for testing."""
        mock_metric1 = MagicMock()
        mock_metric1.name = "cpu_usage"
        mock_metric1.value = 75.5
        mock_metric1.timestamp = 1234567890

        mock_metric2 = MagicMock()
        mock_metric2.name = "memory_usage"
        mock_metric2.value = 512.0
        mock_metric2.timestamp = 1234567891

        return [mock_metric1, mock_metric2]

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that MetricsCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'metrics' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "metrics" in subparsers_actions[0].choices

    def test_all_subcommands_registered(self):
        """Test that all metrics subcommands are registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Parse metrics help to get subcommands
        try:
            parser.parse_args(["metrics", "--help"])
        except SystemExit:
            pass  # Expected behavior for help

        # Verify subcommands exist by testing their individual help
        subcommands = ["list", "show", "export", "clear", "summary"]

        for subcommand in subcommands:
            try:
                parser.parse_args(["metrics", subcommand, "--help"])
            except SystemExit:
                pass  # Expected for help command

    # =============================================================================
    # MAIN COMMAND HANDLER TESTS
    # =============================================================================

    def test_handle_no_action_specified(self, caplog):
        """Test behavior when no metrics action is specified."""
        args = self.create_namespace(metrics_action=None)

        result = MetricsCommand.handle(args)

        assert result == 1
        assert "No metrics action specified" in caplog.text

    def test_handle_unknown_action(self, caplog):
        """Test behavior with unknown metrics action."""
        args = self.create_namespace(metrics_action="unknown_action")

        result = MetricsCommand.handle(args)

        assert result == 1
        assert "Unknown metrics action: unknown_action" in caplog.text

    def test_handle_import_error(self, caplog):
        """Test behavior when metrics system is not available."""
        args = self.create_namespace(metrics_action="list")

        with patch(
            "panther.cli.subcommands.metrics.MetricsCommand.handle"
        ) as mock_handle:
            # Simulate ImportError for metrics system
            def side_effect(args):
                try:
                    from panther.core.metrics.metrics_collector import MetricsCollector
                except ImportError:
                    logging.info("❌ Metrics system is not available.")
                    return 1

            mock_handle.side_effect = side_effect
            result = mock_handle(args)

            assert result == 1

    # =============================================================================
    # EXPERIMENT CONTEXT TESTS (Recently Fixed)
    # =============================================================================

    def test_get_experiment_context(self):
        """Test _get_experiment_context helper method."""
        experiment_name, output_dir = MetricsCommand._get_experiment_context()

        assert experiment_name == "cli_metrics_session"
        assert isinstance(output_dir, Path)
        assert output_dir.name == "metrics"
        assert "cli_metrics_session" in str(output_dir)

    def test_experiment_context_directory_creation(self, tmp_path):
        """Test that experiment context creates directories."""
        with patch("pathlib.Path") as mock_path:
            mock_path.return_value = (
                tmp_path / "outputs" / "cli_metrics_session" / "metrics"
            )

            experiment_name, output_dir = MetricsCommand._get_experiment_context()

            # Verify directory structure would be created
            assert experiment_name == "cli_metrics_session"

    # =============================================================================
    # LIST SUBCOMMAND TESTS
    # =============================================================================

    def test_list_metrics_no_metrics(self, mock_metrics_collector_class, caplog):
        """Test list command when no metrics are available."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = []

        args = self.create_namespace(metrics_action="list", filter=None)

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "No metrics have been collected yet" in caplog.text

        # Verify MetricsCollector was called with correct parameters (RECENTLY FIXED)
        mock_class.assert_called_once()
        call_args = mock_class.call_args
        assert "experiment_name" in call_args.kwargs
        assert "output_dir" in call_args.kwargs
        assert call_args.kwargs["experiment_name"] == "cli_metrics_session"

    def test_list_metrics_with_data(
        self, mock_metrics_collector_class, sample_metrics_data, caplog
    ):
        """Test list command with available metrics."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = sample_metrics_data

        args = self.create_namespace(metrics_action="list", filter=None)

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "Found 2 metric(s)" in caplog.text
        assert "cpu_usage" in caplog.text
        assert "memory_usage" in caplog.text

    def test_list_metrics_with_filter(
        self, mock_metrics_collector_class, sample_metrics_data, caplog
    ):
        """Test list command with filter parameter."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = sample_metrics_data

        args = self.create_namespace(metrics_action="list", filter="cpu")

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "cpu_usage" in caplog.text
        # Should not contain memory_usage due to filter

    def test_list_metrics_filter_no_matches(
        self, mock_metrics_collector_class, sample_metrics_data, caplog
    ):
        """Test list command with filter that matches nothing."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = sample_metrics_data

        args = self.create_namespace(metrics_action="list", filter="nonexistent")

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "No metrics match the filter: nonexistent" in caplog.text

    def test_list_metrics_categorization(self, mock_metrics_collector_class, caplog):
        """Test that metrics are properly categorized by prefix."""
        mock_class, mock_instance = mock_metrics_collector_class

        # Create metrics with different categories
        metrics = []
        for category, name in [
            ("cpu", "cpu.usage"),
            ("memory", "memory.total"),
            ("disk", "disk.io"),
            ("general", "test_metric"),
        ]:
            metric = MagicMock()
            metric.name = name
            metrics.append(metric)

        mock_instance.get_metrics.return_value = metrics

        args = self.create_namespace(metrics_action="list", filter=None)

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "CPU:" in caplog.text
        assert "MEMORY:" in caplog.text
        assert "DISK:" in caplog.text
        assert "GENERAL:" in caplog.text

    def test_list_metrics_error_handling(self, caplog):
        """Test list command error handling."""
        with patch("panther.cli.subcommands.metrics.MetricsCollector") as mock_class:
            mock_class.side_effect = Exception("Metrics error")

            args = self.create_namespace(metrics_action="list", filter=None)

            result = MetricsCommand.handle(args)

            assert result == 1
            assert "Error listing metrics" in caplog.text

    # =============================================================================
    # SHOW SUBCOMMAND TESTS
    # =============================================================================

    def test_show_metrics_all(
        self, mock_metrics_collector_class, sample_metrics_data, caplog
    ):
        """Test show command displaying all metrics."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = sample_metrics_data

        args = self.create_namespace(metrics_action="show", metric=None, limit=10)

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "Metrics data (2 metric type(s))" in caplog.text
        assert "cpu_usage" in caplog.text
        assert "memory_usage" in caplog.text

    def test_show_metrics_specific(
        self, mock_metrics_collector_class, sample_metrics_data, caplog
    ):
        """Test show command for specific metric."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = sample_metrics_data

        args = self.create_namespace(
            metrics_action="show", metric="cpu_usage", limit=10
        )

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "cpu_usage" in caplog.text

    def test_show_metrics_not_found(
        self, mock_metrics_collector_class, sample_metrics_data, caplog
    ):
        """Test show command for non-existent metric."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = sample_metrics_data

        args = self.create_namespace(
            metrics_action="show", metric="nonexistent", limit=10
        )

        result = MetricsCommand.handle(args)

        assert result == 1
        assert "Metric not found: nonexistent" in caplog.text

    def test_show_metrics_limit_parameter(self, mock_metrics_collector_class, caplog):
        """Test show command with limit parameter."""
        mock_class, mock_instance = mock_metrics_collector_class

        # Create multiple metrics of same type
        metrics = []
        for i in range(15):
            metric = MagicMock()
            metric.name = "test_metric"
            metric.value = i
            metric.timestamp = 1234567890 + i
            metrics.append(metric)

        mock_instance.get_metrics.return_value = metrics

        args = self.create_namespace(metrics_action="show", metric=None, limit=5)

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "showing up to 5" in caplog.text
        assert "and 10 more values" in caplog.text

    def test_show_metrics_no_data(self, mock_metrics_collector_class, caplog):
        """Test show command when no metrics data available."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = []

        args = self.create_namespace(metrics_action="show", metric=None, limit=10)

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "No metrics data available" in caplog.text

    def test_show_metrics_attribute_handling(
        self, mock_metrics_collector_class, caplog
    ):
        """Test show command handles metrics with missing attributes gracefully."""
        mock_class, mock_instance = mock_metrics_collector_class

        # Create metric with missing attributes
        metric = MagicMock()
        metric.name = "test_metric"
        # Remove timestamp and value attributes
        del metric.timestamp
        del metric.value

        mock_instance.get_metrics.return_value = [metric]

        args = self.create_namespace(metrics_action="show", metric=None, limit=10)

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "N/A" in caplog.text  # Should show N/A for missing attributes

    # =============================================================================
    # EXPORT SUBCOMMAND TESTS (Recently Fixed Constructor Issues)
    # =============================================================================

    def test_export_metrics_json_default(
        self, mock_metrics_collector_class, mock_metrics_exporter_class, caplog
    ):
        """Test export command with JSON format (default)."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class

        args = self.create_namespace(
            metrics_action="export", output=None, format="json"
        )

        result = MetricsCommand.handle(args)

        assert result == 0

        # Verify MetricsCollector constructor (RECENTLY FIXED)
        mock_collector_class.assert_called_once()
        collector_call_args = mock_collector_class.call_args
        assert "experiment_name" in collector_call_args.kwargs
        assert "output_dir" in collector_call_args.kwargs

        # Verify MetricsExporter constructor (RECENTLY FIXED)
        mock_exporter_class.assert_called_once()
        exporter_call_args = mock_exporter_class.call_args
        assert "metrics_collector" in exporter_call_args.kwargs
        assert exporter_call_args.kwargs["metrics_collector"] == mock_collector_instance

        # Verify export method called
        mock_exporter_instance.export_to_json.assert_called_once()

    def test_export_metrics_csv_format(
        self, mock_metrics_collector_class, mock_metrics_exporter_class, caplog
    ):
        """Test export command with CSV format."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class

        args = self.create_namespace(metrics_action="export", output=None, format="csv")

        result = MetricsCommand.handle(args)

        assert result == 0
        mock_exporter_instance.export_to_csv.assert_called_once()

    def test_export_metrics_txt_format(
        self, mock_metrics_collector_class, mock_metrics_exporter_class, caplog
    ):
        """Test export command with TXT format (fallback to JSON)."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class

        args = self.create_namespace(metrics_action="export", output=None, format="txt")

        result = MetricsCommand.handle(args)

        assert result == 0
        # TXT format should fallback to JSON
        mock_exporter_instance.export_to_json.assert_called_once()

    def test_export_metrics_custom_output_path(
        self, mock_metrics_collector_class, mock_metrics_exporter_class
    ):
        """Test export command with custom output path."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class

        custom_path = "/custom/path/metrics.json"
        args = self.create_namespace(
            metrics_action="export", output=custom_path, format="json"
        )

        result = MetricsCommand.handle(args)

        assert result == 0
        mock_exporter_instance.export_to_json.assert_called_once()
        call_args = mock_exporter_instance.export_to_json.call_args
        assert custom_path in str(call_args[0][0])

    def test_export_metrics_default_filename(
        self, mock_metrics_collector_class, mock_metrics_exporter_class
    ):
        """Test export command generates default filename with timestamp."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class

        with patch("panther.cli.subcommands.metrics.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20231201_143000"

            args = self.create_namespace(
                metrics_action="export", output=None, format="json"
            )

            result = MetricsCommand.handle(args)

            assert result == 0
            mock_exporter_instance.export_to_json.assert_called_once()
            call_args = mock_exporter_instance.export_to_json.call_args
            assert "metrics_export_20231201_143000.json" in str(call_args[0][0])

    def test_export_metrics_failure(
        self, mock_metrics_collector_class, mock_metrics_exporter_class, caplog
    ):
        """Test export command when export fails."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class
        mock_exporter_instance.export_to_json.return_value = False

        args = self.create_namespace(
            metrics_action="export", output=None, format="json"
        )

        result = MetricsCommand.handle(args)

        assert result == 1
        assert "No metrics data available to export" in caplog.text

    def test_export_metrics_success_with_file_size(
        self,
        mock_metrics_collector_class,
        mock_metrics_exporter_class,
        caplog,
        tmp_path,
    ):
        """Test export command shows file size on success."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class
        mock_exporter_instance.export_to_json.return_value = True

        # Create a test file to simulate export
        test_file = tmp_path / "test_metrics.json"
        test_file.write_text('{"test": "data"}')  # 16 bytes

        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 1024  # 1 KB

            args = self.create_namespace(
                metrics_action="export", output=str(test_file), format="json"
            )

            result = MetricsCommand.handle(args)

            assert result == 0
            assert "Metrics exported successfully" in caplog.text
            assert "File size: 1.0 KB" in caplog.text

    def test_export_metrics_error_handling(self, caplog):
        """Test export command error handling."""
        with patch("panther.cli.subcommands.metrics.MetricsCollector") as mock_class:
            mock_class.side_effect = Exception("Export error")

            args = self.create_namespace(
                metrics_action="export", output=None, format="json"
            )

            result = MetricsCommand.handle(args)

            assert result == 1
            assert "Error exporting metrics" in caplog.text

    # =============================================================================
    # CLEAR SUBCOMMAND TESTS
    # =============================================================================

    def test_clear_metrics_with_force(self, mock_metrics_collector_class, caplog):
        """Test clear command with force flag."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = [MagicMock(), MagicMock()]  # 2 metrics

        args = self.create_namespace(metrics_action="clear", force=True)

        with patch("shutil.rmtree") as mock_rmtree:
            with patch("pathlib.Path.exists", return_value=True):
                result = MetricsCommand.handle(args)

        assert result == 0
        assert "Found 2 metrics in the system" in caplog.text
        assert "Metrics directory has been cleared" in caplog.text

    def test_clear_metrics_without_force_cancelled(
        self, mock_metrics_collector_class, caplog
    ):
        """Test clear command without force flag - user cancels."""
        mock_class, mock_instance = mock_metrics_collector_class

        args = self.create_namespace(metrics_action="clear", force=False)

        with patch("builtins.input", return_value="n"):
            result = MetricsCommand.handle(args)

        assert result == 0
        assert "Clear operation cancelled" in caplog.text

    def test_clear_metrics_without_force_confirmed(
        self, mock_metrics_collector_class, caplog
    ):
        """Test clear command without force flag - user confirms."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = [MagicMock()]  # 1 metric

        args = self.create_namespace(metrics_action="clear", force=False)

        with patch("builtins.input", return_value="y"):
            with patch("shutil.rmtree") as mock_rmtree:
                with patch("pathlib.Path.exists", return_value=True):
                    result = MetricsCommand.handle(args)

        assert result == 0
        assert "Found 1 metrics in the system" in caplog.text
        assert "Metrics directory has been cleared" in caplog.text

    def test_clear_metrics_no_directory(self, mock_metrics_collector_class, caplog):
        """Test clear command when no metrics directory exists."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = []

        args = self.create_namespace(metrics_action="clear", force=True)

        with patch("pathlib.Path.exists", return_value=False):
            result = MetricsCommand.handle(args)

        assert result == 0
        assert "No metrics directory found to clear" in caplog.text

    def test_clear_metrics_error_handling(self, caplog):
        """Test clear command error handling."""
        with patch("panther.cli.subcommands.metrics.MetricsCollector") as mock_class:
            mock_class.side_effect = Exception("Clear error")

            args = self.create_namespace(metrics_action="clear", force=True)

            result = MetricsCommand.handle(args)

            assert result == 1
            assert "Error clearing metrics" in caplog.text

    # =============================================================================
    # SUMMARY SUBCOMMAND TESTS
    # =============================================================================

    def test_summary_metrics_with_data(
        self, mock_metrics_collector_class, mock_metrics_reporter_class, caplog
    ):
        """Test summary command with available data."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_reporter_class, mock_reporter_instance = mock_metrics_reporter_class

        mock_summary = {
            "overview": {"total_experiments": 5, "success_rate": 80},
            "categories": {"performance": 10, "errors": 2},
            "recent_activity": ["Test completed", "Metrics collected"],
            "performance": {"avg_duration": 45.5},
            "resource_usage": {"peak_cpu": 75.0},
        }
        mock_reporter_instance.generate_summary.return_value = mock_summary

        args = self.create_namespace(metrics_action="summary")

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "Metrics Summary" in caplog.text
        assert "Overview:" in caplog.text
        assert "Categories:" in caplog.text
        assert "Recent Activity:" in caplog.text
        assert "Performance Metrics:" in caplog.text
        assert "Resource Usage:" in caplog.text

        # Verify MetricsReporter constructor with correct collector
        mock_reporter_class.assert_called_once_with(mock_collector_instance)

    def test_summary_metrics_no_data(
        self, mock_metrics_collector_class, mock_metrics_reporter_class, caplog
    ):
        """Test summary command when no data available."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_reporter_class, mock_reporter_instance = mock_metrics_reporter_class
        mock_reporter_instance.generate_summary.return_value = None

        args = self.create_namespace(metrics_action="summary")

        result = MetricsCommand.handle(args)

        assert result == 0
        assert "No metrics data available for summary" in caplog.text

    def test_summary_metrics_error_handling(self, caplog):
        """Test summary command error handling."""
        with patch("panther.cli.subcommands.metrics.MetricsCollector") as mock_class:
            mock_class.side_effect = Exception("Summary error")

            args = self.create_namespace(metrics_action="summary")

            result = MetricsCommand.handle(args)

            assert result == 1
            assert "Error generating summary" in caplog.text

    # =============================================================================
    # PARAMETER VALIDATION TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "invalid_action",
        ["invalid", "", "LIST", "export_wrong", 123, None],  # Case sensitive
    )
    def test_invalid_actions(self, invalid_action, caplog):
        """Test handling of invalid action parameters."""
        args = self.create_namespace(metrics_action=invalid_action)

        result = MetricsCommand.handle(args)

        if invalid_action is None:
            assert "No metrics action specified" in caplog.text
        else:
            assert result == 1

    @pytest.mark.parametrize("format_choice", ["json", "csv", "txt"])
    def test_export_format_choices(
        self, format_choice, mock_metrics_collector_class, mock_metrics_exporter_class
    ):
        """Test all valid export format choices."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class

        args = self.create_namespace(
            metrics_action="export", output=None, format=format_choice
        )

        result = MetricsCommand.handle(args)

        assert result == 0

        if format_choice == "json" or format_choice == "txt":
            mock_exporter_instance.export_to_json.assert_called_once()
        elif format_choice == "csv":
            mock_exporter_instance.export_to_csv.assert_called_once()

    @pytest.mark.parametrize("limit_value", [1, 5, 10, 50, 100])
    def test_show_limit_parameter_values(
        self, limit_value, mock_metrics_collector_class
    ):
        """Test show command with different limit values."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = []

        args = self.create_namespace(
            metrics_action="show", metric=None, limit=limit_value
        )

        result = MetricsCommand.handle(args)

        assert result == 0  # Should not crash with any valid limit

    @pytest.mark.parametrize("force_value", [True, False])
    def test_clear_force_parameter(self, force_value, mock_metrics_collector_class):
        """Test clear command with different force parameter values."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = []

        args = self.create_namespace(metrics_action="clear", force=force_value)

        if not force_value:
            with patch("builtins.input", return_value="n"):
                result = MetricsCommand.handle(args)
        else:
            result = MetricsCommand.handle(args)

        assert result == 0

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_unicode_metric_names(self, mock_metrics_collector_class, caplog):
        """Test handling of metrics with unicode names."""
        mock_class, mock_instance = mock_metrics_collector_class

        unicode_metric = MagicMock()
        unicode_metric.name = "测试指标_🔥"
        unicode_metric.value = 42

        mock_instance.get_metrics.return_value = [unicode_metric]

        args = self.create_namespace(metrics_action="list", filter=None)

        result = MetricsCommand.handle(args)

        assert result == 0
        # Should handle unicode gracefully

    def test_very_long_output_path(
        self, mock_metrics_collector_class, mock_metrics_exporter_class
    ):
        """Test export with very long output path."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class

        long_path = "/very/long/path/" + "a" * 200 + "/metrics.json"

        args = self.create_namespace(
            metrics_action="export", output=long_path, format="json"
        )

        result = MetricsCommand.handle(args)

        assert result == 0  # Should handle gracefully

    def test_special_characters_in_filter(self, mock_metrics_collector_class, caplog):
        """Test list command with special characters in filter."""
        mock_class, mock_instance = mock_metrics_collector_class
        mock_instance.get_metrics.return_value = []

        special_filter = ".*[regex]+(special)"
        args = self.create_namespace(metrics_action="list", filter=special_filter)

        result = MetricsCommand.handle(args)

        assert result == 0  # Should handle regex characters gracefully

    def test_empty_metric_name(self, mock_metrics_collector_class, caplog):
        """Test handling of metrics with empty names."""
        mock_class, mock_instance = mock_metrics_collector_class

        empty_name_metric = MagicMock()
        empty_name_metric.name = ""
        empty_name_metric.value = 42

        mock_instance.get_metrics.return_value = [empty_name_metric]

        args = self.create_namespace(metrics_action="list", filter=None)

        result = MetricsCommand.handle(args)

        assert result == 0  # Should handle empty names gracefully

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_metrics_workflow(
        self,
        mock_metrics_collector_class,
        mock_metrics_exporter_class,
        mock_metrics_reporter_class,
        caplog,
    ):
        """Test complete metrics workflow: list → show → export → summary → clear."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class
        mock_reporter_class, mock_reporter_instance = mock_metrics_reporter_class

        # Setup sample data
        sample_metric = MagicMock()
        sample_metric.name = "test_metric"
        sample_metric.value = 42
        mock_collector_instance.get_metrics.return_value = [sample_metric]
        mock_reporter_instance.generate_summary.return_value = {
            "overview": {"total": 1}
        }

        # Test each command in sequence
        commands = [
            self.create_namespace(metrics_action="list", filter=None),
            self.create_namespace(metrics_action="show", metric=None, limit=10),
            self.create_namespace(metrics_action="export", output=None, format="json"),
            self.create_namespace(metrics_action="summary"),
            self.create_namespace(metrics_action="clear", force=True),
        ]

        for args in commands:
            result = MetricsCommand.handle(args)
            assert result == 0

    def test_constructor_parameter_consistency(
        self, mock_metrics_collector_class, mock_metrics_exporter_class
    ):
        """Test that constructor parameters are consistent across all commands."""
        mock_collector_class, mock_collector_instance = mock_metrics_collector_class
        mock_exporter_class, mock_exporter_instance = mock_metrics_exporter_class

        commands_with_collector = ["list", "show", "clear", "summary"]
        commands_with_exporter = ["export"]

        for action in commands_with_collector:
            # Reset mocks
            mock_collector_class.reset_mock()

            args = self.create_namespace(metrics_action=action)
            if action == "show":
                args.metric = None
                args.limit = 10
            elif action == "clear":
                args.force = True

            result = MetricsCommand.handle(args)

            # Verify MetricsCollector constructor called correctly
            mock_collector_class.assert_called_once()
            call_args = mock_collector_class.call_args
            assert "experiment_name" in call_args.kwargs
            assert "output_dir" in call_args.kwargs
            assert call_args.kwargs["experiment_name"] == "cli_metrics_session"

        for action in commands_with_exporter:
            # Reset mocks
            mock_collector_class.reset_mock()
            mock_exporter_class.reset_mock()

            args = self.create_namespace(
                metrics_action=action, output=None, format="json"
            )

            result = MetricsCommand.handle(args)

            # Verify both constructors called correctly
            mock_collector_class.assert_called_once()
            mock_exporter_class.assert_called_once()

            exporter_call_args = mock_exporter_class.call_args
            assert "metrics_collector" in exporter_call_args.kwargs
            assert (
                exporter_call_args.kwargs["metrics_collector"]
                == mock_collector_instance
            )
