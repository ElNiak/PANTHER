"""
Environment Plugin Event Mixin Module

This module provides standardized event emission methods for environment plugins.
"""

from typing import Any

from panther.core.events.environment.events import (
    EnvironmentEvent,
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
        if hasattr(self, "event_emitter") and self.event_emitter:
            data = {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "resource_details": resource_details or {},
                **(details or {}),
            }
            event = EnvironmentEvent(
                name="resource_allocated",
                environment_id=environment_id,
                environment_name=environment_id,  # Use environment_id as name
                environment_type=getattr(self, "_get_environment_type", lambda: "unknown")(),
                data=data,
            )
            self.event_emitter.emit_event(event)

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
        if hasattr(self, "event_emitter") and self.event_emitter:
            data = {
                "resource_id": resource_id,
                "resource_type": resource_type,
                "success": success,
                "error_message": error_message,
                **(details or {}),
            }
            event = EnvironmentEvent(
                name="resource_released",
                environment_id=environment_id,
                environment_name=environment_id,  # Use environment_id as name
                environment_type=getattr(self, "_get_environment_type", lambda: "unknown")(),
                data=data,
            )
            self.event_emitter.emit_event(event)
