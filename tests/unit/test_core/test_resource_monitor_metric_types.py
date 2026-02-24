"""Tests for Bug #3 edge cases: ResourceMonitor metric types.

Verifies that I/O metrics are recorded as GAUGE (not COUNTER),
since psutil returns cumulative totals and we want the latest value.

Tests cover:
- disk_read_mb_total and disk_write_mb_total as GAUGE
- network_sent_mb_total and network_recv_mb_total as GAUGE
- cpu_percent and memory_percent remain GAUGE
- process_count is GAUGE
"""

from collections import namedtuple
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]

from panther.core.metrics.enums import MetricType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Named tuples matching psutil return types
VirtualMemory = namedtuple("svmem", ["total", "available", "percent", "used", "free"])
DiskIO = namedtuple(
    "sdiskio",
    [
        "read_count",
        "write_count",
        "read_bytes",
        "write_bytes",
        "read_time",
        "write_time",
    ],
)
NetIO = namedtuple(
    "snetio",
    [
        "bytes_sent",
        "bytes_recv",
        "packets_sent",
        "packets_recv",
        "errin",
        "errout",
        "dropin",
        "dropout",
    ],
)
LoadAvg = (1.0, 0.5, 0.25)


def _get_recorded_metric_types(mock_collector):
    """Extract mapping of metric name -> MetricType from record_metric calls."""
    result = {}
    for c in mock_collector.record_metric.call_args_list:
        kwargs = c.kwargs if c.kwargs else {}
        if not kwargs and len(c.args) >= 2:
            continue
        name = kwargs.get("name", "")
        mtype = kwargs.get("metric_type", None)
        if name and mtype:
            result[name] = mtype
    return result


@pytest.fixture
def mock_psutil():
    """Patch psutil functions to return controlled values."""
    with patch("panther.core.metrics.resource_monitor.psutil") as mock_ps:
        mock_ps.cpu_percent.return_value = 25.0
        mock_ps.cpu_count.return_value = 4

        mem = VirtualMemory(
            total=8 * 1024 * 1024 * 1024,  # 8GB
            available=4 * 1024 * 1024 * 1024,
            percent=50.0,
            used=4 * 1024 * 1024 * 1024,
            free=4 * 1024 * 1024 * 1024,
        )
        mock_ps.virtual_memory.return_value = mem

        disk = DiskIO(
            read_count=100,
            write_count=50,
            read_bytes=200 * 1024 * 1024,
            write_bytes=100 * 1024 * 1024,
            read_time=1000,
            write_time=500,
        )
        mock_ps.disk_io_counters.return_value = disk

        net = NetIO(
            bytes_sent=50 * 1024 * 1024,
            bytes_recv=150 * 1024 * 1024,
            packets_sent=1000,
            packets_recv=2000,
            errin=0,
            errout=0,
            dropin=0,
            dropout=0,
        )
        mock_ps.net_io_counters.return_value = net

        mock_ps.pids.return_value = list(range(100))
        mock_ps.getloadavg.return_value = LoadAvg

        # process_iter for detailed monitoring
        mock_ps.process_iter.return_value = []
        mock_ps.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
        mock_ps.AccessDenied = type("AccessDenied", (Exception,), {})
        mock_ps.Process.return_value = MagicMock()

        yield mock_ps


@pytest.fixture
def mock_metrics_collector():
    """Create a mock MetricsCollector."""
    mc = MagicMock()
    mc.record_metric = MagicMock()
    return mc


# ---------------------------------------------------------------------------
# TestResourceMonitorMetricTypes
# ---------------------------------------------------------------------------


class TestResourceMonitorMetricTypes:
    """Verify that ResourceMonitor records I/O metrics as GAUGE."""

    def _create_monitor_and_record(self, mock_psutil, mock_metrics_collector):
        """Create a ResourceMonitor and take one snapshot."""
        from panther.core.metrics.resource_monitor import ResourceMonitor

        monitor = ResourceMonitor(
            metrics_collector=mock_metrics_collector,
            interval=5.0,
            detailed_monitoring=False,
        )
        snapshot = monitor._take_snapshot()
        monitor._record_snapshot_metrics(snapshot, phase=None)
        return _get_recorded_metric_types(mock_metrics_collector)

    def test_disk_io_metrics_recorded_as_gauge(
        self, mock_psutil, mock_metrics_collector
    ):
        types = self._create_monitor_and_record(mock_psutil, mock_metrics_collector)
        assert types.get("disk_read_mb_total") == MetricType.GAUGE
        assert types.get("disk_write_mb_total") == MetricType.GAUGE

    def test_network_io_metrics_recorded_as_gauge(
        self, mock_psutil, mock_metrics_collector
    ):
        types = self._create_monitor_and_record(mock_psutil, mock_metrics_collector)
        assert types.get("network_sent_mb_total") == MetricType.GAUGE
        assert types.get("network_recv_mb_total") == MetricType.GAUGE

    def test_cpu_and_memory_remain_gauge(self, mock_psutil, mock_metrics_collector):
        types = self._create_monitor_and_record(mock_psutil, mock_metrics_collector)
        assert types.get("cpu_percent") == MetricType.GAUGE
        assert types.get("memory_percent") == MetricType.GAUGE
        assert types.get("memory_used_mb") == MetricType.GAUGE
        assert types.get("memory_available_mb") == MetricType.GAUGE

    def test_process_count_is_gauge(self, mock_psutil, mock_metrics_collector):
        types = self._create_monitor_and_record(mock_psutil, mock_metrics_collector)
        assert types.get("process_count") == MetricType.GAUGE
