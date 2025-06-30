"""
Experiment Observer Mixin for PANTHER framework.

This module contains the ExperimentObserverMixin class which provides observer setup
and management functionality that can be mixed into the ExperimentManager.
"""

import logging
from typing import Any, Optional

from panther.core.observer.factory.factory_builders import (
    create_experiment_observer,
    create_logger,
    create_metrics,
)


class ExperimentObserverMixin:
    """
    Mixin class that provides observer setup and management functionality.

    This mixin centralizes all observer-related functionality that was previously
    scattered in the ExperimentManager class. It can be mixed into any class that
    needs observer management capabilities.

    Required attributes on the class using this mixin:
    - global_config: Global configuration object
    - experiment_name: Name of the experiment
    - logs_dir: Directory for log outputs
    - log_level: Logging level
    - event_manager: Event manager instance
    - workflow_tracker: Workflow state tracker
    - experiment_emitter: Experiment event emitter
    - logger: Logger instance
    - metrics_collector: Optional metrics collector
    """

    def _setup_observers(self):
        """Sets up the observers for the experiment manager."""
        try:
            self.setup_observer()
        except Exception as e:
            # Emit error event with all necessary information for metrics
            self.experiment_emitter.emit_finished_early(
                reason=f"Observer Setup Error: {type(e).__name__}",
                details={
                    "phase": "observer_setup",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "component": "experiment_manager",
                    "experiment_name": self.experiment_name,
                },
            )
            self.logger.error("Failed to set up observers: %s", e, exc_info=True)
            raise

    def setup_observer(self):
        """Main observer setup method that coordinates all observer creation."""
        self.register_state_event_observer()

        if self.global_config.observers.logger.enabled:
            if self.log_level <= logging.DEBUG:
                self.logger.debug(
                    "Skipping regular logger creation - debug logger will be created instead to avoid duplicates"
                )
            else:
                # Create logger observer
                self.create_logger_observer()

        if self.global_config.observers.metrics.enabled:
            try:
                self.register_metric()
            except Exception as metrics_error:  # pylint: disable=broad-exception-caught
                self.logger.warning(
                    "Failed to create metrics observer: %s. Using default configuration instead.",
                    metrics_error,
                )

        # Create an experiment observer to handle experiment-specific events
        create_experiment_observer(
            name="experiment_observer",
            global_config=self.global_config,
            auto_register=True,
            priority=101,  # Higher priority to ensure it gets events first
            output_dir=str(self.logs_dir),
            test_name=self.experiment_name,
            track_timing=True,
            track_steps=True,
        )
        self.logger.info("Registered ExperimentObserver")

        # Create a logger observer with debug mode if debug logging is enabled
        if self.log_level <= logging.DEBUG:
            self.register_debug_logger()

        self.logger.info("Observers set up for experiment: %s", self.experiment_name)

    def create_logger_observer(self):
        """Create and register a logger observer for the experiment."""
        try:
            # Get log level from observer config if available, otherwise fallback to global log level
            observer_log_level = (
                self.global_config.observers.logger.log_level
                if hasattr(self.global_config, "observers")
                and hasattr(self.global_config.observers, "logger")
                else logging.getLevelName(self.log_level)
            )
            global_log_level = logging.getLevelName(self.log_level)

            # Use the more restrictive log level (higher numeric value = more restrictive)
            observer_level_numeric = getattr(
                logging, observer_log_level.upper(), logging.INFO
            )
            global_level_numeric = getattr(
                logging, global_log_level.upper(), logging.INFO
            )
            log_level = (
                global_log_level
                if global_level_numeric >= observer_level_numeric
                else observer_log_level
            )

            if global_level_numeric > observer_level_numeric:
                self.logger.debug(
                    f"Using global log level '{global_log_level}' instead of observer level '{observer_log_level}' (more restrictive)"
                )

            # Use the standalone function to create a logger
            event_logger = create_logger(
                name="experiment_logger",
                global_config=self.global_config,
                auto_register=False,  # Manual registration to avoid duplicates
                log_level=log_level,  # Use observer-specific log level
                output_file=str(self.logs_dir / "event_log.log"),
                enable_colors=True,
                include_event_id=True,
            )
            # Manually register the logger observer using register_observer_once for proper tracking
            self.event_manager.register_observer_once(
                observer=event_logger,
                observer_id="experiment_logger",
                scope="experiment",
                event_types=None,
                priority=0,
            )
            self.logger.info("Registered LoggerObserver")
        except Exception as logger_error:  # pylint: disable=broad-exception-caught
            self.logger.warning(
                "Failed to create logger observer: %s. Falling back to basic observer.",
                logger_error,
            )

    def register_metric(self):
        """Register a metrics observer for the experiment."""
        self.logger.info("Creating metrics observer")
        # Get metrics observer log level if available
        # Respect global log level if it's more restrictive (higher level) than observer-specific level
        observer_metrics_log_level = (
            self.global_config.observers.metrics.log_level
            if hasattr(self.global_config, "observers")
            and hasattr(self.global_config.observers, "metrics")
            else "INFO"
        )
        global_log_level = logging.getLevelName(self.log_level)

        # Use the more restrictive log level (higher numeric value = more restrictive)
        observer_level_numeric = getattr(
            logging, observer_metrics_log_level.upper(), logging.INFO
        )
        global_level_numeric = getattr(logging, global_log_level.upper(), logging.INFO)
        metrics_log_level = (
            global_log_level
            if global_level_numeric >= observer_level_numeric
            else observer_metrics_log_level
        )

        if global_level_numeric > observer_level_numeric:
            self.logger.debug(
                f"Using global log level '{global_log_level}' instead of metrics observer level '{observer_metrics_log_level}' (more restrictive)"
            )

        # Use the standalone function to create a metrics observer
        metrics_observer = create_metrics(
            name="experiment_metrics",
            global_config=self.global_config,
            auto_register=False,  # Manual registration for proper tracking
            output_dir=str(self.logs_dir),
            metrics_collector=self.metrics_collector,
            log_level=metrics_log_level,  # Use observer-specific log level
        )
        # Manually register the metrics observer using register_observer_once for proper tracking
        self.event_manager.register_observer_once(
            observer=metrics_observer,
            observer_id="experiment_metrics",
            scope="experiment",
            event_types=None,
            priority=0,
        )
        self.logger.info("Registered metrics observer")

    def register_debug_logger(self):
        """Register a debug logger observer for detailed event tracking."""
        try:
            from panther.core.observer import (  # pylint: disable=import-outside-toplevel
                LoggerObserver,
            )

            # Create single debug logger that serves as the main logger
            debug_observer = LoggerObserver(
                output_file=str(self.logs_dir / "event_debug.log"),
                log_level="DEBUG",
                debug_mode=True,
                track_event_history=True,
                max_history_size=2000,
                enable_colors=True,
                include_event_id=True,
            )
            # Use register_observer_once to prevent duplicates
            self.event_manager.register_observer_once(
                observer=debug_observer,
                observer_id="experiment_debug_logger",
                scope="experiment",
                event_types=None,
                priority=0,
            )

            self.logger.info(
                "Registered single LoggerObserver with debug mode for detailed event tracking"
            )
        except Exception as debug_error:  # pylint: disable=broad-exception-caught
            self.logger.warning(
                "Failed to create debug observer: %s. Event debugging will be limited.",
                debug_error,
            )

    def register_state_event_observer(self):
        """Register StateEventObserver to sync state with events."""
        # Register StateEventObserver to sync state with events
        from panther.core.observer.impl import (  # pylint: disable=import-outside-toplevel
            StateEventObserver,
        )

        self.state_observer = StateEventObserver(
            self.workflow_tracker, priority=50
        )  # Higher priority
        self.event_manager.register_observer_once(
            observer=self.state_observer,
            observer_id="experiment_state_observer",
            scope="experiment",
            event_types=None,
            priority=50,
        )
        self.logger.info(
            "Registered StateEventObserver for event-driven state management"
        )
