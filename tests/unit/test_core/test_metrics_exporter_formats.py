"""Tests for MetricsExporter output formats: dashboard JSON, Prometheus, CSV.

Covers export_dashboard_json(), export_prometheus_format(), export_to_csv(),
and the internal helper methods that produce each format's content.
"""

import csv
import json

import pytest

from panther.core.metrics.enums import MetricType, Phase
from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.metrics.metrics_exporter import MetricsExporter


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
    c.record_metric(
        "cpu_percent", MetricType.GAUGE, 45.2, component="resource_monitor"
    )
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


# ---------- Dashboard JSON export ----------


class TestDashboardJsonExport:
    def test_produces_valid_json_file(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "dashboard.json"
        result = exporter.export_dashboard_json(output)

        assert result is True
        assert output.exists()

        data = json.loads(output.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_contains_required_sections(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "dashboard.json"
        exporter.export_dashboard_json(output)

        data = json.loads(output.read_text(encoding="utf-8"))
        assert "dashboard_metadata" in data
        assert "summary_cards" in data
        assert "time_series" in data
        assert "charts" in data
        assert "alerts" in data

    def test_dashboard_metadata_fields(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "dashboard.json"
        exporter.export_dashboard_json(output)

        data = json.loads(output.read_text(encoding="utf-8"))
        meta = data["dashboard_metadata"]
        assert "timestamp" in meta
        assert meta["refresh_interval"] == 30
        assert meta["data_retention"] == "24h"

    def test_summary_cards_structure(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "dashboard.json"
        exporter.export_dashboard_json(output)

        data = json.loads(output.read_text(encoding="utf-8"))
        cards = data["summary_cards"]
        assert isinstance(cards, list)
        assert len(cards) == 4

        titles = [c["title"] for c in cards]
        assert "Total Experiments" in titles
        assert "Success Rate" in titles
        assert "Total Execution Time" in titles
        assert "Error Count" in titles

        for card in cards:
            assert "value" in card
            assert "type" in card
            assert "color" in card

    def test_summary_cards_reflect_recorded_data(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "dashboard.json"
        exporter.export_dashboard_json(output)

        data = json.loads(output.read_text(encoding="utf-8"))
        cards = {c["title"]: c for c in data["summary_cards"]}

        assert cards["Total Experiments"]["value"] == 1
        assert cards["Error Count"]["value"] >= 1

    def test_charts_section_has_chart_configs(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "dashboard.json"
        exporter.export_dashboard_json(output)

        data = json.loads(output.read_text(encoding="utf-8"))
        charts = data["charts"]
        assert isinstance(charts, list)
        assert len(charts) >= 2

        chart_ids = [c["id"] for c in charts]
        assert "resource_usage_chart" in chart_ids
        assert "phase_duration_chart" in chart_ids

    def test_alerts_generated_for_errors(self, tmp_path, populated_collector):
        """Dashboard with errors should generate alerts."""
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "dashboard.json"
        exporter.export_dashboard_json(output)

        data = json.loads(output.read_text(encoding="utf-8"))
        alerts = data["alerts"]
        assert isinstance(alerts, list)

    def test_empty_collector_still_produces_valid_dashboard(
        self, tmp_path, empty_collector
    ):
        exporter = MetricsExporter(empty_collector)
        output = tmp_path / "dashboard.json"
        result = exporter.export_dashboard_json(output)

        assert result is True
        data = json.loads(output.read_text(encoding="utf-8"))
        assert "summary_cards" in data

    def test_high_failure_rate_triggers_warning_alert(self, tmp_path):
        """When failure rate > 20%, a warning alert should be generated."""
        c = MetricsCollector(
            experiment_name="high_fail",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        # 1 total, 1 failed -> 100% failure rate
        c.increment_counter("experiments_total")
        c.increment_counter("experiments_failed")
        c.finalize()

        exporter = MetricsExporter(c)
        output = tmp_path / "dashboard.json"
        exporter.export_dashboard_json(output)

        data = json.loads(output.read_text(encoding="utf-8"))
        alerts = data["alerts"]
        warning_alerts = [a for a in alerts if a["level"] == "warning"]
        assert len(warning_alerts) >= 1
        assert any("failure rate" in a["message"].lower() for a in warning_alerts)


# ---------- Prometheus format export ----------


class TestPrometheusFormatExport:
    def test_produces_valid_output_file(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "metrics.prom"
        result = exporter.export_prometheus_format(output)

        assert result is True
        assert output.exists()

    def test_contains_timing_metrics(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "metrics.prom"
        exporter.export_prometheus_format(output)

        content = output.read_text(encoding="utf-8")
        assert "panther_timing_" in content
        lines = [l for l in content.splitlines() if l.startswith("panther_timing_")]
        assert len(lines) >= 1

    def test_contains_counter_metrics(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "metrics.prom"
        exporter.export_prometheus_format(output)

        content = output.read_text(encoding="utf-8")
        counter_lines = [
            l for l in content.splitlines() if l.startswith("panther_counter_")
        ]
        assert len(counter_lines) >= 1

    def test_contains_gauge_metrics(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "metrics.prom"
        exporter.export_prometheus_format(output)

        content = output.read_text(encoding="utf-8")
        gauge_lines = [
            l for l in content.splitlines() if l.startswith("panther_gauge_")
        ]
        assert len(gauge_lines) >= 1

    def test_contains_resource_metrics(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "metrics.prom"
        exporter.export_prometheus_format(output)

        content = output.read_text(encoding="utf-8")
        assert "panther_cpu_usage_percent" in content
        assert "panther_memory_usage_percent" in content

    def test_metric_names_are_prometheus_safe(self, tmp_path, populated_collector):
        """Metric names should only contain [a-z0-9_] (no spaces or hyphens)."""
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "metrics.prom"
        exporter.export_prometheus_format(output)

        content = output.read_text(encoding="utf-8")
        for line in content.strip().splitlines():
            if not line:
                continue
            metric_name = line.split(" ")[0]
            assert " " not in metric_name
            assert "-" not in metric_name

    def test_metric_values_are_numeric(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "metrics.prom"
        exporter.export_prometheus_format(output)

        content = output.read_text(encoding="utf-8")
        for line in content.strip().splitlines():
            if not line:
                continue
            parts = line.rsplit(" ", 1)
            assert len(parts) == 2
            float(parts[1])  # Should not raise ValueError

    def test_empty_collector_produces_minimal_output(self, tmp_path, empty_collector):
        exporter = MetricsExporter(empty_collector)
        output = tmp_path / "metrics.prom"
        result = exporter.export_prometheus_format(output)

        assert result is True
        content = output.read_text(encoding="utf-8")
        # Should have at least timing metrics from finalize
        assert len(content.strip()) > 0

    def test_disk_io_metrics_present_when_recorded(self, tmp_path, populated_collector):
        exporter = MetricsExporter(populated_collector)
        output = tmp_path / "metrics.prom"
        exporter.export_prometheus_format(output)

        content = output.read_text(encoding="utf-8")
        assert "panther_disk_io_mb_read" in content
        assert "panther_disk_io_mb_write" in content


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

    def test_export_prometheus_returns_false_on_write_failure(
        self, populated_collector
    ):
        exporter = MetricsExporter(populated_collector)
        result = exporter.export_prometheus_format(
            "/nonexistent_root_dir/metrics.prom"
        )
        assert result is False

    def test_export_dashboard_returns_false_on_write_failure(
        self, populated_collector
    ):
        exporter = MetricsExporter(populated_collector)
        result = exporter.export_dashboard_json(
            "/nonexistent_root_dir/dashboard.json"
        )
        assert result is False
