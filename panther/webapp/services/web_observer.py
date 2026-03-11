"""WebObserver - Bridges PANTHER events to NiceGUI UI callbacks."""

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

from panther.core.events.base.event_base import BaseEvent
from panther.core.events.event_summarizer import EventImportance, EventSummarizer
from panther.core.observer.impl.gui_observer import GUIObserver

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """A subscriber registration with optional filters.

    Attributes:
        callback: Function called with matching events.
        event_types: If set, only events whose get_type() starts with one of
            these prefixes are delivered (e.g. {"experiment", "test"}).
        importance_threshold: If set, only events at or above this importance
            level are delivered.
        predicate: If set, an arbitrary filter function. Event is delivered
            only when predicate returns True.
        batched: If True (default), events may be buffered when batching is
            enabled. Set to False to always receive events immediately.
    """

    callback: Callable[[BaseEvent], None]
    event_types: Optional[Set[str]] = None
    importance_threshold: Optional[EventImportance] = None
    predicate: Optional[Callable[[BaseEvent], bool]] = None
    batched: bool = True


class WebObserver(GUIObserver):
    """Bridges PANTHER events to NiceGUI UI callbacks.

    Inherits event_history (max 1000) and gui_state counters from GUIObserver.
    The on_event -> update_gui flow dispatches events to registered subscribers.
    Thread-safe: copies subscriber list before iterating since events arrive
    from asyncio.to_thread.

    Supports:
    - Per-subscriber filtering (event type prefix, importance threshold, predicate)
    - Event batching (accumulate + flush at intervals, CRITICAL bypasses)
    - State persistence (save/restore gui_state, export/import history as JSON)
    """

    def __init__(self):
        """Initialize observer with empty subscriber list and batching off."""
        super().__init__()
        self._subscriptions: List[Subscription] = []
        # Batching state
        self._batch_buffer: List[BaseEvent] = []
        self._batching_enabled: bool = False
        self._batch_lock = threading.Lock()

    # ── Filtering helpers ─────────────────────────────────────────────

    @staticmethod
    def _matches_subscription(event: BaseEvent, sub: Subscription) -> bool:
        """Check whether *event* passes all filters on *sub*."""
        event_type = event.get_type()

        # Event type prefix filter
        if sub.event_types is not None:
            if not any(event_type.startswith(prefix) for prefix in sub.event_types):
                return False

        # Importance threshold filter
        if sub.importance_threshold is not None:
            importance = EventSummarizer.IMPORTANT_EVENT_TYPES.get(
                event_type, EventImportance.MEDIUM
            )
            if importance.value < sub.importance_threshold.value:
                return False

        # Custom predicate filter
        if sub.predicate is not None:
            try:
                if not sub.predicate(event):
                    return False
            except Exception:
                logger.warning("Subscription predicate raised", exc_info=True)
                return False

        return True

    # ── Subscribe / Unsubscribe ───────────────────────────────────────

    def subscribe(
        self,
        callback: Callable[[BaseEvent], None],
        *,
        event_types: Optional[Set[str]] = None,
        importance: Optional[EventImportance] = None,
        predicate: Optional[Callable[[BaseEvent], bool]] = None,
        batched: bool = True,
    ) -> Subscription:
        """Add a subscriber callback with optional filters.

        Args:
            callback: Function to invoke with matching events.
            event_types: Prefix set — only events whose get_type() starts with
                one of these strings are delivered.
            importance: Minimum importance threshold for delivery.
            predicate: Arbitrary filter; must return True for delivery.
            batched: Whether this subscriber participates in batching.

        Returns:
            A Subscription handle that can be passed to unsubscribe().
        """
        sub = Subscription(
            callback=callback,
            event_types=event_types,
            importance_threshold=importance,
            predicate=predicate,
            batched=batched,
        )
        self._subscriptions.append(sub)
        return sub

    def unsubscribe(self, subscription_or_callback: Union[Subscription, Callable]):
        """Remove a subscriber by Subscription handle or raw callback.

        Accepts both the Subscription object returned by subscribe() and the
        plain callback function (for backward compatibility). No error if the
        subscriber is not found.
        """
        if isinstance(subscription_or_callback, Subscription):
            try:
                self._subscriptions.remove(subscription_or_callback)
            except ValueError:
                pass
        else:
            # Legacy path: match by callback reference
            self._subscriptions = [
                s
                for s in self._subscriptions
                if s.callback is not subscription_or_callback
            ]

    # ── Dispatch ──────────────────────────────────────────────────────

    def update_gui(self, event: BaseEvent):
        """Dispatch event to matching subscribers (thread-safe copy).

        When batching is enabled, events are buffered for batched subscribers
        (except CRITICAL events, which always dispatch immediately).
        Unbatched subscribers always receive events immediately.
        """
        event_type = event.get_type()
        is_critical = (
            EventSummarizer.IMPORTANT_EVENT_TYPES.get(event_type)
            == EventImportance.CRITICAL
        )

        should_buffer = False
        for sub in list(self._subscriptions):
            if not self._matches_subscription(event, sub):
                continue

            # Decide: immediate delivery or buffer?
            if self._batching_enabled and sub.batched and not is_critical:
                should_buffer = True
                continue  # will be delivered during _flush_batch

            try:
                sub.callback(event)
            except Exception:
                logger.warning(
                    "GUI subscriber callback failed for %s",
                    type(event).__name__,
                    exc_info=True,
                )

        if should_buffer:
            with self._batch_lock:
                self._batch_buffer.append(event)

    def update(self, subject) -> None:
        """Legacy compat - no-op."""
        pass

    # ── Batching ──────────────────────────────────────────────────────

    def enable_batching(self, interval_ms: int = 500):
        """Enable event batching. Events accumulate until _flush_batch().

        Args:
            interval_ms: Hint for the caller (e.g. ExperimentService) to
                configure a timer at this interval. WebObserver itself does
                not create timers to stay NiceGUI-agnostic.
        """
        self._batching_enabled = True

    def disable_batching(self):
        """Disable batching and flush any remaining buffered events."""
        self._batching_enabled = False
        self._flush_batch()

    def _flush_batch(self):
        """Deliver all buffered events to matching batched subscribers."""
        with self._batch_lock:
            events = list(self._batch_buffer)
            self._batch_buffer.clear()

        for event in events:
            for sub in list(self._subscriptions):
                if not sub.batched:
                    continue  # already received immediately
                if not self._matches_subscription(event, sub):
                    continue
                try:
                    sub.callback(event)
                except Exception:
                    logger.warning(
                        "GUI subscriber callback failed during batch flush for %s",
                        type(event).__name__,
                        exc_info=True,
                    )

    # ── Persistence ───────────────────────────────────────────────────

    def save_state(self) -> dict:
        """Serialize gui_state to a dict suitable for app.storage.general."""
        state: Dict[str, Any] = {}
        for key, value in self.gui_state.items():
            if isinstance(value, BaseEvent):
                state[key] = {"__event__": True, **value.to_dict()}
            else:
                try:
                    json.dumps(value)
                    state[key] = value
                except (TypeError, ValueError):
                    state[key] = str(value)
        return state

    def restore_state(self, state: dict):
        """Restore gui_state from a previously saved dict."""
        if not state:
            return
        for key, value in state.items():
            self.gui_state[key] = value

    def export_history(self, path: str):
        """Write event_history to a JSON file."""
        data = [e.to_dict() for e in self.event_history]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def import_history(self, path: str):
        """Load event history dicts from a JSON file.

        Loaded entries are stored as dicts in ``imported_history`` (not
        reconstructed as BaseEvent instances) for display purposes.
        """
        p = Path(path)
        if not p.exists():
            return
        with open(p) as f:
            data = json.load(f)
        if isinstance(data, list):
            self.imported_history: List[Dict[str, Any]] = data
