"""Assertion Events.

This module defines events specific to assertion validation and management.
Uses factory classmethods on the base AssertionEvent class instead of
individual subclasses for most event types.
"""

from enum import Enum
from typing import Any, Dict, Optional

from panther.core.events.base.event_base import BaseEvent, EventType


class AssertionEventType(Enum):
    """Assertion-specific event types."""

    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    UNKNOWN = "unknown"


class AssertionEvent(BaseEvent):
    """Base class for all assertion events."""

    def __init__(
        self,
        event_type: AssertionEventType,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize assertion event."""
        merged_data = data or {}
        merged_data.update(
            {
                "assertion_name": assertion_name,
                "test_case_id": test_case_id,
                "step_id": step_id,
            }
        )

        super().__init__(
            name=event_type.value,
            entity_type=EventType.ASSERTION,
            entity_id=assertion_id,
            data=merged_data,
        )
        self.event_type = event_type
        self.assertion_name = assertion_name
        self.test_case_id = test_case_id
        self.step_id = step_id

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def validation_started(
        cls,
        assertion_id,
        assertion_name,
        test_case_id=None,
        step_id=None,
        total_assertions=None,
        validation_config=None,
    ):
        """Create validation started event."""
        return cls(
            AssertionEventType.VALIDATION_STARTED,
            assertion_id,
            assertion_name,
            test_case_id,
            step_id,
            data={
                "total_assertions": total_assertions,
                "validation_config": validation_config or {},
                "action": "assertions_validation_started",
            },
        )

    @classmethod
    def validation_completed(
        cls,
        assertion_id,
        assertion_name,
        test_case_id=None,
        step_id=None,
        duration=None,
        passed_count=0,
        failed_count=0,
        total_count=0,
        summary=None,
    ):
        """Create validation completed event."""
        return cls(
            AssertionEventType.VALIDATION_COMPLETED,
            assertion_id,
            assertion_name,
            test_case_id,
            step_id,
            data={
                "duration": duration,
                "passed_count": passed_count,
                "failed_count": failed_count,
                "total_count": total_count,
                "summary": summary or {},
                "action": "assertions_validation_completed",
            },
        )

    @classmethod
    def progress(
        cls,
        assertion_id,
        assertion_name,
        test_case_id=None,
        step_id=None,
        current_assertion=None,
        total_assertions=None,
        progress_message="",
    ):
        """Create progress event."""
        return cls(
            AssertionEventType.PROGRESS,
            assertion_id,
            assertion_name,
            test_case_id,
            step_id,
            data={
                "current_assertion": current_assertion,
                "total_assertions": total_assertions,
                "progress_message": progress_message,
                "action": "assertion_progress",
            },
        )

    @classmethod
    def result(
        cls,
        assertion_id,
        assertion_name,
        test_case_id=None,
        step_id=None,
        assertion_passed=False,
        expected_value=None,
        actual_value=None,
        assertion_message="",
        assertion_details=None,
    ):
        """Create result event."""
        return cls(
            AssertionEventType.RESULT,
            assertion_id,
            assertion_name,
            test_case_id,
            step_id,
            data={
                "assertion_passed": assertion_passed,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "assertion_message": assertion_message,
                "assertion_details": assertion_details or {},
                "action": "assertion_result",
            },
        )

    @classmethod
    def error(
        cls,
        assertion_id,
        assertion_name,
        test_case_id=None,
        step_id=None,
        error_message="",
        error_type="unknown",
        error_details=None,
        recoverable=False,
    ):
        """Create error event."""
        return cls(
            AssertionEventType.ERROR,
            assertion_id,
            assertion_name,
            test_case_id,
            step_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "error_details": error_details or {},
                "recoverable": recoverable,
                "action": "assertion_error",
            },
        )

    @classmethod
    def unknown(
        cls,
        assertion_id,
        assertion_name,
        test_case_id=None,
        step_id=None,
        reason="",
        context=None,
    ):
        """Create unknown event."""
        return cls(
            AssertionEventType.UNKNOWN,
            assertion_id,
            assertion_name,
            test_case_id,
            step_id,
            data={
                "reason": reason,
                "context": context or {},
                "action": "assertion_unknown",
            },
        )
