"""
Plugin Observer Module

This module contains observer implementations for handling plugin-based observers and
automatic generation of plugin observers.
"""

from .event_observer_plugin import EventObserverPlugin
from .plugin_interface import IPluginObserver
from .plugin_observer_factory import (
    PluginObserverFactory,
    create_plugin_observer,
    register_plugin_observer,
)

__all__ = [
    "IPluginObserver",
    "EventObserverPlugin",
    "PluginObserverFactory",
    "create_plugin_observer",
    "register_plugin_observer",
]
