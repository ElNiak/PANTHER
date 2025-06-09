"""
Methods for IServiceManager to emit standardized events.
"""

from typing import Any


class ServiceManagerEventMixin:
    """
    Mixin providing standardized event emission methods for service managers.

    This class extends IServiceManager with helper methods to emit standard events.
    It supports the event-driven architecture by providing consistent event emission patterns.
    """

    def _get_service_identifier(self):
        """
        Get a service identifier using a fallback mechanism.

        Attempts to get service name from various attributes with increasing fallbacks:
        1. self.name
        2. self.service_name
        3. self.implementation_name with prefix if available
        4. Class name as last resort

        Returns:
            str: The identified service name or a fallback identifier
        """
        if hasattr(self, "name") and self.name:
            return self.name

        if hasattr(self, "service_name") and self.service_name:
            return self.service_name

        # Check if we have implementation_name to use
        if hasattr(self, "implementation_name") and self.implementation_name:
            # If we also know the service type, use it as a prefix
            prefix = ""
            if hasattr(self, "service_type") and self.service_type:
                prefix = f"{self.service_type.lower()}_"
            return f"{prefix}{self.implementation_name}"

        # Last resort - use the class name
        return f"{self.__class__.__name__}"

    def notify_service_started(self, details: dict[str, Any] | None = None):
        """
        Notify that the service has started using the event emitter.

        Args:
            details: Additional details about the service start
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            self.event_emitter.emit_service_started(
                service_name, {"service_type": service_type, **(details or {})}
            )

            self.event_emitter.emit_service_event(
                name="service_started",
                data={
                    "service_name": service_name,
                    "service_type": service_type,
                    **(details or {}),
                },
            )

    def notify_service_stopped(self, success: bool, details: dict[str, Any] | None = None):
        """
        Notify that the service has stopped using the event emitter.

        Args:
            success: Whether the service stopped cleanly
            details: Additional details about the service stop
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            self.event_emitter.emit_service_stopped(
                service_name, success, {"service_type": service_type, **(details or {})}
            )

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
        self, error_type: str, error_message: str, details: dict[str, Any] | None = None
    ):
        """
        Notify that the service has encountered an error using the event emitter.

        Args:
            error_type: Type of error encountered
            error_message: Error message
            details: Additional details about the error
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_service_error(
                service_name,
                error_type,
                error_message,
                {"service_type": service_type, **(details or {})},
            )

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

    def notify_service_event(self, event_name: str, details: dict[str, Any] | None = None):
        """
        Notify a custom service event using the event emitter.

        Args:
            event_name: Name of the service event
            details: Additional details about the event
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            event_data = {
                "service_name": service_name,
                "service_type": service_type,
                **(details or {}),
            }
            self.event_emitter.emit_service_event(event_name, event_data)

    def notify_service_step_progress(
        self,
        step_id: str,
        progress: float,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Notify progress during a service operation step.

        Args:
            step_id: Identifier for the step
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
            details: Additional progress details
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            step_details = details or {}
            step_details["service_name"] = service_name
            step_details["service_type"] = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_step_progress(
                step_id=step_id, progress=progress, details=step_details
            )

    def notify_service_step_completed(
        self, step_id: str, success: bool, result: dict[str, Any] | None = None
    ):
        """
        Notify completion of a service operation step.

        Args:
            step_id: Identifier for the step
            success: Whether the step completed successfully
            result: Result data from the step
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            step_result = result or {}
            step_result["service_name"] = service_name
            step_result["service_type"] = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_step_completed(
                step_id=step_id, success=success, result=step_result
            )

    def notify_service_metric(
        self,
        metric_type: str,
        metric_name: str,
        value: Any,
        step_id: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """
        Notify a service-related metric value.

        Args:
            metric_type: Type of the metric
            metric_name: Name of the metric
            value: Metric value
            step_id: Optional step identifier
            details: Additional metric details
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            metric_details = details or {}
            metric_details["service_name"] = service_name
            metric_details["service_type"] = getattr(self, "service_type", "unknown")

            self.event_emitter.emit_metric(
                metric_type=metric_type,
                metric_name=metric_name,
                value=value,
                step_id=step_id,
                details=metric_details,
            )
