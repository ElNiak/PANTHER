"""
Service Plugin Event Mixin Module

This module provides standardized event emission methods for service plugins.
"""

from typing import Any

from panther.core.observer.plugin.plugin_events import (
    ServiceStartingEvent,
    ServiceReadyEvent,
    ServiceStoppingEvent,
    ServiceStoppedEvent,
)


class ServicePluginEventMixin:
    """
    Mixin providing standardized event emission methods for service plugins.

    This class provides helper methods to emit standard service-related events.
    It should be mixed into service plugin classes to provide consistent event emission.
    """

    def emit_service_starting(
        self, service_id: str, service_type: str, details: dict[str, Any] = None
    ) -> None:
        """
        Emit an event indicating that a service is starting.

        Args:
            service_id: Unique identifier for the service
            service_type: Type of service being started
            details: Additional details about the service
        """
        if hasattr(self, "plugin_id") and hasattr(self, "plugin_registry"):
            event = ServiceStartingEvent(
                service_id=service_id,
                source_plugin_id=self.plugin_id,
                service_type=service_type,
                data=details or {},
            )
            self.plugin_registry.dispatch_event(event)

    def emit_service_ready(
        self, service_id: str, service_type: str, endpoint: str, details: dict[str, Any] = None
    ) -> None:
        """
        Emit an event indicating that a service is ready to accept connections.

        Args:
            service_id: Unique identifier for the service
            service_type: Type of service
            endpoint: Service endpoint (e.g., host:port)
            details: Additional details about the service
        """
        if hasattr(self, "plugin_id") and hasattr(self, "plugin_registry"):
            event = ServiceReadyEvent(
                service_id=service_id,
                source_plugin_id=self.plugin_id,
                endpoint=endpoint,
                service_type=service_type,
                data=details or {},
            )
            self.plugin_registry.dispatch_event(event)

    def emit_service_stopping(
        self, service_id: str, reason: str = None, details: dict[str, Any] = None
    ) -> None:
        """
        Emit an event indicating that a service is about to stop.

        Args:
            service_id: Unique identifier for the service
            reason: Reason for stopping the service
            details: Additional details about the stopping
        """
        if hasattr(self, "plugin_id") and hasattr(self, "plugin_registry"):
            event = ServiceStoppingEvent(
                service_id=service_id,
                source_plugin_id=self.plugin_id,
                reason=reason,
                data=details or {},
            )
            self.plugin_registry.dispatch_event(event)

    def emit_service_stopped(
        self,
        service_id: str,
        success: bool,
        error_message: str | None = None,
        details: dict[str, Any] = None,
    ) -> None:
        """
        Emit an event indicating that a service has stopped.

        Args:
            service_id: Unique identifier for the service
            success: Whether the service stopped successfully
            error_message: Error message if stop was unsuccessful
            details: Additional details about the stopping
        """
        if hasattr(self, "plugin_id") and hasattr(self, "plugin_registry"):
            event = ServiceStoppedEvent(
                service_id=service_id,
                source_plugin_id=self.plugin_id,
                success=success,
                error_message=error_message,
                data=details or {},
            )
            self.plugin_registry.dispatch_event(event)
