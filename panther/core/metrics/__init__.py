"""Metrics Module - Performance Monitoring for PANTHER.

Thread-safe metrics collection, resource monitoring, and multi-format
reporting for experiment lifecycle tracking.

Architecture::

    MetricsCollector (thread-safe)
        │
        ├── TimingContextManager    ── automatic phase timing via ``with`` blocks
        ├── ResourceMonitor         ── background CPU/memory/disk/network sampling
        ├── MetricsReporter         ── human-readable summaries and reports
        ├── MetricsExporter         ── JSON, CSV, and dashboard-compatible output
        └── MetricsDataLoader       ── reload persisted metrics from output dirs

Metric Types:
    - **TIMING** -- phase and operation durations
    - **COUNTER** -- event counts (tests run, errors, retries)
    - **GAUGE** -- point-in-time values (active connections, queue depth)
    - **HISTOGRAM** -- distribution tracking (latencies, sizes)
    - **RESOURCE** -- CPU, memory, disk, network snapshots
    - **ARTIFACT** -- file paths and sizes of generated outputs
    - **STATUS** / **ERROR** / **PERFORMANCE** -- lifecycle and diagnostics

Experiment Phases:
    Phases tracked via `Phase` enum: ``CONFIG_LOADING`` through
    ``EXPERIMENT_CLEANUP``, enabling per-phase timing breakdowns.

Example::

    from panther.core.metrics import MetricsCollector, Phase

    collector = MetricsCollector()
    with collector.time(Phase.TEST_EXECUTION, "quic_handshake"):
        run_test()
    collector.increment("tests_passed")
    report = MetricsReporter(collector).generate_summary()

See Also:
    `panther.core.observer` -- observers that consume metrics events
    `panther.core.reporting` -- uses metrics for experiment reports
"""

from .data_loader import MetricsDataLoader
from .enums import MetricType, Phase
from .metrics_collector import MetricsCollector, TimingContextManager
from .metrics_exporter import MetricsExporter
from .metrics_reporter import MetricsReporter
from .resource_monitor import ResourceMonitor

__all__ = [
    "MetricsCollector",
    "MetricsDataLoader",
    "MetricType",
    "Phase",
    "TimingContextManager",
    "ResourceMonitor",
    "MetricsReporter",
    "MetricsExporter",
]
