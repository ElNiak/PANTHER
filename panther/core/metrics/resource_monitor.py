from typing import Any, Dict, List, Optional

"""
Resource Monitor Module

This module provides system resource monitoring capabilities during
experiment execution, tracking CPU, memory, disk I/O, and network usage.
"""

import logging
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Union

import psutil

from .metrics_collector import MetricsCollector, MetricType, Phase


@dataclass
class ResourceSnapshot:
    """Snapshot of system resources at a point in time."""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_read_mb: float
    disk_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    load_average: List[float]


class ResourceMonitor:
    """
    System resource monitoring for PANTHER experiments.

    Continuously monitors CPU, memory, disk, and network usage,
    recording metrics at regular intervals during experiment execution.
    """

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        interval: float = 5.0,
        detailed_monitoring: bool = True,
    ):
        """
        Initialize the resource monitor.

        Args:
            metrics_collector: MetricsCollector instance to record metrics
            interval: Monitoring interval in seconds
            detailed_monitoring: Whether to collect detailed per-process metrics
        """
        self.metrics_collector = metrics_collector
        self.interval = interval
        self.detailed_monitoring = detailed_monitoring
        self.logger = logging.getLogger(self.__class__.__name__)

        self.monitoring = False
        self.monitor_thread: threading.Optional[Thread] = None
        self.initial_disk_io: Optional[dict] = None
        self.initial_network_io: Optional[dict] = None

        # Store baseline measurements
        self._record_baseline_metrics()

        self.logger.info("Resource monitor initialized with %ss interval", interval)

    def _record_baseline_metrics(self) -> None:
        """Record baseline system metrics before experiment starts."""
        try:
            # Get initial disk and network counters
            self.initial_disk_io = (
                psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
            )
            self.initial_network_io = (
                psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}
            )

            # Record system information
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)
            memory_total = psutil.virtual_memory().total / (1024 * 1024)  # MB

            self.metrics_collector.record_metric(
                name="system_cpu_count",
                metric_type=MetricType.GAUGE,
                value=cpu_count,
                phase=Phase.EXPERIMENT_INITIALIZATION,
                component="resource_monitor",
                metadata={"logical_cores": cpu_count_logical},
            )

            self.metrics_collector.record_metric(
                name="system_memory_total_mb",
                metric_type=MetricType.GAUGE,
                value=memory_total,
                phase=Phase.EXPERIMENT_INITIALIZATION,
                component="resource_monitor",
            )

            self.logger.debug(
                "Baseline metrics recorded: %s CPUs, %sMB RAM",
                cpu_count,
                f"{memory_total:.0f}",
            )

        except Exception as e:
            self.logger.error("Failed to record baseline metrics: %s", e)

    def start(self, phase: Optional[Phase] = None) -> None:
        """
        Start resource monitoring.

        Args:
            phase: Current experiment phase
        """
        if self.monitoring:
            self.logger.warning("Resource monitoring already active")
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(phase,),
            daemon=True,
            name="ResourceMonitor",
        )
        self.monitor_thread.start()

        self.logger.info("Resource monitoring started")

    def stop(self) -> None:
        """Stop resource monitoring."""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=self.interval + 1)

        self.logger.info("Resource monitoring stopped")

    # The start_monitoring and stop_monitoring methods have been merged with start() and stop()
    # to avoid duplication and prevent runtime errors

    def _monitor_loop(self, phase: Optional[Phase]) -> None:
        """Main monitoring loop running in separate thread."""
        self.logger.debug("Resource monitoring loop started")

        while self.monitoring:
            try:
                snapshot = self._take_snapshot()
                self._record_snapshot_metrics(snapshot, phase)

                if self.detailed_monitoring:
                    self._record_process_metrics(phase)

            except Exception as e:
                self.logger.error("Error in resource monitoring: %s", e)

            # Sleep in small increments to allow quick shutdown
            sleep_time = 0
            while sleep_time < self.interval and self.monitoring:
                time.sleep(0.1)
                sleep_time += 0.1

        self.logger.debug("Resource monitoring loop stopped")

    def _take_snapshot(self) -> ResourceSnapshot:
        """Take a snapshot of current system resources."""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=None)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_available_mb = memory.available / (1024 * 1024)

        # Disk I/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = 0
        disk_write_mb = 0
        if disk_io and self.initial_disk_io:
            disk_read_mb = (
                disk_io.read_bytes - self.initial_disk_io.get("read_bytes", 0)
            ) / (1024 * 1024)
            disk_write_mb = (
                disk_io.write_bytes - self.initial_disk_io.get("write_bytes", 0)
            ) / (1024 * 1024)

        # Network I/O
        network_io = psutil.net_io_counters()
        network_sent_mb = 0
        network_recv_mb = 0
        if network_io and self.initial_network_io:
            network_sent_mb = (
                network_io.bytes_sent - self.initial_network_io.get("bytes_sent", 0)
            ) / (1024 * 1024)
            network_recv_mb = (
                network_io.bytes_recv - self.initial_network_io.get("bytes_recv", 0)
            ) / (1024 * 1024)

        # Process count
        process_count = len(psutil.pids())

        # Load average (Unix-like systems only)
        load_average = []
        try:
            load_average = list(psutil.getloadavg())
        except (AttributeError, OSError):
            # Windows doesn't have load average
            load_average = [0.0, 0.0, 0.0]

        return ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_used_mb=memory_used_mb,
            memory_available_mb=memory_available_mb,
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            process_count=process_count,
            load_average=load_average,
        )

    def _record_snapshot_metrics(
        self, snapshot: ResourceSnapshot, phase: Optional[Phase]
    ) -> None:
        """Record snapshot metrics to the collector."""
        timestamp = snapshot.timestamp

        # CPU metrics
        self.metrics_collector.record_metric(
            name="cpu_percent",
            metric_type=MetricType.GAUGE,
            value=snapshot.cpu_percent,
            phase=phase,
            component="resource_monitor",
        )

        # Memory metrics
        self.metrics_collector.record_metric(
            name="memory_percent",
            metric_type=MetricType.GAUGE,
            value=snapshot.memory_percent,
            phase=phase,
            component="resource_monitor",
        )

        self.metrics_collector.record_metric(
            name="memory_used_mb",
            metric_type=MetricType.GAUGE,
            value=snapshot.memory_used_mb,
            phase=phase,
            component="resource_monitor",
        )

        self.metrics_collector.record_metric(
            name="memory_available_mb",
            metric_type=MetricType.GAUGE,
            value=snapshot.memory_available_mb,
            phase=phase,
            component="resource_monitor",
        )

        # Disk I/O metrics
        self.metrics_collector.record_metric(
            name="disk_read_mb_total",
            metric_type=MetricType.COUNTER,
            value=snapshot.disk_read_mb,
            phase=phase,
            component="resource_monitor",
        )

        self.metrics_collector.record_metric(
            name="disk_write_mb_total",
            metric_type=MetricType.COUNTER,
            value=snapshot.disk_write_mb,
            phase=phase,
            component="resource_monitor",
        )

        # Network I/O metrics
        self.metrics_collector.record_metric(
            name="network_sent_mb_total",
            metric_type=MetricType.COUNTER,
            value=snapshot.network_sent_mb,
            phase=phase,
            component="resource_monitor",
        )

        self.metrics_collector.record_metric(
            name="network_recv_mb_total",
            metric_type=MetricType.COUNTER,
            value=snapshot.network_recv_mb,
            phase=phase,
            component="resource_monitor",
        )

        # Process count
        self.metrics_collector.record_metric(
            name="process_count",
            metric_type=MetricType.GAUGE,
            value=snapshot.process_count,
            phase=phase,
            component="resource_monitor",
        )

        # Load average
        for i, load in enumerate(snapshot.load_average):
            self.metrics_collector.record_metric(
                name=f"load_average_{i+1}min",
                metric_type=MetricType.GAUGE,
                value=load,
                phase=phase,
                component="resource_monitor",
            )

    def _record_process_metrics(self, phase: Optional[Phase]) -> None:
        """Record detailed per-process metrics for high-resource processes."""
        try:
            # Get top CPU and memory consuming processes
            processes = []
            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_percent", "memory_info"]
            ):
                try:
                    proc_info = proc.info
                    cpu_percent = proc_info.get("cpu_percent", 0)
                    memory_percent = proc_info.get("memory_percent", 0)

                    # Check if values are valid numbers before comparison
                    if (cpu_percent is not None and cpu_percent > 1.0) or (
                        memory_percent is not None and memory_percent > 1.0
                    ):
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU usage and take top 10
            top_cpu_processes = sorted(
                processes, key=lambda x: x["cpu_percent"], reverse=True
            )[:10]

            for i, proc in enumerate(top_cpu_processes):
                self.metrics_collector.record_metric(
                    name="top_process_cpu_percent",
                    metric_type=MetricType.GAUGE,
                    value=proc["cpu_percent"],
                    phase=phase,
                    component="resource_monitor",
                    labels={
                        "process_name": proc["name"],
                        "pid": str(proc["pid"]),
                        "rank": str(i + 1),
                    },
                )

                memory_mb = (
                    proc["memory_info"].rss / (1024 * 1024)
                    if proc["memory_info"]
                    else 0
                )
                self.metrics_collector.record_metric(
                    name="top_process_memory_mb",
                    metric_type=MetricType.GAUGE,
                    value=memory_mb,
                    phase=phase,
                    component="resource_monitor",
                    labels={
                        "process_name": proc["name"],
                        "pid": str(proc["pid"]),
                        "rank": str(i + 1),
                    },
                )

        except Exception as e:
            self.logger.debug("Failed to record process metrics: %s", e)

    def get_current_snapshot(self) -> ResourceSnapshot:
        """Get current resource snapshot without recording metrics."""
        return self._take_snapshot()

    def record_custom_resource_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
    ) -> None:
        """
        Record a custom resource-related metric.

        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            phase: Current experiment phase
            test_case: Test case name (if applicable)
        """
        metadata = {}
        if unit:
            metadata["unit"] = unit

        self.metrics_collector.record_metric(
            name=name,
            metric_type=MetricType.RESOURCE,
            value=value,
            phase=phase,
            test_case=test_case,
            component="resource_monitor",
            metadata=metadata,
        )
