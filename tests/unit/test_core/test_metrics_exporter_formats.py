"""Tests for MetricsExporter output formats: CSV.

Covers export_to_csv() and the internal helper methods that produce CSV content.
"""

import csv

import pytest

from panther.core.metrics.enums import MetricType, Phase
from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.metrics.metrics_exporter import MetricsExporter

pytestmark = [pytest.mark.unit]


@pytest.fixture
def populated_collector(tmp_path):
    """Create a MetricsCollector with realistic data across all metric types."""
    c = MetricsCollector(
        experiment_name="format_test",
        output_dir=tmp_path / "experiment",
        collection_interval=60.0,
    )
    # Timing metrics
    c.record_metric(
        "setup_duration", MetricType.TIMING, 5.0, phase=Phase.ENVIRONMENT_SETUP
    )
    c.record_metric(
        "test_case_duration", MetricType.TIMING, 12.5, phase=Phase.TEST_EXECUTION
    )

    # Counters
    c.increment_counter("experiments_total", phase=Phase.TEST_EXECUTION)
    c.increment_counter("experiments_successful", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_total", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_total", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_successful", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_failed", phase=Phase.TEST_EXECUTION)

    # Gauges
    c.record_gauge("total_artifact_size_mb", 42.5)

    # Resource metrics (simulating resource_monitor)
    c.record_metric("cpu_percent", MetricType.GAUGE, 45.2, component="resource_monitor")
    c.record_metric(
        "memory_percent", MetricType.GAUGE, 62.0, component="resource_monitor"
    )
    c.record_metric(
        "disk_read_mb_total", MetricType.GAUGE, 100.0, component="resource_monitor"
    )
    c.record_metric(
        "disk_write_mb_total", MetricType.GAUGE, 50.0, component="resource_monitor"
    )

    # Errors
    c.record_error(
        "timeout",
        error_message="Connection timed out",
        component="client",
        phase=Phase.TEST_EXECUTION,
    )

    c.finalize()
    return c


@pytest.fixture
def empty_collector(tmp_path):
    """Create a MetricsCollector with no user-recorded metrics."""
    c = MetricsCollector(
        experiment_name="empty_test",
        output_dir=tmp_path / "experiment",
        collection_interval=60.0,
    )
    c.finalize()
    return c


# ---------- CSV export ----------


class TestCsvExport:
    def test_produces_csv_files(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        csv_dir = tmp_path / "csv_output"
        result = exporter.export_to_csv(csv_dir)

        assert result is True
        csv_files = list(csv_dir.glob("*.csv"))
        assert len(csv_files) >= 3  # timing, error, summary (resource may be empty)

    def test_timing_csv_has_correct_headers(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        csv_dir = tmp_path / "csv_output"
        exporter.export_to_csv(csv_dir)

        timing_files = list(csv_dir.glob("timing_metrics_*.csv"))
        assert len(timing_files) == 1

        with open(timing_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == ["Metric Name", "Duration (seconds)", "Type"]

    def test_timing_csv_contains_recorded_metrics(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        csv_dir = tmp_path / "csv_output"
        exporter.export_to_csv(csv_dir)

        timing_files = list(csv_dir.glob("timing_metrics_*.csv"))
        with open(timing_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)

        metric_names = [row[0] for row in rows]
        assert any("setup_duration" in n for n in metric_names)

    def test_error_csv_has_correct_headers(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        csv_dir = tmp_path / "csv_output"
        exporter.export_to_csv(csv_dir)

        error_files = list(csv_dir.glob("error_metrics_*.csv"))
        assert len(error_files) == 1

        with open(error_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == [
                "Timestamp",
                "Phase",
                "Error Type",
                "Error Message",
                "Component",
            ]

    def test_error_csv_contains_recorded_errors(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        csv_dir = tmp_path / "csv_output"
        exporter.export_to_csv(csv_dir)

        error_files = list(csv_dir.glob("error_metrics_*.csv"))
        with open(error_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)

        assert len(rows) >= 1
        # Error type should be "timeout"
        error_types = [row[2] for row in rows]
        assert "timeout" in error_types

    def test_summary_csv_has_correct_headers(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        csv_dir = tmp_path / "csv_output"
        exporter.export_to_csv(csv_dir)

        summary_files = list(csv_dir.glob("summary_metrics_*.csv"))
        assert len(summary_files) == 1

        with open(summary_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert headers == ["Metric", "Value", "Type"]

    def test_summary_csv_contains_experiment_stats(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        csv_dir = tmp_path / "csv_output"
        exporter.export_to_csv(csv_dir)

        summary_files = list(csv_dir.glob("summary_metrics_*.csv"))
        with open(summary_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)

        metric_names = [row[0] for row in rows]
        assert "total_experiments" in metric_names
        assert "error_count" in metric_names

    def test_resource_csv_created_when_resource_metrics_exist(
        self, tmp_path, populated_collector
    ):
        exporter = MetricsExporter(populated_collector)
        csv_dir = tmp_path / "csv_output"
        exporter.export_to_csv(csv_dir)

        resource_files = list(csv_dir.glob("resource_metrics_*.csv"))
        assert len(resource_files) == 1

        with open(resource_files[0], "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            assert "timestamp" in headers
            assert "name" in headers
            assert "value" in headers

    def test_empty_collector_csv_export_succeeds(self, tmp_path, empty_collector):
        exporter = MetricsExporter(empty_collector)
        csv_dir = tmp_path / "csv_output"
        result = exporter.export_to_csv(csv_dir)

        assert result is True
        csv_files = list(csv_dir.glob("*.csv"))
        assert len(csv_files) >= 2  # at least timing and summary


# ---------- Edge cases ----------


class TestExporterEdgeCases:
    def test_export_creates_parent_directories(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        deep_path = tmp_path / "a" / "b" / "c" / "metrics.json"
        result = exporter.export_to_json(deep_path)

        assert result is True
        assert deep_path.exists()

    def test_export_json_returns_false_on_write_failure(self, populated_collector):
        exporter = MetricsExporter(populated_collector)
        # Use an invalid path that should cause a write failure
        result = exporter.export_to_json("/nonexistent_root_dir/metrics.json")
        assert result is False

    def test_export_csv_returns_false_on_write_failure(self, populated_collector):
        exporter = MetricsExporter(populated_collector)
        result = exporter.export_to_csv("/nonexistent_root_dir/csv/")
        assert result is False
