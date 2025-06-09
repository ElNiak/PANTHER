"""
Events Module

This module defines core event classes used in the PANTHER framework's observer system.
It centralizes all event types from various modules for easier import and usage.
"""

# Core events (base Event class and core event types)
from panther.core.observer.core.core_events import (
    # Base event class
    Event,
    # Core event categories
    TestEvent,
    NetworkEvent,
    ServiceEvent,
    EnvironmentEvent,
    StepEvent,
    ExperimentEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
    ServiceErrorEvent,
    # Test-related events
    TestStartedEvent,
    TestCompletedEvent,
    TestCaseInitializedEvent,
    TestExecutionStartedEvent,
    TestExecutionCompletedEvent,
    TestExecutionFailedEvent,
    # Environment-related events
    EnvironmentSetupStartedEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentTeardownEvent,
    # Step-related events
    StepProgressEvent,
    StepCompletedEvent,
    # Experiment-related events
    ExperimentInitializedEvent,
    ExperimentFinishedEvent,
    ExperimentFinishedEarlyEvent,
)

# Metrics-related events
from panther.core.observer.metrics.metrics_events import (
    SystemEvent,
    MetricCollectedEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
    CounterMetricEvent,
    MetricsSummaryEvent,
)

# Service-related events
from panther.core.observer.service_events import (
    ServiceSetupStartedEvent,
    ServiceSetupCompletedEvent,
    ServiceSetupFailedEvent,
    ServiceDeploymentEvent,
    ServiceDeploymentFailedEvent,
)

# Environment-related events
from panther.core.observer.environment_events import (
    EnvironmentInitializedEvent,
    EnvironmentSetupFailedEvent,
)

# Step execution events
from panther.core.observer.step_events import (
    StepExecutionStartedEvent,
    StepExecutionCompletedEvent,
    StepUnsupportedEvent,
)

# Assertion events
from panther.core.observer.assertion_events import (
    AssertionEvent,
    AssertionsValidationStartedEvent,
    AssertionProgressEvent,
    AssertionResultEvent,
    AssertionUnknownEvent,
    AssertionErrorEvent,
    AssertionsValidationCompletedEvent,
)


# Define a comprehensive list of all event types for easier access
__all__ = [
    # Base event class
    "Event",
    # Core event categories
    "TestEvent",
    "NetworkEvent",
    "ServiceEvent",
    "EnvironmentEvent",
    "StepEvent",
    "ExperimentEvent",
    "SystemEvent",
    # Test-related events
    "TestStartedEvent",
    "TestCompletedEvent",
    "TestCaseInitializedEvent",
    "TestExecutionStartedEvent",
    "TestExecutionCompletedEvent",
    "TestExecutionFailedEvent",
    # Service-related events
    "ServiceStartedEvent",
    "ServiceStoppedEvent",
    "ServiceErrorEvent",
    "ServiceSetupStartedEvent",
    "ServiceSetupCompletedEvent",
    "ServiceSetupFailedEvent",
    "ServiceDeploymentEvent",
    "ServiceDeploymentFailedEvent",
    # Environment-related events
    "EnvironmentSetupStartedEvent",
    "EnvironmentSetupCompletedEvent",
    "EnvironmentTeardownEvent",
    "EnvironmentInitializedEvent",
    "EnvironmentSetupFailedEvent",
    # Step-related events
    "StepProgressEvent",
    "StepCompletedEvent",
    "StepExecutionStartedEvent",
    "StepExecutionCompletedEvent",
    "StepUnsupportedEvent",
    # Assertion events
    "AssertionEvent",
    "AssertionsValidationStartedEvent",
    "AssertionProgressEvent",
    "AssertionResultEvent",
    "AssertionUnknownEvent",
    "AssertionErrorEvent",
    "AssertionsValidationCompletedEvent",
    # Plugin-related events
    "PluginEvent",
    "PluginServiceEvent",
    "ServiceStartingEvent",
    "ServiceReadyEvent",
    "ServiceStoppingEvent",
    "PluginServiceStoppedEvent",
    "ServiceRequestEvent",
    "PluginEnvironmentEvent",
    "EnvironmentResourceEvent",
    "EnvironmentResourceAllocatedEvent",
    "EnvironmentResourceReleasedEvent",
    "TesterEvent",
    "TestStartingEvent",
    "PluginTestCompletedEvent",
    # Experiment-related events
    "ExperimentInitializedEvent",
    "ExperimentFinishedEvent",
    "ExperimentFinishedEarlyEvent",
    # Metrics-related events
    "MetricCollectedEvent",
    "ResourceMetricEvent",
    "TimingMetricEvent",
    "CounterMetricEvent",
    "MetricsSummaryEvent",
]
