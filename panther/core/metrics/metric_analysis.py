"""Metric querying and analysis for the PANTHER metrics system.

Provides the MetricAnalysisMixin with methods for filtering, aggregating,
and computing summary statistics over collected metrics.
"""

import time
from typing import Any, Dict, List, Optional

from panther.core.metrics.enums import MetricType, Phase
from panther.core.metrics.metric_types import Metric


class MetricAnalysisMixin:
    """Mixin providing metric querying, filtering, and statistical analysis.

    Expects the host class to provide:
        - self.metrics: List[Metric]
        - self.metrics_lock: threading.Lock
        - self.experiment_name: str
        - self.experiment_start_time: float
    """

    def get_metrics(
        self,
        metric_type: Optional[MetricType] = None,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
    ) -> List[Metric]:
        """Retrieve metrics with optional filtering.

        Args:
            metric_type: Filter by metric type
            phase: Filter by phase
            test_case: Filter by test case
            component: Filter by component

        Returns:
            List of matching metrics
        """
        with self.metrics_lock:
            filtered_metrics = self.metrics.copy()

        if metric_type:
            filtered_metrics = [
                m for m in filtered_metrics if m.metric_type == metric_type
            ]
        if phase:
            filtered_metrics = [m for m in filtered_metrics if m.phase == phase]
        if test_case:
            filtered_metrics = [m for m in filtered_metrics if m.test_case == test_case]
        if component:
            filtered_metrics = [m for m in filtered_metrics if m.component == component]

        return filtered_metrics

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of collected metrics.

        Returns:
            Dictionary containing summary statistics
        """
        with self.metrics_lock:
            metrics_copy = self.metrics.copy()

        if not metrics_copy:
            return {}

        stats = {
            "experiment_name": self.experiment_name,
            "total_metrics": len(metrics_copy),
            "experiment_duration": time.time() - self.experiment_start_time,
            "metric_types": {},
            "phases": {},
            "test_cases": set(),
            "components": set(),
            "error_count": 0,
            "timing_stats": {},
        }

        timing_metrics = []

        for metric in metrics_copy:
            metric_type_str = metric.metric_type.value
            stats["metric_types"][metric_type_str] = (
                stats["metric_types"].get(metric_type_str, 0) + 1
            )

            if metric.phase:
                if isinstance(metric.phase, Phase):
                    phase_str = metric.phase.value
                else:
                    phase_str = str(metric.phase)
                stats["phases"][phase_str] = stats["phases"].get(phase_str, 0) + 1

            if metric.test_case:
                stats["test_cases"].add(metric.test_case)
            if metric.component:
                stats["components"].add(metric.component)

            if metric.metric_type == MetricType.ERROR:
                stats["error_count"] += 1

            if metric.metric_type == MetricType.TIMING:
                timing_metrics.append(metric.value)

        stats["test_cases"] = list(stats["test_cases"])
        stats["components"] = list(stats["components"])

        if timing_metrics:
            stats["timing_stats"] = {
                "min": min(timing_metrics),
                "max": max(timing_metrics),
                "avg": sum(timing_metrics) / len(timing_metrics),
                "total": sum(timing_metrics),
                "count": len(timing_metrics),
            }

        return stats

    def get_counter(self, counter_name: str) -> int:
        """Get current value of a counter metric.

        Args:
            counter_name: Name of the counter

        Returns:
            Sum of all increments, 0 if counter doesn't exist
        """
        with self.metrics_lock:
            total = 0
            for metric in self.metrics:
                if (
                    metric.metric_type == MetricType.COUNTER
                    and metric.name == counter_name
                ):
                    total += metric.value
            return total

    def get_gauge(self, gauge_name: str) -> Optional[float]:
        """Get latest value of a gauge metric.

        Args:
            gauge_name: Name of the gauge

        Returns:
            Latest gauge value, None if gauge doesn't exist
        """
        with self.metrics_lock:
            latest_value = None
            latest_timestamp = 0
            for metric in self.metrics:
                if (
                    metric.metric_type == MetricType.GAUGE
                    and metric.name == gauge_name
                    and metric.timestamp > latest_timestamp
                ):
                    latest_value = metric.value
                    latest_timestamp = metric.timestamp
            return latest_value

    def get_timing_metric(self, timing_name: str) -> Optional[float]:
        """Get latest timing metric value.

        Args:
            timing_name: Name of the timing metric

        Returns:
            Latest timing value in seconds, None if doesn't exist
        """
        with self.metrics_lock:
            latest_value = None
            latest_timestamp = 0
            for metric in self.metrics:
                if (
                    metric.metric_type == MetricType.TIMING
                    and metric.name == timing_name
                    and metric.timestamp > latest_timestamp
                ):
                    latest_value = metric.value
                    latest_timestamp = metric.timestamp
            return latest_value

    @property
    def timing_metrics(self) -> Dict[str, float]:
        """All timing metrics as name->latest value dict."""
        with self.metrics_lock:
            timings = {}
            metric_timestamps = {}
            for metric in self.metrics:
                if metric.metric_type == MetricType.TIMING:
                    if (
                        metric.name not in timings
                        or metric.timestamp > metric_timestamps.get(metric.name, 0)
                    ):
                        timings[metric.name] = metric.value
                        metric_timestamps[metric.name] = metric.timestamp
            return timings

    @property
    def errors(self) -> List[Metric]:
        """All error metrics."""
        with self.metrics_lock:
            return [
                metric
                for metric in self.metrics
                if metric.metric_type == MetricType.ERROR
            ]

    @property
    def resource_metrics(self) -> List[Dict[str, Any]]:
        """All resource metrics as sorted list of dicts."""
        with self.metrics_lock:
            resources = []
            for metric in self.metrics:
                if metric.metric_type == MetricType.RESOURCE:
                    resource_data = metric.metadata.copy() if metric.metadata else {}
                    resource_data["timestamp"] = metric.timestamp
                    resource_data["value"] = metric.value
                    resources.append(resource_data)
            return sorted(resources, key=lambda x: x["timestamp"])

    @property
    def counters(self) -> Dict[str, int]:
        """All counters as name->total dict."""
        with self.metrics_lock:
            counter_totals = {}
            for metric in self.metrics:
                if metric.metric_type == MetricType.COUNTER:
                    counter_totals[metric.name] = (
                        counter_totals.get(metric.name, 0) + metric.value
                    )
            return counter_totals

    @property
    def gauges(self) -> Dict[str, float]:
        """All gauges as name->latest value dict."""
        with self.metrics_lock:
            gauge_values = {}
            gauge_timestamps = {}
            for metric in self.metrics:
                if metric.metric_type == MetricType.GAUGE:
                    if (
                        metric.name not in gauge_values
                        or metric.timestamp > gauge_timestamps.get(metric.name, 0)
                    ):
                        gauge_values[metric.name] = metric.value
                        gauge_timestamps[metric.name] = metric.timestamp
            return gauge_values

    @property
    def histograms(self) -> Dict[str, List[float]]:
        """All histograms as name->values list dict."""
        with self.metrics_lock:
            histogram_data = {}
            for metric in self.metrics:
                if metric.metric_type == MetricType.HISTOGRAM:
                    if metric.name not in histogram_data:
                        histogram_data[metric.name] = []
                    histogram_data[metric.name].append(metric.value)
            return histogram_data
