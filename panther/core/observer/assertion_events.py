"""
Assertion Event Types Module

This module defines event types related to assertion validation and results
to integrate the assertion system with the event infrastructure.
"""

from typing import Any

from panther.core.observer.core.core_events import Event


class AssertionEvent(Event):
    """
    Assertion-related events like validation start, progress, results, etc.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new AssertionEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"assertion.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for AssertionEvents has the 'assertion.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name

    def validate(self) -> bool:
        """
        Validate assertion event data.

        Returns:
            bool: True if the event data is valid
        """
        return True


class AssertionsValidationStartedEvent(AssertionEvent):
    """
    Event triggered when assertion validation begins.
    """

    def __init__(self, test_name: str, assertion_count: int = 0, data: dict[str, Any] = None):
        """
        Initialize an assertions validation started event.

        Args:
            test_name: Name of the test being validated
            assertion_count: Number of assertions to validate
            data: Additional event data
        """
        event_data = data or {}
        event_data["test_name"] = test_name
        event_data["assertion_count"] = assertion_count
        super().__init__("validation_started", event_data)

    def validate(self) -> bool:
        """Validate that test_name is present."""
        return "test_name" in self.data and bool(self.data["test_name"])


class AssertionProgressEvent(AssertionEvent):
    """
    Event triggered to report progress during assertion validation.
    """

    def __init__(
        self,
        test_name: str,
        current_assertion: int,
        total_assertions: int,
        data: dict[str, Any] = None,
    ):
        """
        Initialize an assertion progress event.

        Args:
            test_name: Name of the test being validated
            current_assertion: Current assertion being processed
            total_assertions: Total number of assertions
            data: Additional event data
        """
        event_data = data or {}
        event_data["test_name"] = test_name
        event_data["current_assertion"] = current_assertion
        event_data["total_assertions"] = total_assertions
        event_data["progress_percentage"] = (
            (current_assertion / total_assertions) * 100 if total_assertions > 0 else 0
        )
        super().__init__("progress", event_data)

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return (
            "test_name" in self.data
            and bool(self.data["test_name"])
            and "current_assertion" in self.data
            and "total_assertions" in self.data
        )


class AssertionResultEvent(AssertionEvent):
    """
    Event triggered when an individual assertion result is available.
    """

    def __init__(
        self, assertion_name: str, result: bool, message: str = "", data: dict[str, Any] = None
    ):
        """
        Initialize an assertion result event.

        Args:
            assertion_name: Name of the assertion
            result: True if assertion passed, False if failed
            message: Optional message describing the result
            data: Additional event data
        """
        event_data = data or {}
        event_data["assertion_name"] = assertion_name
        event_data["result"] = result
        event_data["message"] = message
        super().__init__("result", event_data)

    def validate(self) -> bool:
        """Validate that assertion_name and result are present."""
        return (
            "assertion_name" in self.data
            and bool(self.data["assertion_name"])
            and "result" in self.data
            and isinstance(self.data["result"], bool)
        )


class AssertionUnknownEvent(AssertionEvent):
    """
    Event triggered when an assertion type is unknown or unsupported.
    """

    def __init__(
        self, assertion_name: str, assertion_type: str, reason: str, data: dict[str, Any] = None
    ):
        """
        Initialize an assertion unknown event.

        Args:
            assertion_name: Name of the unknown assertion
            assertion_type: Type of assertion that is unknown
            reason: Reason why the assertion is unknown
            data: Additional event data
        """
        event_data = data or {}
        event_data["assertion_name"] = assertion_name
        event_data["assertion_type"] = assertion_type
        event_data["reason"] = reason
        super().__init__("unknown", event_data)

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return (
            "assertion_name" in self.data
            and bool(self.data["assertion_name"])
            and "assertion_type" in self.data
            and bool(self.data["assertion_type"])
            and "reason" in self.data
            and bool(self.data["reason"])
        )


class AssertionErrorEvent(AssertionEvent):
    """
    Event triggered when an error occurs during assertion processing.
    """

    def __init__(self, assertion_name: str, error: str, data: dict[str, Any] = None):
        """
        Initialize an assertion error event.

        Args:
            assertion_name: Name of the assertion that caused the error
            error: Error message or description
            data: Additional event data
        """
        event_data = data or {}
        event_data["assertion_name"] = assertion_name
        event_data["error"] = error
        super().__init__("error", event_data)

    def validate(self) -> bool:
        """Validate that assertion_name and error are present."""
        return (
            "assertion_name" in self.data
            and bool(self.data["assertion_name"])
            and "error" in self.data
            and bool(self.data["error"])
        )


class AssertionsValidationCompletedEvent(AssertionEvent):
    """
    Event triggered when assertion validation completes.
    """

    def __init__(
        self,
        test_name: str,
        passed_count: int,
        failed_count: int,
        total_count: int,
        data: dict[str, Any] = None,
    ):
        """
        Initialize an assertions validation completed event.

        Args:
            test_name: Name of the test that was validated
            passed_count: Number of assertions that passed
            failed_count: Number of assertions that failed
            total_count: Total number of assertions processed
            data: Additional event data
        """
        event_data = data or {}
        event_data["test_name"] = test_name
        event_data["passed_count"] = passed_count
        event_data["failed_count"] = failed_count
        event_data["total_count"] = total_count
        event_data["success_rate"] = (passed_count / total_count) * 100 if total_count > 0 else 0
        super().__init__("validation_completed", event_data)

    def validate(self) -> bool:
        """Validate that required fields are present."""
        return (
            "test_name" in self.data
            and bool(self.data["test_name"])
            and "passed_count" in self.data
            and "failed_count" in self.data
            and "total_count" in self.data
        )
