"""WebObserver - Bridges PANTHER events to NiceGUI UI callbacks."""

from typing import Callable, List

from panther.core.events.base.event_base import BaseEvent
from panther.core.observer.impl.gui_observer import GUIObserver


class WebObserver(GUIObserver):
    """Bridges PANTHER events to NiceGUI UI callbacks.

    Inherits event_history (max 1000) and gui_state counters from GUIObserver.
    The on_event -> update_gui flow dispatches events to registered subscribers.
    Thread-safe: copies subscriber list before iterating since events arrive
    from asyncio.to_thread.
    """

    def __init__(self):
        """Initialize observer with empty subscriber list."""
        super().__init__()
        self._subscribers: List[Callable[[BaseEvent], None]] = []

    def update_gui(self, event: BaseEvent):
        """Dispatch event to all subscribers (thread-safe copy)."""
        for cb in list(self._subscribers):
            try:
                cb(event)
            except Exception:
                pass

    def update(self, subject) -> None:
        """Legacy compat - no-op."""
        pass

    def subscribe(self, callback: Callable[[BaseEvent], None]):
        """Add a subscriber callback."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[BaseEvent], None]):
        """Remove a subscriber callback (no error if missing)."""
        try:
            self._subscribers.remove(callback)
        except ValueError:
            pass
