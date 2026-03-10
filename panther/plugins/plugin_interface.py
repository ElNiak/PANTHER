"""Plugin Interface Module - Base Plugin Contract for PANTHER.

Defines the abstract base class that all PANTHER plugins must implement.
``IPlugin`` establishes the plugin lifecycle contract: initialization,
event handling, configuration, and cleanup.

Plugin Lifecycle::

    __init__()  →  initialize(config)  →  handle_event(event)  →  cleanup()
       │               │                       │                     │
       │               ▼                       ▼                     ▼
    plugin_id      is_initialized=True    dispatch to            release
    name           config stored          handler logic          resources

Contract Methods:
    - ``initialize(config)`` -- setup with configuration, returns success bool
    - ``handle_event(event)`` -- **abstract** -- process incoming events
    - ``get_supported_events()`` -- declare event types of interest
    - ``cleanup()`` -- resource teardown (optional override)

Example::

    from panther.plugins.plugin_interface import IPlugin
    from panther.core.events.base.event_base import BaseEvent

    class MyPlugin(IPlugin):
        def handle_event(self, event: BaseEvent) -> None:
            self.logger.info("Received %s", event.name)

Configuration:
    Each plugin provides a ``config_schema.py`` that defines its configuration
    using Pydantic models. Base config classes live in
    ``panther.config.core.models.plugin``. Example::

        # plugins/services/iut/quic/my_impl/config_schema.py
        from dataclasses import dataclass
        from typing import Optional

        @dataclass
        class MyImplConfig:
            binary_path: str = "/usr/local/bin/my_impl"
            timeout: int = 30
            log_level: str = "info"

    See ``panther/plugins/services/iut/quic/picoquic/config_schema.py`` for a
    complete real-world example with protocol-aware port management.

See Also:
    ``panther.plugins.plugin_manager`` -- discovers and manages plugin instances
    ``panther.core.events`` -- event types dispatched to plugins
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from panther.config.core.models.experiment import TestConfig
from panther.core.events.base.event_base import BaseEvent
from panther.core.utils.logging_mixin import LoggerMixin


class IPlugin(LoggerMixin, ABC):
    """Base interface for all PANTHER plugins."""

    def __init__(self, plugin_id: str = None, name: str = None):
        """Initialize a new plugin instance.

        Args:
            plugin_id: Optional unique identifier for this plugin instance
            name: Optional human-readable name for this plugin
        """
        super().__init__()
        self.plugin_id = plugin_id or self.__class__.__name__
        self.name = name or self.__class__.__name__
        # LoggerMixin will handle logger creation, but we can customize it
        if hasattr(self, "_logger") and self._logger is None:
            self._logger = logging.getLogger(f"Plugin:{self.name}")
        self.event_emitter = None
        self.config: TestConfig = {}
        self.is_initialized = False

    def set_event_emitter(self, event_emitter):
        """Set the event emitter for this plugin.

        Args:
            event_emitter: The event emitter instance
        """
        self.event_emitter = event_emitter
        self.logger.debug("BaseEvent emitter set on plugin %s", self.name)

    def get_supported_events(self) -> List[str]:
        """Get the event types this plugin is interested in.

        Returns:
            List of event types the plugin wants to receive
        """
        # Default implementation returns empty list
        # Override this in your plugin to specify events of interest
        return []

    @abstractmethod
    def handle_event(self, event: BaseEvent) -> None:
        """Handle an event sent to this plugin.

        Args:
            event: The event to handle
        """
        pass

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize the plugin with configuration.

        This method is called during plugin loading to perform any
        setup operations needed before the plugin can be used.

        Args:
            config: Configuration dictionary for this plugin

        Returns:
            bool: True if initialization successful, False otherwise
        """
        self.config = config or {}
        self.is_initialized = True
        return True
