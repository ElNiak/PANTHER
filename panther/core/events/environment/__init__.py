"""Environment Events Module.

This module provides event classes, state management, and event emission for environment lifecycle.
"""

from panther.core.events.environment.emitter import EnvironmentEventEmitter
from panther.core.events.environment.events import (  # Network Environment Events; Execution Environment Events; Output Collection Events
    EnvironmentConfigurationEvent,
    EnvironmentCreatedEvent,
    EnvironmentDeploymentCompletedEvent,
    EnvironmentDeploymentFailedEvent,
    EnvironmentDeploymentStartedEvent,
    EnvironmentDestroyedEvent,
    EnvironmentErrorEvent,
    EnvironmentEvent,
    EnvironmentInitializationCompletedEvent,
    EnvironmentInitializationFailedEvent,
    EnvironmentInitializationStartedEvent,
    EnvironmentMonitoringEvent,
    EnvironmentReadyEvent,
    EnvironmentResourceEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentSetupFailedEvent,
    EnvironmentSetupStartedEvent,
    EnvironmentTeardownCompletedEvent,
    EnvironmentTeardownFailedEvent,
    EnvironmentTeardownStartedEvent,
    ExecutionEnvironmentEvent,
    ExecutionEnvironmentLimitExceededEvent,
    ExecutionEnvironmentResourceMonitoringEvent,
    ExecutionEnvironmentSetupCompletedEvent,
    ExecutionEnvironmentSetupStartedEvent,
    NetworkEnvironmentEvent,
    NetworkSetupCompletedEvent,
    NetworkSetupFailedEvent,
    NetworkSetupStartedEvent,
    NetworkTeardownCompletedEvent,
    NetworkTeardownStartedEvent,
    OutputCollectedEvent,
    OutputCollectionCompletedEvent,
    OutputCollectionStartedEvent,
)

__all__ = [
    # Events
    "EnvironmentEvent",
    "EnvironmentCreatedEvent",
    "EnvironmentInitializationStartedEvent",
    "EnvironmentInitializationCompletedEvent",
    "EnvironmentInitializationFailedEvent",
    "EnvironmentSetupStartedEvent",
    "EnvironmentSetupCompletedEvent",
    "EnvironmentSetupFailedEvent",
    "EnvironmentReadyEvent",
    "EnvironmentTeardownStartedEvent",
    "EnvironmentTeardownCompletedEvent",
    "EnvironmentTeardownFailedEvent",
    "EnvironmentDestroyedEvent",
    "EnvironmentErrorEvent",
    "EnvironmentResourceEvent",
    "EnvironmentConfigurationEvent",
    "EnvironmentMonitoringEvent",
    # Deployment Events
    "EnvironmentDeploymentStartedEvent",
    "EnvironmentDeploymentCompletedEvent",
    "EnvironmentDeploymentFailedEvent",
    # Network Environment Events
    "NetworkEnvironmentEvent",
    "NetworkSetupStartedEvent",
    "NetworkSetupCompletedEvent",
    "NetworkSetupFailedEvent",
    "NetworkTeardownStartedEvent",
    "NetworkTeardownCompletedEvent",
    # Execution Environment Events
    "ExecutionEnvironmentEvent",
    "ExecutionEnvironmentSetupStartedEvent",
    "ExecutionEnvironmentSetupCompletedEvent",
    "ExecutionEnvironmentResourceMonitoringEvent",
    "ExecutionEnvironmentLimitExceededEvent",
    # Output Collection Events
    "OutputCollectionStartedEvent",
    "OutputCollectedEvent",
    "OutputCollectionCompletedEvent",
    # Emitter
    "EnvironmentEventEmitter",
]
