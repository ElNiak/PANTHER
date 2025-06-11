"""
Test Event Management

This module provides test-specific events, states, and emitters.
"""

from .events import (
    TestEvent,
    TestEventType,
    TestCreatedEvent,
    TestSetupStartedEvent,
    TestSetupCompletedEvent,
    TestSetupFailedEvent,
    TestEnvironmentSetupStartedEvent,
    TestEnvironmentSetupCompletedEvent,
    TestEnvironmentSetupFailedEvent,
    TestDeploymentStartedEvent,
    TestDeploymentCompletedEvent,
    TestDeploymentFailedEvent,
    TestExecutionStartedEvent,
    TestStepStartedEvent,
    TestStepCompletedEvent,
    TestStepFailedEvent,
    TestAssertionsStartedEvent,
    TestAssertionCheckedEvent,
    TestAssertionsCompletedEvent,
    TestAssertionsFailedEvent,
    TestExecutionCompletedEvent,
    TestExecutionFailedEvent,
    TestTeardownStartedEvent,
    TestTeardownCompletedEvent,
    TestCompletedEvent,
    TestFailedEvent,
)

from .states import (
    TestState,
    TestStateManager,
)

from .emitter import TestEventEmitter

__all__ = [
    # Events
    "TestEvent",
    "TestEventType",
    "TestCreatedEvent",
    "TestSetupStartedEvent",
    "TestSetupCompletedEvent",
    "TestSetupFailedEvent",
    "TestEnvironmentSetupStartedEvent",
    "TestEnvironmentSetupCompletedEvent",
    "TestEnvironmentSetupFailedEvent",
    "TestDeploymentStartedEvent",
    "TestDeploymentCompletedEvent",
    "TestDeploymentFailedEvent",
    "TestExecutionStartedEvent",
    "TestStepStartedEvent",
    "TestStepCompletedEvent",
    "TestStepFailedEvent",
    "TestAssertionsStartedEvent",
    "TestAssertionCheckedEvent",
    "TestAssertionsCompletedEvent",
    "TestAssertionsFailedEvent",
    "TestExecutionCompletedEvent",
    "TestExecutionFailedEvent",
    "TestTeardownStartedEvent",
    "TestTeardownCompletedEvent",
    "TestCompletedEvent",
    "TestFailedEvent",
    # States
    "TestState",
    "TestStateManager",
    # Emitter
    "TestEventEmitter",
]
