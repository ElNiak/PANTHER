"""
Plugin State Management

This module provides state management for plugin events.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


class PluginState(Enum):
    """Plugin lifecycle states."""

    UNKNOWN = "unknown"
    LOADING = "loading"
    LOADED = "loaded"
    LOAD_FAILED = "load_failed"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    STARTING = "starting"
    STARTED = "started"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class ServiceState(Enum):
    """Plugin service states."""

    UNKNOWN = "unknown"
    CREATING = "creating"
    CREATED = "created"
    STARTING = "starting"
    STARTED = "started"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class PluginServiceInfo:
    """Information about a plugin service."""

    service_id: str
    service_name: str
    service_type: str
    state: ServiceState = ServiceState.UNKNOWN
    config: dict[str, Any] = field(default_factory=dict)
    startup_duration: float | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    stop_reason: str = ""


@dataclass
class PluginInfo:
    """Information about a plugin."""

    plugin_id: str
    plugin_name: str
    plugin_type: str
    state: PluginState = PluginState.UNKNOWN
    plugin_path: str | None = None
    version: str | None = None
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    services: dict[str, PluginServiceInfo] = field(default_factory=dict)

    # Timing information
    loading_started_at: datetime | None = None
    loading_completed_at: datetime | None = None
    loading_duration: float | None = None
    startup_duration: float | None = None

    # Error information
    last_error: str | None = None
    error_count: int = 0

    # Configuration
    loading_config: dict[str, Any] = field(default_factory=dict)
    initialization_config: dict[str, Any] = field(default_factory=dict)
    startup_details: dict[str, Any] = field(default_factory=dict)
    cleanup_details: dict[str, Any] = field(default_factory=dict)


class PluginStateManager:
    """Manages state for plugin events."""

    def __init__(self):
        self.plugins: dict[str, PluginInfo] = {}
        self.plugins_by_type: dict[str, set[str]] = {}
        self.plugins_by_state: dict[PluginState, set[str]] = {state: set() for state in PluginState}

    def get_plugin_info(self, plugin_id: str) -> PluginInfo | None:
        """Get plugin information by ID."""
        return self.plugins.get(plugin_id)

    def get_plugins_by_type(self, plugin_type: str) -> list[PluginInfo]:
        """Get all plugins of a specific type."""
        plugin_ids = self.plugins_by_type.get(plugin_type, set())
        return [self.plugins[pid] for pid in plugin_ids if pid in self.plugins]

    def get_plugins_by_state(self, state: PluginState) -> list[PluginInfo]:
        """Get all plugins in a specific state."""
        plugin_ids = self.plugins_by_state.get(state, set())
        return [self.plugins[pid] for pid in plugin_ids if pid in self.plugins]

    def get_all_plugins(self) -> list[PluginInfo]:
        """Get all plugins."""
        return list(self.plugins.values())

    def update_plugin_state(self, plugin_id: str, new_state: PluginState) -> None:
        """Update plugin state and maintain state indices."""
        if plugin_id in self.plugins:
            old_state = self.plugins[plugin_id].state

            # Remove from old state set
            if plugin_id in self.plugins_by_state[old_state]:
                self.plugins_by_state[old_state].remove(plugin_id)

            # Update state
            self.plugins[plugin_id].state = new_state

            # Add to new state set
            self.plugins_by_state[new_state].add(plugin_id)

    def handle_loading_started(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        plugin_path: str | None = None,
        loading_config: dict[str, Any] | None = None,
    ) -> None:
        """Handle plugin loading started event."""
        if plugin_id not in self.plugins:
            self.plugins[plugin_id] = PluginInfo(
                plugin_id=plugin_id,
                plugin_name=plugin_name,
                plugin_type=plugin_type,
                plugin_path=plugin_path,
                loading_config=loading_config or {},
            )

            # Add to type index
            if plugin_type not in self.plugins_by_type:
                self.plugins_by_type[plugin_type] = set()
            self.plugins_by_type[plugin_type].add(plugin_id)

        plugin_info = self.plugins[plugin_id]
        plugin_info.loading_started_at = datetime.now()
        plugin_info.loading_config = loading_config or {}
        self.update_plugin_state(plugin_id, PluginState.LOADING)

    def handle_loading_completed(
        self,
        plugin_id: str,
        duration: float | None = None,
        capabilities: list[str] | None = None,
        version: str | None = None,
    ) -> None:
        """Handle plugin loading completed event."""
        if plugin_id in self.plugins:
            plugin_info = self.plugins[plugin_id]
            plugin_info.loading_completed_at = datetime.now()
            plugin_info.loading_duration = duration
            plugin_info.capabilities = capabilities or []
            plugin_info.version = version
            self.update_plugin_state(plugin_id, PluginState.LOADED)

    def handle_loading_failed(
        self, plugin_id: str, error_message: str = "", duration: float | None = None
    ) -> None:
        """Handle plugin loading failed event."""
        if plugin_id in self.plugins:
            plugin_info = self.plugins[plugin_id]
            plugin_info.loading_duration = duration
            plugin_info.last_error = error_message
            plugin_info.error_count += 1
            self.update_plugin_state(plugin_id, PluginState.LOAD_FAILED)

    def handle_initialized(
        self,
        plugin_id: str,
        initialization_config: dict[str, Any] | None = None,
        dependencies: list[str] | None = None,
    ) -> None:
        """Handle plugin initialized event."""
        if plugin_id in self.plugins:
            plugin_info = self.plugins[plugin_id]
            plugin_info.initialization_config = initialization_config or {}
            plugin_info.dependencies = dependencies or []
            self.update_plugin_state(plugin_id, PluginState.INITIALIZED)

    def handle_started(
        self,
        plugin_id: str,
        startup_duration: float | None = None,
        startup_details: dict[str, Any] | None = None,
    ) -> None:
        """Handle plugin started event."""
        if plugin_id in self.plugins:
            plugin_info = self.plugins[plugin_id]
            plugin_info.startup_duration = startup_duration
            plugin_info.startup_details = startup_details or {}
            self.update_plugin_state(plugin_id, PluginState.STARTED)

    def handle_stopped(
        self,
        plugin_id: str,
        stop_reason: str = "normal_shutdown",
        cleanup_duration: float | None = None,
        cleanup_details: dict[str, Any] | None = None,
    ) -> None:
        """Handle plugin stopped event."""
        if plugin_id in self.plugins:
            plugin_info = self.plugins[plugin_id]
            plugin_info.cleanup_details = cleanup_details or {}
            self.update_plugin_state(plugin_id, PluginState.STOPPED)

    def handle_error(
        self,
        plugin_id: str,
        error_message: str = "",
        error_type: str = "unknown",
        recoverable: bool = False,
    ) -> None:
        """Handle plugin error event."""
        if plugin_id in self.plugins:
            plugin_info = self.plugins[plugin_id]
            plugin_info.last_error = f"{error_type}: {error_message}"
            plugin_info.error_count += 1
            self.update_plugin_state(plugin_id, PluginState.ERROR)

    def handle_service_created(
        self,
        plugin_id: str,
        service_id: str,
        service_name: str,
        service_type: str,
        service_config: dict[str, Any] | None = None,
    ) -> None:
        """Handle plugin service created event."""
        if plugin_id in self.plugins:
            service_info = PluginServiceInfo(
                service_id=service_id,
                service_name=service_name,
                service_type=service_type,
                state=ServiceState.CREATED,
                config=service_config or {},
            )
            self.plugins[plugin_id].services[service_id] = service_info

    def handle_service_started(
        self, plugin_id: str, service_id: str, startup_duration: float | None = None
    ) -> None:
        """Handle plugin service started event."""
        if plugin_id in self.plugins and service_id in self.plugins[plugin_id].services:
            service_info = self.plugins[plugin_id].services[service_id]
            service_info.state = ServiceState.STARTED
            service_info.startup_duration = startup_duration
            service_info.started_at = datetime.now()

    def handle_service_stopped(
        self, plugin_id: str, service_id: str, stop_reason: str = "normal_shutdown"
    ) -> None:
        """Handle plugin service stopped event."""
        if plugin_id in self.plugins and service_id in self.plugins[plugin_id].services:
            service_info = self.plugins[plugin_id].services[service_id]
            service_info.state = ServiceState.STOPPED
            service_info.stop_reason = stop_reason
            service_info.stopped_at = datetime.now()

    def get_plugin_summary(self) -> dict[str, Any]:
        """Get summary of all plugin states."""
        summary = {
            "total_plugins": len(self.plugins),
            "plugins_by_state": {
                state.value: len(self.plugins_by_state[state]) for state in PluginState
            },
            "plugins_by_type": {
                plugin_type: len(plugin_ids)
                for plugin_type, plugin_ids in self.plugins_by_type.items()
            },
            "total_services": sum(len(plugin.services) for plugin in self.plugins.values()),
            "plugins_with_errors": len([p for p in self.plugins.values() if p.error_count > 0]),
        }
        return summary
