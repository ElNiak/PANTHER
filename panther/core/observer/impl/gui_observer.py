"""GUIObserver -- abstract base for observers that drive GUI state updates."""

import logging
import threading
from abc import ABC
from typing import Any, Dict, List

from panther.core.events.base.event_base import BaseEvent as Event
from panther.core.observer.base.observer_interface import IObserver


class GUIObserver(IObserver, ABC):
    """GUI-based observer that updates the UI in response to experiment events.

    This observer provides a foundation for GUI-based event handling with proper event logging
    and state management capabilities.
    """

    def __init__(self):
        """Initialize the GUI observer with logging and state tracking."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._state_lock = threading.RLock()
        self.event_history: List[Event] = []
        self.max_history = 1000
        self.gui_state: Dict[str, Any] = {}

    def on_event(self, event: Event):
        """Handle an event by updating the GUI state and history (thread-safe).

        :param event: The event to handle.
        """
        self.logger.debug(f"GUI received event: {event.get_type()}")

        with self._state_lock:
            # Store event in history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history = self.event_history[-self.max_history :]

            # Update GUI state based on event type
            self._update_gui_state(event)

        # Trigger GUI update (outside lock to avoid holding lock during UI ops)
        self.update_gui(event)

    def _update_gui_state(self, event: Event):
        """Update internal GUI state based on the event.

        :param event: The event to process
        """
        event_type = event.get_type()
        self.gui_state[f"last_{event_type}"] = event.timestamp
        self.gui_state["last_event"] = event

        # Update counters
        counter_key = f"{event_type}_count"
        self.gui_state[counter_key] = self.gui_state.get(counter_key, 0) + 1

    def update_gui(self, event: Event):
        """Update the GUI display based on the event.

        Override this method in concrete implementations.

        :param event: The event that triggered the update
        """
        self.logger.info(f"GUI update triggered by event: {event.get_type()}")

    def update(self, subject) -> None:
        """Legacy update method for backward compatibility.

        This method is called by older Observer pattern implementations.

        :param subject: The subject that changed
        """
        self.logger.info(
            f"GUI observer received legacy update from subject: {type(subject).__name__}"
        )
        # For now, we'll just log this. Concrete implementations can override
        # this method to handle legacy subject updates if needed.

    def get_event_history(
        self, event_type: str = None, limit: int = None
    ) -> List[Event]:
        """Get the event history, optionally filtered by event type (thread-safe).

        :param event_type: Filter by this event type, or None for all events
        :param limit: Maximum number of events to return
        :return: List of events
        """
        with self._state_lock:
            events = list(self.event_history)
        if event_type:
            events = [e for e in events if e.get_type() == event_type]
        if limit:
            events = events[-limit:]
        return events

    def get_gui_state(self) -> Dict[str, Any]:
        """Get the current GUI state (thread-safe).

        :return: Dictionary containing current GUI state
        """
        with self._state_lock:
            return self.gui_state.copy()
