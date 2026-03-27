"""Plugin Events.

This module defines events specific to plugin lifecycle management.
Uses factory classmethods on the base PluginEvent class instead of
individual subclasses for most event types.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from panther.core.events.base.event_base import BaseEvent, EventType


class PluginEventType(Enum):
    """Plugin-specific event types."""

    LOADING_STARTED = "loading_started"
    LOADING_COMPLETED = "loading_completed"
    LOADING_FAILED = "loading_failed"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"
    SERVICE_CREATED = "service_created"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    ENVIRONMENT_CREATED = "environment_created"
    ENVIRONMENT_READY = "environment_ready"
    ENVIRONMENT_DESTROYED = "environment_destroyed"


class PluginEvent(BaseEvent):
    """Base class for all plugin events."""

    def __init__(
        self,
        event_type: PluginEventType,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize plugin event."""
        merged_data = data or {}
        merged_data.update({"plugin_name": plugin_name, "plugin_type": plugin_type})

        super().__init__(
            name=event_type.value,
            entity_type=EventType.PLUGIN,
            entity_id=plugin_id,
            data=merged_data,
        )
        self.event_type = event_type
        self.plugin_name = plugin_name
        self.plugin_type = plugin_type

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def loading_started(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        plugin_path=None,
        loading_config=None,
    ):
        """Create loading started event."""
        return cls(
            PluginEventType.LOADING_STARTED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "plugin_path": plugin_path,
                "loading_config": loading_config or {},
                "action": "plugin_loading_started",
            },
        )

    @classmethod
    def loading_completed(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        duration=None,
        capabilities=None,
        version=None,
    ):
        """Create loading completed event."""
        return cls(
            PluginEventType.LOADING_COMPLETED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "duration": duration,
                "capabilities": capabilities or [],
                "version": version,
                "action": "plugin_loading_completed",
            },
        )

    @classmethod
    def loading_failed(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        error_message="",
        error_details=None,
        duration=None,
    ):
        """Create loading failed event."""
        return cls(
            PluginEventType.LOADING_FAILED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "error_message": error_message,
                "error_details": error_details or {},
                "duration": duration,
                "action": "plugin_loading_failed",
            },
        )

    @classmethod
    def initialized(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        initialization_config=None,
        dependencies=None,
    ):
        """Create initialized event."""
        return cls(
            PluginEventType.INITIALIZED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "initialization_config": initialization_config or {},
                "dependencies": dependencies or [],
                "action": "plugin_initialized",
            },
        )

    @classmethod
    def started(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        startup_duration=None,
        startup_details=None,
    ):
        """Create started event."""
        return cls(
            PluginEventType.STARTED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "startup_duration": startup_duration,
                "startup_details": startup_details or {},
                "action": "plugin_started",
            },
        )

    @classmethod
    def stopped(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        stop_reason="normal_shutdown",
        cleanup_duration=None,
        cleanup_details=None,
    ):
        """Create stopped event."""
        return cls(
            PluginEventType.STOPPED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "stop_reason": stop_reason,
                "cleanup_duration": cleanup_duration,
                "cleanup_details": cleanup_details or {},
                "action": "plugin_stopped",
            },
        )

    @classmethod
    def error(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        error_message="",
        error_type="unknown",
        error_details=None,
        recoverable=False,
    ):
        """Create error event."""
        return cls(
            PluginEventType.ERROR,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "error_details": error_details or {},
                "recoverable": recoverable,
                "action": "plugin_error",
            },
        )

    @classmethod
    def service_created(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        service_id="",
        service_name="",
        service_type="",
        service_config=None,
    ):
        """Create service created event."""
        return cls(
            PluginEventType.SERVICE_CREATED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "service_id": service_id,
                "service_name": service_name,
                "service_type": service_type,
                "service_config": service_config or {},
                "action": "plugin_service_created",
            },
        )

    @classmethod
    def service_started(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        service_id="",
        service_name="",
        startup_duration=None,
    ):
        """Create service started event."""
        return cls(
            PluginEventType.SERVICE_STARTED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "service_id": service_id,
                "service_name": service_name,
                "startup_duration": startup_duration,
                "action": "plugin_service_started",
            },
        )

    @classmethod
    def service_stopped(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        service_id="",
        service_name="",
        stop_reason="normal_shutdown",
    ):
        """Create service stopped event."""
        return cls(
            PluginEventType.SERVICE_STOPPED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "service_id": service_id,
                "service_name": service_name,
                "stop_reason": stop_reason,
                "action": "plugin_service_stopped",
            },
        )

    @classmethod
    def loaded(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        plugin_path="",
        metadata=None,
    ):
        """Create loaded event."""
        return cls(
            PluginEventType.LOADING_COMPLETED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "plugin_path": plugin_path,
                "metadata": metadata or {},
                "action": "plugin_loaded",
            },
        )

    @classmethod
    def service_manager_created(
        cls,
        plugin_id,
        plugin_name,
        plugin_type,
        service_name="",
        implementation="",
        protocol="",
        service_config=None,
    ):
        """Create service manager created event."""
        return cls(
            PluginEventType.SERVICE_CREATED,
            plugin_id,
            plugin_name,
            plugin_type,
            data={
                "service_name": service_name,
                "implementation": implementation,
                "protocol": protocol,
                "service_config": service_config or {},
                "action": "service_manager_created",
            },
        )
