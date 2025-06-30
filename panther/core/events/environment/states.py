"""
Environment State Management

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

    def can_initialize(self) -> bool:
        """Check if environment can be initialized."""
        return self.current_state == EnvironmentState.CREATED

    def can_setup(self) -> bool:
        """Check if environment can be set up."""
        return self.current_state == EnvironmentState.INITIALIZED

    def can_be_ready(self) -> bool:
        """Check if environment can be marked as ready."""
        return self.current_state == EnvironmentState.SETUP

    def can_teardown(self) -> bool:
        """Check if environment can be torn down."""
        return self.current_state in {
            EnvironmentState.SETUP,
            EnvironmentState.READY,
            EnvironmentState.ERROR,
        }

    def can_destroy(self) -> bool:
        """Check if environment can be destroyed."""
        return self.current_state in {
            EnvironmentState.CREATED,
            EnvironmentState.INITIALIZING,
            EnvironmentState.INITIALIZED,
            EnvironmentState.SETTING_UP,
            EnvironmentState.TORN_DOWN,
            EnvironmentState.ERROR,
        }

    def is_operational(self) -> bool:
        """Check if environment is in an operational state."""
        return self.current_state in {EnvironmentState.SETUP, EnvironmentState.READY}

    def is_terminal(self) -> bool:
        """Check if environment is in a terminal state."""
        return self.current_state in {EnvironmentState.DESTROYED}

    def is_error_state(self) -> bool:
        """Check if environment is in an error state."""
        return self.current_state == EnvironmentState.ERROR

    def get_state_description(self) -> str:
        """Get a human-readable description of the current state."""
        descriptions = {
            EnvironmentState.CREATED: "Environment has been created but not initialized",
            EnvironmentState.INITIALIZING: "Environment initialization is in progress",
            EnvironmentState.INITIALIZED: "Environment has been initialized and is ready for setup",
            EnvironmentState.SETTING_UP: "Environment setup is in progress",
            EnvironmentState.SETUP: "Environment has been set up and is ready for use",
            EnvironmentState.READY: "Environment is fully ready and operational",
            EnvironmentState.TEARING_DOWN: "Environment teardown is in progress",
            EnvironmentState.TORN_DOWN: "Environment has been torn down",
            EnvironmentState.DESTROYING: "Environment destruction is in progress",
            EnvironmentState.DESTROYED: "Environment has been completely destroyed",
            EnvironmentState.ERROR: "Environment is in an error state",
        }
        return descriptions.get(
            self.current_state, f"Unknown state: {self.current_state}"
        )

    def get_allowed_actions(self) -> Set[str]:
        """Get the set of allowed actions for the current state."""
        actions = {
            EnvironmentState.CREATED: {"initialize", "destroy"},
            EnvironmentState.INITIALIZING: {"wait_for_completion", "abort"},
            EnvironmentState.INITIALIZED: {"setup", "destroy"},
            EnvironmentState.SETTING_UP: {"wait_for_completion", "teardown"},
            EnvironmentState.SETUP: {"mark_ready", "teardown"},
            EnvironmentState.READY: {"teardown", "monitor"},
            EnvironmentState.TEARING_DOWN: {"wait_for_completion", "force_destroy"},
            EnvironmentState.TORN_DOWN: {"destroy"},
            EnvironmentState.DESTROYING: {"wait_for_completion"},
            EnvironmentState.ERROR: {"recover", "teardown", "destroy"},
            EnvironmentState.DESTROYED: set(),
        }
        return actions.get(self.current_state, set())

    def get_next_expected_states(self) -> Set[BaseState]:
        """Get the expected next states for the current state."""
        if self.current_state == EnvironmentState.CREATED:
            return {EnvironmentState.INITIALIZING}
        elif self.current_state == EnvironmentState.INITIALIZING:
            return {EnvironmentState.INITIALIZED}
        elif self.current_state == EnvironmentState.INITIALIZED:
            return {EnvironmentState.SETTING_UP}
        elif self.current_state == EnvironmentState.SETTING_UP:
            return {EnvironmentState.SETUP}
        elif self.current_state == EnvironmentState.SETUP:
            return {EnvironmentState.READY}
        elif self.current_state == EnvironmentState.READY:
            return {EnvironmentState.TEARING_DOWN}
        elif self.current_state == EnvironmentState.TEARING_DOWN:
            return {EnvironmentState.TORN_DOWN}
        elif self.current_state == EnvironmentState.TORN_DOWN:
            return {EnvironmentState.DESTROYING}
        elif self.current_state == EnvironmentState.DESTROYING:
            return {EnvironmentState.DESTROYED}
        else:
            return set()

    def get_time_in_current_state(self) -> float:
        """Get the time spent in the current state in seconds."""
        if self.state_history:
            return (self.timestamp - self.state_history[-1].timestamp).total_seconds()
        return 0.0

    def get_total_lifecycle_time(self) -> float:
        """Get the total time spent in the lifecycle so far in seconds."""
        if self.state_history:
            return (self.timestamp - self.state_history[0].timestamp).total_seconds()
        return 0.0
