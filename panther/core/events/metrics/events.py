"""
Metrics Events

This module defines events specific to metrics collection and monitoring.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from panther.core.events.base.event_base import BaseEvent, EventType


class MetricsEventType(Enum):
    """Metrics-specific event types."""

    COLLECTED = "collected"
    RESOURCE = "resource"
    TIMING = "timing"
    COUNTER = "counter"
    SUMMARY = "summary"


class MetricsEvent(BaseEvent):
    """Base class for all metrics events."""

    def __init__(
        self,
        event_type: MetricsEventType,
        metric_id: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=event_type.value,
            entity_type=EventType.METRICS,
            entity_id=metric_id,
            data=data,
        )
        self.event_type = event_type


class MetricCollectedEvent(MetricsEvent):
    """Event emitted when a metric is collected."""

    def __init__(
        self,
        metric_name: str,
        metric_type: str,
        value: Any,
        phase: Optional[str] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
            "metric_type": metric_type,
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }

        # Add optional fields if provided
        if phase:
            data["phase"] = phase
        if test_case:
            data["test_case"] = test_case
        if component:
            data["component"] = component
        if labels:
            data["labels"] = labels
        if metadata:
            data["metadata"] = metadata

        super().__init__(
            event_type=MetricsEventType.COLLECTED,
            metric_id=f"{metric_name}_{datetime.now().timestamp()}",
            data=data,
        )

    @property
    def metric_name(self) -> str:
        return self.data.get("metric_name", "")

    @property
    def metric_type(self) -> str:
        return self.data.get("metric_type", "")

    @property
    def value(self) -> Any:
        return self.data.get("value")

    @property
    def phase(self) -> Optional[str]:
        return self.data.get("phase")

    @property
    def test_case(self) -> Optional[str]:
        return self.data.get("test_case")

    @property
    def component(self) -> Optional[str]:
        return self.data.get("component")

    @property
    def labels(self) -> Optional[Dict[str, str]]:
        return self.data.get("labels")

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self.data.get("metadata")

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
        component: Optional[str] = None,
        test_case: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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

        super().__init__(
            event_type=MetricsEventType.RESOURCE,
            metric_id=f"resource_{resource_type}_{datetime.now().timestamp()}",
            data=data,
        )

    @property
    def resource_type(self) -> str:
        return self.data.get("resource_type", "")

    @property
    def usage_value(self) -> float:
        return self.data.get("value", 0.0)

    @property
    def component(self) -> Optional[str]:
        return self.data.get("component")

    @property
    def test_case(self) -> Optional[str]:
        return self.data.get("test_case")

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self.data.get("metadata")

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return (
            "resource_type" in self.data
            and "value" in self.data
            and "timestamp" in self.data
        )


class TimingMetricEvent(MetricsEvent):
    """Event for timing metrics like operation duration."""

    def __init__(
        self,
        operation_name: str,
        duration: float,
        phase: Optional[str] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a timing metric event.

        Args:
            operation_name: Name of the operation being timed
            duration: Duration in seconds
            phase: Experiment phase
            test_case: Related test case name
            component: Component being timed
            metadata: Additional metric metadata
        """
        data = {
            "operation": operation_name,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
        }

        if phase:
            data["phase"] = phase
        if test_case:
            data["test_case"] = test_case
        if component:
            data["component"] = component
        if metadata:
            data["metadata"] = metadata

        super().__init__(
            event_type=MetricsEventType.TIMING,
            metric_id=f"timing_{operation_name}_{datetime.now().timestamp()}",
            data=data,
        )

    @property
    def operation_name(self) -> str:
        return self.data.get("operation", "")

    @property
    def duration(self) -> float:
        return self.data.get("duration", 0.0)

    @property
    def phase(self) -> Optional[str]:
        return self.data.get("phase")

    @property
    def test_case(self) -> Optional[str]:
        return self.data.get("test_case")

    @property
    def component(self) -> Optional[str]:
        return self.data.get("component")

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self.data.get("metadata")

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return (
            "operation" in self.data
            and "duration" in self.data
            and "timestamp" in self.data
        )


class CounterMetricEvent(MetricsEvent):
    """Event for counter metrics like request count."""

    def __init__(
        self,
        counter_name: str,
        value: int,
        increment: bool = True,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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

        super().__init__(
            event_type=MetricsEventType.COUNTER,
            metric_id=f"counter_{counter_name}_{datetime.now().timestamp()}",
            data=data,
        )

    @property
    def counter_name(self) -> str:
        return self.data.get("counter_name", "")

    @property
    def value(self) -> int:
        return self.data.get("value", 0)

    @property
    def increment(self) -> bool:
        return self.data.get("increment", True)

    @property
    def test_case(self) -> Optional[str]:
        return self.data.get("test_case")

    @property
    def component(self) -> Optional[str]:
        return self.data.get("component")

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self.data.get("metadata")

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
        metrics: Dict[str, Any],
        test_case: Optional[str] = None,
        period: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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

        super().__init__(
            event_type=MetricsEventType.SUMMARY,
            metric_id=f"summary_{datetime.now().timestamp()}",
            data=data,
        )

    @property
    def metrics(self) -> Dict[str, Any]:
        return self.data.get("metrics", {})

    @property
    def test_case(self) -> Optional[str]:
        return self.data.get("test_case")

    @property
    def period(self) -> Optional[str]:
        return self.data.get("period")

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self.data.get("metadata")

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return "metrics" in self.data and "timestamp" in self.data
