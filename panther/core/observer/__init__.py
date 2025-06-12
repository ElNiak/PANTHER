"""PANTHER observer package.

This package implements the observer pattern for event handling in the PANTHER framework.
Enhanced with comprehensive observer registry, metrics collection, and storage management.
"""

# Base interfaces
from .base.observer_interface import IObserver
from .base.typed_observer_interface import ITypedObserver

# Observer implementations
from .impl import (
    ExperimentObserver,
    LoggerObserver,
    MetricsObserver,
    StorageObserver,
    GUIObserver,
    PluginObserver,
)

# Event and results management
from .management import EventManager, ResultsManager

# Factory system
from .factory import (
    ObserverFactory,
    get_observer_factory,
    create_observer,
    create_default_observers,
    # Builder methods
    create_logger,
    create_metrics,
    create_storage,
    create_experiment_observer,
    create_default_observer_set,
    # Config loading
    load_observer_config,
)

# Plugin observer infrastructure
from .plugins.plugin_interface import IPluginObserver
from .plugins.plugin_observer_factory import (
    PluginObserverFactory,
    create_plugin_observer,
    register_plugin_observer,
)

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
    "GUIObserver",
    "PluginObserver",
    "IPluginObserver",
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
    "load_observer_config",
    # Plugin observer
    "PluginObserverFactory",
    "create_plugin_observer",
    "register_plugin_observer",
]
