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

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.metrics.enums import MetricType, Phase
from panther.core.metrics.metric_analysis import MetricAnalysisMixin
from panther.core.metrics.metric_types import Metric, TimingContext
from panther.core.utils.logging_mixin import LoggerMixin

try:
    import psutil
except ImportError:
    psutil = None


class MetricsCollector(MetricAnalysisMixin, LoggerMixin):
    """Central metrics collection system for PANTHER experiments.

    Provides thread-safe metrics collection, background monitoring, context
    manager timing, and statistical analysis. Query and analysis methods are
    provided by MetricAnalysisMixin.

    Thread Safety:
        - metrics_lock (Lock): Protects metrics list
        - timers_lock (Lock): Protects active timers dict
        - collection_thread: Optional background monitoring
    """

    def __init__(
        self, experiment_name: str, output_dir: Path, collection_interval: float = 5.0
    ):
        """Initialize the metrics collector.

        Args:
            experiment_name: Name of the experiment
            output_dir: Directory where metrics will be stored
            collection_interval: Background collection interval in seconds
        """
        super().__init__()
        self.experiment_name = experiment_name
        self.output_dir = output_dir
        self.metrics: List[Metric] = []
        self.active_timers: Dict[str, TimingContext] = {}
        self.metrics_lock = threading.Lock()
        self.timers_lock = threading.Lock()

        # Thread management
        self.collection_thread = None
        self.collection_running = False
        self.collection_interval = collection_interval

        # Initialize experiment start time
        self.experiment_start_time = time.time()
        self._finalized = False

        # Create metrics output directory
        self.metrics_dir = output_dir / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

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
                self.logger.error("Error in metrics collection loop: %s", e)

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
            self.logger.debug("Error collecting basic metrics: %s", e)

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

        self.logger.debug("Recorded metric: %s=%s (%s)", name, value, metric_type.value)

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
                    pass

            if final_message is None and message is not None:
                try:
                    final_message = str(message)
                except Exception:
                    pass

            if final_message is None:
                final_message = f"Error of type {safe_error_type}"

            try:
                meta_dict = {
                    "error_type": safe_error_type,
                    "error_message": final_message,
                }
            except Exception:
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
                    pass

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
                    pass

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
                pass

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
