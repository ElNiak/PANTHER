"""Test state management.

This module defines state management for test case lifecycle.
"""

from panther.core.events.base.state_base import BaseState, StateManager


class TestState(BaseState):
    """Test case lifecycle states."""

    # Initial states
    CREATED = "created"
    SETTING_UP = "setting_up"

    # Setup phases
    SETTING_UP_SERVICES = "setting_up_services"
    SERVICES_SETUP = "services_setup"
    SETTING_UP_ENVIRONMENT = "setting_up_environment"
    ENVIRONMENT_SETUP = "environment_setup"

    # Deployment phase
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"

    # Execution phases
    EXECUTING = "executing"
    EXECUTING_STEPS = "executing_steps"
    VALIDATING_ASSERTIONS = "validating_assertions"

    # Cleanup phase
    TEARING_DOWN = "tearing_down"

    # Completion states
    COMPLETED = "completed"
    FAILED = "failed"


class TestStateManager(StateManager):
    """State manager for test case lifecycle."""

    def __init__(self, test_id: str):
        """Initialize with the given test ID."""
        super().__init__(test_id, TestState.CREATED)
        self.setup_transitions()

    def _define_allowed_transitions(self):
        """Define allowed state transitions for test cases."""
        return {
            TestState.CREATED: {TestState.SETTING_UP, TestState.FAILED},
            TestState.SETTING_UP: {TestState.SETTING_UP_SERVICES, TestState.FAILED},
            TestState.SETTING_UP_SERVICES: {TestState.SERVICES_SETUP, TestState.FAILED},
            TestState.SERVICES_SETUP: {
                TestState.SETTING_UP_ENVIRONMENT,
                TestState.FAILED,
            },
            TestState.SETTING_UP_ENVIRONMENT: {
                TestState.ENVIRONMENT_SETUP,
                TestState.FAILED,
            },
            TestState.ENVIRONMENT_SETUP: {TestState.DEPLOYING, TestState.FAILED},
            TestState.DEPLOYING: {TestState.DEPLOYED, TestState.FAILED},
            TestState.DEPLOYED: {TestState.EXECUTING, TestState.FAILED},
            TestState.EXECUTING: {TestState.EXECUTING_STEPS, TestState.FAILED},
            TestState.EXECUTING_STEPS: {
                TestState.VALIDATING_ASSERTIONS,
                TestState.TEARING_DOWN,  # Can skip assertions
                TestState.FAILED,
            },
            TestState.VALIDATING_ASSERTIONS: {TestState.TEARING_DOWN, TestState.FAILED},
            TestState.TEARING_DOWN: {TestState.COMPLETED, TestState.FAILED},
            # Terminal states (no transitions out)
            TestState.COMPLETED: set(),
            TestState.FAILED: set(),
        }
