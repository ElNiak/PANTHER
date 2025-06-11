"""
Service Events Module

This module provides event classes, state management, and event emission for service lifecycle.
"""

from panther.core.events.service.events import (
    ServiceEvent,
    ServiceCreatedEvent,
    ServicePreparationStartedEvent,
    ServicePreparationCompletedEvent,
    ServicePreparationFailedEvent,
    ServiceDeploymentStartedEvent,
    ServiceDeploymentCompletedEvent,
    ServiceDeploymentFailedEvent,
    ServiceStartedEvent,
    ServiceReadyEvent,
    ServiceHealthCheckPassedEvent,
    ServiceHealthCheckFailedEvent,
    ServiceStoppedEvent,
    ServiceErrorEvent,
    ServiceDestroyedEvent,
)

from panther.core.events.service.states import (
    ServiceState,
    ServiceStateManager,
)

from panther.core.events.service.emitter import (
    ServiceEventEmitter,
)

__all__ = [
    # Events
    "ServiceEvent",
    "ServiceCreatedEvent",
    "ServicePreparationStartedEvent",
    "ServicePreparationCompletedEvent",
    "ServicePreparationFailedEvent",
    "ServiceDeploymentStartedEvent",
    "ServiceDeploymentCompletedEvent",
    "ServiceDeploymentFailedEvent",
    "ServiceStartedEvent",
    "ServiceReadyEvent",
    "ServiceHealthCheckPassedEvent",
    "ServiceHealthCheckFailedEvent",
    "ServiceStoppedEvent",
    "ServiceErrorEvent",
    "ServiceDestroyedEvent",
    # States
    "ServiceState",
    "ServiceStateManager",
    # Emitter
    "ServiceEventEmitter",
]
