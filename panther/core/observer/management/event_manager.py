import logging
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from panther.core.events.base.event_base import BaseEvent
from panther.core.observer.base.observer_interface import IObserver


class EventManager:
    """
    Enhanced event manager with support for event filtering, prioritization,
    and improved monitoring capabilities.

    This class manages the registration of observers and the distribution of events
    to interested observers based on event types and priorities.

    Implemented as a singleton to ensure consistent event management across the system.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Ensure only one instance of EventManager exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize a new EventManager."""
        if EventManager._instance._initialized:
            return
        # Prevent re-initialization of the singleton
        self.logger = logging.getLogger("EventManager")
        # Map of event types to prioritized observers
        self.observers: Dict[str, List[Tuple[int, IObserver]]] = defaultdict(list)
        # Global observers receive all events
        self.global_observers: List[Tuple[int, IObserver]] = []
        # Track recent events for debugging
        self.event_history: List[Tuple[datetime, BaseEvent]] = []
        self.max_history_size = 1000
        # Performance metrics
        self.metrics = {"processed": 0, "errors": 0, "by_type": {}}
        # Thread safety
        self._lock = threading.RLock()

        # Event deduplication
        self._recent_events: Dict[str, datetime] = {}
        self._dedup_window_ms = 1000  # 1000ms (1 second) deduplication window

        # Event correlation tracking
        self._active_contexts: Dict[str, Dict[str, Any]] = {}

        # Observer scope and duplicate tracking
        self._observer_registry: Dict[str, Tuple[IObserver, str]] = (
            {}
        )  # observer_id -> (observer, scope)
        self._scoped_observers: Dict[str, Set[str]] = defaultdict(
            set
        )  # scope -> set of observer_ids

        self._initialized = True
        self.logger.info("EventManager singleton initialized")

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of EventManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (mainly for testing)."""
        with cls._lock:
            if cls._instance:
                cls._instance._initialized = False
            cls._instance = None

    def _get_event_type_safely(self, event: BaseEvent) -> str:
        """
        Safely extract event type from BaseEvent.

        Args:
            event: BaseEvent instance

        Returns:
            str: The event type
        """
        # Standardize on BaseEvent.get_type() method
        if hasattr(event, "get_type") and callable(getattr(event, "get_type")):
            return event.get_type()
        else:
            # This should not happen with properly constructed BaseEvent instances
            self.logger.error(
                f"Event {event.__class__.__name__} missing get_type() method"
            )
            return f"{event.__class__.__name__}.unknown"

    def register_observer(
        self, observer: IObserver, event_types: List[str] = None, priority: int = 0
    ):
        """
        Register an observer for specific event types with priority.
        Higher priority (larger number) observers are notified first.

        Args:
            observer: The observer instance to register
            event_types: List of event types to subscribe to, or None for all events
            priority: Notification priority (default: 0)
        """
        # Safety check for None observer
        if observer is None:
            self.logger.error("Cannot register None observer, skipping registration")
            return

        with self._lock:
            if event_types:
                for event_type in event_types:
                    # Check if this observer is already registered for this event type
                    existing_observers = [obs for _, obs in self.observers[event_type]]
                    if observer not in existing_observers:
                        self.observers[event_type].append((priority, observer))
                        # Sort by priority (highest first)
                        self.observers[event_type].sort(
                            key=lambda x: x[0], reverse=True
                        )
                        self.logger.debug(
                            "Registered observer '%s' for event type '%s' with priority %d",
                            observer.__class__.__name__,
                            event_type,
                            priority,
                        )
                    else:
                        self.logger.debug(
                            "Observer '%s' already registered for event type '%s', skipping duplicate",
                            observer.__class__.__name__,
                            event_type,
                        )
            else:
                # Check if this observer is already registered as global observer
                existing_global_observers = [obs for _, obs in self.global_observers]
                if observer not in existing_global_observers:
                    self.global_observers.append((priority, observer))
                    # Sort by priority (highest first)
                    self.global_observers.sort(key=lambda x: x[0], reverse=True)
                    self.logger.debug(
                        "Registered observer '%s' as global observer with priority %d",
                        observer.__class__.__name__,
                        priority,
                    )
                else:
                    self.logger.debug(
                        "Observer '%s' already registered as global observer, skipping duplicate",
                        observer.__class__.__name__,
                    )

    def register_observer_once(
        self,
        observer: IObserver,
        observer_id: str,
        scope: str = "global",
        event_types: List[str] = None,
        priority: int = 0,
    ):
        """
        Register an observer only if not already registered, with scope tracking.

        Args:
            observer: The observer instance to register
            observer_id: Unique identifier for this observer
            scope: Scope of the observer (e.g., 'global', 'test', 'experiment')
            event_types: List of event types to subscribe to, or None for all events
            priority: Notification priority (default: 0)
        """
        with self._lock:
            # Check if observer already exists
            if observer_id in self._observer_registry:
                existing_observer, existing_scope = self._observer_registry[observer_id]
                self.logger.debug(
                    "Observer '%s' with ID '%s' already registered in scope '%s', skipping duplicate",
                    (
                        existing_observer.__class__.__name__
                        if existing_observer
                        else "None"
                    ),
                    observer_id,
                    existing_scope,
                )
                return existing_observer

            # Safety check for None observer
            if observer is None:
                self.logger.error(
                    "Cannot register None observer with ID '%s', skipping registration",
                    observer_id,
                )
                return None

            # Register the observer
            self.register_observer(observer, event_types, priority)

            # Track in registry
            self._observer_registry[observer_id] = (observer, scope)
            self._scoped_observers[scope].add(observer_id)

            self.logger.debug(
                "Registered observer '%s' with ID '%s' in scope '%s'",
                observer.__class__.__name__,
                observer_id,
                scope,
            )

            return observer

    def unregister_observer(self, observer: IObserver, event_types: List[str] = None):
        """
        Unregister an observer from specific or all event types.

        Args:
            observer: The observer instance to unregister
            event_types: List of event types to unsubscribe from, or None for all
        """
        with self._lock:
            if event_types:
                self._unregister_from_specific_types(observer, event_types)
            else:
                self._unregister_from_all_types(observer)

    def _unregister_from_specific_types(
        self, observer: IObserver, event_types: List[str]
    ):
        """Helper to unregister observer from specific event types."""
        for event_type in event_types:
            self.observers[event_type] = [
                (p, o) for p, o in self.observers[event_type] if o != observer
            ]
            self.logger.debug(
                "Unregistered observer '%s' from event type '%s'",
                observer.__class__.__name__,
                event_type,
            )

    def _unregister_from_all_types(self, observer: IObserver):
        """Helper to unregister observer from all event types."""
        self.global_observers = [
            (p, o) for p, o in self.global_observers if o != observer
        ]
        for event_type in self.observers:
            self.observers[event_type] = [
                (p, o) for p, o in self.observers[event_type] if o != observer
            ]
        self.logger.debug(
            "Unregistered observer '%s' from all event types",
            observer.__class__.__name__,
        )

    def _generate_event_signature(self, event: BaseEvent) -> str:
        """Generate a signature for event deduplication."""
        event_type = self._get_event_type_safely(event)
        entity_id = getattr(event, "entity_id", "")
        # Include key data fields in signature
        data_keys = sorted(getattr(event, "data", {}).keys())
        return f"{event_type}:{entity_id}:{','.join(data_keys)}"

    def _is_duplicate_event(self, event: BaseEvent) -> bool:
        """Check if this event is a duplicate within the deduplication window."""
        signature = self._generate_event_signature(event)
        now = datetime.now()

        with self._lock:
            if signature in self._recent_events:
                last_time = self._recent_events[signature]
                time_diff_ms = (now - last_time).total_seconds() * 1000
                if time_diff_ms < self._dedup_window_ms:
                    return True

            # Update the timestamp for this signature
            self._recent_events[signature] = now

            # Clean up old signatures
            cutoff_time = now - timedelta(milliseconds=self._dedup_window_ms * 2)
            self._recent_events = {
                sig: ts for sig, ts in self._recent_events.items() if ts > cutoff_time
            }

        return False

    def set_event_context(self, context_id: str, context_data: Dict[str, Any]):
        """Set context data for event correlation."""
        with self._lock:
            self._active_contexts[context_id] = context_data

    def clear_event_context(self, context_id: str):
        """Clear context data."""
        with self._lock:
            self._active_contexts.pop(context_id, None)

    def get_event_context(self, context_id: str) -> Dict[str, Any]:
        """Get context data for event correlation."""
        with self._lock:
            return self._active_contexts.get(context_id, {})

    def cleanup_none_observers(self):
        """Remove any None observers from all observer lists."""
        with self._lock:
            cleaned_count = 0

            # Clean specific event type observers
            for event_type in list(self.observers.keys()):
                original_count = len(self.observers[event_type])
                self.observers[event_type] = [
                    (priority, observer)
                    for priority, observer in self.observers[event_type]
                    if observer is not None
                ]
                removed_count = original_count - len(self.observers[event_type])
                if removed_count > 0:
                    cleaned_count += removed_count
                    self.logger.info(
                        "Removed %d None observers from event type '%s'",
                        removed_count,
                        event_type,
                    )

            # Clean global observers
            original_global_count = len(self.global_observers)
            self.global_observers = [
                (priority, observer)
                for priority, observer in self.global_observers
                if observer is not None
            ]
            global_removed = original_global_count - len(self.global_observers)
            if global_removed > 0:
                cleaned_count += global_removed
                self.logger.info(
                    "Removed %d None observers from global observers", global_removed
                )

            if cleaned_count > 0:
                self.logger.info("Cleaned up %d None observers total", cleaned_count)

            return cleaned_count

    def notify(self, event: BaseEvent) -> bool:
        """
        Notify all relevant observers about an event.

        Args:
            event: BaseEvent to publish

        Returns:
            bool: True if the event was successfully published
        """
        # Check for duplicate events
        if self._is_duplicate_event(event):
            self.logger.debug("Duplicate event detected, skipping: %s", event)
            return True

        # Validate event
        if not self._validate_event(event):
            return False

        # Record event
        self._record_event(event)

        # Get and notify matching observers
        event_type = self._get_event_type_safely(event)
        matching_observers = self._get_matching_observers(event_type)
        self._notify_observers(matching_observers, event, event_type)

        return True

    def _validate_event(self, event: BaseEvent) -> bool:
        """Validate the event if it has a validate method."""
        if hasattr(event, "validate") and callable(getattr(event, "validate")):
            if not event.validate():
                event_type = self._get_event_type_safely(event)
                event_data = getattr(event, "data", {})
                self.logger.error(
                    "Invalid event data for %s: %s", event_type, event_data
                )
                return False
        return True

    def _record_event(self, event: BaseEvent):
        """Record event in history and update metrics."""
        with self._lock:
            self.event_history.append((datetime.now(), event))
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)

        self.metrics["processed"] += 1
        event_type = self._get_event_type_safely(event)
        self.metrics["by_type"][event_type] = (
            self.metrics["by_type"].get(event_type, 0) + 1
        )
        self.logger.debug("Publishing event: %s", event)

    def _get_matching_observers(self, event_type: str) -> List[Tuple[int, IObserver]]:
        """Get all observers that should be notified for this event type."""
        with self._lock:
            matching_observers = []

            # Add specific observers for this event type
            matching_observers.extend(self.observers.get(event_type, []))

            # Add observers for parent event types
            parts = event_type.split(".")
            for i in range(1, len(parts)):
                parent_type = ".".join(parts[:-i])
                matching_observers.extend(self.observers.get(parent_type, []))

            # Add global observers
            matching_observers.extend(self.global_observers)

            # Remove duplicates while preserving highest priority and filter None observers
            observer_priorities = {}
            for priority, observer in matching_observers:
                # Skip None observers with warning
                if observer is None:
                    self.logger.warning(
                        "Found None observer in observer list for event '%s', filtering out",
                        event_type,
                    )
                    continue

                if (
                    observer not in observer_priorities
                    or priority > observer_priorities[observer]
                ):
                    observer_priorities[observer] = priority

            # Reconstruct list with highest priorities (None observers already filtered)
            matching_observers = [
                (priority, observer)
                for observer, priority in observer_priorities.items()
            ]

            # Sort by priority (highest first)
            matching_observers.sort(key=lambda x: x[0], reverse=True)

            return matching_observers

    def _notify_observers(
        self, observers: List[Tuple[int, IObserver]], event: BaseEvent, event_type: str
    ):
        """Notify all matching observers about the event."""
        for priority, observer in observers:
            # Safety check for None observers
            if observer is None:
                self.logger.error(
                    "Found None observer in observer list for event '%s', skipping",
                    event_type,
                )
                continue

            try:
                if hasattr(observer, "is_interested") and callable(
                    getattr(observer, "is_interested")
                ):
                    if not observer.is_interested(event_type):
                        continue

                observer.on_event(event)

            except (AttributeError, ValueError, TypeError) as e:
                self.logger.error(
                    "Error notifying observer '%s' about event '%s': %s",
                    observer.__class__.__name__ if observer else "None",
                    event_type,
                    str(e),
                )
                self.metrics["errors"] += 1
            except RuntimeError as e:
                self.logger.error(
                    "Runtime error in observer '%s' processing event '%s': %s",
                    observer.__class__.__name__ if observer else "None",
                    event_type,
                    str(e),
                )
                self.metrics["errors"] += 1

    def get_event_history(
        self, event_type: str = None, limit: int = None
    ) -> List[Tuple[datetime, BaseEvent]]:
        """
        Get recent events, optionally filtered by type.

        Args:
            event_type: Type of events to retrieve, or None for all
            limit: Maximum number of events to return, or None for all available

        Returns:
            List of (timestamp, event) tuples
        """
        limit = limit or self.max_history_size
        with self._lock:
            if event_type:
                filtered = [
                    (t, e)
                    for t, e in self.event_history
                    if self._get_event_type_safely(e) == event_type
                ]
                return filtered[-limit:]
            return self.event_history[-limit:]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get event processing metrics.

        Returns:
            dict: Event processing metrics
        """
        return self.metrics

    def cleanup_scoped_observers(self, scope: str):
        """
        Remove all observers from a specific scope.

        Args:
            scope: The scope to clean up (e.g., 'test', 'experiment')
        """
        with self._lock:
            if scope not in self._scoped_observers:
                self.logger.debug("No observers found in scope '%s' to clean up", scope)
                return

            observer_ids_to_remove = list(self._scoped_observers[scope])
            removed_count = 0

            for observer_id in observer_ids_to_remove:
                if observer_id in self._observer_registry:
                    observer, observer_scope = self._observer_registry[observer_id]

                    # Unregister from all event types and global observers
                    self.unregister_observer(observer)

                    # Remove from registry
                    del self._observer_registry[observer_id]
                    removed_count += 1

                    self.logger.debug(
                        "Removed observer '%s' with ID '%s' from scope '%s'",
                        observer.__class__.__name__,
                        observer_id,
                        scope,
                    )

            # Clear the scope
            del self._scoped_observers[scope]

            self.logger.info(
                "Cleaned up %d observers from scope '%s'", removed_count, scope
            )

    def get_scoped_observer_count(self, scope: str = None) -> Dict[str, int]:
        """
        Get count of observers by scope.

        Args:
            scope: Specific scope to count, or None for all scopes

        Returns:
            Dict mapping scope names to observer counts
        """
        with self._lock:
            if scope:
                return {scope: len(self._scoped_observers.get(scope, set()))}
            else:
                return {
                    s: len(obs_set) for s, obs_set in self._scoped_observers.items()
                }

    def has_observer(self, observer_id: str) -> bool:
        """
        Check if an observer with the given ID is already registered.

        Args:
            observer_id: Unique identifier for the observer

        Returns:
            bool: True if observer exists, False otherwise
        """
        with self._lock:
            return observer_id in self._observer_registry

    def get_registered_observer(
        self, observer_id: str
    ) -> Optional[Tuple[IObserver, str]]:
        """
        Get a registered observer by its ID.

        Args:
            observer_id: Unique identifier for the observer

        Returns:
            tuple: (observer, scope) if found, None otherwise
        """
        with self._lock:
            return self._observer_registry.get(observer_id, None)

    def get_observer_by_type(self, observer_type):
        """
        Find and return an observer by its type/class.

        This method searches both global and event-specific observers for
        an instance that matches the provided type. This is useful for getting
        access to specialized observers like the ExperimentObserver.

        Args:
            observer_type: The class/type of observer to find

        Returns:
            Observer instance matching the type or None if not found
        """
        with self._lock:
            # First check global observers
            for _, observer in self.global_observers:
                if isinstance(observer, observer_type):
                    return observer

            # Then check event-specific observers
            for _, observers in self.observers.items():
                for _, observer in observers:
                    if isinstance(observer, observer_type):
                        return observer

        return None
