"""Service state management.

This module defines state management for service lifecycle.
"""

from typing import Dict, Set

from panther.core.events.base.state_base import BaseState, StateManager


class ServiceState(BaseState):
    """Service lifecycle states."""

    # Initial states
    CREATED = "created"
    PREPARING = "preparing"
    PREPARED = "prepared"

    # Deployment states
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"

    # Runtime states
    STARTING = "starting"
    RUNNING = "running"
    READY = "ready"

    # Shutdown states
    STOPPING = "stopping"
    STOPPED = "stopped"

    # Cleanup states
    DESTROYING = "destroying"
    DESTROYED = "destroyed"

    # Error state
    ERROR = "error"


class ServiceStateManager(StateManager):
    """State manager for service lifecycle."""

    def __init__(self, service_id: str):
        """Initialize with the given service ID."""
        super().__init__(service_id, ServiceState.CREATED)
        self.setup_transitions()

    def _define_allowed_transitions(self) -> Dict[BaseState, Set[BaseState]]:
        """Define allowed state transitions for services."""
        return {
            ServiceState.CREATED: {
                ServiceState.PREPARING,
                ServiceState.ERROR,
                ServiceState.DESTROYED,
            },
            ServiceState.PREPARING: {
                ServiceState.PREPARED,
                ServiceState.ERROR,
                ServiceState.DESTROYED,
            },
            ServiceState.PREPARED: {
                ServiceState.DEPLOYING,
                ServiceState.ERROR,
                ServiceState.DESTROYED,
            },
            ServiceState.DEPLOYING: {
                ServiceState.DEPLOYED,
                ServiceState.ERROR,
                ServiceState.DESTROYED,
            },
            ServiceState.DEPLOYED: {
                ServiceState.STARTING,
                ServiceState.STOPPING,
                ServiceState.ERROR,
                ServiceState.DESTROYED,
            },
            ServiceState.STARTING: {
                ServiceState.RUNNING,
                ServiceState.ERROR,
                ServiceState.STOPPING,
                ServiceState.DESTROYED,
            },
            ServiceState.RUNNING: {
                ServiceState.READY,
                ServiceState.STOPPING,
                ServiceState.ERROR,
                ServiceState.DESTROYED,
            },
            ServiceState.READY: {
                ServiceState.RUNNING,  # Can go back to running if readiness fails
                ServiceState.STOPPING,
                ServiceState.ERROR,
                ServiceState.DESTROYED,
            },
            ServiceState.STOPPING: {
                ServiceState.STOPPED,
                ServiceState.ERROR,
                ServiceState.DESTROYED,
            },
            ServiceState.STOPPED: {
                ServiceState.STARTING,  # Can restart
                ServiceState.DESTROYING,
                ServiceState.DESTROYED,
            },
            ServiceState.ERROR: {
                ServiceState.STOPPING,
                ServiceState.DESTROYING,
                ServiceState.DESTROYED,
            },
            ServiceState.DESTROYING: {ServiceState.DESTROYED},
            # Terminal state (no transitions out)
            ServiceState.DESTROYED: set(),
        }
