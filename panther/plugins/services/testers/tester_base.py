"""
Base tester implementation with standardized event handling.
"""

from panther.plugins.services.service_base import ServiceBase
from panther.plugins.services.testers.tester_event_methods import TesterPluginEventMixin


class BaseTesterManager(ServiceBase, TesterPluginEventMixin):
    """
    Base implementation for tester managers with tester-specific event notifications.

    This class extends the ServiceBase to provide specialized functionality for test runners,
    including standardized event notifications for test starts, completions, and failures.

    Attributes:
        All attributes from ServiceBase, plus:
        test_to_compile (str): The name of the test being compiled and run.
        test_results (Dict): Results from the most recent test run.
    """

    def run_tests(self):
        """
        Run tests with proper event notifications.

        Returns:
            Dict: Test results
        """
        try:
            # Notify test run started
            test_name = getattr(self, "test_to_compile", "unknown")
            self.notify_test_started(
                test_name=test_name,
                details={
                    "service_name": self.service_name,
                    "service_type": self.service_type,
                },
            )

            # Run the tests
            results = self._do_run_tests()

            # Notify test run completed
            self.notify_test_completed(
                test_name=test_name, success=results.get("success", False), results=results
            )

            return results
        except Exception as e:  # pylint: disable=broad-except
            # Notify test run failed
            self.notify_test_completed(
                test_name=getattr(self, "test_to_compile", "unknown"),
                success=False,
                results={"error": str(e), "error_type": type(e).__name__},
            )
            raise

    def _do_run_tests(self):
        """
        Actual implementation of test running, to be overridden by subclasses.

        Returns:
            Dict: Test results containing at minimum a 'success' key with boolean value

        Raises:
            NotImplementedError: If the subclass does not implement this method
        """
        raise NotImplementedError("Subclasses must implement _do_run_tests")

    def notify_tester_event(self, event_name: str, details: dict = None):
        """
        Notify of a generic tester event.

        Args:
            event_name: The name of the event
            details: Additional details about the event
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            self.event_emitter.emit_event(f"tester.{event_name}", details or {})
