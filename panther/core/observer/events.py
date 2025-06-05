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

# Storage-related events
from panther.core.observer.storage.store_events import TestResultEvent, EnhancedResultEvent


# GUI-related events - import as needed when implemented
# from panther.core.observer.gui.gui_events import (
#     # GUI event types will be imported here when implemented
# )

# Logger-related events - import as needed when implemented
# from panther.core.observer.logger.logs_events import (
#     # Logger event types will be imported here when implemented
# )

# Plugin-related events
from panther.core.observer.plugin.plugin_events import (
    # Base plugin event
    PluginEvent,
    # Service events
    ServiceEvent as PluginServiceEvent,
    ServiceStartingEvent,
    ServiceReadyEvent,
    ServiceStoppingEvent,
    ServiceStoppedEvent as PluginServiceStoppedEvent,
    ServiceRequestEvent,
    # Environment events
    EnvironmentEvent as PluginEnvironmentEvent,
    EnvironmentResourceEvent,
    EnvironmentResourceAllocatedEvent,
    EnvironmentResourceReleasedEvent,
    # Tester events
    TesterEvent,
    TestStartingEvent,
    TestCompletedEvent as PluginTestCompletedEvent,
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
    "TestResultEvent",
    "EnhancedResultEvent",
    # Environment-related events
    "EnvironmentSetupStartedEvent",
    "EnvironmentSetupCompletedEvent",
    "EnvironmentTeardownEvent",
    # Service-related events
    "ServiceStartedEvent",
    "ServiceStoppedEvent",
    "ServiceErrorEvent",
    # Step-related events
    "StepProgressEvent",
    "StepCompletedEvent",
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
