"""
Plugin Event Emitter

This module provides a type-safe emitter for plugin events.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EventEmitterBase
from .events import (
    PluginLoadingStartedEvent,
    PluginLoadingCompletedEvent,
    PluginLoadingFailedEvent,
    PluginInitializedEvent,
    PluginStartedEvent,
    PluginStoppedEvent,
    PluginErrorEvent,
    PluginServiceCreatedEvent,
    PluginServiceStartedEvent,
    PluginServiceStoppedEvent,
)


class PluginEventEmitter(EventEmitterBase):
    """Event emitter for plugin-related events."""

    def __init__(self, event_manager: "EventManager"):
        super().__init__(event_manager)

    def emit_plugin_loading_started(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        plugin_path: str | None = None,
        loading_config: dict[str, Any] | None = None,
    ) -> None:
        """Emit a plugin loading started event."""
        event = PluginLoadingStartedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            plugin_path=plugin_path,
            loading_config=loading_config,
        )
        self.event_manager.notify(event)

    def emit_plugin_loading_completed(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        duration: float | None = None,
        capabilities: list[str] | None = None,
        version: str | None = None,
    ) -> None:
        """Emit a plugin loading completed event."""
        event = PluginLoadingCompletedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            duration=duration,
            capabilities=capabilities,
            version=version,
        )
        self.event_manager.notify(event)

    def emit_plugin_loading_failed(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        error_message: str = "",
        error_details: dict[str, Any] | None = None,
        duration: float | None = None,
    ) -> None:
        """Emit a plugin loading failed event."""
        event = PluginLoadingFailedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            error_message=error_message,
            error_details=error_details,
            duration=duration,
        )
        self.event_manager.notify(event)

    def emit_plugin_initialized(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        initialization_config: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        """Emit a plugin initialized event."""
        event = PluginInitializedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            initialization_config=initialization_config,
            dependencies=dependencies,
        )
        self.event_manager.notify(event)

    def emit_plugin_started(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        startup_duration: float | None = None,
        startup_details: dict[str, Any] | None = None,
    ) -> None:
        """Emit a plugin started event."""
        event = PluginStartedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            startup_duration=startup_duration,
            startup_details=startup_details,
        )
        self.event_manager.notify(event)

    def emit_plugin_stopped(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        stop_reason: str = "normal_shutdown",
        cleanup_duration: float | None = None,
        cleanup_details: dict[str, Any] | None = None,
    ) -> None:
        """Emit a plugin stopped event."""
        event = PluginStoppedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            stop_reason=stop_reason,
            cleanup_duration=cleanup_duration,
            cleanup_details=cleanup_details,
        )
        self.event_manager.notify(event)

    def emit_plugin_error(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        error_message: str = "",
        error_type: str = "unknown",
        error_details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ) -> None:
        """Emit a plugin error event."""
        event = PluginErrorEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            error_message=error_message,
            error_type=error_type,
            error_details=error_details,
            recoverable=recoverable,
        )
        self.event_manager.notify(event)

    def emit_plugin_service_created(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        service_id: str,
        service_name: str,
        service_type: str,
        service_config: dict[str, Any] | None = None,
    ) -> None:
        """Emit a plugin service created event."""
        event = PluginServiceCreatedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            service_id=service_id,
            service_name=service_name,
            service_type=service_type,
            service_config=service_config,
        )
        self.event_manager.notify(event)

    def emit_plugin_service_started(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        service_id: str,
        service_name: str,
        startup_duration: float | None = None,
    ) -> None:
        """Emit a plugin service started event."""
        event = PluginServiceStartedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            service_id=service_id,
            service_name=service_name,
            startup_duration=startup_duration,
        )
        self.event_manager.notify(event)

    def emit_plugin_service_stopped(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        service_id: str,
        service_name: str,
        stop_reason: str = "normal_shutdown",
    ) -> None:
        """Emit a plugin service stopped event."""
        event = PluginServiceStoppedEvent(
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            service_id=service_id,
            service_name=service_name,
            stop_reason=stop_reason,
        )
        self.event_manager.notify(event)
