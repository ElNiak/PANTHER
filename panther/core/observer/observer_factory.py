"""
Observer Factory Module

Centralized factory for creating and configuring observer instances with
enhanced capabilities and unified configuration management.

This is the primary implementation for observer creation and management in PANTHER.
"""

import logging
import importlib
from typing import Any
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from panther.config.config_observer_schema import (
    ObserverConfig,
    LoggerObserverConfig,
    MetricsObserverConfig,
    StorageObserverConfig,
    ExperimentObserverConfig,
)

from .core.observer_interface import IObserver
from .logger.logger_observer import LoggerObserver
from .metrics.metrics_observer import MetricsObserver
from .storage.storage_observer import StorageObserver
from .core.experiment_observer import ExperimentObserver
from .event_manager import EventManager
from .events import Event

# Import plugin observer factory


class ObserverFactory:
    """
    Factory class for creating observer instances with enhanced capabilities.

    This factory provides a centralized way to create observers with proper
    configuration and enhanced features. It combines the functionality of
    both the observer registry and configuration systems.
    """

    def __init__(
        self,
        event_manager: EventManager | None = None,
        observer_config: ObserverConfig | None = None,
    ):
        self.logger = logging.getLogger(__name__)
        self._registered_types: dict[str, type[IObserver]] = {}  # Observer class types
        self._observer_instances: dict[str, IObserver] = {}  # Named observer instances
        self._configurations: dict[str, dict[str, Any]] = {}  # Observer configurations
        self._event_manager = event_manager  # Event manager for registering observers
        self._config_paths: list[Path] = []  # Paths of loaded configuration files
        self._observer_config = observer_config or ObserverConfig()  # Global observer configuration
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
            }
        )

    def set_event_manager(self, event_manager: EventManager) -> None:
        """
        Set the event manager for this factory.

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
        name: str | None = None,
        auto_register: bool = False,
        event_types: list[str | Event] | None = None,
        priority: int = 0,
        **kwargs,
    ) -> IObserver:
        """
        Create an observer instance of the specified type.

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

        try:
            observer = observer_class(**config)
            self.logger.debug("Created observer of type: %s", observer_type)

            # Store observer if name is provided
            if name:
                self.register_observer(name, observer)

            # Auto-register with event manager if requested and event manager is set
            if auto_register and self._event_manager:
                self._event_manager.register_observer(observer, event_types, priority)
                self.logger.debug(
                    "Auto-registered observer with event manager, priority: %d", priority
                )

            return observer
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.error("Failed to create observer %s: %s", observer_type, e)
            raise

    def create_logger(
        self,
        name: str | None = None,
        global_config=None,
        auto_register: bool = False,
        event_types: list[str | Event] | None = None,
        priority: int = 0,
        **kwargs,
    ) -> LoggerObserver:
        """
        Create an enhanced event-aware logger observer.

        Args:
            name: Optional name to register the observer with
            global_config: Global configuration for the logger
            auto_register: Whether to automatically register the observer with the event manager
            event_types: Optional list of event types to subscribe to if auto_register is True
            priority: Priority for observer registration if auto_register is True
            **kwargs: Additional configuration parameters

        Returns:
            LoggerObserver: Configured logger observer
        """
        # Start with default config from observer_config if available
        logger_config = (
            self._observer_config.logger
            if hasattr(self, "_observer_config")
            else LoggerObserverConfig()
        )

        # Create config dictionary from the logger_config dataclass
        config = {
            "log_level": logger_config.log_level,
            "include_data": logger_config.include_data,
            "include_event_id": logger_config.include_event_id,
            "include_timestamp": logger_config.include_timestamp,
            "enable_colors": logger_config.enable_colors,
            "output_file": logger_config.output_file,
            "correlation_tracking": logger_config.correlation_tracking,
            "structured_output": logger_config.structured_output,
            "max_data_length": logger_config.max_data_length,
            "global_config": global_config,
        }

        # Override with any provided kwargs
        config.update(kwargs)

        # Use configured priority if not explicitly provided
        if priority == 0 and hasattr(logger_config, "priority"):
            priority = logger_config.priority

        # Use configured auto_register if not explicitly provided
        if not auto_register and hasattr(logger_config, "auto_register"):
            auto_register = logger_config.auto_register

        return self.create_observer(
            "logger",
            name=name,
            auto_register=auto_register,
            event_types=event_types,
            priority=priority,
            **config,
        )

    def create_metrics(
        self,
        name: str | None = None,
        auto_register: bool = False,
        event_types: list[str | Event] | None = None,
        priority: int = 0,
        output_dir: str | None = None,
        metrics_collector=None,
        **kwargs,
    ) -> MetricsObserver:
        """
        Create an enhanced metrics observer.

        Args:
            name: Optional name to register the observer with
            auto_register: Whether to automatically register the observer with the event manager
            event_types: Optional list of event types to subscribe to if auto_register is True
            priority: Priority for observer registration if auto_register is True
            **kwargs: Configuration parameters

        Returns:
            MetricsObserver: Configured metrics observer
        """
        # Start with default config from observer_config if available
        metrics_config = (
            self._observer_config.metrics
            if hasattr(self, "_observer_config")
            else MetricsObserverConfig()
        )

        # Create config dictionary from the metrics_config dataclass
        config = {
            "log_level": metrics_config.log_level,
            "publish_metrics": metrics_config.publish_metrics,
            "collect_system_metrics": metrics_config.collect_system_metrics,
            "publish_interval": metrics_config.publish_interval,
            "enable_real_time_monitoring": metrics_config.enable_real_time_monitoring,
            "resource_collection_interval": metrics_config.resource_collection_interval,
            "metric_collection_interval": metrics_config.metric_collection_interval,
        }

        # Override with any provided kwargs
        config.update(kwargs)

        # Use configured priority if not explicitly provided
        if priority == 0 and hasattr(metrics_config, "priority"):
            priority = metrics_config.priority

        # Use configured auto_register if not explicitly provided
        if not auto_register and hasattr(metrics_config, "auto_register"):
            auto_register = metrics_config.auto_register

        return self.create_observer(
            "metrics",
            name=name,
            auto_register=auto_register,
            event_types=event_types,
            priority=priority,
            **config,
        )

    def create_storage(
        self,
        name: str | None = None,
        output_dir: str | None = None,
        auto_register: bool = False,
        event_types: list[str | Event] | None = None,
        priority: int = 0,
        **kwargs,
    ) -> StorageObserver:
        """
        Create an enhanced storage observer.

        Args:
            name: Optional name to register the observer with
            output_dir: Output directory for storage
            auto_register: Whether to automatically register the observer with the event manager
            event_types: Optional list of event types to subscribe to if auto_register is True
            priority: Priority for observer registration if auto_register is True
            **kwargs: Additional configuration parameters

        Returns:
            StorageObserver: Configured storage observer
        """
        # Start with default config from observer_config if available
        storage_config = (
            self._observer_config.storage
            if hasattr(self, "_observer_config")
            else StorageObserverConfig()
        )

        # Create config dictionary from the storage_config dataclass
        config = {
            "log_level": storage_config.log_level,
            "storage_path": output_dir or storage_config.storage_path or "outputs",
            "auto_backup": storage_config.auto_backup,
            "enable_compression": storage_config.enable_compression,
            "max_storage_size": storage_config.max_storage_size,
            "backup_interval": storage_config.backup_interval,
            "retention_days": storage_config.retention_days,
            "batch_size": storage_config.batch_size,
            "async_storage": storage_config.async_storage,
        }

        # Override with any provided kwargs
        config.update(kwargs)

        # Use configured priority if not explicitly provided
        if priority == 0 and hasattr(storage_config, "priority"):
            priority = storage_config.priority

        # Use configured auto_register if not explicitly provided
        if not auto_register and hasattr(storage_config, "auto_register"):
            auto_register = storage_config.auto_register

        return self.create_observer(
            "storage",
            name=name,
            auto_register=auto_register,
            event_types=event_types,
            priority=priority,
            **config,
        )

    def create_experiment_observer(
        self,
        name: str | None = None,
        test_name: str | None = None,
        output_dir: str | None = None,
        global_config: Any = None,
        auto_register: bool = False,
        event_types: list[str | Event] | None = None,
        priority: int = 0,
        **kwargs,
    ) -> ExperimentObserver:
        """
        Create an enhanced experiment observer.

        Args:
            name: Optional name to register the observer with
            test_name: Name of the test being observed
            output_dir: Output directory path
            global_config: Global configuration object
            auto_register: Whether to automatically register the observer with the event manager
            event_types: Optional list of event types to subscribe to if auto_register is True
            priority: Priority for observer registration if auto_register is True
            **kwargs: Additional configuration parameters

        Returns:
            ExperimentObserver: Configured experiment observer
        """
        # Start with default config from observer_config if available
        exp_config = (
            self._observer_config.experiment
            if hasattr(self, "_observer_config")
            else ExperimentObserverConfig()
        )

        # Create config dictionary from the exp_config dataclass
        config = {
            "log_level": exp_config.log_level,
            "output_dir": output_dir or exp_config.output_dir or "outputs",
            "test_name": test_name or exp_config.test_name,
            "track_timing": exp_config.track_timing,
            "track_steps": exp_config.track_steps,
            "global_config": global_config,
        }

        # Override with any provided kwargs
        config.update(kwargs)

        # Use configured priority if not explicitly provided
        if priority == 0 and hasattr(exp_config, "priority"):
            priority = exp_config.priority

        # Use configured auto_register if not explicitly provided
        if not auto_register and hasattr(exp_config, "auto_register"):
            auto_register = exp_config.auto_register

        return self.create_observer(
            "experiment",
            name=name,
            auto_register=auto_register,
            event_types=event_types,
            priority=priority,
            **config,
        )

    def create_default_observer_set(self, config: dict[str, Any]) -> list[IObserver]:
        """
        Create a default set of observers based on configuration.

        Args:
            config: Framework configuration dictionary

        Returns:
            List of configured observer instances
        """
        observers = []

        # Get global configuration if available
        global_config = config.get("global_config", None)
        output_dir = config.get("paths", {}).get("output_dir", "outputs")
        test_name = config.get("test_name", None)

        # Always create enhanced logger
        logger_config = config.get("observer", {}).get("logger", {})
        logger_obs = self.create_logger(
            name="default_logger",
            log_level=config.get("logging", {}).get("level", "INFO"),
            global_config=global_config,
            **logger_config,
        )
        observers.append(logger_obs)

        # Create metrics observer if enabled
        metrics_config = config.get("observer", {}).get("metrics", {})
        if metrics_config.get("enabled", False):
            metrics_obs = self.create_metrics(name="default_metrics", **metrics_config)
            observers.append(metrics_obs)

        # Create storage observer if enabled
        storage_config = config.get("observer", {}).get("storage", {})
        if storage_config.get("enabled", False):
            storage_obs = self.create_storage(
                name="default_storage", output_dir=output_dir, **storage_config
            )
            observers.append(storage_obs)

        # Always create experiment observer for tracking and coordination
        experiment_config = config.get("observer", {}).get("experiment", {})
        experiment_obs = self.create_experiment_observer(
            name="default_experiment",
            test_name=test_name,
            output_dir=output_dir,
            global_config=global_config,
            **experiment_config,
        )
        observers.append(experiment_obs)

        # Create resource observer if enabled
        resource_config = config.get("observer", {}).get("resource", {})
        if resource_config.get("enabled", False):
            resource_obs = self.create_resource_observer(
                name="default_resource", auto_register=True, **resource_config
            )
            observers.append(resource_obs)

        # Register with event manager if available
        if self._event_manager:
            for observer in observers:
                self._event_manager.register_observer(observer)

        self.logger.info("Created default observer set with %d observers", len(observers))
        return observers

    def get_available_types(self) -> list[str]:
        """Get list of available observer types."""
        return list(self._registered_types.keys())

    def register_observer(self, name: str, observer: IObserver) -> None:
        """
        Register an existing observer instance with a name.

        Args:
            name: Name to register the observer with
            observer: Observer instance to register
        """
        self._observer_instances[name] = observer
        self.logger.debug("Registered observer instance with name: %s", name)

    def unregister_observer(self, name: str) -> bool:
        """
        Unregister a named observer.

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

    def get_observer(self, name: str) -> IObserver | None:
        """
        Get a registered observer by name.

        Args:
            name: Name of the observer to retrieve

        Returns:
            Optional[IObserver]: Observer instance if found, None otherwise
        """
        return self._observer_instances.get(name, None)

    def get_all_observers(self) -> dict[str, IObserver]:
        """
        Get all registered observers.

        Returns:
            Dict[str, IObserver]: Dictionary of named observer instances
        """
        return self._observer_instances.copy()

    def configure_observer_type(self, observer_type: str, config: dict[str, Any]) -> None:
        """
        Configure default parameters for an observer type.

        Args:
            observer_type: Type of observer to configure
            config: Configuration parameters to apply
        """
        self._configurations[observer_type] = config
        self.logger.debug("Configured observer type: %s", observer_type)

    def register_with_event_manager(
        self, observer: IObserver, event_types: list[str | Event] | None = None, priority: int = 0
    ) -> None:
        """
        Register an observer with the event manager.

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
        self.logger.debug("Registered observer with event manager, priority: %d", priority)

    def unregister_from_event_manager(self, observer: IObserver) -> None:
        """
        Unregister an observer from the event manager.

        Args:
            observer: Observer instance to unregister

        Raises:
            RuntimeError: If no event manager is set
        """
        if not self._event_manager:
            raise RuntimeError("No event manager set. Use set_event_manager() first.")

        self._event_manager.unregister_observer(observer)
        self.logger.debug("Unregistered observer from event manager")

    def create_observer_by_class_path(
        self, class_path: str, name: str | None = None, **kwargs
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
        try:
            # Split into module and class
            module_path, class_name = class_path.rsplit(".", 1)

            # Security check: Only allow specific modules
            # This is a fixed whitelist to prevent arbitrary code execution
            if module_path == "panther.core.observer.logger_observer":
                module = importlib.import_module("panther.core.observer.logger_observer")
            elif module_path == "panther.core.observer.metrics_observer":
                module = importlib.import_module("panther.core.observer.metrics_observer")
            elif module_path == "panther.core.observer.storage_observer":
                module = importlib.import_module("panther.core.observer.storage_observer")
            elif module_path == "panther.core.observer.experiment_observer":
                module = importlib.import_module("panther.core.observer.experiment_observer")
            # Add other allowed modules as needed
            else:
                raise ValueError(
                    "Security error: Module %s is not in the allowed observer modules list"
                    % module_path
                )

            # Get the class
            observer_class = getattr(module, class_name)

            # Instantiate with parameters
            observer_instance = observer_class(**kwargs)

            # Verify it's an observer
            if not isinstance(observer_instance, IObserver):
                raise ValueError("Class %s is not an IObserver" % class_name)

            # Register if name provided
            if name:
                self.register_observer(name, observer_instance)

            return observer_instance

        except ImportError as e:
            self.logger.error("Could not import module %s: %s", module_path, e)
            raise
        except AttributeError as e:
            self.logger.error("Class %s not found in %s: %s", class_name, module_path, e)
            raise
        except Exception as e:
            self.logger.error("Error creating observer by class path %s: %s", class_path, e)
            raise

    def load_config_file(self, config_path: str | Path) -> bool:
        """
        Load observer configurations from a YAML file.

        Args:
            config_path: Path to the observer configuration YAML file

        Returns:
            bool: True if loading was successful
        """
        if yaml is None:
            self.logger.error("PyYAML is not installed. Cannot load YAML config.")
            return False

        try:
            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            if not isinstance(config_data, dict) or "observers" not in config_data:
                self.logger.error("Invalid configuration format in %s", config_path)
                return False

            success = self._load_config_dict(config_data)
            if success:
                self._config_paths.append(Path(config_path))
            return success

        except (OSError, ValueError, TypeError) as e:
            self.logger.error("Error loading observer config from %s: %s", config_path, e)
            return False

    def _load_config_dict(self, config_data: dict[str, Any]) -> bool:
        """
        Load observer configurations from a dictionary.

        Args:
            config_data: Dictionary containing observer configuration

        Returns:
            bool: True if loading was successful
        """
        if not isinstance(config_data, dict) or "observers" not in config_data:
            self.logger.error("Invalid configuration format: missing observers key")
            return False

        observers_data = config_data["observers"]
        if not isinstance(observers_data, list):
            self.logger.error("Invalid configuration: observers must be a list")
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
                    self.logger.error("Missing class_path for observer #%d", idx)
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
                observer = self.create_observer_by_class_path(
                    class_path, name=observer_id, **params
                )

                # Register with event manager if needed
                if self._event_manager:
                    event_types = observer_data.get("event_types")
                    priority = observer_data.get("priority", 0)
                    self.register_with_event_manager(observer, event_types, priority)

                load_count += 1

            except (ValueError, ImportError, AttributeError, TypeError) as e:
                self.logger.error("Error processing observer #%d: %s", idx, e)

        self.logger.info("Loaded %d observers from configuration", load_count)
        return load_count > 0

    def load_config_directory(self, directory: str | Path) -> int:
        """
        Load observer configurations from all YAML files in directory.

        Args:
            directory: Path to directory containing YAML files

        Returns:
            int: Number of files successfully loaded
        """
        directory_path = Path(directory)
        if not directory_path.exists() or not directory_path.is_dir():
            self.logger.error("Configuration directory does not exist: %s", directory)
            return 0

        load_count = 0
        for file_path in directory_path.glob("*.y*ml"):  # Match both .yml and .yaml
            if self.load_config_file(file_path):
                load_count += 1

        self.logger.info("Loaded %d configuration files from %s", load_count, directory)
        return load_count

    def batch_register_with_event_manager(
        self, observers: list[tuple[IObserver, list[str | Event] | None, int]]
    ) -> None:
        """
        Register multiple observers with the event manager in a single call.

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

        self.logger.debug("Batch registered %d observers with event manager", registered_count)

    def create_and_register_observer_set(
        self, observer_configs: list[dict[str, Any]]
    ) -> list[IObserver]:
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
        if not self._event_manager and any(
            conf.get("auto_register", False) for conf in observer_configs
        ):
            raise RuntimeError("No event manager set. Use set_event_manager() first.")

        observers = []

        for idx, config in enumerate(observer_configs):
            if "type" not in config:
                self.logger.error("Missing observer type in configuration #%d", idx)
                continue

            observer_type = config.pop("type")
            name = config.pop("name", None)
            auto_register = config.pop("auto_register", False)
            event_types = config.pop("event_types", None)
            priority = config.pop("priority", 0)

            try:
                observer = self.create_observer(
                    observer_type,
                    name=name,
                    auto_register=auto_register,
                    event_types=event_types,
                    priority=priority,
                    **config,
                )
                observers.append(observer)
            except ValueError as e:
                self.logger.error("Failed to create observer #%d: %s", idx, e)

        self.logger.info("Created and registered %d observers", len(observers))
        return observers

    def set_observer_config(self, observer_config: ObserverConfig) -> None:
        """
        Set the observer configuration for this factory.

        Args:
            observer_config: Observer configuration instance
        """
        self._observer_config = observer_config
        self.logger.debug("Set observer configuration for factory")


# Global factory instance
_observer_factory = None


def get_observer_factory(global_config=None) -> ObserverFactory:
    """
    Get the global observer factory instance.

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
        # Use a setter method instead of directly accessing the protected member
        _observer_factory.set_observer_config(global_config.observers)
    return _observer_factory


def create_observer(observer_type: str, **kwargs) -> IObserver:
    """Convenience function to create an observer."""
    factory = get_observer_factory()
    return factory.create_observer(observer_type, **kwargs)


def create_default_observers(config: dict[str, Any]) -> list[IObserver]:
    """Convenience function to create default observers."""
    factory = get_observer_factory()
    return factory.create_default_observer_set(config)


def load_observer_config(path: str | Path) -> bool:
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
        return factory.load_config_directory(path) > 0
    else:
        return factory.load_config_file(path)


# Transition functions for legacy code using observer_registry
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
    return create_observer(observer_type, **kwargs)


def convert_config_to_factory_params(observer_config: Any) -> dict[str, Any]:
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
