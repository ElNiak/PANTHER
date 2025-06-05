import logging
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any

from panther.core.observer.events import Event
from panther.core.observer.core.observer_interface import IObserver


class EventManager:
    """
    Enhanced event manager with support for event filtering, prioritization,
    and improved monitoring capabilities.

    This class manages the registration of observers and the distribution of events
    to interested observers based on event types and priorities.
    """

    def __init__(self):
        """Initialize a new EventManager."""
        self.logger = logging.getLogger("EventManager")
        # Map of event types to prioritized observers
        self.observers: dict[str, list[tuple[int, IObserver]]] = defaultdict(list)
        # Global observers receive all events
        self.global_observers: list[tuple[int, IObserver]] = []
        # Track recent events for debugging
        self.event_history = []
        self.max_history = 100
        # Performance metrics
        self.metrics = {"processed": 0, "errors": 0, "by_type": {}}
        # Thread safety
        self._lock = threading.RLock()

    def _get_event_type_safely(self, event: Event) -> str:
        """
        Safely get the event type from an event object, handling different event implementations.

        Args:
            event: The event to get the type from

        Returns:
            str: The event type
        """
        if hasattr(event, "get_type") and callable(getattr(event, "get_type")):
            return event.get_type()
        elif hasattr(event, "name"):
            return event.name
        else:
            # Fallback if neither method is available
            return str(event.__class__.__name__)

    def register_observer(
        self, observer: IObserver, event_types: list[str] = None, priority: int = 0
    ):
        """
        Register an observer for specific event types with priority.
        Higher priority (larger number) observers are notified first.

        Args:
            observer: The observer instance to register
            event_types: List of event types to subscribe to, or None for all events
            priority: Notification priority (default: 0)
        """
        with self._lock:
            if event_types:
                for event_type in event_types:
                    self.observers[event_type].append((priority, observer))
                    # Sort by priority (highest first)
                    self.observers[event_type].sort(key=lambda x: x[0], reverse=True)
                    self.logger.debug(
                        "Registered observer '%s' for event type '%s' with priority %d",
                        observer.__class__.__name__,
                        event_type,
                        priority,
                    )
            else:
                self.global_observers.append((priority, observer))
                # Sort by priority (highest first)
                self.global_observers.sort(key=lambda x: x[0], reverse=True)
                self.logger.debug(
                    "Registered observer '%s' as global observer with priority %d",
                    observer.__class__.__name__,
                    priority,
                )

    def unregister_observer(self, observer: IObserver, event_types: list[str] = None):
        """
        Unregister an observer from specific or all event types.

        Args:
            observer: The observer instance to unregister
            event_types: List of event types to unsubscribe from, or None for all
        """
        with self._lock:
            if event_types:
                for event_type in event_types:
                    self.observers[event_type] = [
                        (p, o) for p, o in self.observers[event_type] if o != observer
                    ]
                    self.logger.debug(
                        "Unregistered observer '%s' from event type '%s'",
                        observer.__class__.__name__,
                        event_type,
                    )
            else:
                self.global_observers = [(p, o) for p, o in self.global_observers if o != observer]
                for event_type in self.observers:
                    self.observers[event_type] = [
                        (p, o) for p, o in self.observers[event_type] if o != observer
                    ]
                self.logger.debug(
                    "Unregistered observer '%s' from all event types", observer.__class__.__name__
                )

    def notify(self, event: Event) -> bool:
        """
        Notify all relevant observers about an event.

        Args:
            event: The event to publish

        Returns:
            bool: True if the event was successfully published
        """
        # Validate event if it has a validate method
        if hasattr(event, "validate") and callable(getattr(event, "validate")):
            if not event.validate():
                # Get event type safely for the error message
                event_type = self._get_event_type_safely(event)
                event_data = getattr(event, "data", {})
                self.logger.error("Invalid event data for %s: %s", event_type, event_data)
                return False

        # Store in history
        with self._lock:
            self.event_history.append((datetime.now(), event))
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)

        # Update metrics
        self.metrics["processed"] += 1
        event_type = self._get_event_type_safely(event)
        self.metrics["by_type"][event_type] = self.metrics["by_type"].get(event_type, 0) + 1

        # Always log the event for debugging, but at a lower level to avoid noise
        # LoggerObserver will provide more detailed logs for normal operations
        self.logger.debug("Publishing event: %s", event)

        # Get matching observers
        matching_observers = []
        with self._lock:
            # Add specific observers for this event type
            matching_observers.extend(self.observers.get(event_type, []))

            # Add observers for parent event types (using dot notation hierarchy)
            parts = event_type.split(".")
            for i in range(1, len(parts)):
                parent_type = ".".join(parts[:-i])
                matching_observers.extend(self.observers.get(parent_type, []))

            # Add global observers
            matching_observers.extend(self.global_observers)

            # Remove duplicates while preserving highest priority
            # Create a dictionary keyed by observer with highest priority value
            observer_priorities = {}
            for priority, observer in matching_observers:
                if observer not in observer_priorities or priority > observer_priorities[observer]:
                    observer_priorities[observer] = priority

            # Reconstruct list with highest priorities
            matching_observers = [
                (priority, observer) for observer, priority in observer_priorities.items()
            ]

            # Sort by priority (highest first)
            matching_observers.sort(key=lambda x: x[0], reverse=True)

        # Notify observers
        for priority, observer in matching_observers:
            try:
                if hasattr(observer, "is_interested") and callable(
                    getattr(observer, "is_interested")
                ):
                    if not observer.is_interested(event_type):
                        continue

                # Call the observer and handle the event
                observer.on_event(event)

            except (AttributeError, ValueError, TypeError) as e:
                self.logger.error(
                    "Error notifying observer '%s' about event '%s': %s",
                    observer.__class__.__name__,
                    event_type,
                    str(e),
                )
                self.metrics["errors"] += 1
            except RuntimeError as e:
                self.logger.error(
                    "Runtime error in observer '%s' processing event '%s': %s",
                    observer.__class__.__name__,
                    event_type,
                    str(e),
                )
                self.metrics["errors"] += 1

        return True

    def get_event_history(
        self, event_type: str = None, limit: int = None
    ) -> list[tuple[datetime, Event]]:
        """
        Get recent events, optionally filtered by type.

        Args:
            event_type: Type of events to retrieve, or None for all
            limit: Maximum number of events to return, or None for all available

        Returns:
            List of (timestamp, event) tuples
        """
        limit = limit or self.max_history
        with self._lock:
            if event_type:
                filtered = [
                    (t, e)
                    for t, e in self.event_history
                    if self._get_event_type_safely(e) == event_type
                ]
                return filtered[-limit:]
            return self.event_history[-limit:]

    def get_metrics(self) -> dict[str, Any]:
        """
        Get event processing metrics.

        Returns:
            dict: Event processing metrics
        """
        return self.metrics

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
            for event_type, observers in self.observers.items():
                for _, observer in observers:
                    if isinstance(observer, observer_type):
                        return observer

        return None
