"""
Plugin Events Module

This module provides events, emitters, and state management for plugin lifecycle events.
"""

from .emitter import PluginEventEmitter
from .events import (
    PluginErrorEvent,
    PluginEvent,
    PluginEventType,
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
from .states import (
    PluginInfo,
    PluginServiceInfo,
    PluginState,
    PluginStateManager,
    ServiceState,
)

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
