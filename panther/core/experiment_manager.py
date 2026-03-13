"""Central orchestrator for PANTHER experiment lifecycle.

``ExperimentManager`` drives the four-phase execution model:

1. **Initialization** – parse YAML config, set up logging, register emitters.
2. **Plugin Loading** – discover plugins, create service managers, generate
   commands, build Docker images.
3. **Environment Deployment** – set up network (Docker Compose / Shadow NS),
   deploy containers, run health checks.
4. **Test Execution** – iterate test scenarios, collect metrics, teardown,
   generate reports.

The manager delegates to `ErrorHandlerMixin` for structured
error recovery and `FastFailHandler` for early termination on
unrecoverable failures (certificate, Ivy compilation, port conflicts,
resource exhaustion, etc.).

See Also:
    `panther.core.test_cases`
        Mixin-based test runners invoked by the manager.
    `panther.core.events`
        Event bus wiring configured during initialization.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from panther.config.core.models import GlobalConfig
from panther.core.events.emitter_registry import EmitterRegistry
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.exceptions.fast_fail import FastFailHandler
from panther.core.experiment_analysis import ExperimentAnalysisMixin
from panther.core.experiment_cleanup import ExperimentCleanupMixin
from panther.core.experiment_observer import ExperimentObserverMixin
from panther.core.experiment_phases import ExperimentPhasesMixin
from panther.core.metrics.enums import Phase
from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.observer.factory import get_observer_factory
from panther.core.observer.management.event_manager import EventManager
from panther.core.observer.workflow import (  # pylint: disable=import-outside-toplevel
    WorkflowStateTracker,
)
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.core.utils.logger_factory import LoggerFactory
from panther.plugins.plugin_manager import PluginManager


# TODO implement errors management strategy (e.g., retry, fail, etc.)
class ExperimentManager(
    ExperimentPhasesMixin,
    ExperimentCleanupMixin,
    ErrorHandlerMixin,
    ExperimentObserverMixin,
    ExperimentAnalysisMixin,
):
    """Orchestrate experiment lifecycle with event-driven coordination.

    ExperimentManager implements the Facade pattern, coordinating multiple subsystems for
    reproducible network protocol testing. The class provides centralized control over
    experiment initialization, execution, monitoring, and cleanup.

    This class is the primary entry point for running PANTHER experiments and manages
    the complete lifecycle from configuration validation to result collection.

    Args:
        global_config: Global configuration containing paths and defaults.
        experiment_name: Optional name for the experiment (sanitized automatically).
        plugin_dir: Directory containing plugin implementations.
        logger: Optional logger instance (creates default if None).
        metrics_collector: Optional metrics collection system.
        fast_fail_enabled: Whether to terminate on critical errors.
        dry_run: Execute in validation mode without running actual tests.

    Attributes:
        global_config (GlobalConfig): Global configuration for the experiment.
        experiment_name (str): Sanitized experiment identifier with timestamp.
        experiment_dir (Path): Output directory for experiment artifacts.
        plugin_manager (PluginManager): Plugin discovery and management system.
        test_cases (List[ITestCase]): Configured test scenarios for execution.
        event_manager (EventManager): Central event coordination system.
        fast_fail_handler (FastFailHandler): Critical error management system.

    Raises:
        ExperimentInitializationError: When configuration validation fails.
        PluginValidationError: When required plugins cannot be loaded.
        TestCaseInitializationError: When test cases cannot be created.

    Examples:
        >>> config = GlobalConfig.load("config.yaml")
        >>> manager = ExperimentManager(config, experiment_name="quic_test")
        >>> manager.initialize_experiments(experiment_config)
        >>> manager.run_tests()
        >>> manager.cleanup()

        Using as context manager:
        >>> with ExperimentManager(config) as manager:
        ...     manager.initialize_experiments(experiment_config)
        ...     manager.run_tests()

    Note:
        - Not thread-safe: designed for single-threaded execution
        - Uses event-driven architecture for loose coupling between components
        - Implements observer pattern for extensible monitoring and analysis
        - Resource cleanup happens automatically when used as context manager

    Architecture:
        The manager coordinates four main phases:
        1. Initialization: Plugin validation and observer setup
        2. Preparation: Test case creation and environment validation
        3. Execution: Progress-tracked test running with error recovery
        4. Cleanup: Resource teardown and result aggregation
    """

    def __init__(
        self,
        global_config: GlobalConfig,
        experiment_name: str = None,
        plugin_dir: str = "panther/plugins/",
        logger: logging.Logger = None,
        metrics_collector: Optional[MetricsCollector] = None,
        fast_fail_enabled: bool = True,
        dry_run: bool = False,
    ):
        """Initialize ExperimentManager."""
        # Initialize parent class
        super().__init__()

        self.experiment_config = None
        self.global_config = global_config
        self.metrics_collector = metrics_collector
        self.dry_run = dry_run
        if experiment_name:
            experiment_name = re.sub(r"[^a-zA-Z0-9_]", "_", experiment_name.strip())
            experiment_name = re.sub(r"_+", "_", experiment_name)

        self.experiment_name = (
            f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{experiment_name}"
            if experiment_name
            else f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        )
        self.experiment_dir = (
            Path(global_config.paths.output_dir) / self.experiment_name
        )
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        # Handle logging level - could be string or enum
        level_name = (
            self.global_config.logging.level.name
            if hasattr(self.global_config.logging.level, "name")
            else str(self.global_config.logging.level)
        )
        self.log_level = getattr(logging, level_name, logging.INFO)
        self.log_format = self.global_config.logging.format

        logging_config = {
            "level": (
                self.global_config.logging.level.name
                if hasattr(self.global_config.logging.level, "name")
                else str(self.global_config.logging.level)
            ),
            "format": self.global_config.logging.format,
            "enable_colors": getattr(self.global_config.logging, "enable_colors", True),
            "feature_levels": getattr(
                self.global_config.logging, "feature_levels", None
            ),
        }
        LoggerFactory.initialize(logging_config)

        # Update any existing loggers with the new feature levels
        # This handles loggers created during config loading before LoggerFactory was initialized
        self.configure_logging_features()

        # Initialize log statistics if enabled
        self.log_statistics_display = None
        self._setup_log_statistics()

        self.logs_dir = self.experiment_dir
        self.plugin_dir = plugin_dir
        # Don't assign to self.logger directly as it's a property from LoggerMixin
        if logger:
            self._logger = logger
        self._load_logging()

        # Configure fast fail handler based on global config
        fast_fail_config = global_config.fast_fail
        self.fast_fail_handler = FastFailHandler(
            enabled=fast_fail_enabled and fast_fail_config.enabled, logger=self.logger
        )
        self.plugin_dir = Path(plugin_dir)

        # Initialize event manager for experiment-level events
        self.event_manager = EventManager.get_instance()
        factory = get_observer_factory(self.global_config)
        factory.set_event_manager(self.event_manager)

        # Initialize workflow state tracker for experiment coordination
        self.workflow_tracker = WorkflowStateTracker()

        # Initialize centralized emitter registry
        self.emitter_registry = EmitterRegistry(self.event_manager)

        # Access emitters through the registry
        self.experiment_emitter = self.emitter_registry.experiment_emitter
        self.service_emitter = self.emitter_registry.service_emitter
        self.environment_emitter = self.emitter_registry.environment_emitter
        self.metrics_emitter = self.emitter_registry.metrics_emitter
        self.plugin_emitter = self.emitter_registry.plugin_emitter

        # Setup plugin manager with event manager and fast fail handler
        self.plugin_manager = PluginManager(
            plugin_directories=None,  # Use default plugin directories
            event_manager=self.event_manager,
            global_config=self.global_config,
            fast_fail_handler=self.fast_fail_handler,
            experiment_context=self,
        )

        self._setup_observers()

        # Clean up any None observers that might exist
        cleaned = self.event_manager.cleanup_none_observers()
        if cleaned > 0:
            self.logger.info(
                "Cleaned up %d None observers during initialization", cleaned
            )

        self.test_cases: List[ITestCase] = []

    def configure_logging_features(self):
        """Configure feature-level logging from global config."""
        if (
            not hasattr(self.global_config.logging, "feature_levels")
            or not self.global_config.logging.feature_levels
        ):
            return
        feature_levels_dict = {}
        # Convert feature_levels dataclass to dictionary
        if hasattr(self.global_config.logging.feature_levels, "__dict__"):
            self.logger.debug(
                f"Feature_levels in global_config: {list(list(self.global_config.logging.feature_levels.__dict__.items())[:3])}"
            )
            for (
                attr_name,
                attr_value,
            ) in self.global_config.logging.feature_levels.__dict__.items():
                # Skip None values and omega_config
                if attr_value is None or attr_name == "_omega_config":
                    continue
                if hasattr(attr_value, "name"):  # It's an enum
                    feature_levels_dict[attr_name] = attr_value.name
                else:
                    feature_levels_dict[attr_name] = str(attr_value)
        # Only update if we have actual feature levels to set
        if feature_levels_dict:
            LoggerFactory.update_all_feature_levels(feature_levels_dict)

    def record_failed_test(self, test_case, test_error):
        """Record a failed test case and log the error."""
        if self.global_config.progress.show_test_status:
            emoji = "❌ " if self.global_config.progress.use_emojis else ""
            self.logger.info(
                f"{emoji}Failed: {test_case.test_config.name} - {str(test_error)[:50]}..."
            )

    def _handle_test_error(self, test_case, test_error):
        """Helper method to handle test errors consistently."""
        # Get test-specific emitter for this test case
        test_specific_emitter = self.emitter_registry.get_test_emitter(
            test_case.test_config.name
        )

        # Emit test failed event
        test_specific_emitter.emit_failed(
            error_message=str(test_error),
            error_type=type(test_error).__name__,
            phase="execution",
            summary={"test_name": test_case.test_config.name},
        )
        self.logger.error(
            "Test case %s failed: %s",
            test_case.test_config.name,
            test_error,
            exc_info=True,
        )

    def _load_logging(self):
        """Load and configure logging for the experiment manager with dual-level support."""
        # Initialize LoggerFactory with experiment-specific configuration
        # Handle both enum and string values for logging level
        level_value = self.global_config.logging.level
        if hasattr(level_value, "value"):
            level_str = level_value.value
        else:
            level_str = str(level_value)

        logging_config = {
            "level": level_str,
            "format": self.log_format,
            "enable_colors": getattr(self.global_config.logging, "enable_colors", True),
            "debug_file_logging": getattr(
                self.global_config.logging, "debug_file_logging", True
            ),
            "output_file": str(self.logs_dir / "experiment.log"),
        }

        # Add feature levels if available
        if (
            hasattr(self.global_config.logging, "feature_levels")
            and self.global_config.logging.feature_levels
        ):
            logging_config["feature_levels"] = self.global_config.logging.feature_levels

        # Initialize LoggerFactory with the configuration
        LoggerFactory.initialize(logging_config)

        # Create a directory for logs if it doesn't exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # The logger is already configured through LoggerFactory, just log initialization
        self.logger.info(
            "ExperimentManager initialized for experiment: %s", self.experiment_name
        )

    def _record_test_metric(self, outcome: str) -> None:
        """Record test outcome metrics (total + outcome-specific counter).

        Args:
            outcome: The test outcome to record (e.g., "failed", "successful").
        """
        try:
            if self.metrics_collector:
                self.metrics_collector.increment_counter(
                    "test_cases_total", phase=Phase.TEST_EXECUTION
                )
                self.metrics_collector.increment_counter(
                    f"test_cases_{outcome}", phase=Phase.TEST_EXECUTION
                )
        except Exception as metrics_err:  # pylint: disable=broad-exception-caught
            self.logger.warning(
                "Failed to record test %s metrics: %s",
                outcome,
                metrics_err,
            )

    def __enter__(self):
        """Context manager entry - return self for use in with statements."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup happens."""
        self.cleanup()
        # Don't suppress exceptions
        return False
