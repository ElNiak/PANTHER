"""Observer management functionality for test cases."""

from typing import List

from panther.core.observer.factory import get_observer_factory
from panther.core.observer.factory.factory_builders import (
    create_logger,
    create_metrics,
    create_storage,
)
from panther.core.observer.impl.experiment_observer import ExperimentObserver


class ObserverManagementMixin:
    """Mixin providing observer management capabilities for test cases."""

    def __init__(self, *args, **kwargs):
        """Initialize the mixin."""
        super().__init__(*args, **kwargs)
        # Initialize registered_observers if not already set
        if not hasattr(self, "registered_observers"):
            self.registered_observers: List[str] = []

    def setup_observers(self) -> None:
        """
        Set up and register default observers for the test case.

        This method sets up the standard observers for logging, metrics, storage,
        and experiment tracking using the enhanced observer registry system.
        """
        self.logger.debug("Setting up observers for test case")
        self._setup_logger_observer()
        self._setup_metrics_observer()
        self._setup_storage_observer()
        # Note: ExperimentObserver is registered at the experiment level

    def _setup_logger_observer(self) -> None:
        """Set up the logger observer."""
        if not self.global_config.observers.logger.enabled:
            return

        try:
            logger_id = f"test_logger_{self.test_name}"

            if existing_logger_observers := [
                obs_id
                for obs_id in [
                    "experiment_logger",
                    "experiment_debug_logger",
                    logger_id,
                ]
                if self.event_manager.has_observer(obs_id)
            ]:
                self.logger.debug(
                    f"Logger observer already exists: {existing_logger_observers[0]}. Skipping test-specific logger observer to avoid duplicates."
                )
                return

            # Check if test-specific observer already exists
            if not self.event_manager.has_observer(logger_id):
                self.logger.debug("Creating enhanced logger observer")

                # Get log level from observer config
                log_level = (
                    self.global_config.observers.logger.log_level
                    if hasattr(self.global_config.observers.logger, "log_level")
                    else self.log_level
                )

                observer = create_logger(
                    name=logger_id,
                    global_config=self.global_config,
                    auto_register=False,
                    log_level=log_level,
                    enable_colors=True,
                    output_file=str(self.test_experiment_dir / "event_log.log"),
                    correlation_tracking=True,
                )

                # Register the observer
                self.event_manager.register_observer_once(
                    observer=observer,
                    observer_id=logger_id,
                    scope="test",
                    event_types=None,
                    priority=0,
                )

                self.registered_observers.append(logger_id)
                self.logger.debug("Registered enhanced logger observer")
            else:
                self.logger.debug("Logger observer already exists")

        except Exception as e:
            self.logger.warning(f"Failed to create logger observer: {e}")

    def _setup_metrics_observer(self) -> None:
        """Set up the metrics observer."""
        if not self.global_config.observers.metrics.enabled:
            return

        try:
            metrics_id = f"test_metrics_{self.test_name}"

            # Check if any metrics observer already exists (experiment-level or test-specific)
            existing_metrics_observers = [
                obs_id
                for obs_id in ["experiment_metrics", metrics_id]
                if self.event_manager.has_observer(obs_id)
            ]

            if existing_metrics_observers:
                self.logger.debug(
                    f"Metrics observer already exists: {existing_metrics_observers[0]}. Skipping test-specific metrics observer to avoid duplicates."
                )
                return

            # Check if test-specific observer already exists
            if not self.event_manager.has_observer(metrics_id):
                self.logger.info("Creating enhanced metrics observer")

                # Get metrics observer log level
                metrics_log_level = (
                    self.global_config.observers.metrics.log_level
                    if hasattr(self.global_config.observers.metrics, "log_level")
                    else "INFO"
                )

                # Ensure metrics directory exists
                metrics_dir = self.test_experiment_dir / "metrics"
                metrics_dir.mkdir(parents=True, exist_ok=True)

                observer = create_metrics(
                    name=metrics_id,
                    global_config=self.global_config,
                    auto_register=False,
                    publish_metrics=True,
                    collect_system_metrics=True,
                    output_dir=str(metrics_dir),
                    publish_interval=30,
                    enable_real_time_monitoring=True,
                    log_level=metrics_log_level,
                )

                # Register the observer
                self.event_manager.register_observer_once(
                    observer=observer,
                    observer_id=metrics_id,
                    scope="test",
                    event_types=None,
                    priority=10,
                )

                self.registered_observers.append(metrics_id)
                self.logger.debug("Registered enhanced metrics observer")
            else:
                self.logger.debug("Metrics observer already exists")

        except Exception as e:
            self.logger.warning(f"Failed to create metrics observer: {e}")

    def _setup_storage_observer(self) -> None:
        """Set up the storage observer."""
        if not self.global_config.observers.storage.enabled:
            return

        try:
            storage_id = f"test_storage_{self.test_name}"

            # Check if observer already exists
            if not self.event_manager.has_observer(storage_id):
                self.logger.info("Creating enhanced storage observer")

                observer = create_storage(
                    name=storage_id,
                    global_config=self.global_config,
                    auto_register=False,
                    storage_path=str(self.test_experiment_dir),
                    enable_compression=True,
                    auto_backup=True,
                    retention_days=30,
                    batch_size=100,
                )

                # Register the observer
                self.event_manager.register_observer_once(
                    observer=observer,
                    observer_id=storage_id,
                    scope="test",
                    event_types=None,
                    priority=20,
                )

                self.registered_observers.append(storage_id)
                self.logger.debug("Registered enhanced storage observer")
            else:
                self.logger.debug("Storage observer already exists")

        except Exception as e:
            self.logger.warning(f"Failed to create storage observer: {e}")

    def teardown_observers(self) -> None:
        """
        Unregister all observers registered by this test case.

        This method should be called in the finally block of the test run.
        """
        try:
            factory = get_observer_factory()

            for observer_name in self.registered_observers:
                if factory.unregister_observer(observer_name):
                    self.logger.debug(f"Unregistered observer '{observer_name}'")
                else:
                    self.logger.warning(
                        f"Failed to unregister observer '{observer_name}'"
                    )

            self.registered_observers.clear()
            self.logger.debug("Unregistered all observers after test completion")

        except Exception as e:
            self.logger.error(f"Error during observer cleanup: {e}")
            # Continue with cleanup even if observer unregistration fails

    def get_experiment_observer(self) -> ExperimentObserver:
        """
        Get the ExperimentObserver instance from the event manager.

        Returns:
            ExperimentObserver or None: The experiment observer instance if found
        """
        if not hasattr(self, "event_manager") or self.event_manager is None:
            self.logger.warning(
                "No event_manager available for getting experiment observer"
            )
            return None

        experiment_observer = self.event_manager.get_observer_by_type(
            ExperimentObserver
        )

        if experiment_observer is None:
            self.logger.warning("No ExperimentObserver found in event_manager")

        return experiment_observer
