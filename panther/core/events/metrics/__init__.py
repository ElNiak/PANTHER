"""
Metrics Module

This module provides metrics-related events, emitters, and states.
"""

from .emitter import MetricsEventEmitter
from .events import (
    CounterMetricEvent,
    MetricCollectedEvent,
    MetricsEvent,
    MetricsEventType,
    MetricsSummaryEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
)
from .states import MetricsCollectionState, MetricsState

__all__ = [
    # Event types and base classes
    "MetricsEventType",
    "MetricsEvent",
    # Specific event classes
    "MetricCollectedEvent",
    "ResourceMetricEvent",
    "TimingMetricEvent",
    "CounterMetricEvent",
    "MetricsSummaryEvent",
    # Event emitter
    "MetricsEventEmitter",
    # States
    "MetricsState",
    "MetricsCollectionState",
]
