"""Metric data structures for the PANTHER metrics system.

Provides the Metric and TimingContext dataclasses used throughout
the metrics collection and analysis pipeline.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from panther.core.metrics.enums import MetricType, Phase


@dataclass
class Metric:
    """Individual metric data point with metadata.

    Attributes:
        name: Metric identifier
        metric_type: Category of metric (timing, counter, gauge, etc.)
        value: Recorded value
        timestamp: High-precision recording time
        phase: Experiment phase context
        test_case: Test case attribution
        component: Component attribution
        labels: Additional key-value labels
        metadata: Extensible metadata storage
    """

    name: str
    metric_type: MetricType
    value: Any
    timestamp: float
    phase: Optional[Phase]
    test_case: Optional[str]
    component: Optional[str]
    labels: Dict[str, str]
    metadata: Dict[str, Any]

    def __init__(
        self,
        name: str,
        metric_type: MetricType,
        value: Any,
        timestamp: float,
        phase: Optional[Phase] = None,
        test_case: Optional[str] = None,
        component: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize metric with name, type, value, and optional context."""
        self.name = name
        self.metric_type = metric_type
        self.value = value
        self.timestamp = timestamp
        self.phase = phase
        self.test_case = test_case
        self.component = component
        self.labels = labels or {}
        self.metadata = metadata or {}


@dataclass
class TimingContext:
    """Context data for active timing operations.

    Used internally by MetricsCollector for timer lifecycle management.
    """

    name: str
    phase: Optional[Phase] = None
    test_case: Optional[str] = None
    component: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    start_time: Optional[float] = None
