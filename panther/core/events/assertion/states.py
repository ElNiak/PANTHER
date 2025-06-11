"""
Assertion States

This module defines states for assertion validation management.
"""

from enum import Enum
from typing import Any

from panther.core.events.base.state_base import BaseState


class AssertionState(Enum):
    """Enumeration of assertion validation states."""

    CREATED = "created"
    PENDING = "pending"
    VALIDATING = "validating"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"


class AssertionValidationState(BaseState):
    """
    State for assertion validation process.

    Tracks the current state of assertion validation within a test case or step.
    """

    def __init__(
        self,
        entity_id: str,
        state: AssertionState = AssertionState.CREATED,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Initialize assertion validation state.

        Args:
            entity_id: Identifier of the assertion
            state: Current assertion validation state
            metadata: Additional state metadata
        """
        super().__init__(entity_id=entity_id, state=state.value, metadata=metadata)
        self.assertion_state = state

    def is_created(self) -> bool:
        """Check if assertion is in created state."""
        return self.assertion_state == AssertionState.CREATED

    def is_pending(self) -> bool:
        """Check if assertion is pending validation."""
        return self.assertion_state == AssertionState.PENDING

    def is_validating(self) -> bool:
        """Check if assertion is currently being validated."""
        return self.assertion_state == AssertionState.VALIDATING

    def is_passed(self) -> bool:
        """Check if assertion validation passed."""
        return self.assertion_state == AssertionState.PASSED

    def is_failed(self) -> bool:
        """Check if assertion validation failed."""
        return self.assertion_state == AssertionState.FAILED

    def is_error(self) -> bool:
        """Check if assertion validation encountered an error."""
        return self.assertion_state == AssertionState.ERROR

    def is_unknown(self) -> bool:
        """Check if assertion validation result is unknown."""
        return self.assertion_state == AssertionState.UNKNOWN

    def is_skipped(self) -> bool:
        """Check if assertion was skipped."""
        return self.assertion_state == AssertionState.SKIPPED

    def start_validation(self) -> None:
        """Start assertion validation."""
        if self.assertion_state in [AssertionState.CREATED, AssertionState.PENDING]:
            self.assertion_state = AssertionState.VALIDATING
            self.state = self.assertion_state.value

    def pass_assertion(self) -> None:
        """Mark assertion as passed."""
        if self.assertion_state == AssertionState.VALIDATING:
            self.assertion_state = AssertionState.PASSED
            self.state = self.assertion_state.value

    def fail_assertion(self) -> None:
        """Mark assertion as failed."""
        if self.assertion_state == AssertionState.VALIDATING:
            self.assertion_state = AssertionState.FAILED
            self.state = self.assertion_state.value

    def error_assertion(self) -> None:
        """Mark assertion as having an error."""
        if self.assertion_state == AssertionState.VALIDATING:
            self.assertion_state = AssertionState.ERROR
            self.state = self.assertion_state.value

    def unknown_assertion(self) -> None:
        """Mark assertion result as unknown."""
        if self.assertion_state == AssertionState.VALIDATING:
            self.assertion_state = AssertionState.UNKNOWN
            self.state = self.assertion_state.value

    def skip_assertion(self) -> None:
        """Mark assertion as skipped."""
        if self.assertion_state in [AssertionState.CREATED, AssertionState.PENDING]:
            self.assertion_state = AssertionState.SKIPPED
            self.state = self.assertion_state.value
