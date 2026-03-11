"""WebObserver -- event bridge between PANTHER's observer subsystem and the NiceGUI UI.

This module implements the observer-pattern adapter that connects
PANTHER's internal event bus to the web frontend.  During an experiment
run, every lifecycle event (experiment started, test completed, service
crashed, etc.) flows through the core EventManager (PANTHER's global
publish-subscribe hub) and arrives at this observer's ``on_event``
method.  WebObserver then fans the event out to zero or more
*subscriber callbacks* registered by UI components.

Design highlights:

Subscription model:
    Subscribers register via ``subscribe()`` and receive a ``Subscription``
    handle.  Each subscription may carry optional filters -- event-type
    prefixes (e.g. ``{"test", "experiment"}``), an importance threshold
    (``EventImportance.HIGH``), or an arbitrary predicate function.  Only
    events that pass **all** active filters are delivered.

Event batching:
    During long-running experiments, high-frequency events (step progress,
    metrics collected) can overwhelm the UI.  ``enable_batching()``
    switches the observer into buffered mode: events for *batched*
    subscribers accumulate in an internal buffer and are flushed at a
    caller-controlled interval (typically via a ``ui.timer``).  Events
    classified as ``CRITICAL`` by the ``EventSummarizer`` always bypass
    the buffer and are delivered immediately.  Subscribers may opt out of
    batching by passing ``batched=False`` to ``subscribe()``.

Thread safety:
    Events arrive from a background thread (``asyncio.to_thread`` in
    ``ExperimentService``).  The subscriber list is snapshot-copied
    (``list(self._subscriptions)``) before iteration, and the batch
    buffer is guarded by a ``threading.Lock``.

State persistence:
    ``save_state()`` / ``restore_state()`` serialise the inherited
    ``gui_state`` dict (event counters, last-event timestamps) to and
    from NiceGUI's ``app.storage.general``.  ``export_history()`` /
    ``import_history()`` write the full event history to a JSON file
    for offline inspection.

Event types and importance levels:
    Event types are dot-delimited strings (e.g. ``"experiment.started"``,
    ``"test.completed"``, ``"service.crashed"``).  Importance levels are
    defined by ``EventImportance`` (LOW, MEDIUM, HIGH, CRITICAL) and
    mapped in ``EventSummarizer.IMPORTANT_EVENT_TYPES``.
"""

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
    """A subscriber registration with optional per-subscriber filters.

    Each ``Subscription`` represents a single registered callback together
    with zero or more filter criteria that restrict which events are
    delivered to it.  Filters are combined with AND semantics: an event
    must pass *all* active filters to be delivered.

    Attributes:
        callback: Function invoked with each matching ``BaseEvent``.
        event_types: Optional set of event-type prefixes.  When set, only
            events whose ``get_type()`` return value starts with one of
            these strings are delivered (e.g. ``{"experiment", "test"}``
            matches ``"experiment.started"`` and ``"test.completed"``).
        importance_threshold: Optional minimum importance level.  Events
            below this level (as classified by ``EventSummarizer``) are
            filtered out.  Importance levels are ``LOW``, ``MEDIUM``,
            ``HIGH``, and ``CRITICAL``.
        predicate: Optional arbitrary filter function.  Must accept a
            ``BaseEvent`` and return ``True`` for the event to be
            delivered.  Exceptions in the predicate are caught and
            treated as ``False``.
        batched: Whether this subscriber participates in event batching.
            When ``True`` (the default) and batching is enabled, events
            accumulate in a buffer and are flushed periodically.  Set to
            ``False`` to always receive events immediately regardless of
            the batching state.
    """

    callback: Callable[[BaseEvent], None]
    event_types: Optional[Set[str]] = None
    importance_threshold: Optional[EventImportance] = None
    predicate: Optional[Callable[[BaseEvent], bool]] = None
    batched: bool = True


class WebObserver(GUIObserver):
    """Event bridge that adapts PANTHER's observer subsystem for NiceGUI.

    WebObserver extends ``GUIObserver`` (PANTHER's base class for GUI-bound
    observers, which maintains an ``event_history`` ring buffer of up to
    1 000 events and a ``gui_state`` dict of per-event-type counters and
    timestamps) and adds:

    - **Subscriber dispatch** -- UI components register callbacks via
      ``subscribe()`` and receive ``BaseEvent`` objects that match their
      filter criteria.
    - **Per-subscriber filtering** -- each ``Subscription`` can restrict
      delivery by event-type prefix, importance threshold, or an arbitrary
      predicate function.
    - **Event batching** -- when enabled, non-critical events for batched
      subscribers are buffered and flushed at a caller-controlled interval,
      reducing UI update frequency during high-throughput phases.  Events
      classified as ``CRITICAL`` always bypass the buffer.
    - **State persistence** -- ``save_state`` / ``restore_state`` serialise
      the ``gui_state`` dict for storage in NiceGUI's
      ``app.storage.general``.  ``export_history`` / ``import_history``
      write the full event history to JSON for offline analysis.

    The event flow is:
        ``EventManager.notify`` -> ``GUIObserver.on_event`` ->
        ``GUIObserver._update_gui_state`` -> ``WebObserver.update_gui``
        (dispatch to subscribers).

    Thread safety:
        Events arrive from a background thread (the experiment runner in
        ``ExperimentService``).  The subscriber list is snapshot-copied
        before iteration (``list(self._subscriptions)``), and the batch
        buffer is protected by ``self._batch_lock`` (a ``threading.Lock``).

    Attributes:
        _subscriptions: List of active ``Subscription`` registrations.
        _batch_buffer: Events waiting to be flushed to batched subscribers.
        _batching_enabled: Whether batching mode is currently active.
        _batch_lock: Lock protecting ``_batch_buffer``.

    Example::

        observer = WebObserver()
        sub = observer.subscribe(
            my_callback,
            event_types={"test", "experiment"},
            importance=EventImportance.HIGH,
        )
        # ... later ...
        observer.unsubscribe(sub)
    """

    def __init__(self):
        """Initialise the observer with an empty subscriber list and batching disabled."""
        super().__init__()
        self._subscriptions: List[Subscription] = []
        # Batching state
        self._batch_buffer: List[BaseEvent] = []
        self._batching_enabled: bool = False
        self._batch_lock = threading.Lock()

    # ── Filtering helpers ─────────────────────────────────────────────

    @staticmethod
    def _matches_subscription(event: BaseEvent, sub: Subscription) -> bool:
        """Return True if *event* passes all filter criteria on *sub*."""
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
        """Register a subscriber callback with optional filter criteria.

        All filter parameters are optional and are combined with AND
        semantics: an event must satisfy every specified filter to be
        delivered.  With no filters, the subscriber receives all events.

        Args:
            callback: Function to invoke with each matching ``BaseEvent``.
                Called from the background experiment thread when events
                arrive, so it must be thread-safe.
            event_types: Set of event-type prefix strings.  Only events
                whose ``get_type()`` starts with one of these prefixes are
                delivered (e.g. ``{"test"}`` matches ``"test.started"``
                and ``"test.completed"``).
            importance: Minimum ``EventImportance`` threshold.  Events
                classified below this level by ``EventSummarizer`` are
                dropped.  Levels: ``LOW``, ``MEDIUM``, ``HIGH``,
                ``CRITICAL``.
            predicate: Arbitrary filter function accepting a ``BaseEvent``
                and returning a bool.  Exceptions are caught and treated
                as ``False``.
            batched: If ``True`` (default), the subscriber participates
                in event batching when enabled.  If ``False``, events are
                always delivered immediately.

        Returns:
            A ``Subscription`` handle that can be passed to
            ``unsubscribe()`` to remove this registration.
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
        """Remove a subscriber by ``Subscription`` handle or raw callback reference.

        For backward compatibility this method accepts either the
        ``Subscription`` object returned by ``subscribe()`` or the plain
        callback function.  When a callback is provided, all subscriptions
        whose callback is the same object (identity check) are removed.
        No error is raised if the subscriber is not currently registered.

        Args:
            subscription_or_callback: The ``Subscription`` handle or the
                raw callback function to remove.
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
        """Dispatch an event to all matching subscribers.

        Overrides ``GUIObserver.update_gui``.  Called by the base class's
        ``on_event`` method after the event has been recorded in the
        history and gui_state.

        Dispatch behaviour depends on batching state:

        - **Batching disabled** -- all matching subscribers receive the
          event immediately.
        - **Batching enabled** -- unbatched subscribers and CRITICAL events
          are delivered immediately.  Other events for batched subscribers
          are appended to ``_batch_buffer`` and delivered later by
          ``_flush_batch``.

        Thread safety is achieved by iterating over a snapshot copy of the
        subscriber list.

        Args:
            event: The ``BaseEvent`` to dispatch.
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
        """Legacy observer interface method -- no-op in this implementation."""
        pass

    # ── Batching ──────────────────────────────────────────────────────

    def enable_batching(self, interval_ms: int = 500):
        """Enable event batching mode.

        When enabled, events destined for batched subscribers are
        accumulated in ``_batch_buffer`` instead of being delivered
        immediately.  The caller is responsible for periodically calling
        ``_flush_batch()`` (e.g. via a ``ui.timer``) to deliver the
        buffered events.

        WebObserver itself does **not** create timers, keeping it
        NiceGUI-agnostic.  The ``interval_ms`` parameter serves as a hint
        to the caller for configuring the flush timer.

        Args:
            interval_ms: Suggested flush interval in milliseconds.  Not
                used internally; provided as a contract hint for the
                caller (e.g. ``ExperimentService``).
        """
        self._batching_enabled = True

    def disable_batching(self):
        """Disable batching mode and flush any remaining buffered events.

        After this call, all events are delivered immediately to all
        matching subscribers.
        """
        self._batching_enabled = False
        self._flush_batch()

    def _flush_batch(self):
        """Drain the batch buffer and deliver events to matching batched subscribers."""
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
        """Serialise ``gui_state`` to a JSON-compatible dict for persistence.

        ``BaseEvent`` values are converted via ``to_dict()``.  Other values
        are tested for JSON serialisability; non-serialisable values are
        stringified.

        Returns:
            A dict suitable for storage in NiceGUI's
            ``app.storage.general``.
        """
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
        """Restore ``gui_state`` from a previously saved dict.

        Args:
            state: A dict previously produced by ``save_state()``.  If
                empty or ``None``, this method is a no-op.
        """
        if not state:
            return
        for key, value in state.items():
            self.gui_state[key] = value

    def export_history(self, path: str):
        """Write the full event history to a JSON file for offline analysis.

        Each event is serialised via ``BaseEvent.to_dict()``.  Parent
        directories are created automatically if they do not exist.

        Args:
            path: Destination filesystem path for the JSON file.
        """
        data = [e.to_dict() for e in self.event_history]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def import_history(self, path: str):
        """Load event history entries from a previously exported JSON file.

        Loaded entries are stored as plain dicts in the
        ``imported_history`` instance attribute (not reconstructed as
        ``BaseEvent`` instances) for read-only display purposes.  If the
        file does not exist, this method is a silent no-op.

        Args:
            path: Filesystem path to the JSON file to import.
        """
        p = Path(path)
        if not p.exists():
            return
        with open(p) as f:
            data = json.load(f)
        if isinstance(data, list):
            self.imported_history: List[Dict[str, Any]] = data
