"""
Observer Setup Mixin

This module provides a mixin for standardized observer setup patterns,
reducing duplication in observer initialization across managers.
"""

from typing import Any
from pathlib import Path

from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.observer.management.event_manager import EventManager
from panther.core.observer.factory.factory_builders import create_logger
from panther.core.observer.factory.observer_factory import ObserverFactory

# setup_colored_logging removed - not available in event_colors
from panther.config.config_global_schema import GlobalConfig


class ObserverSetupMixin(LoggerMixin):
    """
    Mixin that provides standardized observer setup functionality.

    Reduces duplication of observer initialization patterns across managers.
    """

    def setup_observers(
        self,
        global_config: GlobalConfig,
        event_manager: EventManager,
        logs_dir: Path | None = None,
        entity_type: str = "experiment",
        additional_observers: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Set up observers based on global configuration.

        Args:
            global_config: Global configuration with observer settings
            event_manager: Event manager to register observers with
            logs_dir: Directory for log files
            entity_type: Type of entity (experiment, test, service, etc.)
            additional_observers: Additional observer configurations

        Returns:
            Dictionary of created observers
        """
        created_observers = {}

        # Determine log level
        log_level = (
            global_config.observers.logger.log_level
            if hasattr(global_config.observers.logger, "log_level")
            else global_config.logging.level
        )

        # Setup logger observer
        if global_config.observers.logger.enabled:
            logger_observer = self._setup_logger_observer(
                global_config, event_manager, logs_dir, entity_type, log_level
            )
            if logger_observer:
                created_observers["logger"] = logger_observer

        # Setup metrics observer
        if global_config.observers.metrics.enabled:
            metrics_observer = self._setup_metrics_observer(
                global_config, event_manager, entity_type
            )
            if metrics_observer:
                created_observers["metrics"] = metrics_observer

        # Setup storage observer
        if global_config.observers.storage.enabled:
            storage_observer = self._setup_storage_observer(
                global_config, event_manager, entity_type
            )
            if storage_observer:
                created_observers["storage"] = storage_observer

        # Setup experiment observer
        if (
            hasattr(global_config.observers, "experiment")
            and global_config.observers.experiment.enabled
        ):
            experiment_observer = self._setup_experiment_observer(
                global_config, event_manager, entity_type
            )
            if experiment_observer:
                created_observers["experiment"] = experiment_observer

        # Setup additional observers
        if additional_observers:
            for name, config in additional_observers.items():
                observer = self._setup_custom_observer(
                    name, config, global_config, event_manager, entity_type
                )
                if observer:
                    created_observers[name] = observer

        return created_observers

    def _setup_logger_observer(
        self,
        global_config: GlobalConfig,
        event_manager: EventManager,
        logs_dir: Path | None,
        entity_type: str,
        log_level: str,
    ) -> Any | None:
        """Set up the logger observer."""
        try:
            # Create logger
            output_file = None
            if logs_dir:
                output_file = str(logs_dir / f"{entity_type}_event_log.log")

            create_logger(
                name=f"{entity_type}_logger",
                global_config=global_config,
                auto_register=True,
                log_level=log_level,
                output_file=output_file,
                enable_colors=getattr(global_config.observers.logger, "enable_colors", True),
                include_event_id=getattr(global_config.observers.logger, "include_event_id", True),
                include_timestamp=getattr(
                    global_config.observers.logger, "include_timestamp", True
                ),
                include_source=getattr(global_config.observers.logger, "include_source", True),
                correlation_tracking=getattr(
                    global_config.observers.logger, "correlation_tracking", True
                ),
            )

            self.logger.info(f"Registered enhanced LoggerObserver for {entity_type}")
            return True

        except Exception as e:
            self.logger.warning(f"Failed to create logger observer: {e}")
            return None

    def _setup_metrics_observer(
        self, global_config: GlobalConfig, event_manager: EventManager, entity_type: str
    ) -> Any | None:
        """Set up the metrics observer."""
        try:
            factory = ObserverFactory(global_config, event_manager)
            observer = factory.create_metrics_observer(
                priority=getattr(global_config.observers.metrics, "priority", 90),
                config=global_config.observers.metrics,
            )

            if observer:
                event_manager.register_observer(observer)
                self.logger.info(f"Registered MetricsObserver for {entity_type}")

            return observer

        except Exception as e:
            self.logger.warning(f"Failed to create metrics observer: {e}")
            return None

    def _setup_storage_observer(
        self, global_config: GlobalConfig, event_manager: EventManager, entity_type: str
    ) -> Any | None:
        """Set up the storage observer."""
        try:
            factory = ObserverFactory(global_config, event_manager)
            observer = factory.create_storage_observer(
                priority=getattr(global_config.observers.storage, "priority", 100),
                config=global_config.observers.storage,
            )

            if observer:
                event_manager.register_observer(observer)
                self.logger.info(f"Registered StorageObserver for {entity_type}")

            return observer

        except Exception as e:
            self.logger.warning(f"Failed to create storage observer: {e}")
            return None

    def _setup_experiment_observer(
        self, global_config: GlobalConfig, event_manager: EventManager, entity_type: str
    ) -> Any | None:
        """Set up the experiment observer."""
        try:
            factory = ObserverFactory(global_config, event_manager)
            observer = factory.create_experiment_observer(
                priority=getattr(global_config.observers.experiment, "priority", 115),
                config=global_config.observers.experiment,
            )

            if observer:
                event_manager.register_observer(observer)
                self.logger.info(f"Registered ExperimentObserver for {entity_type}")

            return observer

        except Exception as e:
            self.logger.warning(f"Failed to create experiment observer: {e}")
            return None

    def _setup_custom_observer(
        self,
        name: str,
        config: dict[str, Any],
        global_config: GlobalConfig,
        event_manager: EventManager,
        entity_type: str,
    ) -> Any | None:
        """Set up a custom observer."""
        try:
            # Custom observer setup logic would go here
            # This is a placeholder for future custom observer types
            self.logger.info(f"Custom observer '{name}' setup not implemented")
            return None

        except Exception as e:
            self.logger.warning(f"Failed to create custom observer '{name}': {e}")
            return None

    def cleanup_observers(
        self, created_observers: dict[str, Any], event_manager: EventManager
    ) -> None:
        """
        Clean up observers.

        Args:
            created_observers: Dictionary of created observers
            event_manager: Event manager to unregister from
        """
        for name, observer in created_observers.items():
            try:
                if hasattr(observer, "cleanup"):
                    observer.cleanup()
                # Additional cleanup logic if needed
            except Exception as e:
                self.logger.warning(f"Failed to cleanup observer '{name}': {e}")
