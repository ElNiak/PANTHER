"""
Step Event Emitter

This module provides a type-safe event emitter for step-related events.
"""
from typing import TYPE_CHECKING, Any, Dict, List, Optional
if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.step.events import (
    StepExecutionCompletedEvent,
    StepExecutionFailedEvent,
    StepExecutionStartedEvent,
    StepProgressEvent,
    StepSkippedEvent,
    StepUnsupportedEvent,
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
        test_case_id: Optional[str] = None,
        step_config: Optional[Dict[str, Any]] = None,
        prerequisites: Optional[list] = None,
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
        test_case_id: Optional[str] = None,
        duration: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None,
        output: Optional[str] = None,
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
        test_case_id: Optional[str] = None,
        error_message: str = "",
        error_details: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
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
        test_case_id: Optional[str] = None,
        progress_percentage: Optional[float] = None,
        progress_message: str = "",
        current_operation: Optional[str] = None,
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
        test_case_id: Optional[str] = None,
        reason: str = "",
        alternative_steps: Optional[list] = None,
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
        test_case_id: Optional[str] = None,
        skip_reason: str = "",
        skip_condition: Optional[str] = None,
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
