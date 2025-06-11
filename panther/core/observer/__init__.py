"""PANTHER observer package.

This package implements the observer pattern for event handling in the PANTHER framework.
Enhanced with comprehensive observer registry, metrics collection, and storage management.
"""

# Core observer infrastructure (primary API)
# from . import events  # Temporarily disabled due to missing events
from . import event_manager
from .core.observer_interface import IObserver
from .storage.event_store import EventStore
from .core.experiment_observer import ExperimentObserver
from .gui.gui_observer import GUIObserver

# Import from reorganized structure
from .plugin.plugin_interface import IPluginObserver
from .plugin.plugin_observer_factory import (
    PluginObserverFactory,
    create_plugin_observer,
    register_plugin_observer,
)

# Import from metrics
from .metrics.metrics_observer import MetricsObserver

# Import from storage
from .storage.results_manager import ResultsManager
from .storage.storage_observer import StorageObserver

# Import from logger
from .logger.logger_observer import LoggerObserver

# Factory system
from .observer_factory import (
    ObserverFactory,
    get_observer_factory,
    create_observer,
    create_default_observers,
)

# Define the public API
__all__ = [
    # Event imports
    # "events",  # Temporarily disabled due to missing events
    # Core observer classes
    "IObserver",
    "ExperimentObserver",
    "GUIObserver",
    "IPluginObserver",
    # Event handling
    "event_manager",
    "EventStore",
    # Observer implementations
    "MetricsObserver",
    "ResultsManager",
    "StorageObserver",
    "LoggerObserver",
    # Factory system classes
    "ObserverFactory",
    "get_observer_factory",
    "create_observer",
    "create_default_observers",
    "PluginObserverFactory",
    "create_plugin_observer",
    "register_plugin_observer",
]
