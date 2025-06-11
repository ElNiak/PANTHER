"""
Plugin Events Module

This module provides events, emitters, and state management for plugin lifecycle events.
"""

from .events import (
    PluginEventType,
    PluginEvent,
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

from .emitter import PluginEventEmitter

from .states import PluginState, ServiceState, PluginServiceInfo, PluginInfo, PluginStateManager

__all__ = [
    # Event types and base classes
    "PluginEventType",
    "PluginEvent",
    # Plugin lifecycle events
    "PluginLoadingStartedEvent",
    "PluginLoadingCompletedEvent",
    "PluginLoadingFailedEvent",
    "PluginInitializedEvent",
    "PluginStartedEvent",
    "PluginStoppedEvent",
    "PluginErrorEvent",
    # Plugin service events
    "PluginServiceCreatedEvent",
    "PluginServiceStartedEvent",
    "PluginServiceStoppedEvent",
    # Event emitter
    "PluginEventEmitter",
    # State management
    "PluginState",
    "ServiceState",
    "PluginServiceInfo",
    "PluginInfo",
    "PluginStateManager",
]
