"""
Tester Plugin Event Mixin Module

This module provides standardized event emission methods for tester plugins.
"""

from typing import Any

from panther.core.observer.plugin.plugin_events import (
    TestStartingEvent,
    PluginTestCompletedEvent,
)


class TesterPluginEventMixin:
    """
    Mixin providing standardized event emission methods for tester plugins.

    This class provides helper methods to emit standard tester-related events.
    It should be mixed into tester plugin classes to provide consistent event emission.
    """

    def emit_test_starting(
        self, test_id: str, test_type: str, details: dict[str, Any] = None
    ) -> None:
        """
        Emit an event indicating that a test is starting.

        Args:
            test_id: Unique identifier for the test
            test_type: Type of test being started
            details: Additional details about the test
        """
        if hasattr(self, "plugin_id") and hasattr(self, "plugin_registry"):
            event = TestStartingEvent(
                test_id=test_id,
                source_plugin_id=self.plugin_id,
                test_type=test_type,
                data=details or {},
            )
            self.plugin_registry.dispatch_event(event)

    def emit_test_completed(
        self,
        test_id: str,
        success: bool,
        result: dict[str, Any] = None,
        error_message: str | None = None,
        details: dict[str, Any] = None,
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
        if hasattr(self, "plugin_id") and hasattr(self, "plugin_registry"):
            event = PluginTestCompletedEvent(
                test_id=test_id,
                source_plugin_id=self.plugin_id,
                success=success,
                result=result or {},
                error_message=error_message,
                data=details or {},
            )
            self.plugin_registry.dispatch_event(event)
