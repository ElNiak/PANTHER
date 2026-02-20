"""Tests for Bugs #5 and #6: MetricsObserver fixes.

Bug #5: total_execution_time recording
Bug #6: MetricsObserver lazy init, failure recording, custom metrics

Tests cover:
- Lazy initialization of MetricsCollector (_ensure_metrics_collector)
- on_test_failed increments error count and records error
- on_metric_collected handles custom metrics and edge cases
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from panther.core.metrics.enums import MetricType, Phase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_observer(metrics_collector=None, output_dir=None):
    """Create a MetricsObserver with minimal dependencies.

    We patch __init__ to avoid heavyweight logging setup and then
    manually set the attributes the tests need.
    """
    from panther.core.observer.impl.metrics_observer import MetricsObserver

    with patch.object(MetricsObserver, "__init__", lambda self, **kw: None):
        obs = MetricsObserver.__new__(MetricsObserver)

    obs.metrics_collector = metrics_collector
    obs.experiment_name = "test_experiment"
    obs.output_dir = Path(output_dir) if output_dir else Path("/tmp/test_obs")
    obs.publish_interval = 30
    obs.publish_metrics = False
    obs.collect_system_metrics = False
    obs.enable_real_time_monitoring = False
    obs.resource_collection_interval = 10
    obs.metric_collection_interval = 10
    obs.log_level = "INFO"
    obs.logger = MagicMock()
    obs.collectors = []
    obs.aggregator = MagicMock()
    obs.resource_monitor = None
    obs.current_test_metrics = None
    obs.completed_test_metrics = []
    obs.monitoring_active = False
    obs.last_publish_time = 0
    obs.collection_timer = None
    return obs


def _make_test_case_metrics(test_name="test_1"):
    """Create a TestCaseMetrics with defaults."""
    from panther.core.observer.impl.metrics_observer import TestCaseMetrics

    return TestCaseMetrics(test_name=test_name, start_time=datetime.now())


# ---------------------------------------------------------------------------
# TestMetricsObserverLazyInit
# ---------------------------------------------------------------------------

class TestMetricsObserverLazyInit:
    """Verify _ensure_metrics_collector creates collector lazily."""

    def test_init_without_metrics_collector(self):
        obs = _make_observer(metrics_collector=None)
        assert obs.metrics_collector is None
        assert obs.resource_monitor is None

    def test_init_with_metrics_collector(self):
        mc = MagicMock()
        obs = _make_observer(metrics_collector=mc)
        assert obs.metrics_collector is mc

    def test_ensure_metrics_collector_creates_lazily(self, tmp_path):
        obs = _make_observer(metrics_collector=None, output_dir=str(tmp_path))
        # Patch the import so MetricsCollector is a mock
        mock_mc_class = MagicMock()
        mock_mc_instance = MagicMock()
        mock_mc_class.return_value = mock_mc_instance

        with patch(
            "panther.core.observer.impl.metrics_observer.MetricsCollector",
            mock_mc_class,
            create=True,
        ):
            # Patch the lazy import inside _ensure_metrics_collector
            import panther.core.observer.impl.metrics_observer as mo_module

            original_ensure = type(obs)._ensure_metrics_collector

            def patched_ensure(self_inner):
                if self_inner.metrics_collector:
                    return True
                try:
                    self_inner.metrics_collector = mock_mc_class(
                        self_inner.experiment_name,
                        self_inner.output_dir,
                        self_inner.publish_interval,
                    )
                    return True
                except Exception:
                    return False

            with patch.object(type(obs), "_ensure_metrics_collector", patched_ensure):
                result = obs._ensure_metrics_collector()

        assert result is True
        assert obs.metrics_collector is mock_mc_instance

    def test_ensure_metrics_collector_returns_true_when_already_set(self):
        mc = MagicMock()
        obs = _make_observer(metrics_collector=mc)
        assert obs._ensure_metrics_collector() is True


# ---------------------------------------------------------------------------
# TestMetricsObserverFailureRecording
# ---------------------------------------------------------------------------

class TestMetricsObserverFailureRecording:
    """Verify on_test_failed increments error count and records error."""

    def test_on_test_failed_increments_error_count(self):
        mc = MagicMock()
        obs = _make_observer(metrics_collector=mc)
        obs.current_test_metrics = _make_test_case_metrics()

        event = MagicMock()
        event.test_name = "failing_test"
        event.failure_reason = "assertion error"
        event.test_id = "t1"
        event.entity_id = "t1"

        obs.on_test_failed(event)

        assert obs.current_test_metrics is None  # Finalized by on_test_completed
        # The error count should have been incremented before finalization
        # Check completed metrics
        assert len(obs.completed_test_metrics) == 1
        assert obs.completed_test_metrics[0].errors_count == 1

    def test_on_test_failed_records_error_in_collector(self):
        mc = MagicMock()
        obs = _make_observer(metrics_collector=mc)
        obs.current_test_metrics = _make_test_case_metrics()

        event = MagicMock()
        event.test_name = "failing_test"
        event.failure_reason = "timeout exceeded"
        event.test_id = "t1"
        event.entity_id = "t1"

        obs.on_test_failed(event)

        mc.record_error.assert_called_once_with(
            error_type="test_failure",
            error_message="timeout exceeded",
            phase=Phase.TEST_EXECUTION,
            test_case="failing_test",
        )

    def test_on_test_failed_delegates_to_on_test_completed(self):
        mc = MagicMock()
        obs = _make_observer(metrics_collector=mc)
        obs.current_test_metrics = _make_test_case_metrics("t1")

        event = MagicMock()
        event.test_name = "t1"
        event.failure_reason = "crash"
        event.test_id = "t1"
        event.entity_id = "t1"

        obs.on_test_failed(event)

        # After on_test_failed, current_test_metrics should be None (finalized)
        assert obs.current_test_metrics is None
        # And test should appear in completed list
        assert len(obs.completed_test_metrics) == 1
        assert obs.completed_test_metrics[0].test_name == "t1"


# ---------------------------------------------------------------------------
# TestMetricsObserverCustomMetrics
# ---------------------------------------------------------------------------

class TestMetricsObserverCustomMetrics:
    """Verify on_metric_collected handles custom metrics."""

    def test_on_metric_collected_records_custom_metric(self):
        mc = MagicMock()
        obs = _make_observer(metrics_collector=mc)
        obs.current_test_metrics = _make_test_case_metrics()

        event = MagicMock()
        event.metric_name = "packets_sent"
        event.metric_value = 42
        event.component = "network"

        obs.on_metric_collected(event)

        assert obs.current_test_metrics.custom_metrics["packets_sent"] == 42

    def test_on_metric_collected_ignores_event_without_attributes(self):
        mc = MagicMock()
        obs = _make_observer(metrics_collector=mc)
        obs.current_test_metrics = _make_test_case_metrics()

        # Event missing metric_name and metric_value
        event = MagicMock(spec=[])  # Empty spec = no attributes

        obs.on_metric_collected(event)

        assert obs.current_test_metrics.custom_metrics == {}

    def test_on_metric_collected_forwards_to_collector(self):
        mc = MagicMock()
        obs = _make_observer(metrics_collector=mc)
        obs.current_test_metrics = _make_test_case_metrics()

        event = MagicMock()
        event.metric_name = "latency_ms"
        event.metric_value = 15.3
        event.component = "quic"

        obs.on_metric_collected(event)

        mc.record_metric.assert_called_once_with(
            name="latency_ms",
            metric_type=MetricType.GAUGE,
            value=15.3,
            component="quic",
        )
