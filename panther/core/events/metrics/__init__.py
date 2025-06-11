"""
Metrics Module

This module provides metrics-related events, emitters, and states.
"""

from .events import (
    MetricsEventType,
    MetricsEvent,
    MetricCollectedEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
    CounterMetricEvent,
    MetricsSummaryEvent,
)
from .emitter import MetricsEventEmitter
from .states import MetricsState, MetricsCollectionState

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
