"""Environment state management.

This module defines state management for environment lifecycle.
"""

from typing import Dict, Set

from panther.core.events.base.state_base import BaseState, StateManager


class EnvironmentState(BaseState):
    """Environment lifecycle states."""

    # Initial states
    CREATED = "created"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"

    # Setup states
    SETTING_UP = "setting_up"
    SETUP = "setup"

    # Ready state
    READY = "ready"

    # Teardown states
    TEARING_DOWN = "tearing_down"
    TORN_DOWN = "torn_down"

    # Cleanup states
    DESTROYING = "destroying"
    DESTROYED = "destroyed"

    # Error state
    ERROR = "error"


class EnvironmentStateManager(StateManager):
    """State manager for environment lifecycle."""

    def __init__(self, environment_id: str):
        """Initialize with the given environment ID."""
        super().__init__(environment_id, EnvironmentState.CREATED)
        self.setup_transitions()

    def _define_allowed_transitions(self) -> Dict[BaseState, Set[BaseState]]:
        """Define allowed state transitions for environments."""
        return {
            EnvironmentState.CREATED: {
                EnvironmentState.INITIALIZING,
                EnvironmentState.ERROR,
                EnvironmentState.DESTROYING,
            },
            EnvironmentState.INITIALIZING: {
                EnvironmentState.INITIALIZED,
                EnvironmentState.ERROR,
                EnvironmentState.DESTROYING,
            },
            EnvironmentState.INITIALIZED: {
                EnvironmentState.SETTING_UP,
                EnvironmentState.ERROR,
                EnvironmentState.DESTROYING,
            },
            EnvironmentState.SETTING_UP: {
                EnvironmentState.SETUP,
                EnvironmentState.ERROR,
                EnvironmentState.TEARING_DOWN,
            },
            EnvironmentState.SETUP: {
                EnvironmentState.READY,
                EnvironmentState.ERROR,
                EnvironmentState.TEARING_DOWN,
            },
            EnvironmentState.READY: {
                EnvironmentState.TEARING_DOWN,
                EnvironmentState.ERROR,
            },
            EnvironmentState.TEARING_DOWN: {
                EnvironmentState.TORN_DOWN,
                EnvironmentState.ERROR,
                EnvironmentState.DESTROYING,
            },
            EnvironmentState.TORN_DOWN: {
                EnvironmentState.DESTROYING,
                EnvironmentState.ERROR,
            },
            EnvironmentState.DESTROYING: {
                EnvironmentState.DESTROYED,
                EnvironmentState.ERROR,
            },
            EnvironmentState.ERROR: {
                EnvironmentState.TEARING_DOWN,
                EnvironmentState.DESTROYING,
                EnvironmentState.READY,  # Recovery possible
            },
            EnvironmentState.DESTROYED: set(),  # Terminal state
        }
