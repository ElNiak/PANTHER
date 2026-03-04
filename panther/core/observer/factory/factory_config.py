"""Observer Factory Configuration Module - YAML config loading and class-path instantiation.

Handles configuration-driven observer creation from YAML files or dictionaries.
Supports loading individual config files, entire directories of YAML files,
and dynamic observer instantiation via Python class paths (with a security
whitelist of allowed modules).

YAML configuration format::

    observers:
      - id: my_logger
        class_path: panther.core.observer.impl.logger_observer.LoggerObserver
        enabled: true
        params:
          log_level: DEBUG
        event_types: ["test.started", "test.completed"]
        priority: 5

Security:
    ``create_observer_by_class_path()`` only allows instantiation from a fixed
    whitelist of ``panther.core.observer.impl.*`` modules to prevent arbitrary
    code execution from config files.

See Also:
    :mod:`panther.core.observer.factory.observer_factory`
    :mod:`panther.core.observer.factory.factory_builders`
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None

from panther.core.observer.base.observer_interface import IObserver

from .observer_factory import get_observer_factory


def load_observer_config(path: Union[str, Path]) -> bool:
    """

    Convenience function to load observer configuration.

    Args:
        path: Path to configuration file or directory

    Returns:
        bool: True if loading was successful
    """
    factory = get_observer_factory()
    path_obj = Path(path)

    if path_obj.is_dir():
        return load_config_directory(path) > 0
    else:
        return load_config_file(path)


def load_config_file(config_path: Union[str, Path]) -> bool:
    """
    Load observer configurations from a YAML file.

    Args:
        config_path: Path to the observer configuration YAML file

    Returns:
        bool: True if loading was successful
    """
    factory = get_observer_factory()
    logger = logging.getLogger(__name__)

    if yaml is None:
        logger.error("PyYAML is not installed. Cannot load YAML config.")
        return False

    try:
        with open(config_path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if not isinstance(config_data, dict) or "observers" not in config_data:
            logger.error("Invalid configuration format in %s", config_path)
            return False

        success = _load_config_dict(config_data)
        if success:
            factory._config_paths.append(Path(config_path))
        return success

    except (OSError, ValueError, TypeError) as e:
        logger.error("Error loading observer config from %s: %s", config_path, e)
        return False


def load_config_directory(directory: Union[str, Path]) -> int:
    """
    Load observer configurations from all YAML files in directory.

    Args:
        directory: Path to directory containing YAML files

    Returns:
        int: Number of files successfully loaded
    """
    logger = logging.getLogger(__name__)
    directory_path = Path(directory)

    if not directory_path.exists() or not directory_path.is_dir():
        logger.error("Configuration directory does not exist: %s", directory)
        return 0

    load_count = 0
    for file_path in directory_path.glob("*.y*ml"):  # Match both .yml and .yaml
        if load_config_file(file_path):
            load_count += 1

    logger.info("Loaded %d configuration files from %s", load_count, directory)
    return load_count


def _load_config_dict(config_data: Dict[str, Any]) -> bool:
    """
    Load observer configurations from a dictionary.

    Args:
        config_data: Dictionary containing observer configuration

    Returns:
        bool: True if loading was successful
    """
    factory = get_observer_factory()
    logger = logging.getLogger(__name__)

    if not isinstance(config_data, dict) or "observers" not in config_data:
        logger.error("Invalid configuration format: missing observers key")
        return False

    observers_data = config_data["observers"]
    if not isinstance(observers_data, list):
        logger.error("Invalid configuration: observers must be a list")
        return False

    load_count = 0
    for idx, observer_data in enumerate(observers_data):
        try:
            # Check if observer is enabled
            if not observer_data.get("enabled", True):
                continue

            # Get observer ID or generate one
            observer_id = observer_data.get("id")
            class_path = observer_data.get("class_path")

            if not class_path:
                logger.error("Missing class_path for observer #%d", idx)
                continue

            if not observer_id:
                # Generate ID from class name
                observer_id = class_path.split(".")[-1]
                if idx > 0:
                    # Ensure uniqueness
                    observer_id = f"{observer_id}_{idx}"

            # Get parameters
            params = observer_data.get("params", {})

            # Create the observer
            observer = create_observer_by_class_path(
                class_path, name=observer_id, **params
            )

            # Register with event manager if needed
            if factory._event_manager:
                event_types = observer_data.get("event_types")
                priority = observer_data.get("priority", 0)
                factory.register_with_event_manager(observer, event_types, priority)

            load_count += 1

        except (ValueError, ImportError, AttributeError, TypeError) as e:
            logger.error("Error processing observer #%d: %s", idx, e)

    logger.info("Loaded %d observers from configuration", load_count)
    return load_count > 0


def create_observer_by_class_path(
    class_path: str, name: Optional[str] = None, **kwargs
) -> IObserver:
    """
    Create an observer by class path.

    Args:
        class_path: Python import path to observer class
        name: Optional name to register observer with
        **kwargs: Arguments to pass to the observer constructor

    Returns:
        Configured observer instance

    Raises:
        ImportError: If module cannot be imported
        AttributeError: If class cannot be found
        ValueError: If class is not an IObserver or if the class_path is not in the whitelist
    """
    factory = get_observer_factory()
    logger = logging.getLogger(__name__)

    try:
        # Split into module and class
        module_path, class_name = class_path.rsplit(".", 1)

        # Security check: Only allow specific modules
        # This is a fixed whitelist to prevent arbitrary code execution
        allowed_modules = [
            "panther.core.observer.impl.logger_observer",
            "panther.core.observer.impl.metrics_observer",
            "panther.core.observer.impl.storage_observer",
            "panther.core.observer.impl.experiment_observer",
            "panther.core.observer.impl.gui.gui_observer",
            "panther.core.observer.impl.plugin_observer",
        ]

        if module_path not in allowed_modules:
            raise ValueError(
                "Security error: Module %s is not in the allowed observer modules list"
                % module_path
            )

        # Import the module
        module = importlib.import_module(module_path)

        # Get the class
        observer_class = getattr(module, class_name)

        # Instantiate with parameters
        observer_instance = observer_class(**kwargs)

        # Verify it's an observer
        if not isinstance(observer_instance, IObserver):
            raise ValueError("Class %s is not an IObserver" % class_name)

        # Register if name provided
        if name:
            factory.register_observer(name, observer_instance)

        return observer_instance

    except ImportError as e:
        logger.error("Could not import module %s: %s", module_path, e)
        raise
    except AttributeError as e:
        logger.error("Class %s not found in %s: %s", class_name, module_path, e)
        raise
    except Exception as e:
        logger.error("Error creating observer by class path %s: %s", class_path, e)
        raise


def create_and_register_observer_set(
    observer_configs: List[Dict[str, Any]]
) -> List[IObserver]:
    """
    Create and register multiple observers based on configuration dictionaries.

    Args:
        observer_configs: List of dictionaries with observer configurations.
                         Each dictionary must contain 'type' key and can optionally contain
                         'name', 'auto_register', 'event_types', 'priority', and other config parameters.

    Returns:
        List of created and registered observer instances

    Raises:
        RuntimeError: If auto_register is True but no event manager is set
        ValueError: If an observer type is not recognized
    """
    factory = get_observer_factory()
    logger = logging.getLogger(__name__)

    if not factory._event_manager and any(
        conf.get("auto_register", False) for conf in observer_configs
    ):
        raise RuntimeError("No event manager set. Use set_event_manager() first.")

    observers = []

    for idx, config in enumerate(observer_configs):
        if "type" not in config:
            logger.error("Missing observer type in configuration #%d", idx)
            continue

        observer_type = config.pop("type")
        name = config.pop("name", None)
        auto_register = config.pop("auto_register", False)
        event_types = config.pop("event_types", None)
        priority = config.pop("priority", 0)

        try:
            observer = factory.create_observer(
                observer_type,
                name=name,
                auto_register=auto_register,
                event_types=event_types,
                priority=priority,
                **config,
            )
            observers.append(observer)
        except ValueError as e:
            logger.error("Failed to create observer #%d: %s", idx, e)

    logger.info("Created and registered %d observers", len(observers))
    return observers


# Transition functions for legacy code
def create_observer_from_registry_type(observer_type_enum: Any, **kwargs) -> IObserver:
    """
    Transition function for code using ObserverType from observer_registry.

    Args:
        observer_type_enum: ObserverType enum from observer_registry
        **kwargs: Configuration parameters for the observer

    Returns:
        Configured observer instance
    """
    # Map from ObserverRegistry.ObserverType to string type
    type_map = {
        "LOGGER": "logger",
        "METRICS": "metrics",
        "STORAGE": "storage",
        "EVENT_LOGGER": "event_logger",
        "EXPERIMENT": "experiment",
    }

    # Get string type from enum
    if hasattr(observer_type_enum, "name"):
        observer_type = type_map.get(observer_type_enum.name, "logger")
    elif isinstance(observer_type_enum, str):
        observer_type = type_map.get(observer_type_enum.upper(), "logger")
    else:
        observer_type = "logger"

    # Create observer using the factory
    factory = get_observer_factory()
    return factory.create_observer(observer_type, **kwargs)


def convert_config_to_factory_params(observer_config: Any) -> Dict[str, Any]:
    """
    Convert observer_config.ObserverConfig to factory parameters.

    Args:
        observer_config: ObserverConfig from observer_config

    Returns:
        Dictionary of parameters for create_observer
    """
    params = {}

    if hasattr(observer_config, "params"):
        params.update(observer_config.params)

    if hasattr(observer_config, "enabled"):
        params["enabled"] = observer_config.enabled

    if hasattr(observer_config, "priority"):
        params["priority"] = observer_config.priority

    return params
