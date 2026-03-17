"""Observer Factory Module - Centralized observer creation and management.

Provides the ``ObserverFactory`` class for creating, configuring, and managing
observer instances using Pydantic-validated configuration from the main config
pipeline (``GlobalConfig.observers``).

Default observer types registered at initialization:
    - ``"logger"`` / ``"event_logger"`` --> ``LoggerObserver``
    - ``"metrics"`` --> ``MetricsObserver``
    - ``"storage"`` --> ``StorageObserver``
    - ``"experiment"`` --> ``ExperimentObserver``
    - ``"event_stream"`` --> ``EventStreamRecorder``

Module-level convenience functions:
    - ``get_observer_factory()`` -- get/create the global factory singleton
    - ``create_observer(type, **kwargs)`` -- shorthand for factory creation
    - ``create_default_observers(config)`` -- create a standard observer set

Builder functions:
    - ``create_logger()`` -- Create a ``LoggerObserver`` with color/format config
    - ``create_metrics()`` -- Create a ``MetricsObserver`` with collection intervals
    - ``create_storage()`` -- Create a ``StorageObserver`` with path/retention config
    - ``create_experiment_observer()`` -- Create an ``ExperimentObserver`` with timing/steps
    - ``create_default_observer_set()`` -- Create the standard observer set from config dict

Example:
    Programmatic observer creation::

        factory = get_observer_factory()
        factory.register_observer_type("custom", MyCustomObserver)
        obs = factory.create_observer("custom", auto_register=True, priority=5)

    Configuration-driven creation::

        factory = get_observer_factory(global_config)
        logger_obs = factory.create_observer("logger", log_level="DEBUG")
"""

import inspect
import logging
from typing import Any, Dict, List, Optional, Union

from panther.config.core.models import BaseObserverConfig
from panther.config.core.models.observer import (
    ExperimentObserverConfig,
    LoggerObserverConfig,
    MetricsObserverConfig,
    StorageObserverConfig,
)
from panther.core.events.base.event_base import BaseEvent as Event
from panther.core.observer.base.observer_interface import IObserver
from panther.core.observer.impl import (
    EventStreamRecorder,
    ExperimentObserver,
    LoggerObserver,
    MetricsObserver,
    StorageObserver,
)
from panther.core.observer.management.event_manager import EventManager

# ── Core Factory ─────────────────────────────────────────────────────


class ObserverFactory:
    """Factory for creating and managing observer instances.

    Provides centralized observer creation with type registration, named
    instance tracking, configuration management, and optional auto-registration
    with the ``EventManager``.

    Attributes:
        _registered_types: Maps type name strings to observer classes.
        _observer_instances: Maps instance names to live observer instances.
        _configurations: Default configuration dicts per observer type.
        _event_manager: Optional EventManager for auto-registration.
        _observer_config: Pydantic-validated ``BaseObserverConfig`` for default values.

    Example:
        Register a custom type and create an instance::

            factory = ObserverFactory()
            factory.register_observer_type("my_type", MyObserver)
            obs = factory.create_observer("my_type", name="obs1", priority=5)
    """

    def __init__(
        self,
        event_manager: Optional[EventManager] = None,
        observer_config: Optional[BaseObserverConfig] = None,
    ):
        """Initialize ObserverFactory."""
        self.logger = logging.getLogger(__name__)
        self._registered_types: Dict[str, type[IObserver]] = {}
        self._observer_instances: Dict[str, IObserver] = {}
        self._configurations: Dict[str, Dict[str, Any]] = {}
        self._event_manager = event_manager
        self._observer_config = observer_config or BaseObserverConfig()
        self._initialize_default_observers()

    def _initialize_default_observers(self):
        """Initialize default observer types."""
        self._registered_types.update(
            {
                "logger": LoggerObserver,
                "event_logger": LoggerObserver,
                "metrics": MetricsObserver,
                "storage": StorageObserver,
                "experiment": ExperimentObserver,
                "event_stream": EventStreamRecorder,
            }
        )

    def set_event_manager(self, event_manager: EventManager) -> None:
        """Set the event manager for this factory.

        Args:
            event_manager: Event manager instance for registering observers
        """
        self._event_manager = event_manager
        self.logger.debug("Set event manager for observer factory")

    def register_observer_type(self, name: str, observer_class: type[IObserver]):
        """Register a custom observer type."""
        self._registered_types[name] = observer_class
        self.logger.debug("Registered observer type: %s", name)

    def create_observer(
        self,
        observer_type: str,
        name: Optional[str] = None,
        auto_register: bool = False,
        event_types: Optional[List[Union[str, Event]]] = None,
        priority: int = 0,
        **kwargs,
    ) -> IObserver:
        """Create an observer instance of the specified type.

        Args:
            observer_type: Type of observer to create
            name: Optional name to register the observer with
            auto_register: Whether to automatically register the observer with the event manager
            event_types: Optional list of event types to subscribe to if auto_register is True
            priority: Priority for observer registration if auto_register is True
            **kwargs: Configuration parameters for the observer

        Returns:
            Configured observer instance

        Raises:
            ValueError: If observer type is not registered
        """
        if observer_type not in self._registered_types:
            raise ValueError("Unknown observer type: %s" % observer_type)

        observer_class = self._registered_types[observer_type]

        # Apply any stored configuration for this type
        config = {}
        if observer_type in self._configurations:
            config.update(self._configurations[observer_type])

        # Override with provided kwargs
        config.update(kwargs)

        # Filter config to only include parameters accepted by the constructor
        sig = inspect.signature(observer_class.__init__)
        params = sig.parameters
        if not any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            accepted = set(params.keys()) - {"self"}
            config = {k: v for k, v in config.items() if k in accepted}

        try:
            observer = observer_class(**config)
            self.logger.debug("Created observer of type: %s", observer_type)

            # Store observer if name is provided
            if name:
                # Check if observer with this name already exists
                if name in self._observer_instances:
                    self.logger.warning(
                        "Observer with name '%s' already exists. Replacing with new instance.",
                        name,
                    )
                    # Unregister the old observer from event manager if it exists
                    old_observer = self._observer_instances[name]
                    if (
                        auto_register
                        and self._event_manager
                        and hasattr(self._event_manager, "unregister_observer")
                    ):
                        try:
                            self._event_manager.unregister_observer(old_observer)
                        except Exception as exc:
                            self.logger.warning(
                                "Failed to unregister old observer '%s' during replacement: %s",
                                name,
                                exc,
                            )
                self.register_observer(name, observer)

            # Auto-register with event manager if requested and event manager is set
            if auto_register and self._event_manager:
                self._event_manager.register_observer(observer, event_types, priority)
                self.logger.debug(
                    "Auto-registered observer with event manager, priority: %d",
                    priority,
                )

            return observer
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error("Failed to create observer %s: %s", observer_type, e)
            raise

    def register_observer(self, name: str, observer: IObserver) -> None:
        """Register an existing observer instance with a name.

        Args:
            name: Name to register the observer with
            observer: Observer instance to register
        """
        self._observer_instances[name] = observer
        self.logger.debug("Registered observer instance with name: %s", name)

    def unregister_observer(self, name: str) -> bool:
        """Unregister a named observer.

        Args:
            name: Name of the observer to unregister

        Returns:
            bool: True if observer was found and unregistered, False otherwise
        """
        if name in self._observer_instances:
            del self._observer_instances[name]
            self.logger.debug("Unregistered observer: %s", name)
            return True
        return False

    def get_observer(self, name: str) -> Optional[IObserver]:
        """Get a registered observer by name.

        Args:
            name: Name of the observer to retrieve

        Returns:
            Optional[IObserver]: Observer instance if found, None otherwise
        """
        return self._observer_instances.get(name, None)

    def get_all_observers(self) -> Dict[str, IObserver]:
        """Get all registered observers.

        Returns:
            Dict[str, IObserver]: Dictionary of named observer instances
        """
        return self._observer_instances.copy()

    def get_available_types(self) -> List[str]:
        """Get list of available observer types."""
        return list(self._registered_types.keys())

    def configure_observer_type(
        self, observer_type: str, config: Dict[str, Any]
    ) -> None:
        """Configure default parameters for an observer type.

        Args:
            observer_type: Type of observer to configure
            config: Configuration parameters to apply
        """
        self._configurations[observer_type] = config
        self.logger.debug("Configured observer type: %s", observer_type)

    def register_with_event_manager(
        self,
        observer: IObserver,
        event_types: Optional[List[Union[str, Event]]] = None,
        priority: int = 0,
    ) -> None:
        """Register an observer with the event manager.

        Args:
            observer: Observer instance to register
            event_types: List of event types or None for all events
            priority: Priority for observer registration

        Raises:
            RuntimeError: If no event manager is set
        """
        if not self._event_manager:
            raise RuntimeError("No event manager set. Use set_event_manager() first.")

        self._event_manager.register_observer(observer, event_types, priority)
        self.logger.debug(
            "Registered observer with event manager, priority: %d", priority
        )

    def unregister_from_event_manager(self, observer: IObserver) -> None:
        """Unregister an observer from the event manager.

        Args:
            observer: Observer instance to unregister

        Raises:
            RuntimeError: If no event manager is set
        """
        if not self._event_manager:
            raise RuntimeError("No event manager set. Use set_event_manager() first.")

        self._event_manager.unregister_observer(observer)
        self.logger.debug("Unregistered observer from event manager")

    def set_observer_config(self, observer_config: BaseObserverConfig) -> None:
        """Set the observer configuration for this factory.

        Args:
            observer_config: Observer configuration instance
        """
        self._observer_config = observer_config
        self.logger.debug("Set observer configuration for factory")

    def batch_register_with_event_manager(
        self, observers: list[tuple[IObserver, list[str | Event] | None, int]]
    ) -> None:
        """Register multiple observers with the event manager in a single call.

        Args:
            observers: List of tuples containing (observer, event_types, priority)
                      where event_types can be None for all events

        Raises:
            RuntimeError: If no event manager is set
        """
        if not self._event_manager:
            raise RuntimeError("No event manager set. Use set_event_manager() first.")

        registered_count = 0
        for observer, event_types, priority in observers:
            self._event_manager.register_observer(observer, event_types, priority)
            registered_count += 1

        self.logger.debug(
            "Batch registered %d observers with event manager", registered_count
        )


# Global factory instance
_observer_factory = None


def get_observer_factory(global_config=None) -> ObserverFactory:
    """Get the global observer factory instance.

    Args:
        global_config: Optional global configuration object containing observer configs

    Returns:
        ObserverFactory instance
    """
    global _observer_factory
    if _observer_factory is None:
        observer_config = None
        if global_config and hasattr(global_config, "observers"):
            observer_config = global_config.observers
        _observer_factory = ObserverFactory(observer_config=observer_config)
    elif global_config and hasattr(global_config, "observers"):
        # Update the observer config in the existing factory
        _observer_factory.set_observer_config(global_config.observers)
    return _observer_factory


def create_observer(observer_type: str, **kwargs) -> IObserver:
    """Convenience function to create an observer."""
    factory = get_observer_factory()
    return factory.create_observer(observer_type, **kwargs)


def create_default_observers(config: Dict[str, Any]) -> List[IObserver]:
    """Convenience function to create default observers."""
    return create_default_observer_set(config)


# ── Builder Functions ────────────────────────────────────────────────


def _create_typed_observer(
    observer_type: str,
    config_attr: str,
    default_config_cls: type,
    name: Optional[str] = None,
    global_config=None,
    auto_register: bool = False,
    event_types: Optional[list] = None,
    priority: int = 0,
    extra_config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> IObserver:
    """Shared builder logic for typed observer creation.

    Args:
        observer_type: Factory type key (e.g. "logger", "metrics")
        config_attr: Attribute name on _observer_config (e.g. "logger", "metrics")
        default_config_cls: Default Pydantic config class to use as fallback
        name: Optional name to register the observer with
        global_config: Optional global configuration object
        auto_register: Whether to auto-register with event manager
        event_types: Optional event type filter for auto-registration
        priority: Priority for observer registration
        extra_config: Extra config fields to set before kwargs merge
        **kwargs: Additional configuration parameters
    """
    factory = get_observer_factory(global_config)

    typed_config = (
        getattr(factory._observer_config, config_attr, None)
        if factory._observer_config
        else None
    ) or default_config_cls()

    config = typed_config.model_dump(exclude_none=True)
    if extra_config:
        config.update(extra_config)
    config |= kwargs

    for key in ("priority", "auto_register", "enabled"):
        config.pop(key, None)

    if priority == 0:
        priority = typed_config.priority
    if not auto_register:
        auto_register = typed_config.auto_register

    return factory.create_observer(
        observer_type,
        name=name,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        **config,
    )


def create_logger(
    name: Optional[str] = None,
    global_config=None,
    auto_register: bool = False,
    event_types: Optional[list] = None,
    priority: int = 0,
    **kwargs,
) -> LoggerObserver:
    """Create an enhanced event-aware logger observer."""
    return _create_typed_observer(
        "logger",
        "logger",
        LoggerObserverConfig,
        name=name,
        global_config=global_config,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        extra_config={"global_config": global_config},
        **kwargs,
    )


def create_metrics(
    name: Optional[str] = None,
    global_config=None,
    auto_register: bool = False,
    event_types: Optional[list] = None,
    priority: int = 0,
    output_dir: Optional[str] = None,
    metrics_collector=None,
    **kwargs,
) -> MetricsObserver:
    """Create an enhanced metrics observer."""
    return _create_typed_observer(
        "metrics",
        "metrics",
        MetricsObserverConfig,
        name=name,
        global_config=global_config,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        extra_config={"output_dir": output_dir, "metrics_collector": metrics_collector},
        **kwargs,
    )


def create_storage(
    name: Optional[str] = None,
    global_config=None,
    output_dir: Optional[str] = None,
    auto_register: bool = False,
    event_types: Optional[list] = None,
    priority: int = 0,
    **kwargs,
) -> StorageObserver:
    """Create an enhanced storage observer."""
    factory = get_observer_factory()
    storage_config = (
        getattr(factory._observer_config, "storage", None)
        if factory._observer_config
        else None
    ) or StorageObserverConfig()
    default_path = storage_config.model_dump(exclude_none=True).get(
        "storage_path", "outputs"
    )

    return _create_typed_observer(
        "storage",
        "storage",
        StorageObserverConfig,
        name=name,
        global_config=global_config,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        extra_config={"storage_path": output_dir or default_path},
        **kwargs,
    )


def create_experiment_observer(
    name: Optional[str] = None,
    test_name: Optional[str] = None,
    output_dir: Optional[str] = None,
    global_config: Any = None,
    auto_register: bool = False,
    event_types: Optional[list] = None,
    priority: int = 0,
    **kwargs,
) -> ExperimentObserver:
    """Create an enhanced experiment observer."""
    return _create_typed_observer(
        "experiment",
        "experiment",
        ExperimentObserverConfig,
        name=name,
        global_config=global_config,
        auto_register=auto_register,
        event_types=event_types,
        priority=priority,
        extra_config={
            "output_dir": output_dir or "outputs",
            "test_name": test_name,
            "global_config": global_config,
        },
        **kwargs,
    )


def create_default_observer_set(config: Dict[str, Any]) -> List[IObserver]:
    """Create a default set of observers based on configuration.

    Args:
        config: Framework configuration dictionary

    Returns:
        List of configured observer instances
    """
    factory = get_observer_factory()
    observers = []

    # Get global configuration if available
    global_config = config.get("global_config")
    output_dir = config.get("paths", {}).get("output_dir", "outputs")
    test_name = config.get("test_name")

    # Always create enhanced logger
    logger_config = config.get("observer", {}).get("logger", {})
    logger_obs = create_logger(
        name="default_logger",
        log_level=config.get("logging", {}).get("level", "INFO"),
        global_config=global_config,
        **logger_config,
    )
    observers.append(logger_obs)

    # Create metrics observer if enabled
    metrics_config = config.get("observer", {}).get("metrics", {})
    if metrics_config.get("enabled", False):
        metrics_obs = create_metrics(
            name="default_metrics", output_dir=output_dir, **metrics_config
        )
        observers.append(metrics_obs)

    # Create storage observer if enabled
    storage_config = config.get("observer", {}).get("storage", {})
    if storage_config.get("enabled", False):
        storage_obs = create_storage(
            name="default_storage", output_dir=output_dir, **storage_config
        )
        observers.append(storage_obs)

    # Always create experiment observer for tracking and coordination
    experiment_config = config.get("observer", {}).get("experiment", {})
    experiment_obs = create_experiment_observer(
        name="default_experiment",
        test_name=test_name,
        output_dir=output_dir,
        global_config=global_config,
        **experiment_config,
    )
    observers.append(experiment_obs)

    # Register with event manager if available
    if factory._event_manager:
        for observer in observers:
            factory._event_manager.register_observer(observer)

    logger = logging.getLogger(__name__)
    logger.info("Created default observer set with %d observers", len(observers))
    return observers


__all__ = [
    # Core factory
    "ObserverFactory",
    "get_observer_factory",
    "create_observer",
    "create_default_observers",
    # Builder functions
    "create_logger",
    "create_metrics",
    "create_storage",
    "create_experiment_observer",
    "create_default_observer_set",
]
