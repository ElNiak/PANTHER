"""Plugin Events.

This module defines events specific to plugin lifecycle management.
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

    @property
    def plugin_name_property(self) -> str:
        """Return the plugin name."""
        return self.data.get("plugin_name", "")

    @property
    def plugin_type_property(self) -> str:
        """Return the plugin type."""
        return self.data.get("plugin_type", "")


class PluginLoadingStartedEvent(PluginEvent):
    """Event emitted when plugin loading starts."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        plugin_path: Optional[str] = None,
        loading_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize plugin loading started event."""
        super().__init__(
            event_type=PluginEventType.LOADING_STARTED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "plugin_path": plugin_path,
                "loading_config": loading_config or {},
                "action": "plugin_loading_started",
            },
        )

    @property
    def plugin_path(self) -> Optional[str]:
        """Return the plugin path."""
        return self.data.get("plugin_path")

    @property
    def loading_config(self) -> Dict[str, Any]:
        """Return the loading configuration."""
        return self.data.get("loading_config", {})


class PluginLoadingCompletedEvent(PluginEvent):
    """Event emitted when plugin loading completes successfully."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        duration: Optional[float] = None,
        capabilities: Optional[list] = None,
        version: Optional[str] = None,
    ):
        """Initialize plugin loading completed event."""
        super().__init__(
            event_type=PluginEventType.LOADING_COMPLETED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "duration": duration,
                "capabilities": capabilities or [],
                "version": version,
                "action": "plugin_loading_completed",
            },
        )

    @property
    def duration(self) -> Optional[float]:
        """Return the loading duration."""
        return self.data.get("duration")

    @property
    def capabilities(self) -> list:
        """Return the plugin capabilities."""
        return self.data.get("capabilities", [])

    @property
    def version(self) -> Optional[str]:
        """Return the plugin version."""
        return self.data.get("version")


class PluginLoadingFailedEvent(PluginEvent):
    """Event emitted when plugin loading fails."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        error_message: str = "",
        error_details: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
    ):
        """Initialize plugin loading failed event."""
        super().__init__(
            event_type=PluginEventType.LOADING_FAILED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "error_message": error_message,
                "error_details": error_details or {},
                "duration": duration,
                "action": "plugin_loading_failed",
            },
        )

    @property
    def error_message(self) -> str:
        """Return the error message."""
        return self.data.get("error_message", "")

    @property
    def error_details(self) -> Dict[str, Any]:
        """Return the error details."""
        return self.data.get("error_details", {})

    @property
    def duration(self) -> Optional[float]:
        """Return the loading duration."""
        return self.data.get("duration")


class PluginInitializedEvent(PluginEvent):
    """Event emitted when plugin is initialized."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        initialization_config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[list] = None,
    ):
        """Initialize plugin initialized event."""
        super().__init__(
            event_type=PluginEventType.INITIALIZED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "initialization_config": initialization_config or {},
                "dependencies": dependencies or [],
                "action": "plugin_initialized",
            },
        )

    @property
    def initialization_config(self) -> Dict[str, Any]:
        """Return the initialization configuration."""
        return self.data.get("initialization_config", {})

    @property
    def dependencies(self) -> list:
        """Return the plugin dependencies."""
        return self.data.get("dependencies", [])


class PluginStartedEvent(PluginEvent):
    """Event emitted when plugin starts."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        startup_duration: Optional[float] = None,
        startup_details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize plugin started event."""
        super().__init__(
            event_type=PluginEventType.STARTED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "startup_duration": startup_duration,
                "startup_details": startup_details or {},
                "action": "plugin_started",
            },
        )

    @property
    def startup_duration(self) -> Optional[float]:
        """Return the startup duration."""
        return self.data.get("startup_duration")

    @property
    def startup_details(self) -> Dict[str, Any]:
        """Return the startup details."""
        return self.data.get("startup_details", {})


class PluginStoppedEvent(PluginEvent):
    """Event emitted when plugin stops."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        stop_reason: str = "normal_shutdown",
        cleanup_duration: Optional[float] = None,
        cleanup_details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize plugin stopped event."""
        super().__init__(
            event_type=PluginEventType.STOPPED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "stop_reason": stop_reason,
                "cleanup_duration": cleanup_duration,
                "cleanup_details": cleanup_details or {},
                "action": "plugin_stopped",
            },
        )

    @property
    def stop_reason(self) -> str:
        """Return the stop reason."""
        return self.data.get("stop_reason", "normal_shutdown")

    @property
    def cleanup_duration(self) -> Optional[float]:
        """Return the cleanup duration."""
        return self.data.get("cleanup_duration")

    @property
    def cleanup_details(self) -> Dict[str, Any]:
        """Return the cleanup details."""
        return self.data.get("cleanup_details", {})


class PluginErrorEvent(PluginEvent):
    """Event emitted when plugin encounters an error."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        error_message: str = "",
        error_type: str = "unknown",
        error_details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
    ):
        """Initialize plugin error event."""
        super().__init__(
            event_type=PluginEventType.ERROR,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "error_details": error_details or {},
                "recoverable": recoverable,
                "action": "plugin_error",
            },
        )

    @property
    def error_message(self) -> str:
        """Return the error message."""
        return self.data.get("error_message", "")

    @property
    def error_type(self) -> str:
        """Return the error type."""
        return self.data.get("error_type", "unknown")

    @property
    def error_details(self) -> Dict[str, Any]:
        """Return the error details."""
        return self.data.get("error_details", {})

    @property
    def recoverable(self) -> bool:
        """Return whether the error is recoverable."""
        return self.data.get("recoverable", False)


class PluginServiceCreatedEvent(PluginEvent):
    """Event emitted when plugin creates a service."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        service_id: str,
        service_name: str,
        service_type: str,
        service_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize plugin service created event."""
        super().__init__(
            event_type=PluginEventType.SERVICE_CREATED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "service_id": service_id,
                "service_name": service_name,
                "service_type": service_type,
                "service_config": service_config or {},
                "action": "plugin_service_created",
            },
        )

    @property
    def service_id(self) -> str:
        """Return the service ID."""
        return self.data.get("service_id", "")

    @property
    def service_name(self) -> str:
        """Return the service name."""
        return self.data.get("service_name", "")

    @property
    def service_type(self) -> str:
        """Return the service type."""
        return self.data.get("service_type", "")

    @property
    def service_config(self) -> Dict[str, Any]:
        """Return the service configuration."""
        return self.data.get("service_config", {})


class PluginServiceStartedEvent(PluginEvent):
    """Event emitted when plugin starts a service."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        service_id: str,
        service_name: str,
        startup_duration: Optional[float] = None,
    ):
        """Initialize plugin service started event."""
        super().__init__(
            event_type=PluginEventType.SERVICE_STARTED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "service_id": service_id,
                "service_name": service_name,
                "startup_duration": startup_duration,
                "action": "plugin_service_started",
            },
        )

    @property
    def service_id(self) -> str:
        """Return the service ID."""
        return self.data.get("service_id", "")

    @property
    def service_name(self) -> str:
        """Return the service name."""
        return self.data.get("service_name", "")

    @property
    def startup_duration(self) -> Optional[float]:
        """Return the startup duration."""
        return self.data.get("startup_duration")


class PluginServiceStoppedEvent(PluginEvent):
    """Event emitted when plugin stops a service."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        service_id: str,
        service_name: str,
        stop_reason: str = "normal_shutdown",
    ):
        """Initialize plugin service stopped event."""
        super().__init__(
            event_type=PluginEventType.SERVICE_STOPPED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "service_id": service_id,
                "service_name": service_name,
                "stop_reason": stop_reason,
                "action": "plugin_service_stopped",
            },
        )

    @property
    def service_id(self) -> str:
        """Return the service ID."""
        return self.data.get("service_id", "")

    @property
    def service_name(self) -> str:
        """Return the service name."""
        return self.data.get("service_name", "")

    @property
    def stop_reason(self) -> str:
        """Return the stop reason."""
        return self.data.get("stop_reason", "normal_shutdown")


class PluginLoadedEvent(PluginEvent):
    """Event emitted when a plugin is successfully loaded and available for use."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        plugin_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize plugin loaded event."""
        super().__init__(
            event_type=PluginEventType.LOADING_COMPLETED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "plugin_path": plugin_path,
                "metadata": metadata or {},
                "action": "plugin_loaded",
            },
        )

    @property
    def plugin_path(self) -> str:
        """Return the plugin path."""
        return self.data.get("plugin_path", "")

    @property
    def metadata(self) -> Dict[str, Any]:
        """Return the plugin metadata."""
        return self.data.get("metadata", {})


class ServiceManagerCreatedEvent(PluginEvent):
    """Event emitted when a service manager is created from a plugin."""

    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        service_name: str,
        implementation: str,
        protocol: str,
        service_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize service manager created event."""
        super().__init__(
            event_type=PluginEventType.SERVICE_CREATED,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            plugin_type=plugin_type,
            data={
                "service_name": service_name,
                "implementation": implementation,
                "protocol": protocol,
                "service_config": service_config or {},
                "action": "service_manager_created",
            },
        )

    @property
    def service_name(self) -> str:
        """Return the service name."""
        return self.data.get("service_name", "")

    @property
    def implementation(self) -> str:
        """Return the implementation name."""
        return self.data.get("implementation", "")

    @property
    def protocol(self) -> str:
        """Return the protocol name."""
        return self.data.get("protocol", "")
