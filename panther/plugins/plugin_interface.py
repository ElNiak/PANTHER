import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from panther.config.core.models.experiment import TestConfig
from panther.core.events.base.event_base import BaseEvent
from panther.core.utils.logging_mixin import LoggerMixin


class IPlugin(LoggerMixin, ABC):
    def __init__(self, plugin_id: str = None, name: str = None):
        """
        Initialize a new plugin instance.

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
        """
        Set the event emitter for this plugin.

        Args:
            event_emitter: The event emitter instance
        """
        self.event_emitter = event_emitter
        self.logger.debug("BaseEvent emitter set on plugin %s", self.name)

    def get_supported_events(self) -> List[str]:
        """
        Get the event types this plugin is interested in.

        Returns:
            List of event types the plugin wants to receive
        """
        # Default implementation returns empty list
        # Override this in your plugin to specify events of interest
        return []

    @abstractmethod
    def handle_event(self, event: BaseEvent) -> None:
        """
        Handle an event sent to this plugin.

        Args:
            event: The event to handle
        """
        pass

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the plugin with configuration.

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
