from typing import TYPE_CHECKING, Any, Dict, List, Optional

"""
Plugin Event Emitter

This module provides a type-safe emitter for plugin events.
"""

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EventEmitterBase

from .events import (
    PluginErrorEvent,
    PluginInitializedEvent,
    PluginLoadingCompletedEvent,
    PluginLoadingFailedEvent,
    PluginLoadingStartedEvent,
    PluginServiceCreatedEvent,
    PluginServiceStartedEvent,
    PluginServiceStoppedEvent,
    PluginStartedEvent,
    PluginStoppedEvent,
)


class PluginEventEmitter(EventEmitterBase):
    """

    from typing import Any, Dict, List, Optional, TYPE_CHECKING, TYPE_CHECKINGEvent emitter for plugin-related events.
    """

    def __init__(self, event_manager: "EventManager"):
        super().__init__(event_manager)

    def emit_plugin_loading_started(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        plugin_path: Optional[str] = None,
        loading_config: Optional[Dict[str, Any]] = None,
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
        duration: Optional[float] = None,
        capabilities: Optional[List[str]] = None,
        version: Optional[str] = None,
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
        error_details: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
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
        initialization_config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
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
        startup_duration: Optional[float] = None,
        startup_details: Optional[Dict[str, Any]] = None,
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
        cleanup_duration: Optional[float] = None,
        cleanup_details: Optional[Dict[str, Any]] = None,
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
        error_details: Optional[Dict[str, Any]] = None,
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
        service_config: Optional[Dict[str, Any]] = None,
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
        startup_duration: Optional[float] = None,
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
