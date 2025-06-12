import logging
from abc import ABC
from typing import Any
from panther.core.events import BaseEvent as Event
from panther.core.observer.base.observer_interface import IObserver


class GUIObserver(IObserver, ABC):
    """
    GUIObserver is a concrete implementation of the Observer interface that is intended to update the GUI based on changes in the Experiment subject.

    This observer provides a foundation for GUI-based event handling with proper event logging
    and state management capabilities.
    """

    def __init__(self):
        """Initialize the GUI observer with logging and state tracking."""
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.event_history: list[Event] = []
        self.max_history = 1000
        self.gui_state: dict[str, Any] = {}

    def on_event(self, event: Event):
        """
        Handles an event by updating the GUI state and history.

        :param event: The event to handle.
        """
        self.logger.debug(f"GUI received event: {event.get_type()}")

        # Store event in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history :]

        # Update GUI state based on event type
        self._update_gui_state(event)

        # Trigger GUI update
        self.update_gui(event)

    def _update_gui_state(self, event: Event):
        """
        Update internal GUI state based on the event.

        :param event: The event to process
        """
        event_type = event.get_type()
        self.gui_state[f"last_{event_type}"] = event.timestamp
        self.gui_state["last_event"] = event

        # Update counters
        counter_key = f"{event_type}_count"
        self.gui_state[counter_key] = self.gui_state.get(counter_key, 0) + 1

    def update_gui(self, event: Event):
        """
        Update the GUI display based on the event.
        Override this method in concrete implementations.

        :param event: The event that triggered the update
        """
        self.logger.info(f"GUI update triggered by event: {event.get_type()}")

    def update(self, subject) -> None:
        """
        Legacy update method for backward compatibility.
        This method is called by older Observer pattern implementations.

        :param subject: The subject that changed
        """
        self.logger.info(
            f"GUI observer received legacy update from subject: {type(subject).__name__}"
        )
        # For now, we'll just log this. Concrete implementations can override
        # this method to handle legacy subject updates if needed.

    def get_event_history(self, event_type: str = None, limit: int = None) -> list[Event]:
        """
        Get the event history, optionally filtered by event type.

        :param event_type: Filter by this event type, or None for all events
        :param limit: Maximum number of events to return
        :return: List of events
        """
        events = self.event_history
        if event_type:
            events = [e for e in events if e.get_type() == event_type]

        if limit:
            events = events[-limit:]

        return events

    def get_gui_state(self) -> dict[str, Any]:
        """
        Get the current GUI state.

        :return: Dictionary containing current GUI state
        """
        return self.gui_state.copy()
