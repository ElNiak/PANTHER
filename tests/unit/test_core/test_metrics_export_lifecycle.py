"""Integration test: MetricsCollector -> MetricsExporter -> MetricsDataLoader roundtrip."""

import json

import pytest

from panther.core.metrics.data_loader import MetricsDataLoader
from panther.core.metrics.metrics_collector import MetricsCollector, MetricType
from panther.core.metrics.enums import Phase
from panther.core.metrics.metrics_exporter import MetricsExporter


@pytest.fixture
def collector(tmp_path):
    """Create a MetricsCollector with some recorded metrics."""
    c = MetricsCollector(
        experiment_name="lifecycle_test",
        output_dir=tmp_path / "experiment",
        collection_interval=60.0,
    )
    # Record various metric types
    c.record_metric("test_op_duration", MetricType.TIMING, 1.5, phase=Phase.TEST_EXECUTION)
    c.record_metric("test_op_duration", MetricType.TIMING, 2.3, phase=Phase.TEST_EXECUTION)
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
        assert any("error" in n.lower() for n in names) or data.get("error_metrics", {}).get("total_errors", 0) > 0

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
    """Test that ExperimentManager.cleanup() exports metrics to disk."""

    def test_cleanup_exports_metrics_json(self, tmp_path):
        """cleanup() with a real MetricsCollector writes metrics/metrics.json to experiment_dir."""
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

        with patch.object(
            ExperimentManager, "_generate_final_log_report", return_value=None
        ), patch.object(
            ExperimentManager, "_generate_experiment_report", return_value=None
        ), patch.object(
            ExperimentManager, "_setup_observers", return_value=None
        ):
            # Call the real cleanup code by invoking the unbound method on
            # our mock, binding it manually.
            ExperimentManager.cleanup(manager)

        # Assert that metrics.json was written to experiment_dir/metrics/
        metrics_json = manager.experiment_dir / "metrics" / "metrics.json"
        assert metrics_json.exists(), (
            f"Expected {metrics_json} to exist after cleanup()"
        )

        # Verify the file contains valid JSON with expected structure
        data = json.load(open(metrics_json, "r", encoding="utf-8"))
        assert "timing_metrics" in data
        assert "error_metrics" in data
