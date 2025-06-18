from typing import TYPE_CHECKING, Any, Dict, List, Optional

"""
Assertion Event Emitter

This module provides a type-safe event emitter for assertion-related events.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.assertion.events import (
    AssertionErrorEvent,
    AssertionProgressEvent,
    AssertionResultEvent,
    AssertionsValidationCompletedEvent,
    AssertionsValidationStartedEvent,
    AssertionUnknownEvent,
)


class AssertionEventEmitter:
    """, TYPE_CHECKING
    Type-safe event emitter for assertion-related events.

    This class provides methods for emitting all assertion validation events
    with proper typing and validation.
    """

    def __init__(self, event_manager: "EventManager"):
        """
        Initialize the assertion event emitter.

        Args:
            event_manager: Event manager to use for event emission
        """
        self.event_manager = event_manager

    def emit_assertions_validation_started(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        total_assertions: Optional[int] = None,
        validation_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit an assertions validation started event.

        Args:
            assertion_id: Unique assertion identifier
            assertion_name: Human-readable assertion name
            test_case_id: ID of the test case this assertion belongs to
            step_id: ID of the step this assertion belongs to
            total_assertions: Total number of assertions to be validated
            validation_config: Configuration for the validation process
        """
        event = AssertionsValidationStartedEvent(
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            total_assertions=total_assertions,
            validation_config=validation_config,
        )
        self.event_manager.notify(event)

    def emit_assertions_validation_completed(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        duration: Optional[float] = None,
        passed_count: int = 0,
        failed_count: int = 0,
        total_count: int = 0,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit an assertions validation completed event.

        Args:
            assertion_id: Unique assertion identifier
            assertion_name: Human-readable assertion name
            test_case_id: ID of the test case this assertion belongs to
            step_id: ID of the step this assertion belongs to
            duration: Validation duration in seconds
            passed_count: Number of assertions that passed
            failed_count: Number of assertions that failed
            total_count: Total number of assertions processed
            summary: Summary of validation results
        """
        event = AssertionsValidationCompletedEvent(
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            duration=duration,
            passed_count=passed_count,
            failed_count=failed_count,
            total_count=total_count,
            summary=summary,
        )
        self.event_manager.notify(event)

    def emit_assertion_progress(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        current_assertion: Optional[int] = None,
        total_assertions: Optional[int] = None,
        progress_message: str = "",
    ) -> None:
        """
        Emit an assertion progress event.

        Args:
            assertion_id: Unique assertion identifier
            assertion_name: Human-readable assertion name
            test_case_id: ID of the test case this assertion belongs to
            step_id: ID of the step this assertion belongs to
            current_assertion: Index of current assertion being processed
            total_assertions: Total number of assertions
            progress_message: Human-readable progress message
        """
        event = AssertionProgressEvent(
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            current_assertion=current_assertion,
            total_assertions=total_assertions,
            progress_message=progress_message,
        )
        self.event_manager.notify(event)

    def emit_assertion_result(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        assertion_passed: bool = False,
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None,
        assertion_message: str = "",
        assertion_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit an assertion result event.

        Args:
            assertion_id: Unique assertion identifier
            assertion_name: Human-readable assertion name
            test_case_id: ID of the test case this assertion belongs to
            step_id: ID of the step this assertion belongs to
            assertion_passed: Whether the assertion passed
            expected_value: Expected value for the assertion
            actual_value: Actual value encountered
            assertion_message: Human-readable assertion message
            assertion_details: Additional assertion details
        """
        event = AssertionResultEvent(
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            assertion_passed=assertion_passed,
            expected_value=expected_value,
            actual_value=actual_value,
            assertion_message=assertion_message,
            assertion_details=assertion_details,
        )
        self.event_manager.notify(event)

    def emit_assertion_error(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        error_message: str = "",
        error_type: str = "unknown",
        error_details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
    ) -> None:
        """
        Emit an assertion error event.

        Args:
            assertion_id: Unique assertion identifier
            assertion_name: Human-readable assertion name
            test_case_id: ID of the test case this assertion belongs to
            step_id: ID of the step this assertion belongs to
            error_message: Error message describing the issue
            error_type: Type/category of error
            error_details: Additional error details
            recoverable: Whether the error is recoverable
        """
        event = AssertionErrorEvent(
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            error_message=error_message,
            error_type=error_type,
            error_details=error_details,
            recoverable=recoverable,
        )
        self.event_manager.notify(event)

    def emit_assertion_unknown(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        reason: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit an assertion unknown event.

        Args:
            assertion_id: Unique assertion identifier
            assertion_name: Human-readable assertion name
            test_case_id: ID of the test case this assertion belongs to
            step_id: ID of the step this assertion belongs to
            reason: Reason why the result is unknown
            context: Additional context information
        """
        event = AssertionUnknownEvent(
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            reason=reason,
            context=context,
        )
        self.event_manager.notify(event)
