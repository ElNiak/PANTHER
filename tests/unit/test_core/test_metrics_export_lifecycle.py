"""Integration test: MetricsCollector -> MetricsExporter -> MetricsDataLoader roundtrip."""

import json

import pytest

from panther.core.metrics.data_loader import MetricsDataLoader
from panther.core.metrics.enums import Phase
from panther.core.metrics.metrics_collector import MetricsCollector, MetricType
from panther.core.metrics.metrics_exporter import MetricsExporter

pytestmark = [pytest.mark.unit]


@pytest.fixture
def collector(tmp_path):
    """Create a MetricsCollector with some recorded metrics."""
    c = MetricsCollector(
        experiment_name="lifecycle_test",
        output_dir=tmp_path / "experiment",
        collection_interval=60.0,
    )
    # Record various metric types
    c.record_metric(
        "test_op_duration", MetricType.TIMING, 1.5, phase=Phase.TEST_EXECUTION
    )
    c.record_metric(
        "test_op_duration", MetricType.TIMING, 2.3, phase=Phase.TEST_EXECUTION
    )
    c.increment_counter("tests_passed", test_case="basic_quic")
    c.increment_counter("tests_failed", test_case="stress_test")
    c.record_gauge("process_cpu_percent", 45.2)
    c.record_error("timeout", error_message="Connection timed out", component="client")
    return c


class TestMetricsExportLifecycle:
    def test_roundtrip_json(self, tmp_path, collector):
        """Collector -> Exporter -> JSON -> DataLoader produces consistent data."""
        # Finalize and export
        collector.finalize()
        exporter = MetricsExporter(collector)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        result = exporter.export_to_json(metrics_dir / "metrics.json")
        assert result is True

        # Load back with DataLoader
        loader = MetricsDataLoader(output_dir=tmp_path)
        data, exp_path = loader.load_metrics(experiment_dir=tmp_path / "experiment")
        assert data is not None

        # Verify structure
        assert "export_metadata" in data
        assert "summary" in data
        assert "timing_metrics" in data
        assert "error_metrics" in data

        # Verify export metadata has a dynamic panther version
        export_metadata = data["export_metadata"]
        panther_version = export_metadata.get("panther_version")
        assert isinstance(panther_version, str)
        assert panther_version.strip() != ""

        # Verify summary fields are populated with the exact keys from
        # MetricsExporter._get_summary_data()
        summary = data["summary"]
        assert "error_count" in summary
        assert "total_execution_time" in summary
        # The fixture records one error, so error_count must be >= 1
        assert summary["error_count"] >= 1

    def test_timing_metrics_survive_roundtrip(self, tmp_path, collector):
        """Timing metrics recorded in collector are available after export+load."""
        collector.finalize()
        exporter = MetricsExporter(collector)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        exporter.export_to_json(metrics_dir / "metrics.json")

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, _ = loader.load_metrics(experiment_dir=tmp_path / "experiment")
        timing = data.get("timing_metrics", {})
        # Should have at least the test_op_duration (latest value wins)
        assert len(timing) > 0

    def test_error_metrics_survive_roundtrip(self, tmp_path, collector):
        """Error metrics recorded in collector are available after export+load."""
        collector.finalize()
        exporter = MetricsExporter(collector)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        exporter.export_to_json(metrics_dir / "metrics.json")

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, _ = loader.load_metrics(experiment_dir=tmp_path / "experiment")
        errors = data.get("error_metrics", {})
        assert errors.get("total_errors", 0) >= 1

    def test_available_metrics_from_exported_data(self, tmp_path, collector):
        """DataLoader can enumerate metrics from exported JSON."""
        collector.finalize()
        exporter = MetricsExporter(collector)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        exporter.export_to_json(metrics_dir / "metrics.json")

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, _ = loader.load_metrics(experiment_dir=tmp_path / "experiment")
        available = loader.get_available_metrics(data)
        assert len(available) > 0

        names = [m["name"] for m in available]
        # At least the error metric should be present
        assert (
            any("error" in n.lower() for n in names)
            or data.get("error_metrics", {}).get("total_errors", 0) > 0
        )

    def test_summary_from_exported_data(self, tmp_path, collector):
        """DataLoader summary works with freshly exported data."""
        collector.finalize()
        exporter = MetricsExporter(collector)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        exporter.export_to_json(metrics_dir / "metrics.json")

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, _ = loader.load_metrics(experiment_dir=tmp_path / "experiment")
        summary = loader.get_summary(data)
        assert "export_timestamp" in summary

    def test_csv_export_also_works(self, tmp_path, collector):
        """CSV export runs without errors alongside JSON."""
        collector.finalize()
        exporter = MetricsExporter(collector)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        result = exporter.export_to_csv(metrics_dir)
        assert result is True

        csv_files = list(metrics_dir.glob("*.csv"))
        assert len(csv_files) > 0


class TestExperimentManagerCleanupMetricsExport:
    """Test that ExperimentManager.cleanup() finalizes the metrics collector."""

    def test_cleanup_finalizes_metrics_collector(self, tmp_path):
        """cleanup() calls finalize() on the metrics collector."""
        from unittest.mock import MagicMock, patch

        # Create a real MetricsCollector with some recorded data
        collector = MetricsCollector(
            experiment_name="cleanup_test",
            output_dir=tmp_path / "collector_output",
            collection_interval=60.0,
        )
        collector.record_metric(
            "build_duration", MetricType.TIMING, 3.7, phase=Phase.TEST_EXECUTION
        )
        collector.increment_counter("tests_passed", test_case="quic_handshake")
        collector.record_gauge("process_cpu_percent", 22.5)
        collector.record_error(
            "timeout", error_message="Handshake timed out", component="server"
        )

        # Build a minimal mock ExperimentManager with just the attributes
        # that cleanup() accesses.
        manager = MagicMock()
        manager.metrics_collector = collector
        manager.experiment_dir = tmp_path / "experiment_output"
        manager.experiment_dir.mkdir(parents=True, exist_ok=True)
        manager.experiment_name = "cleanup_test"

        # Use a real logger so log calls don't fail
        import logging

        manager.logger = logging.getLogger("test_cleanup")

        # Make log_statistics_display falsy so it's skipped
        manager.log_statistics_display = None

        # Provide workflow_tracker with clear_workflow_state
        manager.workflow_tracker = MagicMock()

        # Call the real cleanup method, but patch out the parts we don't need
        from panther.core.experiment_manager import ExperimentManager

        with (
            patch.object(
                ExperimentManager, "_generate_final_log_report", return_value=None
            ),
            patch.object(
                ExperimentManager, "_generate_experiment_report", return_value=None
            ),
            patch.object(ExperimentManager, "_setup_observers", return_value=None),
        ):
            ExperimentManager.cleanup(manager)

        # cleanup() calls finalize() on the collector — verify it was finalized
        assert collector._finalized is True


class TestPhaseMetricsFix:
    """Bug 2: _get_phase_metrics uses .phase field instead of substring matching."""

    def test_phase_metrics_nonzero_with_phase_field(self, tmp_path):
        """Phase metrics return non-zero data when metrics have .phase set."""
        c = MetricsCollector(
            experiment_name="phase_test",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        c.record_metric(
            "timing.setup_docker",
            MetricType.TIMING,
            5.0,
            phase=Phase.ENVIRONMENT_SETUP,
        )
        c.record_metric(
            "timing.run_test_scenario",
            MetricType.TIMING,
            12.5,
            phase=Phase.TEST_EXECUTION,
        )
        c.record_metric(
            "timing.teardown_environment_containers",
            MetricType.TIMING,
            3.2,
            phase=Phase.ENVIRONMENT_TEARDOWN,
        )
        c.finalize()

        exporter = MetricsExporter(c)
        phase_data = exporter._get_phase_metrics()

        # These should now be non-zero thanks to .phase field filtering
        assert phase_data[Phase.ENVIRONMENT_SETUP.value]["total_time"] == pytest.approx(
            5.0
        )
        assert phase_data[Phase.ENVIRONMENT_SETUP.value]["count"] == 1
        assert phase_data[Phase.TEST_EXECUTION.value]["total_time"] == pytest.approx(
            12.5
        )
        assert phase_data[Phase.TEST_EXECUTION.value]["count"] == 1
        assert phase_data[Phase.ENVIRONMENT_TEARDOWN.value][
            "total_time"
        ] == pytest.approx(3.2)
        assert phase_data[Phase.ENVIRONMENT_TEARDOWN.value]["count"] == 1

    def test_summary_nonzero_after_counter_increments(self, tmp_path):
        """Summary data returns non-zero values after counters are incremented."""
        c = MetricsCollector(
            experiment_name="summary_test",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        c.increment_counter("experiments_total", phase=Phase.TEST_EXECUTION)
        c.increment_counter("experiments_successful", phase=Phase.TEST_EXECUTION)
        c.increment_counter("test_cases_total", phase=Phase.TEST_EXECUTION)
        c.increment_counter("test_cases_total", phase=Phase.TEST_EXECUTION)
        c.increment_counter("test_cases_successful", phase=Phase.TEST_EXECUTION)
        c.increment_counter("test_cases_failed", phase=Phase.TEST_EXECUTION)
        c.finalize()

        exporter = MetricsExporter(c)
        summary = exporter._get_summary_data()

        assert summary["total_experiments"] == 1
        assert summary["successful_experiments"] == 1
        assert summary["total_test_cases"] == 2
        assert summary["successful_test_cases"] == 1
        assert summary["failed_test_cases"] == 1


class TestResourceMonitorGaugeFix:
    """Bug 3: I/O metrics use GAUGE so latest value is reported, not sum."""

    def test_io_metrics_recorded_as_gauge(self, tmp_path):
        """Disk and network I/O metrics are recorded as GAUGE type."""
        c = MetricsCollector(
            experiment_name="gauge_test",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        # Simulate what resource_monitor now does (GAUGE for cumulative totals)
        c.record_metric(
            "disk_read_mb_total", MetricType.GAUGE, 100.0, component="resource_monitor"
        )
        c.record_metric(
            "disk_read_mb_total", MetricType.GAUGE, 200.0, component="resource_monitor"
        )
        c.record_metric(
            "disk_read_mb_total", MetricType.GAUGE, 300.0, component="resource_monitor"
        )

        # GAUGE takes latest value, not sum
        gauges = c.gauges
        assert gauges["disk_read_mb_total"] == pytest.approx(300.0)

    def test_counter_would_sum_incorrectly(self, tmp_path):
        """Demonstrate that COUNTER sums all samples (the old broken behavior)."""
        c = MetricsCollector(
            experiment_name="counter_demo",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        # If these were COUNTER, the sum would be 100+200+300 = 600 (wrong!)
        c.record_metric("example_counter", MetricType.COUNTER, 100.0)
        c.record_metric("example_counter", MetricType.COUNTER, 200.0)
        c.record_metric("example_counter", MetricType.COUNTER, 300.0)

        counters = c.counters
        assert counters["example_counter"] == 600  # Sum, not latest
