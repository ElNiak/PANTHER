"""
Methods for IServiceManager to emit standardized events.
"""

from typing import Any


class ServiceManagerEventMixin:
    """
    Mixin providing standardized event emission methods for service managers.

    This class extends IServiceManager with helper methods to emit standard events.
    """

    def notify_service_started(self, details: dict[str, Any] = None):
        """
        Notify that the service has started using the event emitter.

        Args:
            details: Additional details about the service start
        """
        if hasattr(self, "event_emitter"):
            service_name = getattr(self, "service_name", "unknown")
            service_type = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_service_event(
                name="service_started",
                data={
                    "service_name": service_name,
                    "service_type": service_type,
                    **(details or {}),
                },
            )

    def notify_service_stopped(self, success: bool, details: dict[str, Any] = None):
        """
        Notify that the service has stopped using the event emitter.

        Args:
            success: Whether the service stopped cleanly
            details: Additional details about the service stop
        """
        if hasattr(self, "event_emitter"):
            service_name = getattr(self, "service_name", "unknown")
            service_type = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_service_event(
                name="service_stopped",
                data={
                    "service_name": service_name,
                    "service_type": service_type,
                    "success": success,
                    **(details or {}),
                },
            )

    def notify_service_error(
        self, error_type: str, error_message: str, details: dict[str, Any] = None
    ):
        """
        Notify that the service has encountered an error using the event emitter.

        Args:
            error_type: Type of error encountered
            error_message: Error message
            details: Additional details about the error
        """
        if hasattr(self, "event_emitter"):
            service_name = getattr(self, "service_name", "unknown")
            service_type = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_service_event(
                name="service_error",
                data={
                    "service_name": service_name,
                    "service_type": service_type,
                    "error_type": error_type,
                    "error_message": error_message,
                    **(details or {}),
                },
            )
