"""
Experiment State Management

This module defines state management for experiment lifecycle.
"""

from panther.core.events.base.state_base import BaseState, StateManager


class ExperimentState(BaseState):
    """Experiment lifecycle states."""

    # Initial states
    CREATED = "created"
    INITIALIZING = "initializing"

    # Plugin loading phase
    LOADING_PLUGINS = "loading_plugins"
    PLUGINS_LOADED = "plugins_loaded"

    # Test case setup phase
    INITIALIZING_TESTS = "initializing_tests"
    TESTS_INITIALIZED = "tests_initialized"

    # Execution phase
    RUNNING = "running"

    # Completion states
    COLLECTING_RESULTS = "collecting_results"
    COMPLETED = "completed"

    # Error states
    FAILED = "failed"
    FINISHED_EARLY = "finished_early"


class ExperimentStateManager(StateManager):
    """State manager for experiment lifecycle."""

    def __init__(self, experiment_id: str):
        super().__init__(experiment_id, ExperimentState.CREATED)
        self.setup_transitions()

    def _define_allowed_transitions(self) -> dict[BaseState, set[BaseState]]:
        """Define allowed state transitions for experiments."""
        return {
            ExperimentState.CREATED: {ExperimentState.INITIALIZING, ExperimentState.FAILED},
            ExperimentState.INITIALIZING: {
                ExperimentState.LOADING_PLUGINS,
                ExperimentState.FAILED,
                ExperimentState.FINISHED_EARLY,
            },
            ExperimentState.LOADING_PLUGINS: {
                ExperimentState.PLUGINS_LOADED,
                ExperimentState.FAILED,
                ExperimentState.FINISHED_EARLY,
            },
            ExperimentState.PLUGINS_LOADED: {
                ExperimentState.INITIALIZING_TESTS,
                ExperimentState.FAILED,
                ExperimentState.FINISHED_EARLY,
            },
            ExperimentState.INITIALIZING_TESTS: {
                ExperimentState.TESTS_INITIALIZED,
                ExperimentState.FAILED,
                ExperimentState.FINISHED_EARLY,
            },
            ExperimentState.TESTS_INITIALIZED: {
                ExperimentState.RUNNING,
                ExperimentState.FAILED,
                ExperimentState.FINISHED_EARLY,
            },
            ExperimentState.RUNNING: {
                ExperimentState.COLLECTING_RESULTS,
                ExperimentState.FAILED,
                ExperimentState.FINISHED_EARLY,
            },
            ExperimentState.COLLECTING_RESULTS: {ExperimentState.COMPLETED, ExperimentState.FAILED},
            # Terminal states (no transitions out)
            ExperimentState.COMPLETED: set(),
            ExperimentState.FAILED: set(),
            ExperimentState.FINISHED_EARLY: set(),
        }

    def is_running(self) -> bool:
        """Check if experiment is currently running."""
        return self.is_in_state(ExperimentState.RUNNING)

    def is_finished(self) -> bool:
        """Check if experiment has finished (completed, failed, or early)."""
        return self.is_in_any_state(
            {ExperimentState.COMPLETED, ExperimentState.FAILED, ExperimentState.FINISHED_EARLY}
        )

    def is_successful(self) -> bool:
        """Check if experiment completed successfully."""
        return self.is_in_state(ExperimentState.COMPLETED)

    def can_start_execution(self) -> bool:
        """Check if experiment can start execution."""
        return self.is_in_state(ExperimentState.TESTS_INITIALIZED)

    def can_initialize(self) -> bool:
        """Check if experiment can be initialized."""
        return self.is_in_state(ExperimentState.CREATED)
