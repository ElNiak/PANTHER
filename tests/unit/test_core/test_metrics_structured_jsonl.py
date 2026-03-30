"""Tests for metrics writing to structured.jsonl."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from panther.core.metrics.enums import MetricType, Phase
from panther.core.metrics.metric_types import Metric
from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.reporting.log_query_engine import LogFilter, LogQueryEngine
from panther.core.utils.jsonl_writer import JsonlWriter
from panther.core.utils.log_context import log_context


@pytest.fixture
def tmp_experiment(tmp_path):
    """Create a temporary experiment directory with structured.jsonl."""
    structured = tmp_path / "structured.jsonl"
    return tmp_path, structured


class TestMetricsToStructuredJsonl:
    """Tests for MetricsCollector writing to structured.jsonl."""

    def test_metric_written_to_jsonl(self, tmp_experiment):
        """Recorded metrics appear as JSONL lines."""
        exp_dir, structured = tmp_experiment
        writer = JsonlWriter(structured)
        collector = MetricsCollector("test_exp", exp_dir, jsonl_writer=writer)
        collector.record_metric("test_duration", MetricType.TIMING, 1.23)
        collector.stop_collection_thread()

        lines = [
            json.loads(l) for l in structured.read_text().splitlines() if l.strip()
        ]
        metric_lines = [l for l in lines if l.get("source") == "metrics"]
        assert len(metric_lines) >= 1
        found = [m for m in metric_lines if m["metric_name"] == "test_duration"]
        assert len(found) == 1
        assert found[0]["metric_value"] == 1.23
        assert found[0]["metric_type"] == "timing"
        assert found[0]["level"] == "METRIC"
        assert found[0]["level_num"] == 15

    def test_context_inherited(self, tmp_experiment):
        """Metrics pick up experiment_id/test_id from LogContext."""
        exp_dir, structured = tmp_experiment
        writer = JsonlWriter(structured)
        collector = MetricsCollector("test_exp", exp_dir, jsonl_writer=writer)
        with log_context(experiment_id="exp-1", test_id="test-1"):
            collector.record_metric("latency", MetricType.GAUGE, 42.0)
        collector.stop_collection_thread()

        lines = [
            json.loads(l) for l in structured.read_text().splitlines() if l.strip()
        ]
        metric_lines = [l for l in lines if l.get("metric_name") == "latency"]
        assert len(metric_lines) == 1
        assert metric_lines[0]["experiment_id"] == "exp-1"
        assert metric_lines[0]["test_id"] == "test-1"

    def test_no_jsonl_without_writer(self, tmp_experiment):
        """No file written when jsonl_writer is None."""
        exp_dir, structured = tmp_experiment
        collector = MetricsCollector("test_exp", exp_dir)
        collector.record_metric("count", MetricType.COUNTER, 1)
        collector.stop_collection_thread()
        assert not structured.exists()

    def test_phase_from_metric(self, tmp_experiment):
        """Phase field uses metric's phase when set."""
        exp_dir, structured = tmp_experiment
        writer = JsonlWriter(structured)
        collector = MetricsCollector("test_exp", exp_dir, jsonl_writer=writer)
        collector.record_metric(
            "setup_time", MetricType.TIMING, 2.0, phase=Phase.TEST_EXECUTION
        )
        collector.stop_collection_thread()

        lines = [
            json.loads(l) for l in structured.read_text().splitlines() if l.strip()
        ]
        metric_lines = [l for l in lines if l.get("metric_name") == "setup_time"]
        assert metric_lines[0]["phase"] == "test_execution"

    def test_jsonl_write_error_warns_once(self, tmp_path):
        """Circuit-breaker: first JSONL write failure logs warning, second is silent."""
        import time

        # Create collector without writer first (so __init__ metric doesn't trigger)
        collector = MetricsCollector("test-exp", str(tmp_path))

        # Now point to an unwritable path (path is a directory, not a file)
        bad_path = tmp_path / "bad_structured.jsonl"
        bad_path.mkdir(parents=True, exist_ok=True)
        writer = JsonlWriter(bad_path)
        collector._jsonl_writer = writer

        metric1 = Metric(
            name="test", metric_type=MetricType.COUNTER, value=1, timestamp=time.time()
        )
        metric2 = Metric(
            name="test2", metric_type=MetricType.COUNTER, value=2, timestamp=time.time()
        )

        with patch.object(collector.logger, "warning") as mock_warn:
            collector._write_metric_jsonl(metric1)
            first_count = mock_warn.call_count
            assert first_count >= 1, "First failure should log a warning"

            collector._write_metric_jsonl(metric2)
            assert (
                mock_warn.call_count == first_count
            ), "Second failure should be suppressed"

        assert collector._jsonl_write_warned is True


class TestMetricQueryFilters:
    """Tests for metric_names and metric_types filters in LogQueryEngine."""

    @pytest.fixture
    def engine_with_metrics(self, tmp_path):
        """Create an engine with mixed log and metric records."""
        structured = tmp_path / "structured.jsonl"
        records = [
            {
                "ts": "2026-01-01T00:00:01+00:00",
                "level": "INFO",
                "source": "logging",
                "message": "hello",
            },
            {
                "ts": "2026-01-01T00:00:02+00:00",
                "level": "METRIC",
                "source": "metrics",
                "metric_name": "duration",
                "metric_type": "timing",
                "metric_value": 1.5,
            },
            {
                "ts": "2026-01-01T00:00:03+00:00",
                "level": "METRIC",
                "source": "metrics",
                "metric_name": "count",
                "metric_type": "counter",
                "metric_value": 42,
            },
            {
                "ts": "2026-01-01T00:00:04+00:00",
                "level": "METRIC",
                "source": "metrics",
                "metric_name": "cpu",
                "metric_type": "gauge",
                "metric_value": 55.3,
            },
        ]
        structured.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        return LogQueryEngine(tmp_path)

    def test_filter_by_source_metrics(self, engine_with_metrics):
        results = list(engine_with_metrics.query(LogFilter(sources={"metrics"})))
        assert len(results) == 3

    def test_filter_by_metric_name(self, engine_with_metrics):
        results = list(
            engine_with_metrics.query(
                LogFilter(sources={"metrics"}, metric_names={"duration"})
            )
        )
        assert len(results) == 1
        assert results[0]["metric_name"] == "duration"

    def test_filter_by_metric_type(self, engine_with_metrics):
        results = list(engine_with_metrics.query(LogFilter(metric_types={"counter"})))
        assert len(results) == 1
        assert results[0]["metric_name"] == "count"

    def test_combined_metric_filters(self, engine_with_metrics):
        results = list(
            engine_with_metrics.query(
                LogFilter(
                    sources={"metrics"},
                    metric_types={"gauge", "timing"},
                )
            )
        )
        assert len(results) == 2
        names = {r["metric_name"] for r in results}
        assert names == {"duration", "cpu"}
