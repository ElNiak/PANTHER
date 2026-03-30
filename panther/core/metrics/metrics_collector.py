"""Comprehensive metrics collection system for PANTHER experiments.

Thread-safe metrics collection with multi-type support (counters, gauges,
timings, histograms, errors), context managers for automatic timing,
optional background system monitoring, and statistical analysis.

Usage::

    collector = MetricsCollector("experiment_1", output_dir)
    collector.record_metric("test_count", MetricType.COUNTER, 1)
    with collector.timing_context("test_execution"):
        run_test()
    collector.start_collection_thread(interval=1.0)
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.metrics.enums import MetricType, Phase
from panther.core.metrics.metric_types import Metric, TimingContext
from panther.core.utils.log_context import get_log_context
from panther.core.utils.logging_mixin import LoggerMixin

try:
    import psutil
except ImportError:
    psutil = None


class MetricsCollector(LoggerMixin):
    """Central metrics collection system for PANTHER experiments.

    Provides thread-safe metrics collection, background monitoring, context
    manager timing, statistical analysis, and metric querying/filtering.

    Thread Safety:
        - metrics_lock (Lock): Protects metrics list
        - timers_lock (Lock): Protects active timers dict
        - collection_thread: Optional background monitoring
    """

    def __init__(
        self,
        experiment_name: str,
        output_dir: Path,
        collection_interval: float = 5.0,
        structured_log_path: Optional[Path] = None,
    ):
        """Initialize the metrics collector.

        Args:
            experiment_name: Name of the experiment.
            output_dir: Directory where metrics will be stored.
            collection_interval: Background collection interval in seconds.
            structured_log_path: Path to structured.jsonl for inline metric writing.
                When set, each recorded metric is also appended as a JSONL line.
        """
        super().__init__()
        self.experiment_name = experiment_name
        self.output_dir = output_dir
        self.metrics: List[Metric] = []
        self.active_timers: Dict[str, TimingContext] = {}
        self.metrics_lock = threading.Lock()
        self.timers_lock = threading.Lock()
        self._jsonl_lock = threading.Lock()

        # Thread management
        self.collection_thread = None
        self.collection_running = False
        self.collection_interval = collection_interval

        # Initialize experiment start time
        self.experiment_start_time = time.time()
        self._finalized = False

        # Structured JSONL output (shared with logging/event handlers)
        self._structured_log_path = structured_log_path

        # Record experiment start
        self.record_metric(
            name="experiment_start",
            metric_type=MetricType.STATUS,
            value="started",
            phase=Phase.EXPERIMENT_INITIALIZATION,
            metadata={"experiment_name": experiment_name},
        )

        self.logger.info(
            "Metrics collector initialized for experiment: %s", experiment_name
        )

    # ── Background collection thread ─────────────────────────────────

    def start_collection_thread(self, interval: float = 1.0):
        """Start background metrics collection thread.

        Args:
            interval: Collection interval in seconds
        """
        if self.collection_running:
            self.logger.warning("Metrics collection thread is already running")
            return

        self.collection_interval = interval
        self.collection_running = True
        self.collection_thread = threading.Thread(
            target=self._collection_loop, daemon=True, name="MetricsCollector"
        )
        self.collection_thread.start()
        self.logger.info(
            "Metrics collection thread started with interval %ss", interval
        )

    def stop_collection_thread(self):
        """Stop the metrics collection thread."""
        if not self.collection_running:
            self.logger.debug("No metrics collection thread to stop")
            return

        self.collection_running = False
        if self.collection_thread and self.collection_thread.is_alive():
            self.collection_thread.join(timeout=self.collection_interval + 1)

        self.logger.info("Metrics collection thread stopped")

    def _collection_loop(self):
        """Background loop for periodic metrics collection."""
        self.logger.debug("Metrics collection loop started")

        while self.collection_running:
            start_time = time.time()

            try:
                self._collect_basic_metrics()
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.error(
                    "Error in metrics collection loop (interval=%.1fs): %s",
                    self.collection_interval,
                    e,
                )

            elapsed = time.time() - start_time
            sleep_duration = max(0, self.collection_interval - elapsed)

            sleep_time = 0
            while sleep_time < sleep_duration and self.collection_running:
                time.sleep(min(0.1, sleep_duration - sleep_time))
                sleep_time += 0.1

        self.logger.debug("Metrics collection loop stopped")

    def _collect_basic_metrics(self):
        """Collect basic system metrics (CPU, memory)."""
        try:
            if psutil is None:
                return

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent(interval=None)

            self.record_metric(
                name="process_memory_rss_mb",
                metric_type=MetricType.GAUGE,
                value=memory_info.rss / (1024 * 1024),
                component="metrics_collector",
            )

            self.record_metric(
                name="process_cpu_percent",
                metric_type=MetricType.GAUGE,
                value=cpu_percent,
                component="metrics_collector",
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            if not getattr(self, "_basic_metrics_warned", False):
                self._basic_metrics_warned = True
                self.logger.warning(
                    "Error collecting basic metrics (further errors suppressed): %s", e
                )

    # ── Core recording methods ───────────────────────────────────────

    def record_metric(
        self,
        name: str,
        metric_type: MetricType,
        value: Any,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a metric with thread-safe storage.

        Args:
            name: Metric name
            metric_type: Type of metric
            value: Metric value
            phase: Experiment phase
            test_case: Test case name
            component: Component name
            labels: Additional labels
            metadata: Additional metadata
        """
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            timestamp=time.time(),
            phase=phase,
            test_case=test_case,
            component=component,
            labels=labels or {},
            metadata=metadata or {},
        )

        with self.metrics_lock:
            self.metrics.append(metric)

        self._write_metric_jsonl(metric)
        self.logger.debug("Recorded metric: %s=%s (%s)", name, value, metric_type.value)

    def _write_metric_jsonl(self, metric: Metric) -> None:
        """Append a metric as a JSONL line to the structured log.

        Args:
            metric: The metric to write.
        """
        if self._structured_log_path is None:
            return
        ctx = get_log_context()
        record: Dict[str, Any] = {
            "ts": datetime.fromtimestamp(metric.timestamp, tz=timezone.utc).isoformat(
                timespec="microseconds"
            ),
            "level": "METRIC",
            "level_num": 15,
            "source": "metrics",
            "metric_name": metric.name,
            "metric_type": metric.metric_type.value,
            "metric_value": metric.value,
            "phase": metric.phase.value if metric.phase else ctx.phase,
            "experiment_id": ctx.experiment_id,
            "test_id": metric.test_case or ctx.test_id,
            "service_id": ctx.service_id,
            "component": metric.component,
        }
        record = {k: v for k, v in record.items() if v is not None}
        try:
            line = json.dumps(record, default=str)
            with self._jsonl_lock:
                with open(self._structured_log_path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if not getattr(self, "_jsonl_write_warned", False):
                self._jsonl_write_warned = True
                self.logger.warning(
                    "Failed to write metric to structured JSONL (further errors suppressed): %s",
                    exc,
                )

    def start_timer(
        self,
        name: str,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Start a timing operation.

        Args:
            name: Timer name
            phase: Experiment phase
            test_case: Test case name
            component: Component name
            labels: Additional labels
        """
        timer_key = f"{component or 'global'}:{test_case or 'global'}:{name}"
        timer_context = TimingContext(
            name=name,
            phase=phase,
            test_case=test_case,
            component=component,
            labels=labels or {},
            start_time=time.time(),
        )

        with self.timers_lock:
            if timer_key in self.active_timers:
                self.logger.warning(
                    "Timer %s already active, replacing with new timer", timer_key
                )
            self.active_timers[timer_key] = timer_context

        self.logger.debug("Started timer: %s", timer_key)

    def stop_timer(
        self,
        name: str,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
    ) -> Optional[float]:
        """Stop a timing operation and record the duration.

        Args:
            name: Timer name
            test_case: Test case name
            component: Component name

        Returns:
            Duration in seconds, or None if timer wasn't found
        """
        timer_key = f"{component or 'global'}:{test_case or 'global'}:{name}"

        with self.timers_lock:
            if timer_key not in self.active_timers:
                self.logger.warning("Timer %s not found", timer_key)
                return None
            timer_context = self.active_timers.pop(timer_key)

        duration = time.time() - timer_context.start_time

        self.record_metric(
            name=f"{name}_duration",
            metric_type=MetricType.TIMING,
            value=duration,
            phase=timer_context.phase,
            test_case=timer_context.test_case,
            component=timer_context.component,
            labels=timer_context.labels,
            metadata={"timer_name": name},
        )

        self.logger.debug(
            "Stopped timer: %s, duration: %ss", timer_key, f"{duration:.3f}"
        )
        return duration

    def timing_context(
        self,
        name: str,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Context manager for timing operations.

        Usage::

            with collector.timing_context("operation_name"):
                # Timed operation
                pass
        """
        return TimingContextManager(self, name, phase, test_case, component, labels)

    def time_operation(
        self,
        name: str,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Context manager for timing operations (alias for timing_context)."""
        return TimingContextManager(self, name, phase, test_case, component, labels)

    # ── Convenience recording methods ────────────────────────────────

    def increment_counter(
        self,
        name: str,
        value: int = 1,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Increment a counter metric."""
        self.record_metric(
            name=name,
            metric_type=MetricType.COUNTER,
            value=value,
            phase=phase,
            test_case=test_case,
            component=component,
            labels=labels,
        )

    def record_gauge(
        self,
        name: str,
        value: float,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a gauge metric (point-in-time value)."""
        self.record_metric(
            name=name,
            metric_type=MetricType.GAUGE,
            value=value,
            phase=phase,
            test_case=test_case,
            component=component,
            labels=labels,
        )

    def set_gauge(
        self,
        name: str,
        value: float,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a gauge metric (alias for record_gauge)."""
        self.record_metric(
            name=name,
            metric_type=MetricType.GAUGE,
            value=value,
            phase=phase,
            test_case=test_case,
            component=component,
            labels=labels,
        )

    def record_error(
        self,
        error_type: str,
        error_message: str = None,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        exception: Optional[Exception] = None,
        message: str = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an error occurrence.

        Args:
            error_type: Type/category of error
            error_message: Error message (preferred)
            phase: Experiment phase
            test_case: Test case name
            component: Component name
            exception: Original exception (if available)
            message: Error message (alternative parameter name)
            details: Additional error details (deprecated, use metadata)
            metadata: Additional metadata for the error
        """
        try:
            safe_error_type = (
                str(error_type) if error_type is not None else "UnknownError"
            )

            final_message = None
            if error_message is not None:
                try:
                    final_message = str(error_message)
                except Exception:
                    self.logger.warning("Error building error metadata", exc_info=True)

            if final_message is None and message is not None:
                try:
                    final_message = str(message)
                except Exception:
                    self.logger.warning("Error building error metadata", exc_info=True)

            if final_message is None:
                final_message = f"Error of type {safe_error_type}"

            try:
                meta_dict = {
                    "error_type": safe_error_type,
                    "error_message": final_message,
                }
            except Exception:
                self.logger.debug("Error building error metadata", exc_info=True)
                meta_dict = {"error_occurred": "true"}

            if exception is not None:
                try:
                    meta_dict["exception_type"] = type(exception).__name__
                except Exception:
                    meta_dict["exception_type"] = "UnknownExceptionType"
                try:
                    meta_dict["exception_str"] = str(exception)
                except Exception:
                    meta_dict["exception_str"] = "Unable to stringify exception"

            if details is not None:
                try:
                    for key, value in details.items():
                        try:
                            if (
                                isinstance(value, (str, int, float, bool))
                                or value is None
                            ):
                                meta_dict[key] = value
                            else:
                                meta_dict[key] = str(value)
                        except Exception:
                            continue
                except Exception:
                    self.logger.warning("Error building error metadata", exc_info=True)

            if metadata is not None:
                try:
                    for key, value in metadata.items():
                        try:
                            if (
                                isinstance(value, (str, int, float, bool))
                                or value is None
                            ):
                                meta_dict[key] = value
                            else:
                                meta_dict[key] = str(value)
                        except Exception:
                            continue
                except Exception:
                    self.logger.warning("Error building error metadata", exc_info=True)

            try:
                self.record_metric(
                    name="error_occurred",
                    metric_type=MetricType.ERROR,
                    value=1,
                    phase=phase,
                    test_case=test_case,
                    component=component,
                    metadata=meta_dict,
                )
                self.logger.warning(
                    "Recorded error: %s - %s", safe_error_type, final_message
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.error("Failed to record metric for error: %s", e)

        except Exception as e:  # pylint: disable=broad-exception-caught
            try:
                self.logger.error("Exception in record_error: %s", e)
            except Exception:  # pylint: disable=broad-exception-caught
                # Last resort: use module-level logging (self.logger may be broken)
                logging.error("Exception in record_error (logger unavailable): %s", e)

    def record_artifact_info(
        self,
        artifact_type: str,
        artifact_path: Path,
        size_bytes: Optional[int] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
    ) -> None:
        """Record information about generated artifacts."""
        if size_bytes is None and artifact_path.exists():
            size_bytes = artifact_path.stat().st_size

        self.record_metric(
            name="artifact_created",
            metric_type=MetricType.ARTIFACT,
            value=1,
            test_case=test_case,
            component=component,
            metadata={
                "artifact_type": artifact_type,
                "artifact_path": str(artifact_path),
                "size_bytes": size_bytes or 0,
            },
        )

    # ── Lifecycle ────────────────────────────────────────────────────

    def finalize(self) -> None:
        """Finalize metrics collection and record experiment completion.

        Idempotent: calling finalize() multiple times has no additional effect.
        """
        if self._finalized:
            return
        self._finalized = True

        if self.collection_running:
            self.stop_collection_thread()

        # Snapshot active timers without holding lock during stop_timer
        active_timer_keys = []
        active_timer_contexts = []

        with self.timers_lock:
            for timer_key in list(self.active_timers.keys()):
                active_timer_keys.append(timer_key)
                active_timer_contexts.append(self.active_timers[timer_key])

        for i, timer_key in enumerate(active_timer_keys):
            timer_context = active_timer_contexts[i]
            self.logger.warning("Force stopping active timer: %s", timer_key)
            self.stop_timer(
                timer_context.name, timer_context.test_case, timer_context.component
            )

        total_duration = time.time() - self.experiment_start_time
        self.record_metric(
            name="total_execution_time",
            metric_type=MetricType.TIMING,
            value=total_duration,
            phase=Phase.EXPERIMENT_CLEANUP,
            metadata={"experiment_name": self.experiment_name},
        )

        self.record_metric(
            name="experiment_end",
            metric_type=MetricType.STATUS,
            value="completed",
            phase=Phase.EXPERIMENT_CLEANUP,
            metadata={
                "experiment_name": self.experiment_name,
                "total_duration": total_duration,
            },
        )

        self.logger.info(
            "Metrics collection finalized for experiment: %s", self.experiment_name
        )

    def start_timing(
        self,
        name: str,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Start a timing operation (alias for start_timer with context manager return)."""
        timer = TimingContextManager(self, name, phase, test_case, component, labels)
        timer.__enter__()  # pylint: disable=unnecessary-dunder-call
        return timer

    # ── Metric querying, filtering, and analysis ────────────────────

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


class TimingContextManager:
    """Context manager for automatic timing operations."""

    def __init__(
        self,
        collector: MetricsCollector,
        name: str,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Initialize with collector, timer name, and optional context."""
        self.collector = collector
        self.name = name
        self.phase = phase
        self.test_case = test_case
        self.component = component
        self.labels = labels
        self.timer_started = False

    def stop(self):
        """Manually stop the timer if it was started."""
        if (
            self.timer_started
            and hasattr(self.collector, "stop_timer")
            and self.collector.stop_timer is not None
        ):
            try:
                self.collector.stop_timer(self.name, self.test_case, self.component)
                self.timer_started = False
            except Exception as e:  # pylint: disable=broad-exception-caught
                if hasattr(self.collector, "logger"):
                    self.collector.logger.error(
                        "Error stopping timer '%s': %s", self.name, e
                    )
        else:
            if hasattr(self.collector, "logger") and self.timer_started:
                self.collector.logger.warning(
                    "Attempted to stop timer '%s' that wasn't started or was already stopped",
                    self.name,
                )

    def __enter__(self):
        """Start the timer and return self."""
        try:
            self.collector.start_timer(
                self.name, self.phase, self.test_case, self.component, self.labels
            )
            self.timer_started = True
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.collector.logger.error("Failed to start timer '%s': %s", self.name, e)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and record any exceptions."""
        try:
            self.stop()

            if (
                exc_type is not None
                and hasattr(self, "collector")
                and self.collector is not None
            ):
                try:
                    if hasattr(self.collector, "record_error"):
                        self.collector.record_error(
                            error_type="timing_context_exception",
                            error_message=f"Exception in timing context '{self.name}': {exc_val}",
                            phase=self.phase,
                            test_case=self.test_case,
                            component=self.component,
                            exception=exc_val,
                            metadata={"context_name": self.name},
                        )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    if hasattr(self.collector, "logger"):
                        self.collector.logger.error(
                            "Failed to record timing context error: %s", e
                        )
        except Exception as e:  # pylint: disable=broad-exception-caught
            if (
                hasattr(self, "collector")
                and self.collector is not None
                and hasattr(self.collector, "logger")
            ):
                self.collector.logger.error("Error in timing context __exit__: %s", e)
            else:
                logging.error("Error in timing context __exit__: %s", e)

        return False
