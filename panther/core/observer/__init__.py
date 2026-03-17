"""Observer Module - Observer Pattern Implementation for PANTHER.

This package implements a sophisticated observer pattern for PANTHER's event-driven
architecture. It provides a flexible, extensible system for monitoring, logging, and
reacting to events across the network testing framework.

Architecture::

    EventManager (singleton)
        |
        +--> register_observer(obs, event_types, priority)
        |
        +--> notify(event)
                |
                +--> Duplicate Detection (content-based + time-based)
                +--> Observer Matching (specific + hierarchical + global)
                +--> Priority-based Notification (highest first)
                +--> Error Isolation (failures don't cascade)

    ObserverFactory
        |
        +--> create_observer(type, **config)
        +--> register_observer_type(name, cls)
        +--> batch_register_with_event_manager(observers)

Key design principles:
    - **Interest-based filtering**: Observers implement ``is_interested()`` to
      efficiently filter relevant events, reducing processing overhead.
    - **Deduplication protection**: Built-in protection against duplicate event
      processing through UUID tracking and content-based signatures.
    - **Priority-based notification**: Higher-priority observers are notified
      first via priority queue ordering.
    - **Type-safe observer registration**: ``ITypedObserver`` provides automatic
      event routing to typed handler methods with compile-time type checking.
    - **Thread-safe observer management**: RLock-based synchronization for
      concurrent access in all management classes.
    - **Configuration-driven**: Factory module supports programmatic
      observer setup via Pydantic-validated config.

Event Processing Pipeline:
    1. **Event Emission** -- Events broadcast through ``EventManager.notify()``
    2. **Interest Filtering** -- Only interested observers receive events
    3. **Deduplication** -- Previously processed events filtered out
    4. **Event Handling** -- Observer-specific processing logic executes
    5. **State Updates** -- Observer state updated based on event content
    6. **Result Aggregation** -- Results collected by ``ResultsManager``

Built-in Observer Types:
    - **LoggerObserver**: Structured event logging with color-coded terminal output,
      severity indicators, and TQDM integration.
    - **MetricsObserver**: CPU, memory, network monitoring, test timing, and
      resource metric aggregation.
    - **StorageObserver**: Event persistence for audit and analytics with file
      output and event serialization.
    - **ExperimentObserver**: High-level experiment execution coordination,
      multi-test orchestration, and result aggregation.

Example:
    Create and register a custom observer::

        from panther.core.observer import IObserver, EventManager
        from panther.core.events.base.event_base import BaseEvent

        class MyObserver(IObserver):
            def is_interested(self, event_type: str) -> bool:
                return event_type.startswith("test.")

            def on_event(self, event: BaseEvent):
                if event.id in self.processed_events_uuids:
                    return
                print(f"Event: {event.event_type}")
                self.processed_events_uuids.append(event.id)

        event_manager = EventManager.get_instance()
        event_manager.register_observer(MyObserver(), priority=5)

    Use the factory for configuration-driven creation::

        from panther.core.observer import get_observer_factory

        factory = get_observer_factory()
        logger_obs = factory.create_observer("logger", auto_register=True)

See Also:
    `panther.core.events` -- Event system implementation
    `panther.core.observer.management.event_manager` -- Central event coordination
    `panther.core.observer.factory` -- Observer creation, builders, and configuration
    `panther.core.observer.workflow` -- Workflow state tracking
"""

# Base interfaces
from .base.observer_interface import IObserver
from .base.typed_observer_interface import ITypedObserver

# Factory system
from .factory import (  # Builder methods
    ObserverFactory,
    create_default_observer_set,
    create_default_observers,
    create_experiment_observer,
    create_logger,
    create_metrics,
    create_observer,
    create_storage,
    get_observer_factory,
)

# Observer implementations
from .impl import (
    ExperimentObserver,
    LoggerObserver,
    MetricsObserver,
    PluginObserver,
    StorageObserver,
)

# Event and results management
from .management import EventManager, ResultsManager

# Define the public API
__all__ = [
    # Base interfaces
    "IObserver",
    "ITypedObserver",
    # Observer implementations
    "ExperimentObserver",
    "LoggerObserver",
    "MetricsObserver",
    "StorageObserver",
    "PluginObserver",
    # Management
    "EventManager",
    "ResultsManager",
    # Factory system
    "ObserverFactory",
    "get_observer_factory",
    "create_observer",
    "create_default_observers",
    "create_logger",
    "create_metrics",
    "create_storage",
    "create_experiment_observer",
    "create_default_observer_set",
]
