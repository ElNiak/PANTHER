from typing import TYPE_CHECKING, Any, Dict, List, Optional

"""
Metrics Event Emitter

This module provides a type-safe event emitter for metrics-related events.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.metrics.events import (
    CounterMetricEvent,
    MetricCollectedEvent,
    MetricsSummaryEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
)


class MetricsEventEmitter:
    """Type-safe event emitter for metrics-related events.

    This class provides methods for emitting all metrics events
    with proper typing and validation.
    """

    def __init__(self, event_manager: "EventManager"):
        """
        Initialize the metrics event emitter.

        Args:
            event_manager: Event manager to use for event emission
        """
        self.event_manager = event_manager

    def emit_metric_collected(
        self,
        metric_name: str,
        metric_type: str,
        value: Any,
        phase: Optional[str] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a metric collected event.

        Args:
            metric_name: Name of the metric
            metric_type: Type of metric (timing, counter, etc.)
            value: Metric value
            phase: Experiment phase when metric was collected
            test_case: Related test case name
            component: Component the metric belongs to
            labels: Additional metric labels
            metadata: Additional metric metadata
        """
        event = MetricCollectedEvent(
            metric_name=metric_name,
            metric_type=metric_type,
            value=value,
            phase=phase,
            test_case=test_case,
            component=component,
            labels=labels,
            metadata=metadata,
        )
        self.event_manager.notify(event)

    def emit_resource_metric(
        self,
        resource_type: str,
        usage_value: float,
        component: Optional[str] = None,
        test_case: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a resource usage metric event.

        Args:
            resource_type: Type of resource (cpu, memory, etc.)
            usage_value: Resource usage value
            component: Component being monitored
            test_case: Related test case name
            metadata: Additional metric metadata
        """
        event = ResourceMetricEvent(
            resource_type=resource_type,
            usage_value=usage_value,
            component=component,
            test_case=test_case,
            metadata=metadata,
        )
        self.event_manager.notify(event)

    def emit_timing_metric(
        self,
        operation_name: str,
        duration: float,
        phase: Optional[str] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a timing metric event.

        Args:
            operation_name: Name of the operation being timed
            duration: Duration in seconds
            phase: Experiment phase
            test_case: Related test case name
            component: Component being timed
            metadata: Additional metric metadata
        """
        event = TimingMetricEvent(
            operation_name=operation_name,
            duration=duration,
            phase=phase,
            test_case=test_case,
            component=component,
            metadata=metadata,
        )
        self.event_manager.notify(event)

    def emit_counter_metric(
        self,
        counter_name: str,
        value: int,
        increment: bool = True,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a counter metric event.

        Args:
            counter_name: Name of the counter
            value: Counter value (or increment)
            increment: Whether this is an increment (True) or absolute value (False)
            test_case: Related test case name
            component: Component being counted
            metadata: Additional metric metadata
        """
        event = CounterMetricEvent(
            counter_name=counter_name,
            value=value,
            increment=increment,
            test_case=test_case,
            component=component,
            metadata=metadata,
        )
        self.event_manager.notify(event)

    def emit_metrics_summary(
        self,
        metrics: Dict[str, Any],
        test_case: Optional[str] = None,
        period: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit a metrics summary event.

        Args:
            metrics: Dictionary of metrics summaries
            test_case: Related test case name
            period: Period covered by the summary (e.g. "5m", "1h")
            metadata: Additional metadata
        """
        event = MetricsSummaryEvent(
            metrics=metrics, test_case=test_case, period=period, metadata=metadata
        )
        self.event_manager.notify(event)
