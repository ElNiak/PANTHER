"""
Step States

This module defines states for step execution management.
"""

from enum import Enum
from typing import Any, Dict, Optional

from panther.core.events.base.state_base import BaseState


class StepState(Enum):
    """Step execution states."""

    CREATED = "created"
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"
    RETRYING = "retrying"


class StepExecutionState(BaseState):
    """
    State for step execution process.

    Tracks the current state of step execution within a test case.
    """

    def __init__(
        self,
        entity_id: str,
        state: StepState = StepState.CREATED,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize step execution state.

        Args:
            entity_id: Identifier of the step
            state: Current step execution state
            metadata: Additional state metadata
        """
        super().__init__(entity_id=entity_id, state=state.value, metadata=metadata)
        self.step_state = state

    def is_created(self) -> bool:
        """Check if step is in created state."""
        return self.step_state == StepState.CREATED

    def is_pending(self) -> bool:
        """Check if step is pending execution."""
        return self.step_state == StepState.PENDING

    def is_executing(self) -> bool:
        """Check if step is currently executing."""
        return self.step_state == StepState.EXECUTING

    def is_completed(self) -> bool:
        """Check if step execution completed successfully."""
        return self.step_state == StepState.COMPLETED

    def is_failed(self) -> bool:
        """Check if step execution failed."""
        return self.step_state == StepState.FAILED

    def is_skipped(self) -> bool:
        """Check if step was skipped."""
        return self.step_state == StepState.SKIPPED

    def is_unsupported(self) -> bool:
        """Check if step is unsupported."""
        return self.step_state == StepState.UNSUPPORTED

    def is_retrying(self) -> bool:
        """Check if step is being retried."""
        return self.step_state == StepState.RETRYING

    def start_execution(self) -> None:
        """Start step execution."""
        if self.step_state in [StepState.CREATED, StepState.PENDING]:
            self.step_state = StepState.EXECUTING
            self.state = self.step_state.value

    def complete(self) -> None:
        """Mark step as completed."""
        if self.step_state == StepState.EXECUTING:
            self.step_state = StepState.COMPLETED
            self.state = self.step_state.value

    def fail(self) -> None:
        """Mark step as failed."""
        if self.step_state in [StepState.EXECUTING, StepState.RETRYING]:
            self.step_state = StepState.FAILED
            self.state = self.step_state.value

    def skip(self) -> None:
        """Mark step as skipped."""
        if self.step_state in [StepState.CREATED, StepState.PENDING]:
            self.step_state = StepState.SKIPPED
            self.state = self.step_state.value

    def mark_unsupported(self) -> None:
        """Mark step as unsupported."""
        self.step_state = StepState.UNSUPPORTED
        self.state = self.step_state.value

    def start_retry(self) -> None:
        """Start step retry."""
        if self.step_state == StepState.FAILED:
            self.step_state = StepState.RETRYING
            self.state = self.step_state.value
