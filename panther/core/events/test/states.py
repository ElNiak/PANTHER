"""
Test State Management

This module defines state management for test case lifecycle.
"""

from typing import Dict, Set

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

    def is_setting_up(self) -> bool:
        """Check if test is in any setup phase."""
        return self.is_in_any_state(
            {
                TestState.SETTING_UP,
                TestState.SETTING_UP_SERVICES,
                TestState.SETTING_UP_ENVIRONMENT,
            }
        )

    def is_executing(self) -> bool:
        """Check if test is currently executing."""
        return self.is_in_any_state(
            {
                TestState.EXECUTING,
                TestState.EXECUTING_STEPS,
                TestState.VALIDATING_ASSERTIONS,
            }
        )

    def is_finished(self) -> bool:
        """Check if test has finished (completed or failed)."""
        return self.is_in_any_state({TestState.COMPLETED, TestState.FAILED})

    def is_successful(self) -> bool:
        """Check if test completed successfully."""
        return self.is_in_state(TestState.COMPLETED)

    def can_start_setup(self) -> bool:
        """Check if test can start setup."""
        return self.is_in_state(TestState.CREATED)

    def can_deploy(self) -> bool:
        """Check if test can start deployment."""
        return self.is_in_state(TestState.ENVIRONMENT_SETUP)

    def can_execute(self) -> bool:
        """Check if test can start execution."""
        return self.is_in_state(TestState.DEPLOYED)

    def can_teardown(self) -> bool:
        """Check if test can start teardown."""
        return self.is_in_any_state(
            {TestState.EXECUTING_STEPS, TestState.VALIDATING_ASSERTIONS}
        )
