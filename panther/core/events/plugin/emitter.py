"""Plugin Event Emitter.

This module provides a type-safe emitter for plugin events.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EventEmitterBase

from .events import (
    PluginLoadingCompletedEvent,
    PluginLoadingStartedEvent,
    PluginServiceCreatedEvent,
    PluginServiceStartedEvent,
)


class PluginEventEmitter(EventEmitterBase):
    """Event emitter for plugin-related events."""

    def __init__(self, event_manager: "EventManager"):
        """Initialize plugin event emitter."""
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
