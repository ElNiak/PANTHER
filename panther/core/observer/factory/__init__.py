"""Observer factory system."""

from .observer_factory import (
    ObserverFactory,
    get_observer_factory,
    create_observer,
    create_default_observers,
)
from .factory_builders import (
    create_logger,
    create_metrics,
    create_storage,
    create_experiment_observer,
    create_default_observer_set,
)
from .factory_config import (
    load_observer_config,
    load_config_file,
    load_config_directory,
    create_and_register_observer_set,
    create_observer_by_class_path,
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
