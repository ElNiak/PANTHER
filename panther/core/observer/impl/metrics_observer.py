"""
Enhanced Metrics Observer Module

This module provides a comprehensive observer implementation that connects the metrics
collection system with the event system, allowing metrics to be published as events
and events to be recorded as metrics. Enhanced with advanced analytics, resource
monitoring, and comprehensive test case metrics.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

from panther.core.events.metrics.events import (
    CounterMetricEvent,
    MetricCollectedEvent,
    MetricsSummaryEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
)
from panther.core.events.step.events import (
    StepExecutionCompletedEvent,
    StepExecutionFailedEvent,
    StepExecutionStartedEvent,
    StepSkippedEvent,
)
from panther.core.events.test.events import (
    TestCompletedEvent,
    TestExecutionStartedEvent,
    TestFailedEvent,
)
from panther.core.metrics.enums import MetricType, Phase
from panther.core.observer.base.typed_observer_interface import ITypedObserver

if PSUTIL_AVAILABLE:
    from panther.core.metrics.resource_monitor import ResourceMonitor
else:
    ResourceMonitor = None  # type: ignore[assignment]


@dataclass
class MetricsSnapshot:
    """Snapshot of metrics at a specific point in time."""

    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    disk_io_read: int
    disk_io_write: int
    network_sent: int
    network_recv: int
    custom_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestCaseMetrics:
    """Comprehensive metrics for a test case."""

    test_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Resource metrics
    peak_cpu_percent: float = 0.0
    avg_cpu_percent: float = 0.0
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0
    total_disk_read: int = 0
    total_disk_write: int = 0
    total_network_sent: int = 0
    total_network_recv: int = 0

    # Performance metrics
    steps_executed: int = 0
    steps_passed: int = 0
    steps_failed: int = 0
    steps_skipped: int = 0

    # Error metrics
    errors_count: int = 0
    warnings_count: int = 0
    critical_errors: int = 0

    # Custom metrics
    custom_metrics: Dict[str, Any] = field(default_factory=dict)

    # Detailed snapshots
    snapshots: List[MetricsSnapshot] = field(default_factory=list)

    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistical metrics from snapshots."""
        if not self.snapshots:
            return {}

        cpu_values = [s.cpu_percent for s in self.snapshots]
        memory_values = [s.memory_mb for s in self.snapshots]

        stats = {
            "cpu_stats": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "mean": mean(cpu_values),
                "median": median(cpu_values),
                "std_dev": stdev(cpu_values) if len(cpu_values) > 1 else 0.0,
            },
            "memory_stats": {
                "min": min(memory_values),
                "max": max(memory_values),
                "mean": mean(memory_values),
                "median": median(memory_values),
                "std_dev": stdev(memory_values) if len(memory_values) > 1 else 0.0,
            },
            "snapshot_count": len(self.snapshots),
            "success_rate": (
                (self.steps_passed / self.steps_executed * 100)
                if self.steps_executed > 0
                else 0.0
            ),
            "error_rate": (
                (self.errors_count / self.steps_executed * 100)
                if self.steps_executed > 0
                else 0.0
            ),
        }

        return stats


class IMetricsCollector(ABC):
    """Interface for metrics collectors."""

    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """Collect metrics."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get collector name."""
        pass


class SystemMetricsCollector(IMetricsCollector):
    """Collects system resource metrics."""

    def __init__(self):
        """Initialize system metrics collector."""
        if PSUTIL_AVAILABLE:
            try:
                self.process = psutil.Process()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.process = None
        else:
            self.process = None

    def collect(self) -> Dict[str, Any]:
        """Collect system metrics."""
        if not PSUTIL_AVAILABLE or not self.process:
            return {}

        try:
            # CPU metrics
            cpu_percent = self.process.cpu_percent()
            system_cpu = psutil.cpu_percent(interval=0.1)

            # Memory metrics
            memory_info = self.process.memory_info()
            system_memory = psutil.virtual_memory()

            # Disk I/O
            try:
                disk_io = psutil.disk_io_counters()
                disk_read = disk_io.read_bytes if disk_io else 0
                disk_write = disk_io.write_bytes if disk_io else 0
            except (AttributeError, OSError):
                disk_read = disk_write = 0

            # Network I/O
            try:
                network_io = psutil.net_io_counters()
                network_sent = network_io.bytes_sent if network_io else 0
                network_recv = network_io.bytes_recv if network_io else 0
            except (AttributeError, OSError):
                network_sent = network_recv = 0

            return {
                "process_cpu_percent": cpu_percent,
                "system_cpu_percent": system_cpu,
                "process_memory_mb": memory_info.rss / 1024 / 1024,
                "system_memory_percent": system_memory.percent,
                "disk_read_bytes": disk_read,
                "disk_write_bytes": disk_write,
                "network_sent_bytes": network_sent,
                "network_recv_bytes": network_recv,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logging.error("Error collecting system metrics: %s", str(e))
            return {}

    def get_name(self) -> str:
        """Get collector name."""
        return "system"


class TestMetricsCollector(IMetricsCollector):
    """Collects test-specific metrics."""

    def __init__(self):
        """Initialize test metrics collector."""
        self.test_counts = defaultdict(int)
        self.test_durations = defaultdict(list)

    def collect(self) -> Dict[str, Any]:
        """Collect test metrics."""
        total_tests = sum(self.test_counts.values())
        avg_durations = {}

        for test_type, durations in self.test_durations.items():
            if durations:
                avg_durations[f"{test_type}_avg_duration"] = mean(durations)
                avg_durations[f"{test_type}_max_duration"] = max(durations)
                avg_durations[f"{test_type}_min_duration"] = min(durations)

        return {
            "total_tests": total_tests,
            "test_counts": dict(self.test_counts),
            "avg_durations": avg_durations,
            "timestamp": datetime.now().isoformat(),
        }

    def get_name(self) -> str:
        """Get collector name."""
        return "test"

    def record_test(self, test_type: str, duration: float = None):
        """Record a test execution."""
        self.test_counts[test_type] += 1
        if duration is not None:
            self.test_durations[test_type].append(duration)


class MetricsAggregator:
    """Aggregates and analyzes metrics over time."""

    def __init__(self, window_size: int = 100):
        """
        Initialize metrics aggregator.

        Args:
            window_size: Maximum number of metrics to keep in memory
        """
        self.window_size = window_size
        self.metrics_history = deque(maxlen=window_size)
        self.event_types = ["test", "environment", "service"]

    def add_metrics(self, metrics: Dict[str, Any]):
        """Add metrics to the aggregator."""
        timestamped_metrics = {"timestamp": datetime.now(), "data": metrics}
        self.metrics_history.append(timestamped_metrics)

    def get_trend_analysis(self, metric_name: str) -> Dict[str, Any]:
        """Analyze trends for a specific metric."""
        values = []
        timestamps = []

        for entry in self.metrics_history:
            if metric_name in entry["data"]:
                values.append(entry["data"][metric_name])
                timestamps.append(entry["timestamp"])

        if not values:
            return {}

        return {
            "metric_name": metric_name,
            "count": len(values),
            "mean": mean(values),
            "median": median(values),
            "std_dev": stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "latest": values[-1],
            "trend": (
                "increasing"
                if len(values) > 1 and values[-1] > values[0]
                else "decreasing"
            ),
        }


class MetricsObserver(ITypedObserver):
    """
    Comprehensive metrics observer with real-time monitoring and advanced analytics.

    This observer implements a sophisticated metrics collection system that integrates
    with PANTHER's event architecture to provide real-time performance monitoring,
    resource tracking, and statistical analysis for test execution environments.

    **Architecture Overview:**
    ```mermaid
    graph TB
        subgraph "MetricsObserver Core"
            MO[MetricsObserver]
            SMC[SystemMetricsCollector]
            TMC[TestMetricsCollector]
            MA[MetricsAggregator]
        end

        subgraph "Monitoring Layer"
            RM[ResourceMonitor]
            RT[Real-time Thread]
            LFH[Lazy File Handlers]
        end

        subgraph "Data Structures"
            MS[MetricsSnapshot]
            TCM[TestCaseMetrics]
            TH[Timeseries History]
        end

        subgraph "Event Integration"
            TE[Test Events]
            SE[Step Events]
            ME[Metrics Events]
        end

        MO --> SMC
        MO --> TMC
        MO --> MA
        MO --> RM
        MO --> RT
        MO --> LFH

        SMC --> MS
        TMC --> TCM
        MA --> TH

        TE --> MO
        SE --> MO
        ME --> MO
    ```

    **Key Capabilities:**
    - **Real-time Resource Monitoring**: CPU, memory, disk I/O, network tracking
    - **Test Lifecycle Analytics**: Complete test execution performance profiling
    - **Statistical Analysis**: Mean, median, standard deviation calculations
    - **Trend Detection**: Historical analysis with trend identification
    - **Memory-Efficient Collection**: Windowed data collection with cleanup
    - **Multi-threaded Monitoring**: Background collection without blocking tests

    **Performance Metrics Collected:**
    - Process and system CPU utilization
    - Memory usage (RSS, virtual, system-wide)
    - Disk I/O operations (read/write bytes)
    - Network I/O traffic (sent/received bytes)
    - Test step execution statistics
    - Custom application-specific metrics

    **Integration with Event System:**
    The observer automatically responds to test lifecycle events, creating comprehensive
    metrics profiles for each test execution while maintaining low overhead through
    intelligent batching and lazy file creation.
    """

    def __init__(
        self,
        publish_metrics: bool = True,
        collect_system_metrics: bool = True,
        publish_interval: int = 30,
        log_level: str = "INFO",
        enable_real_time_monitoring: bool = False,
        resource_collection_interval: int = 10,
        metric_collection_interval: int = 10,
        output_dir: str = None,
        metrics_collector=None,
    ):
        """
        Initialize the enhanced metrics observer.

        Args:
            publish_metrics: Whether to publish metrics as events
            collect_system_metrics: Whether to collect system resource metrics
            publish_interval: Interval for publishing summary metrics (seconds)
            log_level: Log level for this observer
            enable_real_time_monitoring: Enable real-time resource monitoring
            resource_collection_interval: Interval for resource collection in seconds
            metric_collection_interval: Interval for metric collection in seconds
            output_dir: Output directory for metrics and logs
            metrics_collector: Optional pre-configured MetricsCollector instance
        """
        self.publish_metrics = publish_metrics
        self.collect_system_metrics = collect_system_metrics
        self.publish_interval = publish_interval
        self.enable_real_time_monitoring = enable_real_time_monitoring
        self.resource_collection_interval = resource_collection_interval
        self.metric_collection_interval = metric_collection_interval

        self.log_level = log_level

        # Initialize metrics collector with default values or use provided one
        # Will be properly configured when connected to a test case if not provided
        super().__init__()
        self.experiment_name = "default_experiment"
        self.output_dir = Path(output_dir) if output_dir else Path("./outputs")
        self.metrics_collector = (
            metrics_collector  # Use provided collector if available
        )

        self.logger = self._setup_logging(
            logger_name="MetricsObserver",
            log_level=self.log_level,
            enable_colors=True,
            output_file=self.output_dir / "metrics_observer.log",
            structured_output=False,
        )

        # Initialize specialized collectors
        self.collectors: List[IMetricsCollector] = []
        if collect_system_metrics and PSUTIL_AVAILABLE:
            self.collectors.append(SystemMetricsCollector())
        self.collectors.append(TestMetricsCollector())

        # Initialize resource monitor if metrics collector is provided
        self.resource_monitor = None
        if metrics_collector and collect_system_metrics:
            try:
                self.resource_monitor = ResourceMonitor(
                    metrics_collector=metrics_collector,
                    interval=resource_collection_interval,
                    detailed_monitoring=True,
                )
                self.logger.info(
                    "ResourceMonitor initialized with interval=%d seconds",
                    resource_collection_interval,
                )
            except Exception as err:
                self.logger.warning(
                    "Failed to initialize ResourceMonitor: %s", str(err)
                )

        # Initialize aggregator
        self.aggregator = MetricsAggregator()

        # Test metrics tracking
        self.current_test_metrics: Optional[TestCaseMetrics] = None
        self.completed_test_metrics: List[TestCaseMetrics] = []

        # Real-time monitoring
        self.monitoring_active = False
        self.last_publish_time = time.time()
        self.collection_timer = None

        # Circuit breaker for lazy MetricsCollector creation
        self._collector_creation_failed = False

        self.logger.info(
            "MetricsObserver initialized with publish_interval=%d seconds",
            self.publish_interval,
        )

        # Start real-time monitoring if enabled
        if self.enable_real_time_monitoring:
            self.start_monitoring()

    # Override typed event handlers

    def on_test_execution_started(self, event: TestExecutionStartedEvent) -> bool:
        """Handle test started event."""
        # Start tracking a new test
        test_name = getattr(
            event, "test_name", getattr(event, "test_id", event.entity_id)
        )
        self.logger.info("Starting metrics collection for test: %s", test_name)

        # Initialize or update the metrics collector with test information
        output_dir = getattr(event, "output_dir", self.output_dir)
        if isinstance(output_dir, str):
            output_dir = Path(output_dir)

        # Create metrics collector if it doesn't exist
        if not self.metrics_collector:
            experiment_name = getattr(event, "experiment_name", self.experiment_name)
            # Lazy import to avoid circular dependency
            from panther.core.metrics.metrics_collector import MetricsCollector

            self.metrics_collector = MetricsCollector(
                experiment_name, output_dir, self.metric_collection_interval
            )

        self.current_test_metrics = TestCaseMetrics(
            test_name=test_name, start_time=datetime.now()
        )

        # Check if it's time to publish summary
        self._check_publish_interval()
        return True

    def on_test_completed(self, event: TestCompletedEvent) -> bool:
        """Handle test completed event."""
        # Finalize the current test metrics
        if self.current_test_metrics:
            self.current_test_metrics.end_time = datetime.now()
            if self.current_test_metrics.start_time:
                self.current_test_metrics.duration_seconds = (
                    self.current_test_metrics.end_time
                    - self.current_test_metrics.start_time
                ).total_seconds()

            self.completed_test_metrics.append(self.current_test_metrics)
            self.logger.info(
                "Completed metrics collection for test: %s (duration: %.2f seconds)",
                self.current_test_metrics.test_name,
                self.current_test_metrics.duration_seconds or 0,
            )
            self.current_test_metrics = None

        self._check_publish_interval()
        return True

    def on_test_failed(self, event: TestFailedEvent) -> bool:
        """Handle test failed event."""
        # Increment error count for the current test
        if self.current_test_metrics:
            self.current_test_metrics.errors_count += 1

        # Record error in the metrics collector
        if self._ensure_metrics_collector():
            self.metrics_collector.record_error(
                error_type="test_failure",
                error_message=getattr(event, "failure_reason", "Test failed"),
                phase=Phase.TEST_EXECUTION,
                test_case=getattr(event, "test_name", None),
            )

        # Finalize test metrics same as completed
        return self.on_test_completed(event)

    def on_step_execution_started(self, event: StepExecutionStartedEvent) -> bool:
        """Handle step started event."""
        if self.current_test_metrics:
            self.current_test_metrics.steps_executed += 1
        return True

    def on_step_execution_completed(self, event: StepExecutionCompletedEvent) -> bool:
        """Handle step completed event."""
        if self.current_test_metrics:
            self.current_test_metrics.steps_passed += 1
        return True

    def on_step_execution_failed(self, event: StepExecutionFailedEvent) -> bool:
        """Handle step failed event."""
        if self.current_test_metrics:
            self.current_test_metrics.steps_failed += 1
        return True

    def on_step_skipped(self, event: StepSkippedEvent) -> bool:
        """Handle step skipped event."""
        if self.current_test_metrics:
            self.current_test_metrics.steps_skipped += 1
        return True

    def on_metrics_summary(self, event: MetricsSummaryEvent) -> bool:
        """Handle metrics snapshot event."""
        if not self.current_test_metrics:
            return True

        snapshot_data = event.metrics if hasattr(event, "metrics") else {}
        if "cpu" in snapshot_data and "memory" in snapshot_data:
            snapshot = MetricsSnapshot(
                timestamp=datetime.now(),
                cpu_percent=snapshot_data.get("cpu", {}).get("percent", 0.0),
                memory_mb=snapshot_data.get("memory", {}).get("used_mb", 0.0),
                disk_io_read=snapshot_data.get("disk_io", {}).get("read_bytes", 0),
                disk_io_write=snapshot_data.get("disk_io", {}).get("write_bytes", 0),
                network_sent=snapshot_data.get("network", {}).get("sent_bytes", 0),
                network_recv=snapshot_data.get("network", {}).get("received_bytes", 0),
            )

            # Update peak values
            self.current_test_metrics.peak_cpu_percent = max(
                self.current_test_metrics.peak_cpu_percent, snapshot.cpu_percent
            )
            self.current_test_metrics.peak_memory_mb = max(
                self.current_test_metrics.peak_memory_mb, snapshot.memory_mb
            )

            # Add to snapshots list
            self.current_test_metrics.snapshots.append(snapshot)

            # Calculate running averages
            cpu_values = [s.cpu_percent for s in self.current_test_metrics.snapshots]
            memory_values = [s.memory_mb for s in self.current_test_metrics.snapshots]

            self.current_test_metrics.avg_cpu_percent = sum(cpu_values) / len(
                cpu_values
            )
            self.current_test_metrics.avg_memory_mb = sum(memory_values) / len(
                memory_values
            )

        return True

    def on_metric_collected(self, event: MetricCollectedEvent) -> bool:
        """Handle custom metric recorded event."""
        if (
            self.current_test_metrics
            and hasattr(event, "metric_name")
            and hasattr(event, "metric_value")
        ):
            self.current_test_metrics.custom_metrics[
                event.metric_name
            ] = event.metric_value
            self.logger.debug(
                "Recorded custom metric: %s = %s", event.metric_name, event.metric_value
            )

        # Also record in the metrics collector if available
        if self._ensure_metrics_collector() and hasattr(event, "metric_name"):
            self.metrics_collector.record_metric(
                name=event.metric_name,
                metric_type=MetricType.GAUGE,
                value=getattr(event, "metric_value", 0),
                component=getattr(event, "component", None),
            )
        return True

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer is interested in metrics events."""
        # We're interested in all metrics events
        return event_type.startswith("metrics.")

    def _ensure_metrics_collector(self) -> bool:
        """Ensure a metrics collector is available, creating one lazily if needed.

        Returns:
            True if a collector is available, False otherwise.
        """
        if self.metrics_collector:
            return True
        if self._collector_creation_failed:
            return False
        try:
            from panther.core.metrics.metrics_collector import MetricsCollector

            self.metrics_collector = MetricsCollector(
                self.experiment_name,
                self.output_dir,
                self.metric_collection_interval,
            )
            self.logger.info(
                "Lazily created MetricsCollector for experiment: %s",
                self.experiment_name,
            )
            return True
        except Exception as e:
            self._collector_creation_failed = True
            self.logger.error(
                "Failed to create MetricsCollector (will not retry): %s", e
            )
            return False

    def on_counter_metric(self, event: CounterMetricEvent) -> bool:
        """Handle counter metric event."""
        if self._ensure_metrics_collector():
            # Record the counter metric in the metrics collector
            self.metrics_collector.record_metric(
                name=event.counter_name,
                metric_type=MetricType.COUNTER,
                value=event.value,
                component=event.component,
                labels=None,
                metadata={"increment": event.increment},
            )
            self.logger.debug(
                "Recorded counter metric: %s = %s (increment: %s)",
                event.counter_name,
                event.value,
                event.increment,
            )
        return True

    def on_resource_metric(self, event: ResourceMetricEvent) -> bool:
        """Handle resource metric event."""
        if self._ensure_metrics_collector():
            # Record the resource metric in the metrics collector
            self.metrics_collector.record_metric(
                name=f"resource.{event.resource_type}",
                metric_type=MetricType.GAUGE,
                value=event.usage_value,
                component=event.component,
                metadata=event.metadata or {},
            )
            self.logger.debug(
                "Recorded resource metric: %s = %s",
                f"resource.{event.resource_type}",
                event.usage_value,
            )
        return True

    def on_timing_metric(self, event: TimingMetricEvent) -> bool:
        """Handle timing metric event."""
        if self._ensure_metrics_collector():
            # Record the timing metric in the metrics collector
            self.metrics_collector.record_metric(
                name=f"timing.{event.operation_name}",
                metric_type=MetricType.TIMING,
                value=event.duration,
                component=event.component,
                metadata=event.metadata or {},
            )
            self.logger.debug(
                "Recorded timing metric: %s = %s",
                f"timing.{event.operation_name}",
                event.duration,
            )
        return True

    def _check_publish_interval(self):
        """Check if it's time to publish metrics summary."""
        current_time = time.time()
        if current_time - self.last_publish_time >= self.publish_interval:
            self.publish_metrics_summary()
            self.last_publish_time = current_time

    def start_monitoring(self):
        """
        Start real-time resource monitoring.

        This method activates the real-time monitoring of system resources,
        which will collect metrics at regular intervals and can trigger alerts
        when thresholds are exceeded.
        """
        if self.monitoring_active:
            self.logger.debug("Monitoring already active")
            return

        self.logger.info("Starting real-time resource monitoring")
        self.monitoring_active = True

        # Collect initial metrics
        self._collect_current_metrics()

        # Start resource monitor if available
        if self.resource_monitor is None and self.metrics_collector:
            try:
                self.resource_monitor = ResourceMonitor(
                    metrics_collector=self.metrics_collector,
                    interval=self.resource_collection_interval,
                    detailed_monitoring=True,
                )
                self.logger.info(
                    "ResourceMonitor initialized with interval=%d seconds",
                    self.resource_collection_interval,
                )
            except Exception as err:
                self.logger.warning(
                    "Failed to initialize ResourceMonitor: %s", str(err)
                )

        # Start resource monitor
        if self.resource_monitor:
            self.resource_monitor.start()
            self.logger.info("Started ResourceMonitor")

        # Start metrics collection thread if metrics_collector is available
        if self.metrics_collector:
            self.metrics_collector.start_collection_thread(
                interval=self.publish_interval
            )
        else:
            # Create a dedicated monitoring thread
            import threading

            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True, name="MetricsObserverMonitor"
            )
            self.monitoring_thread.start()
            self.logger.debug("Started monitoring thread")

    def stop_monitoring(self):
        """
        Stop real-time resource monitoring.
        """
        if not self.monitoring_active:
            self.logger.debug("Monitoring not active")
            return

        self.logger.info("Stopping real-time resource monitoring")
        self.monitoring_active = False

        # Cancel any active collection timer
        if self.collection_timer and self.collection_timer.is_alive():
            self.collection_timer.cancel()
            self.collection_timer = None

        # Stop the resource monitor if it was started
        if hasattr(self, "resource_monitor") and self.resource_monitor:
            try:
                self.resource_monitor.stop()
                self.logger.info("Stopped ResourceMonitor")
            except Exception as err:
                self.logger.warning("Error stopping ResourceMonitor: %s", str(err))

        # Stop the metrics collection thread if it was started through MetricsCollector
        if hasattr(self, "metrics_collector") and self.metrics_collector:
            self.metrics_collector.stop_collection_thread()

        # Wait for our monitoring thread to stop if we created one
        if hasattr(self, "monitoring_thread") and self.monitoring_thread:
            if self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=self.publish_interval + 1)
            self.logger.debug("Monitoring thread stopped")

    def _collect_current_metrics(self):
        """Collect metrics from all registered collectors and aggregate them."""
        if not self.monitoring_active:
            return

        all_metrics = {}

        # Collect metrics from each collector
        for collector in self.collectors:
            try:
                collector_metrics = collector.collect()
                if collector_metrics:
                    all_metrics[collector.get_name()] = collector_metrics
            except Exception as e:
                self.logger.error(
                    "Error collecting metrics from %s: %s", collector.get_name(), str(e)
                )

        # Add to aggregator
        if all_metrics:
            self.aggregator.add_metrics(all_metrics)

            # Store in metrics collector if available
            if self.metrics_collector:
                for category, metrics in all_metrics.items():
                    for name, value in metrics.items():
                        if isinstance(value, (int, float)):
                            self.metrics_collector.record_metric(
                                name=f"{category}.{name}",
                                value=value,
                                metric_type=(
                                    MetricType.COUNTER
                                    if name.endswith("_count")
                                    else MetricType.GAUGE
                                ),
                                phase=Phase.TEST_EXECUTION,
                            )

        # Schedule next collection if real-time monitoring is active
        if self.monitoring_active:
            # Cancel any existing timer
            if (
                hasattr(self, "collection_timer")
                and self.collection_timer
                and self.collection_timer.is_alive()
            ):
                self.collection_timer.cancel()

            # Only schedule if we don't already have an active timer
            if not (
                hasattr(self, "collection_timer")
                and self.collection_timer
                and self.collection_timer.is_alive()
            ):
                # Schedule next collection using threading.Timer
                import threading

                def next_collection():
                    if self.monitoring_active:
                        self._collect_current_metrics()

                self.collection_timer = threading.Timer(
                    self.metric_collection_interval, next_collection
                )
                self.collection_timer.daemon = True
                self.collection_timer.start()

                self.logger.debug(
                    "Scheduled next metrics collection in %d seconds",
                    self.metric_collection_interval,
                )

    def publish_metrics_summary(self):
        """
        Publish a summary of collected metrics.

        This method aggregates and publishes a summary of all collected metrics,
        which can be useful for monitoring and debugging purposes.
        """
        if not self.publish_metrics:
            return

        # Collect current metrics
        self._collect_current_metrics()

        # Create a summary if we have a current test
        if self.current_test_metrics and self.current_test_metrics.snapshots:
            # Calculate statistics
            stats = self.current_test_metrics.calculate_statistics()

            self.logger.info(
                "Metrics summary for %s:", self.current_test_metrics.test_name
            )
            self.logger.info(
                "  CPU: %.2f%% avg, %.2f%% peak",
                self.current_test_metrics.avg_cpu_percent,
                self.current_test_metrics.peak_cpu_percent,
            )
            self.logger.info(
                "  Memory: %.2f MB avg, %.2f MB peak",
                self.current_test_metrics.avg_memory_mb,
                self.current_test_metrics.peak_memory_mb,
            )
            self.logger.info(
                "  Steps: %d total, %d passed, %d failed, %d skipped",
                self.current_test_metrics.steps_executed,
                self.current_test_metrics.steps_passed,
                self.current_test_metrics.steps_failed,
                self.current_test_metrics.steps_skipped,
            )

            # Publish statistics if we have a metrics collector
            if self.metrics_collector:
                for category, metrics in stats.items():
                    if isinstance(metrics, dict):
                        for name, value in metrics.items():
                            if isinstance(value, (int, float)):
                                self.metrics_collector.record_metric(
                                    name=f"summary.{category}.{name}",
                                    value=value,
                                    metric_type=MetricType.GAUGE,
                                    phase=Phase.TEST_EXECUTION,
                                )
                    elif isinstance(metrics, (int, float)):
                        self.metrics_collector.record_metric(
                            name=f"summary.{category}",
                            value=metrics,
                            metric_type=MetricType.GAUGE,
                            phase=Phase.TEST_EXECUTION,
                        )

    def _monitoring_loop(self):
        """
        Background loop for periodic metrics collection when not using MetricsCollector's thread.
        """
        self.logger.debug("Metrics observer monitoring loop started")
        import time

        while self.monitoring_active:
            start_time = time.time()

            try:
                # Collect current metrics
                self._collect_current_metrics()
            except Exception as e:
                # Log but continue - we don't want to crash the monitoring thread
                self.logger.error("Error in metrics collection loop: %s", str(e))

            # Calculate how long to sleep to maintain the interval
            elapsed = time.time() - start_time
            sleep_duration = max(0, self.publish_interval - elapsed)

            # Sleep in small increments to allow quick shutdown
            sleep_time = 0
            while sleep_time < sleep_duration and self.monitoring_active:
                time.sleep(min(0.1, sleep_duration - sleep_time))
                sleep_time += 0.1

        self.logger.debug("Metrics observer monitoring loop stopped")

    def initialize_resource_monitor(self):
        """
        Initialize the ResourceMonitor if metrics_collector is available.

        This method creates and configures a ResourceMonitor instance that will
        collect detailed system resource metrics at regular intervals.
        """
        if not self.metrics_collector:
            self.logger.warning(
                "Cannot initialize ResourceMonitor without a MetricsCollector"
            )
            return None

        try:
            resource_monitor = ResourceMonitor(
                metrics_collector=self.metrics_collector,
                interval=self.resource_collection_interval,
                detailed_monitoring=True,
            )
            self.logger.info(
                "ResourceMonitor initialized with interval=%d seconds",
                self.resource_collection_interval,
            )

            # Store the resource monitor reference
            self.resource_monitor = resource_monitor

            return resource_monitor
        except Exception as e:
            self.logger.warning("Failed to initialize ResourceMonitor: %s", str(e))
            return None
