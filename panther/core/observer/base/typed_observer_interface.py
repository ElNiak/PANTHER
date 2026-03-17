"""Typed Observer Interface Module - Automatic event routing for PANTHER observers.

This module provides ``ITypedObserver``, an enhanced observer interface that
extends ``IObserver`` with automatic event routing to typed handler methods.
Instead of implementing a single ``on_event()`` with manual type-switching,
subclasses override only the ``on_*`` handler methods they need.

Dispatch strategy:
    1. **Type-based** -- Kept subclasses (e.g., ``TestCompletedEvent``,
       ``DockerBuildStartedEvent``) and metrics events are dispatched by
       ``type(event)`` lookup.
    2. **Name-based** -- All factory-created events are dispatched by
       ``(event.entity_type, event.name)`` to a handler method name resolved
       via ``getattr``. This allows subclasses to define handlers without
       requiring base class stubs.

Handler naming convention:
    ``on_{entity_prefix}_{event_name}`` where the entity prefix comes from
    the ``_ENTITY_PREFIX`` map.  Dot-separated event names (e.g.
    ``network.setup.started``) are handled via ``_HANDLER_OVERRIDES``.

Example:
    Create a typed observer that only handles test lifecycle events::

        from panther.core.observer.base.typed_observer_interface import ITypedObserver

        class TestLifecycleObserver(ITypedObserver):
            def on_test_created(self, event):
                print(f"Test created: {event.entity_id}")
                return True

            def on_test_completed(self, event):
                print(f"Test completed: {event.entity_id}")
                return True

See Also:
    `panther.core.observer.base.observer_interface.IObserver`
"""

import logging
from collections.abc import Callable
from typing import Dict, Tuple

from panther.core.events.base.event_base import BaseEvent, EventType

# Kept subclasses that use isinstance() or have custom attributes
from panther.core.events.experiment.events import (
    ExperimentFinishedEarlyEvent,
    ExperimentServiceFailureEvent,
)
from panther.core.events.metrics.events import (
    CounterMetricEvent,
    MetricCollectedEvent,
    MetricsSummaryEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
)
from panther.core.events.service.events import (
    DockerBuildCompletedEvent,
    DockerBuildFailedEvent,
    DockerBuildStartedEvent,
)
from panther.core.events.test.events import (
    EnhancedResultEvent,
    TestCompletedEvent,
    TestFailedEvent,
    TestResultEvent,
)

from .observer_interface import IObserver

# Maps entity_type to the prefix used in handler method names.
_ENTITY_PREFIX: Dict[EventType, str] = {
    EventType.EXPERIMENT: "experiment",
    EventType.TEST: "test",
    EventType.SERVICE: "service",
    EventType.ENVIRONMENT: "environment",
    EventType.STEP: "step",
    EventType.ASSERTION: "assertion",
    EventType.METRICS: "metrics",
    EventType.PLUGIN: "plugin",
}

# Maps (entity_type, event_name) → handler method name for cases where
# the convention ``on_{prefix}_{name}`` does not hold.
_HANDLER_OVERRIDES: Dict[Tuple[EventType, str], str] = {
    # Assertion handlers use mixed singular/plural naming
    (EventType.ASSERTION, "validation_started"): "on_assertions_validation_started",
    (EventType.ASSERTION, "validation_completed"): "on_assertions_validation_completed",
    (EventType.ASSERTION, "progress"): "on_assertion_progress",
    (EventType.ASSERTION, "result"): "on_assertion_result",
    (EventType.ASSERTION, "error"): "on_assertion_error",
    (EventType.ASSERTION, "unknown"): "on_assertion_unknown",
}


def _handler_name_for(entity_type: EventType, event_name: str) -> str:
    """Derive handler method name from entity type and event name.

    Checks ``_HANDLER_OVERRIDES`` first, then falls back to the convention
    ``on_{prefix}_{event_name}``.
    """
    override = _HANDLER_OVERRIDES.get((entity_type, event_name))
    if override:
        return override
    prefix = _ENTITY_PREFIX.get(entity_type, entity_type.value)
    safe_name = event_name.replace(".", "_")
    return f"on_{prefix}_{safe_name}"


class ITypedObserver(IObserver):
    """Enhanced observer interface with automatic event routing to typed handlers.

    Extends ``IObserver`` to provide automatic routing of events to named
    ``on_*`` handler methods. Subclasses override only the handlers they need;
    unhandled events are logged at DEBUG level and return ``True``.

    Dispatch order:
        1. Exact ``type(event)`` lookup in ``_type_handlers`` (kept subclasses,
           metrics events).
        2. ``(entity_type, event_name)`` lookup resolved to a handler method name
           via ``getattr(self, handler_name)``.
        3. Fall through to ``on_unknown_event()``.

    Error handling:
        - Exceptions in individual handlers are caught and logged without
          propagating to other observers.
        - ``RecursionError`` is caught specially and logged at ERROR level.
        - Error/failure event handlers are logged at ERROR level to avoid cascading events.
    """

    def __init__(self):
        """Initialize ITypedObserver."""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Type-based dispatch for kept subclasses and metrics events
        self._type_handlers: Dict[type, Callable] = {
            # Test events (kept for isinstance() / custom attributes)
            TestCompletedEvent: self.on_test_completed,
            TestFailedEvent: self.on_test_failed,
            TestResultEvent: self.on_test_result,
            EnhancedResultEvent: self.on_enhanced_result,
            # Experiment events (kept for isinstance() / custom properties)
            ExperimentFinishedEarlyEvent: self.on_experiment_finished_early,
            ExperimentServiceFailureEvent: self.on_experiment_service_failure,
            # Service events (kept as subclasses)
            DockerBuildStartedEvent: self.on_docker_build_started,
            DockerBuildCompletedEvent: self.on_docker_build_completed,
            DockerBuildFailedEvent: self.on_docker_build_failed,
            # Metrics events (kept as subclasses with validate() methods)
            MetricCollectedEvent: self.on_metric_collected,
            ResourceMetricEvent: self.on_resource_metric,
            TimingMetricEvent: self.on_timing_metric,
            CounterMetricEvent: self.on_counter_metric,
            MetricsSummaryEvent: self.on_metrics_summary,
        }

    def on_event(self, event: BaseEvent):
        """Route an event to its specific typed handler method.

        Tries type-based dispatch first (for kept subclasses and metrics),
        then name-based dispatch for factory-created events. Falls back to
        ``on_unknown_event()`` for unregistered event types.

        Args:
            event: The event to route and handle.

        Returns:
            The return value from the matched handler, or False on error.
        """
        # Deduplication check via event.id
        if hasattr(event, "id"):
            if event.id in self.processed_events_uuids:
                return True
            self.processed_events_uuids.add(event.id)

        # 1. Try exact type match (kept subclasses, metrics)
        handler = self._type_handlers.get(type(event))

        if handler is None:
            # 2. Try name-based dispatch
            handler_name = _handler_name_for(event.entity_type, event.name)
            handler = getattr(self, handler_name, None)

        if handler is None:
            return self.on_unknown_event(event)

        try:
            return handler(event)
        except RecursionError:
            logging.getLogger("ITypedObserver").error(
                "RecursionError in handler for %s", event.name
            )
            return False
        except Exception as e:
            # Avoid cascading events from error handlers
            if event.name in ("failed", "error"):
                logging.getLogger("ITypedObserver").error(
                    "Error handling %s: %s", event.name, e
                )
            else:
                self.logger.error(
                    "Error handling event %s in %s: %s",
                    event.name,
                    self.__class__.__name__,
                    str(e),
                    exc_info=True,
                )
            return False

    def on_unknown_event(self, event: BaseEvent) -> bool:
        """Handle event types not matched by any dispatch path.

        Default implementation logs a debug warning and returns True.
        Override this method to handle custom or unregistered event types.
        """
        self.logger.debug(
            "Received unknown event type: %s (name=%s) in observer: %s",
            type(event).__name__,
            event.name,
            self.__class__.__name__,
        )
        return True

    # -- Kept-subclass handlers (must exist for _type_handlers bindings) ------

    def on_test_completed(self, event) -> bool:
        """Handle test completed event."""
        return True

    def on_test_failed(self, event) -> bool:
        """Handle test failed event."""
        return True

    def on_test_result(self, event) -> bool:
        """Handle basic test result event."""
        return True

    def on_enhanced_result(self, event) -> bool:
        """Handle enhanced test result event."""
        return True

    def on_experiment_finished_early(self, event) -> bool:
        """Handle experiment finished early event."""
        return True

    def on_experiment_service_failure(self, event) -> bool:
        """Handle experiment service failure event."""
        return True

    def on_docker_build_started(self, event) -> bool:
        """Handle Docker build started event."""
        return True

    def on_docker_build_completed(self, event) -> bool:
        """Handle Docker build completed event."""
        return True

    def on_docker_build_failed(self, event) -> bool:
        """Handle Docker build failed event."""
        return True

    def on_metric_collected(self, event) -> bool:
        """Handle metric collected event."""
        return True

    def on_resource_metric(self, event) -> bool:
        """Handle resource metric event."""
        return True

    def on_timing_metric(self, event) -> bool:
        """Handle timing metric event."""
        return True

    def on_counter_metric(self, event) -> bool:
        """Handle counter metric event."""
        return True

    def on_metrics_summary(self, event) -> bool:
        """Handle metrics summary event."""
        return True

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer might handle the given event type.

        Uses partial string matching against known entity types and handler
        method names.

        Args:
            event_type: Event type string to check interest for.

        Returns:
            True if a matching handler likely exists.
        """
        if not event_type or len(event_type) < 2:
            return False

        event_type_lower = event_type.lower()

        # Check type-based handlers (bidirectional prefix matching)
        for event_class in self._type_handlers:
            class_lower = event_class.__name__.lower()
            if class_lower.startswith(event_type_lower) or event_type_lower.startswith(
                class_lower
            ):
                return True

        # Check if any entity prefix matches (bidirectional prefix matching)
        for prefix in _ENTITY_PREFIX.values():
            if prefix.startswith(event_type_lower) or event_type_lower.startswith(
                prefix
            ):
                return True

        return False
