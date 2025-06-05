"""
Methods for ITesterManager to emit standardized events.
"""

from typing import Any


class TesterPluginEventMixin:
    """
    Mixin providing standardized event emission methods for tester plugins.

    This class extends ITesterManager with helper methods to emit standard events
    related to test execution.
    """

    def notify_test_started(self, test_name: str, details: dict[str, Any] = None):
        """
        Notify that a test has started using the event emitter.

        Args:
            test_name: Name of the test that started
            details: Additional details about the test
        """
        if hasattr(self, "event_emitter"):
            service_name = getattr(self, "service_name", "unknown")
            service_type = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_event(
                name="tester.test_started",
                data={
                    "service_name": service_name,
                    "service_type": service_type,
                    "test_name": test_name,
                    **(details or {}),
                },
            )

    def notify_test_completed(self, test_name: str, success: bool, results: dict[str, Any] = None):
        """
        Notify that a test has completed using the event emitter.

        Args:
            test_name: Name of the test that completed
            success: Whether the test was successful
            results: Test results and details
        """
        if hasattr(self, "event_emitter"):
            service_name = getattr(self, "service_name", "unknown")
            service_type = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_event(
                name="tester.test_completed",
                data={
                    "service_name": service_name,
                    "service_type": service_type,
                    "test_name": test_name,
                    "success": success,
                    "results": results or {},
                },
            )

    def notify_test_error(
        self, test_name: str, error_type: str, error_message: str, details: dict[str, Any] = None
    ):
        """
        Notify that a test has encountered an error using the event emitter.

        Args:
            test_name: Name of the test with an error
            error_type: Type of error encountered
            error_message: Error message
            details: Additional details about the error
        """
        if hasattr(self, "event_emitter"):
            service_name = getattr(self, "service_name", "unknown")
            service_type = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_event(
                name="tester.test_error",
                data={
                    "service_name": service_name,
                    "service_type": service_type,
                    "test_name": test_name,
                    "error_type": error_type,
                    "error_message": error_message,
                    **(details or {}),
                },
            )
