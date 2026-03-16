"""Events Module - Event-Driven Architecture for PANTHER.

Provides a comprehensive, type-safe, hierarchical event system that enables
real-time monitoring, logging, and coordination across all testing components.
"""

from panther.core.events.assertion import (
    AssertionEvent,
    AssertionEventEmitter,
    AssertionEventType,
)
from panther.core.events.base.event_base import BaseEvent, EventType
from panther.core.events.base.state_base import BaseState, StateManager
from panther.core.events.environment import (
    EnvironmentEvent,
    EnvironmentEventEmitter,
    ExecutionEnvironmentEvent,
    NetworkEnvironmentEvent,
)
from panther.core.events.experiment import (
    ExperimentEvent,
    ExperimentEventEmitter,
    ExperimentFinishedEarlyEvent,
    ExperimentServiceFailureEvent,
)
from panther.core.events.metrics import (
    CounterMetricEvent,
    MetricCollectedEvent,
    MetricsEvent,
    MetricsEventEmitter,
    MetricsSummaryEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
)
from panther.core.events.plugin import PluginEvent, PluginEventEmitter
from panther.core.events.service import (
    DockerBuildCompletedEvent,
    DockerBuildFailedEvent,
    DockerBuildStartedEvent,
    ServiceEvent,
    ServiceEventEmitter,
    ServiceState,
)
from panther.core.events.step import StepEvent, StepEventEmitter
from panther.core.events.test import (
    EnhancedResultEvent,
    TestCompletedEvent,
    TestEvent,
    TestEventEmitter,
    TestFailedEvent,
    TestResultEvent,
)

__all__ = [
    # Base classes
    "BaseEvent",
    "EventType",
    "BaseState",
    "StateManager",
    # Experiment
    "ExperimentEvent",
    "ExperimentEventEmitter",
    "ExperimentFinishedEarlyEvent",
    "ExperimentServiceFailureEvent",
    # Test
    "TestEvent",
    "TestEventEmitter",
    "TestCompletedEvent",
    "TestFailedEvent",
    "TestResultEvent",
    "EnhancedResultEvent",
    # Service
    "ServiceState",
    "ServiceEvent",
    "ServiceEventEmitter",
    "DockerBuildStartedEvent",
    "DockerBuildCompletedEvent",
    "DockerBuildFailedEvent",
    # Environment
    "EnvironmentEvent",
    "EnvironmentEventEmitter",
    "NetworkEnvironmentEvent",
    "ExecutionEnvironmentEvent",
    # Metrics
    "MetricsEvent",
    "MetricsEventEmitter",
    "MetricCollectedEvent",
    "ResourceMetricEvent",
    "TimingMetricEvent",
    "CounterMetricEvent",
    "MetricsSummaryEvent",
    # Step
    "StepEvent",
    "StepEventEmitter",
    # Assertion
    "AssertionEvent",
    "AssertionEventEmitter",
    # Plugin
    "PluginEvent",
    "PluginEventEmitter",
]
