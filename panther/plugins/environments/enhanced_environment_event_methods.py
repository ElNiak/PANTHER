"""
Environment Plugin Event Mixin Module

This module provides standardized event emission methods for environment plugins.
"""

from typing import Any

from panther.core.observer.plugin.plugin_events import (
    EnvironmentResourceAllocatedEvent,
    EnvironmentResourceReleasedEvent,
)


class EnhancedEnvironmentPluginEventMixin:
    """
    Enhanced mixin providing standardized event emission methods for environment plugins.

    This class extends the existing EnvironmentPluginEventMixin with additional
    methods focused on resource management and event-driven architecture.
    """

    def emit_environment_resource_allocated(
        self,
        environment_id: str,
        resource_id: str,
        resource_type: str,
        resource_details: dict[str, Any] = None,
        details: dict[str, Any] = None,
    ) -> None:
        """
        Emit an event indicating that an environment resource has been allocated.

        Args:
            environment_id: Unique identifier for the environment
            resource_id: Unique identifier for the allocated resource
            resource_type: Type of resource that was allocated
            resource_details: Details about the allocated resource
            details: Additional event details
        """
        if hasattr(self, "plugin_id") and hasattr(self, "plugin_registry"):
            event = EnvironmentResourceAllocatedEvent(
                environment_id=environment_id,
                resource_id=resource_id,
                resource_type=resource_type,
                source_plugin_id=self.plugin_id,
                resource_details=resource_details or {},
                data=details or {},
            )
            self.plugin_registry.dispatch_event(event)

    def emit_environment_resource_released(
        self,
        environment_id: str,
        resource_id: str,
        resource_type: str,
        success: bool = True,
        error_message: str | None = None,
        details: dict[str, Any] = None,
    ) -> None:
        """
        Emit an event indicating that an environment resource has been released.

        Args:
            environment_id: Unique identifier for the environment
            resource_id: Unique identifier for the released resource
            resource_type: Type of resource that was released
            success: Whether the resource was released successfully
            error_message: Error message if release was unsuccessful
            details: Additional event details
        """
        if hasattr(self, "plugin_id") and hasattr(self, "plugin_registry"):
            event = EnvironmentResourceReleasedEvent(
                environment_id=environment_id,
                resource_id=resource_id,
                resource_type=resource_type,
                source_plugin_id=self.plugin_id,
                success=success,
                error_message=error_message,
                data=details or {},
            )
            self.plugin_registry.dispatch_event(event)
