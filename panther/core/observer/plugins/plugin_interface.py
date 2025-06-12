"""
Plugin interface for observer plugins.
"""

from abc import ABC, abstractmethod
from typing import Any


class IPluginObserver(ABC):
    """Interface for observer plugins."""

    @abstractmethod
    def on_event(self, event: Any) -> bool:
        """Handle an event.

        Args:
            event: The event to handle

        Returns:
            bool: True if the event was handled successfully
        """
        pass

    @abstractmethod
    def get_priority(self) -> int:
        """Get the priority of this observer.

        Returns:
            int: Priority value (lower = higher priority)
        """
        pass

    @abstractmethod
    def is_interested(self, event_type: str) -> bool:
        """Check if this observer is interested in an event type.

        Args:
            event_type: The type of event

        Returns:
            bool: True if interested in this event type
        """
        pass
