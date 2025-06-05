"""
Metrics Event Types Module

This module defines event types related to system and application metrics
to integrate the metrics collection system with the event infrastructure.
"""

from datetime import datetime
from typing import Any

from panther.core.observer.core.core_events import Event
from panther.core.metrics.metrics_collector import MetricType, Phase


class SystemEvent(Event):
    """
    System-level events like startup, shutdown, configuration changes.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new SystemEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"system.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for SystemEvents has the 'system.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name


class MetricsEvent(SystemEvent):
    """Base class for metrics-related events."""

    def __init__(self, name: str, data: dict[str, Any] = None):
        """Initialize a metrics event."""
        super().__init__(f"metrics.{name}", data or {})

    def get_type(self) -> str:
        """Get the event type with metrics prefix."""
        return self.name

    def validate(self) -> bool:
        """Validate metrics event data."""
        return True


class MetricCollectedEvent(MetricsEvent):
    """Event emitted when a metric is collected."""

    def __init__(
        self,
        metric_name: str,
        metric_type: MetricType,
        value: Any,
        phase: Phase | None = None,
        test_case: str | None = None,
        component: str | None = None,
        labels: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a metric collected event.

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
        data = {
            "metric_name": metric_name,
            "metric_type": (
                metric_type.value if isinstance(metric_type, MetricType) else metric_type
            ),
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }

        # Add optional fields if provided
        if phase:
            data["phase"] = phase.value
        if test_case:
            data["test_case"] = test_case
        if component:
            data["component"] = component
        if labels:
            data["labels"] = labels
        if metadata:
            data["metadata"] = metadata

        super().__init__("collected", data)

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return (
            "metric_name" in self.data
            and "metric_type" in self.data
            and "value" in self.data
            and "timestamp" in self.data
        )


class ResourceMetricEvent(MetricsEvent):
    """Event for resource usage metrics like CPU, memory, etc."""

    def __init__(
        self,
        resource_type: str,
        usage_value: float,
        component: str | None = None,
        test_case: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a resource metric event.

        Args:
            resource_type: Type of resource (cpu, memory, etc.)
            usage_value: Resource usage value
            component: Component being monitored
            test_case: Related test case name
            metadata: Additional metric metadata
        """
        data = {
            "resource_type": resource_type,
            "value": usage_value,
            "timestamp": datetime.now().isoformat(),
        }

        if component:
            data["component"] = component
        if test_case:
            data["test_case"] = test_case
        if metadata:
            data["metadata"] = metadata

        super().__init__(f"resource.{resource_type}", data)

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return "resource_type" in self.data and "value" in self.data and "timestamp" in self.data


class TimingMetricEvent(MetricsEvent):
    """Event for timing metrics like operation duration."""

    def __init__(
        self,
        metric_name: str,
        duration: float,
        phase: Phase | None = None,
        test_case: str | None = None,
        component: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a timing metric event.

        Args:
            operation: Operation being timed
            duration: Duration in seconds
            phase: Experiment phase
            test_case: Related test case name
            component: Component being timed
            metadata: Additional metric metadata
        """
        data = {
            "operation": metric_name,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }

        if phase:
            data["phase"] = phase.value
        if test_case:
            data["test_case"] = test_case
        if component:
            data["component"] = component
        if metadata:
            data["metadata"] = metadata

        super().__init__("timing", data)

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return "operation" in self.data and "duration" in self.data and "timestamp" in self.data


class CounterMetricEvent(MetricsEvent):
    """Event for counter metrics like request count."""

    def __init__(
        self,
        counter_name: str,
        value: int,
        increment: bool = True,
        test_case: str | None = None,
        component: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a counter metric event.

        Args:
            counter_name: Name of the counter
            value: Counter value (or increment)
            increment: Whether this is an increment (True) or absolute value (False)
            test_case: Related test case name
            component: Component being counted
            metadata: Additional metric metadata
        """
        data = {
            "counter_name": counter_name,
            "value": value,
            "increment": increment,
            "timestamp": datetime.now().isoformat(),
        }

        if test_case:
            data["test_case"] = test_case
        if component:
            data["component"] = component
        if metadata:
            data["metadata"] = metadata

        super().__init__("counter", data)

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return (
            "counter_name" in self.data
            and "value" in self.data
            and "increment" in self.data
            and "timestamp" in self.data
        )


class MetricsSummaryEvent(MetricsEvent):
    """Event containing a summary of collected metrics."""

    def __init__(
        self,
        metrics: dict[str, Any],
        test_case: str | None = None,
        period: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize a metrics summary event.

        Args:
            metrics: Dictionary of metrics summaries
            test_case: Related test case name
            period: Period covered by the summary (e.g. "5m", "1h")
            metadata: Additional metadata
        """
        data = {
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }

        if test_case:
            data["test_case"] = test_case
        if period:
            data["period"] = period
        if metadata:
            data["metadata"] = metadata

        super().__init__("summary", data)

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return "metrics" in self.data and "timestamp" in self.data
