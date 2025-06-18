"""
Assertion Events

This module defines events specific to assertion validation and management.
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

    @property
    def assertion_name_property(self) -> str:
        return self.data.get("assertion_name", "")

    @property
    def test_case_id_property(self) -> Optional[str]:
        return self.data.get("test_case_id")

    @property
    def step_id_property(self) -> Optional[str]:
        return self.data.get("step_id")


class AssertionsValidationStartedEvent(AssertionEvent):
    """Event emitted when assertion validation starts."""

    def __init__(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        total_assertions: Optional[int] = None,
        validation_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            event_type=AssertionEventType.VALIDATION_STARTED,
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            data={
                "total_assertions": total_assertions,
                "validation_config": validation_config or {},
                "action": "assertions_validation_started",
            },
        )

    @property
    def total_assertions(self) -> Optional[int]:
        return self.data.get("total_assertions")

    @property
    def validation_config(self) -> Dict[str, Any]:
        return self.data.get("validation_config", {})


class AssertionsValidationCompletedEvent(AssertionEvent):
    """Event emitted when assertion validation completes."""

    def __init__(
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
    ):
        super().__init__(
            event_type=AssertionEventType.VALIDATION_COMPLETED,
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            data={
                "duration": duration,
                "passed_count": passed_count,
                "failed_count": failed_count,
                "total_count": total_count,
                "summary": summary or {},
                "action": "assertions_validation_completed",
            },
        )

    @property
    def duration(self) -> Optional[float]:
        return self.data.get("duration")

    @property
    def passed_count(self) -> int:
        return self.data.get("passed_count", 0)

    @property
    def failed_count(self) -> int:
        return self.data.get("failed_count", 0)

    @property
    def total_count(self) -> int:
        return self.data.get("total_count", 0)

    @property
    def summary(self) -> Dict[str, Any]:
        return self.data.get("summary", {})


class AssertionProgressEvent(AssertionEvent):
    """Event emitted to report assertion validation progress."""

    def __init__(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        current_assertion: Optional[int] = None,
        total_assertions: Optional[int] = None,
        progress_message: str = "",
    ):
        super().__init__(
            event_type=AssertionEventType.PROGRESS,
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            data={
                "current_assertion": current_assertion,
                "total_assertions": total_assertions,
                "progress_message": progress_message,
                "action": "assertion_progress",
            },
        )

    @property
    def current_assertion(self) -> Optional[int]:
        return self.data.get("current_assertion")

    @property
    def total_assertions(self) -> Optional[int]:
        return self.data.get("total_assertions")

    @property
    def progress_message(self) -> str:
        return self.data.get("progress_message", "")

    @property
    def progress_percentage(self) -> Optional[float]:
        """Calculate progress percentage if both current and total are available."""
        current = self.current_assertion
        total = self.total_assertions
        if current is not None and total is not None and total > 0:
            return (current / total) * 100.0
        return None


class AssertionResultEvent(AssertionEvent):
    """Event emitted with assertion validation result."""

    def __init__(
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
    ):
        super().__init__(
            event_type=AssertionEventType.RESULT,
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            data={
                "assertion_passed": assertion_passed,
                "expected_value": expected_value,
                "actual_value": actual_value,
                "assertion_message": assertion_message,
                "assertion_details": assertion_details or {},
                "action": "assertion_result",
            },
        )

    @property
    def assertion_passed(self) -> bool:
        return self.data.get("assertion_passed", False)

    @property
    def expected_value(self) -> Optional[Any]:
        return self.data.get("expected_value")

    @property
    def actual_value(self) -> Optional[Any]:
        return self.data.get("actual_value")

    @property
    def assertion_message(self) -> str:
        return self.data.get("assertion_message", "")

    @property
    def assertion_details(self) -> Dict[str, Any]:
        return self.data.get("assertion_details", {})


class AssertionErrorEvent(AssertionEvent):
    """Event emitted when assertion validation encounters an error."""

    def __init__(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        error_message: str = "",
        error_type: str = "unknown",
        error_details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
    ):
        super().__init__(
            event_type=AssertionEventType.ERROR,
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "error_details": error_details or {},
                "recoverable": recoverable,
                "action": "assertion_error",
            },
        )

    @property
    def error_message(self) -> str:
        return self.data.get("error_message", "")

    @property
    def error_type(self) -> str:
        return self.data.get("error_type", "unknown")

    @property
    def error_details(self) -> Dict[str, Any]:
        return self.data.get("error_details", {})

    @property
    def recoverable(self) -> bool:
        return self.data.get("recoverable", False)


class AssertionUnknownEvent(AssertionEvent):
    """Event emitted when assertion validation result is unknown or indeterminate."""

    def __init__(
        self,
        assertion_id: str,
        assertion_name: str,
        test_case_id: Optional[str] = None,
        step_id: Optional[str] = None,
        reason: str = "",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            event_type=AssertionEventType.UNKNOWN,
            assertion_id=assertion_id,
            assertion_name=assertion_name,
            test_case_id=test_case_id,
            step_id=step_id,
            data={
                "reason": reason,
                "context": context or {},
                "action": "assertion_unknown",
            },
        )

    @property
    def reason(self) -> str:
        return self.data.get("reason", "")

    @property
    def context(self) -> Dict[str, Any]:
        return self.data.get("context", {})
