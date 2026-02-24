"""Full metrics pipeline integration test.

Tests the complete data flow: record -> collect -> finalize -> export -> load,
with assertions on actual metric values at each stage.
"""

import pytest

from panther.core.metrics.data_loader import MetricsDataLoader
from panther.core.metrics.enums import MetricType, Phase
from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.metrics.metrics_exporter import MetricsExporter

pytestmark = [pytest.mark.unit]


@pytest.fixture
def pipeline_collector(tmp_path):
    """Create a collector with precisely known metric values for pipeline testing."""
    c = MetricsCollector(
        experiment_name="pipeline_integration",
        output_dir=tmp_path / "experiment",
        collection_interval=60.0,  # Long interval to avoid background collection
    )

    # --- Record exact, verifiable values ---

    # Timing metrics (2 phases, known durations)
    c.record_metric(
        "setup_docker", MetricType.TIMING, 5.25, phase=Phase.ENVIRONMENT_SETUP
    )
    c.record_metric(
        "run_scenario_a", MetricType.TIMING, 10.0, phase=Phase.TEST_EXECUTION
    )
    c.record_metric(
        "run_scenario_b", MetricType.TIMING, 7.5, phase=Phase.TEST_EXECUTION
    )
    c.record_metric(
        "teardown_env", MetricType.TIMING, 2.0, phase=Phase.ENVIRONMENT_TEARDOWN
    )

    # Counters with known totals
    c.increment_counter("experiments_total", phase=Phase.TEST_EXECUTION)
    c.increment_counter("experiments_successful", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_total", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_total", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_total", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_successful", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_successful", phase=Phase.TEST_EXECUTION)
    c.increment_counter("test_cases_failed", phase=Phase.TEST_EXECUTION)
    c.increment_counter("artifacts_total", phase=Phase.TEST_EXECUTION)
    c.increment_counter("logs_generated", phase=Phase.TEST_EXECUTION)

    # Gauges
    c.record_gauge("total_artifact_size_mb", 15.7)

    # Resource metrics (simulated samples)
    c.record_metric("cpu_percent", MetricType.GAUGE, 30.0, component="resource_monitor")
    c.record_metric("cpu_percent", MetricType.GAUGE, 60.0, component="resource_monitor")
    c.record_metric("cpu_percent", MetricType.GAUGE, 45.0, component="resource_monitor")
    c.record_metric(
        "memory_percent", MetricType.GAUGE, 50.0, component="resource_monitor"
    )
    c.record_metric(
        "memory_percent", MetricType.GAUGE, 70.0, component="resource_monitor"
    )

    # Errors (2 distinct errors)
    c.record_error(
        "timeout",
        error_message="Connection timed out after 30s",
        phase=Phase.TEST_EXECUTION,
        test_case="scenario_b",
        component="client",
    )
    c.record_error(
        "assertion_failure",
        error_message="Expected QUIC handshake complete",
        phase=Phase.ASSERTION_VALIDATION,
        test_case="scenario_b",
        component="tester",
    )

    return c


class TestFullPipelineRoundtrip:
    """End-to-end: collector -> finalize -> export -> load -> verify values."""

    def _export_and_load(self, tmp_path, collector):
        """Helper: finalize, export JSON, load back via DataLoader."""
        collector.finalize()

        exporter = MetricsExporter(collector)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        json_path = metrics_dir / "metrics.json"
        assert exporter.export_to_json(json_path) is True

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, _exp_path = loader.load_metrics(experiment_dir=tmp_path / "experiment")
        assert data is not None
        return data, loader

    def test_summary_counters_match_recorded_values(self, tmp_path, pipeline_collector):
        data, _ = self._export_and_load(tmp_path, pipeline_collector)
        summary = data["summary"]

        assert summary["total_experiments"] == 1
        assert summary["successful_experiments"] == 1
        assert summary["failed_experiments"] == 0
        assert summary["total_test_cases"] == 3
        assert summary["successful_test_cases"] == 2
        assert summary["failed_test_cases"] == 1
        assert summary["error_count"] == 2

    def test_timing_metrics_values_match(self, tmp_path, pipeline_collector):
        data, _ = self._export_and_load(tmp_path, pipeline_collector)
        timing = data["timing_metrics"]

        assert timing["setup_docker"] == pytest.approx(5.25)
        assert timing["run_scenario_a"] == pytest.approx(10.0)
        assert timing["run_scenario_b"] == pytest.approx(7.5)
        assert timing["teardown_env"] == pytest.approx(2.0)
        # finalize() adds total_execution_time
        assert "total_execution_time" in timing
        assert timing["total_execution_time"] > 0

    def test_phase_metrics_aggregate_correctly(self, tmp_path, pipeline_collector):
        data, _ = self._export_and_load(tmp_path, pipeline_collector)
        phases = data["phase_metrics"]

        setup = phases[Phase.ENVIRONMENT_SETUP.value]
        assert setup["total_time"] == pytest.approx(5.25)
        assert setup["count"] == 1

        execution = phases[Phase.TEST_EXECUTION.value]
        assert execution["total_time"] == pytest.approx(17.5)  # 10.0 + 7.5
        assert execution["count"] == 2

        teardown = phases[Phase.ENVIRONMENT_TEARDOWN.value]
        assert teardown["total_time"] == pytest.approx(2.0)
        assert teardown["count"] == 1

    def test_error_metrics_match_recorded_errors(self, tmp_path, pipeline_collector):
        data, _ = self._export_and_load(tmp_path, pipeline_collector)
        errors = data["error_metrics"]

        assert errors["total_errors"] == 2
        assert "timeout" in errors["error_categories"]
        assert "assertion_failure" in errors["error_categories"]
        assert len(errors["error_timeline"]) == 2

    def test_error_timeline_has_correct_fields(self, tmp_path, pipeline_collector):
        data, _ = self._export_and_load(tmp_path, pipeline_collector)
        timeline = data["error_metrics"]["error_timeline"]

        for entry in timeline:
            assert "timestamp" in entry
            assert "error_type" in entry
            assert "error_message" in entry
            assert "component" in entry

        error_types = {e["error_type"] for e in timeline}
        assert error_types == {"timeout", "assertion_failure"}

    def test_resource_metrics_reflect_recorded_samples(
        self, tmp_path, pipeline_collector
    ):
        data, _ = self._export_and_load(tmp_path, pipeline_collector)
        resource = data["resource_metrics"]

        # cpu_percent: values 30, 60, 45 -> avg=45, peak=60, min=30
        cpu = resource["cpu_usage"]
        assert cpu["average"] == pytest.approx(45.0)
        assert cpu["peak"] == pytest.approx(60.0)
        assert cpu["min"] == pytest.approx(30.0)

        # memory_percent: values 50, 70 -> avg=60, peak=70, min=50
        mem = resource["memory_usage"]
        assert mem["average"] == pytest.approx(60.0)
        assert mem["peak"] == pytest.approx(70.0)
        assert mem["min"] == pytest.approx(50.0)

    def test_artifact_metrics_match(self, tmp_path, pipeline_collector):
        data, _ = self._export_and_load(tmp_path, pipeline_collector)
        artifacts = data["artifact_metrics"]

        assert artifacts["total_artifacts"] == 1
        assert artifacts["logs_generated"] == 1
        assert artifacts["total_artifact_size_mb"] == pytest.approx(15.7)

    def test_raw_metrics_include_counters_and_gauges(
        self, tmp_path, pipeline_collector
    ):
        data, _ = self._export_and_load(tmp_path, pipeline_collector)
        raw = data.get("raw_metrics", {})

        counters = raw.get("counters", {})
        assert counters.get("experiments_total") == 1
        assert counters.get("test_cases_total") == 3
        assert counters.get("test_cases_failed") == 1

        gauges = raw.get("gauges", {})
        assert gauges.get("total_artifact_size_mb") == pytest.approx(15.7)

    def test_data_loader_summary_reflects_exported_data(
        self, tmp_path, pipeline_collector
    ):
        data, loader = self._export_and_load(tmp_path, pipeline_collector)
        summary = loader.get_summary(data)

        assert summary["total_experiments"] == 1
        assert summary["error_count"] == 2
        assert summary["total_errors"] == 2
        assert "export_timestamp" in summary

    def test_data_loader_available_metrics_lists_all_categories(
        self, tmp_path, pipeline_collector
    ):
        data, loader = self._export_and_load(tmp_path, pipeline_collector)
        available = loader.get_available_metrics(data)

        categories = {m["category"] for m in available}
        assert "timing" in categories
        assert "error" in categories

    def test_data_loader_get_metric_values_returns_timing(
        self, tmp_path, pipeline_collector
    ):
        data, loader = self._export_and_load(tmp_path, pipeline_collector)
        values = loader.get_metric_values(data, "setup_docker")

        assert len(values) >= 1
        assert values[0]["value"] == pytest.approx(5.25)
        assert values[0]["type"] == "timing"


class TestPipelineWithEmptyCollector:
    """Verify pipeline handles empty/minimal data without errors."""

    def test_empty_collector_roundtrip(self, tmp_path):
        c = MetricsCollector(
            experiment_name="empty_pipeline",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        c.finalize()

        exporter = MetricsExporter(c)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        json_path = metrics_dir / "metrics.json"
        assert exporter.export_to_json(json_path) is True

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, _ = loader.load_metrics(experiment_dir=tmp_path / "experiment")
        assert data is not None

        # Summary should have zero counts
        summary = data["summary"]
        assert summary["total_experiments"] == 0
        assert summary["error_count"] == 0

    def test_errors_only_collector_roundtrip(self, tmp_path):
        c = MetricsCollector(
            experiment_name="errors_only",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        c.record_error("crash", error_message="Segfault in client")
        c.record_error("crash", error_message="Segfault in server")
        c.finalize()

        exporter = MetricsExporter(c)
        metrics_dir = tmp_path / "experiment" / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)
        json_path = metrics_dir / "metrics.json"
        assert exporter.export_to_json(json_path) is True

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, _ = loader.load_metrics(experiment_dir=tmp_path / "experiment")
        assert data is not None
        assert data["error_metrics"]["total_errors"] == 2


class TestFinalizationBehavior:
    """Verify finalization effects on the pipeline."""

    def test_finalize_is_idempotent(self, tmp_path):
        c = MetricsCollector(
            experiment_name="idempotent_test",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        c.record_metric("test_op", MetricType.TIMING, 1.0, phase=Phase.TEST_EXECUTION)

        c.finalize()
        metrics_after_first = len(c.metrics)

        c.finalize()
        metrics_after_second = len(c.metrics)

        # Second finalize should not add new metrics
        assert metrics_after_first == metrics_after_second

    def test_finalize_adds_total_execution_time(self, tmp_path):
        c = MetricsCollector(
            experiment_name="finalize_timing",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        c.finalize()

        timing = c.timing_metrics
        assert "total_execution_time" in timing
        assert timing["total_execution_time"] > 0

    def test_finalize_stops_active_timers(self, tmp_path):
        c = MetricsCollector(
            experiment_name="timer_cleanup",
            output_dir=tmp_path / "experiment",
            collection_interval=60.0,
        )
        c.start_timer("orphan_timer", phase=Phase.TEST_EXECUTION)

        c.finalize()

        # Timer should have been force-stopped
        assert len(c.active_timers) == 0
        # Duration metric should have been recorded
        timing = c.timing_metrics
        assert "orphan_timer_duration" in timing
