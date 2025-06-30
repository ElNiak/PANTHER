"""
Service State Management

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

    def is_preparing(self) -> bool:
        """Check if service is in preparation phase."""
        return self.is_in_any_state({ServiceState.PREPARING, ServiceState.PREPARED})

    def is_deploying(self) -> bool:
        """Check if service is being deployed."""
        return self.is_in_state(ServiceState.DEPLOYING)

    def is_running(self) -> bool:
        """Check if service is running (but may not be ready)."""
        return self.is_in_any_state({ServiceState.RUNNING, ServiceState.READY})

    def is_ready(self) -> bool:
        """Check if service is ready to accept requests."""
        return self.is_in_state(ServiceState.READY)

    def is_operational(self) -> bool:
        """Check if service is operational (deployed and running/ready)."""
        return self.is_in_any_state(
            {
                ServiceState.DEPLOYED,
                ServiceState.STARTING,
                ServiceState.RUNNING,
                ServiceState.READY,
            }
        )

    def is_stopped(self) -> bool:
        """Check if service is stopped."""
        return self.is_in_state(ServiceState.STOPPED)

    def is_error(self) -> bool:
        """Check if service is in error state."""
        return self.is_in_state(ServiceState.ERROR)

    def is_destroyed(self) -> bool:
        """Check if service has been destroyed."""
        return self.is_in_state(ServiceState.DESTROYED)

    def can_prepare(self) -> bool:
        """Check if service can start preparation."""
        return self.is_in_state(ServiceState.CREATED)

    def can_deploy(self) -> bool:
        """Check if service can be deployed."""
        return self.is_in_state(ServiceState.PREPARED)

    def can_start(self) -> bool:
        """Check if service can be started."""
        return self.is_in_any_state({ServiceState.DEPLOYED, ServiceState.STOPPED})

    def can_stop(self) -> bool:
        """Check if service can be stopped."""
        return self.is_in_any_state(
            {
                ServiceState.DEPLOYED,
                ServiceState.STARTING,
                ServiceState.RUNNING,
                ServiceState.READY,
                ServiceState.ERROR,
            }
        )

    def can_destroy(self) -> bool:
        """Check if service can be destroyed."""
        # Can destroy from most states except already destroyed
        return not self.is_in_state(ServiceState.DESTROYED)
