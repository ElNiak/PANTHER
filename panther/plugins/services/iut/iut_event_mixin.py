"""
IUT Plugin Event Mixin Module
This module provides standardized event emission methods for IUT plugins.
"""

from typing import Any, Dict, Optional

from panther.core.events.test.events import (
    TestCompletedEvent,
    TestExecutionStartedEvent,
    TestFailedEvent,
)
from panther.plugins.services.service_event_mixin import ServiceManagerEventMixin


class IUTManagerEventMixin(ServiceManagerEventMixin):
    """
    Mixin providing standardized event emission methods for IUT plugins.

    This class provides helper methods to emit standard IUT-related events.
    It should be mixed into IUT plugin classes to provide consistent event emission.
    """

    def emit_test_starting(
        self, test_id: str, test_type: str, details: Dict[str, Any] = None
    ) -> None:
        """
        Emit an event indicating that a test is starting.

        Args:
            test_id: Unique identifier for the test
            test_type: Type of test being started
            details: Additional details about the test
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            event = TestExecutionStartedEvent(
                test_id=test_id,
                steps=details.get("steps", []) if details else [],
            )
            self.event_emitter.emit_event(event)

    def emit_test_completed(
        self,
        test_id: str,
        success: bool,
        result: Dict[str, Any] = None,
        error_message: Optional[str] = None,
        details: Dict[str, Any] = None,
    ) -> None:
        """
        Emit an event indicating that a test has completed.

        Args:
            test_id: Unique identifier for the test
            success: Whether the test completed successfully
            result: Test result data
            error_message: Error message if test was unsuccessful
            details: Additional details about the test completion
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            if success:
                summary = {"result": result or {}, "details": details or {}}
                event = TestCompletedEvent(
                    test_id=test_id,
                    summary=summary,
                )
            else:
                event = TestFailedEvent(
                    test_id=test_id,
                    error_message=error_message or "Test failed",
                    summary={"result": result or {}, "details": details or {}},
                )
            self.event_emitter.emit_event(event)

    def handle_event(self, event):
        return super().handle_event(event)
