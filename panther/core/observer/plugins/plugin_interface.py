"""Plugin interface for observer plugins.

Defines the minimal abstract contract that all plugin-based observers must
implement: ``on_event()``, ``get_priority()``, and ``is_interested()``.
"""

from abc import ABC, abstractmethod
from typing import Any


class IPluginObserver(ABC):
    """Abstract interface for observer plugins.

    Defines the contract for plugin observers that participate in the
    event notification system. Implementations must handle events,
    declare their priority, and indicate which event types they
    are interested in.
    """

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
