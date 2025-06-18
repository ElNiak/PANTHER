"""Observer factory system."""

from .factory_builders import (
    create_default_observer_set,
    create_experiment_observer,
    create_logger,
    create_metrics,
    create_storage,
)
from .factory_config import (
    create_and_register_observer_set,
    create_observer_by_class_path,
    load_config_directory,
    load_config_file,
    load_observer_config,
)
from .observer_factory import (
    ObserverFactory,
    create_default_observers,
    create_observer,
    get_observer_factory,
)

__all__ = [
    # Core factory
    "ObserverFactory",
    "get_observer_factory",
    "create_observer",
    "create_default_observers",
    # Builder methods
    "create_logger",
    "create_metrics",
    "create_storage",
    "create_experiment_observer",
    "create_default_observer_set",
    # Config loading
    "load_observer_config",
    "load_config_file",
    "load_config_directory",
    "create_and_register_observer_set",
    "create_observer_by_class_path",
]
