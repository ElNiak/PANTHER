"""OTLP-inspired concurrency for observability data export pipelines.

Implements OpenTelemetry Protocol patterns for efficient concurrent
data export with linear throughput scaling and pipeline parallelism.
"""

from .concurrent_exporter import ConcurrentExporter, ExportBatch, ExportResult

__all__ = [
    'ConcurrentExporter',
    'ExportBatch',
    'ExportResult'
]