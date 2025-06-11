"""
Step Event Emitter

This module provides a type-safe event emitter for step-related events.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from panther.core.observer.event_manager import EventManager
from panther.core.events.step.events import (
    StepExecutionStartedEvent,
    StepExecutionCompletedEvent,
    StepExecutionFailedEvent,
    StepProgressEvent,
    StepUnsupportedEvent,
    StepSkippedEvent,
)


class StepEventEmitter:
    """
    Type-safe event emitter for step-related events.

    This class provides methods for emitting all step lifecycle events
    with proper typing and validation.
    """

    def __init__(self, event_manager: "EventManager"):
        """
        Initialize the step event emitter.

        Args:
            event_manager: Event manager to use for event emission
        """
        self.event_manager = event_manager

    def emit_step_execution_started(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        step_config: dict[str, Any] | None = None,
        prerequisites: list | None = None,
    ) -> None:
        """
        Emit a step execution started event.

        Args:
            step_id: Unique step identifier
            step_name: Human-readable step name
            test_case_id: ID of the test case this step belongs to
            step_config: Step configuration details
            prerequisites: List of prerequisite steps or conditions
        """
        event = StepExecutionStartedEvent(
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            step_config=step_config,
            prerequisites=prerequisites,
        )
        self.event_manager.notify(event)

    def emit_step_execution_completed(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        duration: float | None = None,
        result: dict[str, Any] | None = None,
        output: str | None = None,
    ) -> None:
        """
        Emit a step execution completed event.

        Args:
            step_id: Unique step identifier
            step_name: Human-readable step name
            test_case_id: ID of the test case this step belongs to
            duration: Step execution duration in seconds
            result: Step execution result details
            output: Step execution output/logs
        """
        event = StepExecutionCompletedEvent(
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            duration=duration,
            result=result,
            output=output,
        )
        self.event_manager.notify(event)

    def emit_step_execution_failed(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        error_message: str = "",
        error_details: dict[str, Any] | None = None,
        duration: float | None = None,
        retry_count: int = 0,
    ) -> None:
        """
        Emit a step execution failed event.

        Args:
            step_id: Unique step identifier
            step_name: Human-readable step name
            test_case_id: ID of the test case this step belongs to
            error_message: Error message describing the failure
            error_details: Additional error details
            duration: Step execution duration before failure
            retry_count: Number of retry attempts
        """
        event = StepExecutionFailedEvent(
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            error_message=error_message,
            error_details=error_details,
            duration=duration,
            retry_count=retry_count,
        )
        self.event_manager.notify(event)

    def emit_step_progress(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        progress_percentage: float | None = None,
        progress_message: str = "",
        current_operation: str | None = None,
    ) -> None:
        """
        Emit a step progress event.

        Args:
            step_id: Unique step identifier
            step_name: Human-readable step name
            test_case_id: ID of the test case this step belongs to
            progress_percentage: Progress as percentage (0-100)
            progress_message: Human-readable progress message
            current_operation: Description of current operation
        """
        event = StepProgressEvent(
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            progress_percentage=progress_percentage,
            progress_message=progress_message,
            current_operation=current_operation,
        )
        self.event_manager.notify(event)

    def emit_step_unsupported(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        reason: str = "",
        alternative_steps: list | None = None,
    ) -> None:
        """
        Emit a step unsupported event.

        Args:
            step_id: Unique step identifier
            step_name: Human-readable step name
            test_case_id: ID of the test case this step belongs to
            reason: Reason why the step is unsupported
            alternative_steps: List of alternative steps that could be used
        """
        event = StepUnsupportedEvent(
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            reason=reason,
            alternative_steps=alternative_steps,
        )
        self.event_manager.notify(event)

    def emit_step_skipped(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        skip_reason: str = "",
        skip_condition: str | None = None,
    ) -> None:
        """
        Emit a step skipped event.

        Args:
            step_id: Unique step identifier
            step_name: Human-readable step name
            test_case_id: ID of the test case this step belongs to
            skip_reason: Reason why the step was skipped
            skip_condition: Condition that caused the step to be skipped
        """
        event = StepSkippedEvent(
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            skip_reason=skip_reason,
            skip_condition=skip_condition,
        )
        self.event_manager.notify(event)
