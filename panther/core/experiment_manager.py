"""Experiment manager for PANTHER framework.

This module contains the ExperimentManager class which manages the lifecycle
of experiments including initialization, configuration, and execution.
"""

import logging
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from colorlog import ColoredFormatter
from omegaconf import OmegaConf
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from panther.config.core.models import ExperimentConfig, GlobalConfig
from panther.core.events.emitter_registry import EmitterRegistry
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.exceptions.experiment_exceptions import (
    ExperimentInitializationError,
    PantherExperimentError,
    PluginValidationError,
    TestCaseInitializationError,
    TestExecutionError,
)
from panther.core.exceptions.fast_fail import (
    CertificateException,
    ConfigurationException,
    DockerComposeException,
    ErrorCategory,
    ErrorSeverity,
    FastFailHandler,
    IvyCompilationException,
    PortConflictException,
    ResourceExhaustionException,
    TimeoutCascadeException,
)
from panther.core.metrics.metrics_collector import MetricsCollector
from panther.core.observer.factory import ObserverFactory, get_observer_factory
from panther.core.observer.factory.factory_builders import (
    create_experiment_observer,
    create_logger,
    create_metrics,
)
from panther.core.observer.management.event_manager import EventManager
from panther.core.test_cases.test_case_impl import TestCase
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.core.workflow import (  # pylint: disable=import-outside-toplevel
    WorkflowStateTracker,
)
from panther.plugins.plugin_manager import PluginManager


# TODO implement errors management strategy (e.g., retry, fail, etc.)
class ExperimentManager(ErrorHandlerMixin):
    """
    Manages the lifecycle of an experiment, including initialization, configuration,
    and execution of test cases.

    Attributes:
        global_config (GlobalConfig): The global configuration for the experiment.
        experiment_name (str): The name of the experiment.
        plugin_dir (str): The directory where plugins are located.
        logger (logging.Logger): Logger for the experiment manager.
        experiment_config (ExperimentConfig): Configuration specific to the experiment.
        experiment_dir (Path): Directory where experiment outputs are stored.
        logs_dir (Path): Directory where logs are stored.
        plugin_manager (PluginManager): Manager for experiment plugins.
        test_cases (List[ITestCase]): List of test cases to be executed.

    Methods:
        initialize_experiments(experiment_config: ExperimentConfig):
            Initializes plugins, environment, and validates configuration.

        _save_configuration():
            Saves the experiment configuration file in the experiment folder.

        _initialize_test_cases():
            Initializes the test cases from the experiment configuration.

        run_tests():
            Runs the tests defined in the experiment configuration.

        _load_logging():
    """

    def __init__(
        self,
        global_config: GlobalConfig,
        experiment_name: str = None,
        plugin_dir: str = "panther/plugins/",
        logger: logging.Logger = None,
        metrics_collector: Optional[MetricsCollector] = None,
        fast_fail_enabled: bool = True,
    ):
        # Initialize parent class
        super().__init__()

        self.experiment_config = None
        self.global_config = global_config
        self.metrics_collector = metrics_collector
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

        # Initialize LoggerFactory early with global config to ensure consistent colors for all plugins
        from panther.core.utils.logger_factory import LoggerFactory

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
        if hasattr(self.global_config.logging, "feature_levels") and self.global_config.logging.feature_levels:
            feature_levels_dict = {}
            # Convert feature_levels dataclass to dictionary
            if hasattr(self.global_config.logging.feature_levels, "__dict__"):
                print(f"DEBUG: feature_levels in global_config: {[(k, v) for k, v in list(self.global_config.logging.feature_levels.__dict__.items())[:3]]}")
                for attr_name, attr_value in self.global_config.logging.feature_levels.__dict__.items():
                    # Skip None values and omega_config
                    if attr_value is None or attr_name == "_omega_config":
                        continue
                    if hasattr(attr_value, 'name'):  # It's an enum
                        feature_levels_dict[attr_name] = attr_value.name
                    else:
                        feature_levels_dict[attr_name] = str(attr_value)
            # Only update if we have actual feature levels to set
            if feature_levels_dict:
                LoggerFactory.update_all_feature_levels(feature_levels_dict)

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
            plugin_directories=[str(self.plugin_dir)],
            event_manager=self.event_manager,
            global_config=self.global_config,
            fast_fail_handler=self.fast_fail_handler,
        )

        self._setup_observers()

        # Clean up any None observers that might exist
        cleaned = self.event_manager.cleanup_none_observers()
        if cleaned > 0:
            self.logger.info(
                "Cleaned up %d None observers during initialization", cleaned
            )

        self.test_cases: List[ITestCase] = []

    def initialize_experiments(self, experiment_config: ExperimentConfig) -> None:
        """Initializes plugins, environment, and validates configuration."""
        try:
            # State tracking now happens automatically through events

            self.experiment_config = experiment_config
            self._save_configuration()

            # Emit experiment initialized event using the experiment emitter
            self.experiment_emitter.emit_initialized(
                config={
                    "experiment_name": self.experiment_name,
                    "test_count": len(experiment_config.tests),
                }
            )

            # State transitions are handled automatically by StateEventObserver

            # Emit plugin loading started event
            self.experiment_emitter.emit_plugin_loading_started()

            # Validate plugins before loading
            self._validate_plugins()

            # Emit plugin loading completed event
            self.experiment_emitter.emit_plugin_loading_completed()

            self._initialize_test_cases()

            # Emit test cases initialized event to trigger workflow transition
            test_names = [test.test_config.name for test in self.test_cases]
            self.experiment_emitter.emit_test_cases_initialized(
                test_count=len(self.test_cases), test_names=test_names
            )

        except PluginValidationError as e:
            # Handle plugin validation errors specifically
            self.logger.error("Plugin validation failed: %s", e)

            # State transitions are handled automatically by StateEventObserver

            self.experiment_emitter.emit_finished_early(
                reason="Plugin Validation Failed",
                details={
                    "phase": "initialization",
                    "error": str(e),
                    "type": "PluginValidationError",
                },
            )
            raise
        except (ImportError, ModuleNotFoundError) as e:
            # Handle import-related errors separately

            # State transitions are handled automatically by StateEventObserver

            # Emit experiment finished early event with error details
            self.experiment_emitter.emit_finished_early(
                reason=f"Import Error: {type(e).__name__}",
                details={
                    "phase": "initialization",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "details": "Failed to import a required module",
                },
            )

            self.logger.error(
                "Initialization failed due to import error: %s", e, exc_info=True
            )
            raise ExperimentInitializationError(f"Import error: {str(e)}") from e

        # We need to catch all exceptions to properly handle them as initialization errors
        except Exception as e:  # pylint: disable=broad-except
            # State transitions are handled automatically by StateEventObserver

            # Emit experiment finished early event with error details
            self.experiment_emitter.emit_finished_early(
                reason=f"Initialization Error: {type(e).__name__}",
                details={
                    "phase": "initialization",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            self.logger.error("Initialization failed: %s", e, exc_info=True)
            raise ExperimentInitializationError(
                f"Failed to initialize experiment: {str(e)}"
            ) from e

    def _validate_plugins(self):
        """
        Validate that all required plugins are available and compatible
        before attempting to run the experiment.
        """
        self.logger.info("Validating plugins for experiment...")

        # Use PluginManager's validation method
        (
            is_valid,
            errors,
        ) = self.plugin_manager.plugin_discovery.validate_experiment_plugins(
            self.experiment_config
        )

        if not is_valid:
            error_message = "Plugin validation failed:\n" + "\n".join(
                f"  - {error}" for error in errors
            )
            self.logger.error(error_message)

            # Log additional helpful information
            available_plugins = self.plugin_manager.list_available_plugins()
            self.logger.info("Available plugins:")
            for plugin_type, plugins in available_plugins.items():
                self.logger.info("  %s: %s", plugin_type, plugins)

            raise PluginValidationError(error_message)

        self.logger.info("All required plugins validated successfully")

    def _save_configuration(self):
        """Save the experiment configuration file in the experiment folder."""
        config_file_path = self.experiment_dir / "experiment_config.yaml"
        with open(config_file_path, "w", encoding="utf-8") as config_file:
            # Convert Pydantic models to dicts for OmegaConf compatibility
            global_config_dict = self.global_config.dict() if hasattr(self.global_config, 'dict') else self.global_config
            experiment_config_dict = self.experiment_config.dict() if hasattr(self.experiment_config, 'dict') else self.experiment_config
            
            config_file.write("# Global Configuration\n")
            config_file.write(OmegaConf.to_yaml(global_config_dict))
            config_file.write("\n# Experiment Configuration\n")
            config_file.write(OmegaConf.to_yaml(experiment_config_dict))

    def _initialize_test_cases(self):
        """Initializes the test cases from the experiment configuration."""
        try:
            test_count = len(self.experiment_config.tests)
            test_names = [test.name for test in self.experiment_config.tests]

            for test_config in self.experiment_config.tests:
                self.logger.info("Initializing test case: %s", test_config.name)

                # Get or create a test-specific emitter for this test case
                test_specific_emitter = self.emitter_registry.get_test_emitter(
                    test_config.name
                )

                # Emit test initialization start event with test-specific emitter
                test_specific_emitter.emit_created(
                    test_name=test_config.name,
                    description=test_config.description,
                    config={"phase": "initialization"},
                )

                # Create the test case with shared emitter registry and workflow tracker
                test_case = TestCase(
                    test_config=test_config,
                    global_config=self.global_config,
                    plugin_manager=self.plugin_manager,
                    experiment_dir=self.experiment_dir,
                    metrics_collector=self.metrics_collector,
                    emitter_registry=self.emitter_registry,
                    workflow_tracker=self.workflow_tracker,
                )

                self.logger.info("Initialized test case '%s'", test_case)
                self.test_cases.append(test_case)

                # Test initialization is already tracked by emit_created above

            # Summary of test case initialization is handled at experiment level
            self.logger.debug("Initialized %d test cases: %s", test_count, test_names)

            self.logger.info("Initialized %s test cases.", len(self.test_cases))

        # We need to catch all exceptions to properly handle them as test initialization errors
        except Exception as e:  # pylint: disable=broad-except
            # Emit experiment finished early event with error details
            self.experiment_emitter.emit_finished_early(
                reason=f"Test Case Initialization Error: {type(e).__name__}",
                details={
                    "phase": "test_case_initialization",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            self.logger.error("Failed to initialize test cases: %s", e, exc_info=True)
            raise TestCaseInitializationError(
                f"Failed to initialize test cases: {str(e)}"
            ) from e

    def run_tests(self) -> None:
        """Runs the tests defined in the experiment configuration."""
        try:
            # State transitions are handled automatically by StateEventObserver

            # Emit execution started event to trigger proper workflow transition
            self.experiment_emitter.emit_execution_started(
                test_count=len(self.test_cases)
            )

            # Experiment-level execution tracking is handled by experiment_emitter
            self.logger.info(
                "Starting test execution for experiment: %s", self.experiment_name
            )

            # Conditionally redirect main loggers through tqdm to prevent progress bar corruption
            # Observer logs will still go to files for detailed analysis
            if self.global_config.progress.redirect_logging:
                redirect_context = logging_redirect_tqdm()
            else:
                # No-op context manager when logging redirection is disabled
                from contextlib import nullcontext

                redirect_context = nullcontext()

            with redirect_context:
                # Use tqdm progress bar if enabled, otherwise use a simple iterator
                if self.global_config.progress.enable_progress_bar:
                    progress_context = tqdm(
                        self.test_cases,
                        total=len(self.test_cases),
                        desc="Number of Tests",
                        position=1,
                        leave=True,
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                        dynamic_ncols=False,
                        file=sys.stdout,
                    )
                else:
                    # Simple iterator wrapper that provides write() method for compatibility
                    class SimpleProgressIterator:
                        def __init__(self, iterable):
                            self.iterable = iterable

                        def __iter__(self):
                            return iter(self.iterable)

                        def __enter__(self):
                            return self

                        def __exit__(self, *args):
                            pass

                        def write(self, msg):
                            print(msg)  # Simple print for status messages

                    progress_context = SimpleProgressIterator(self.test_cases)

                with progress_context as progress_bar:
                    successful_tests = 0
                    failed_tests = 0

                    for test_case in progress_bar:
                        # Show important status updates using tqdm.write (configurable)
                        if self.global_config.progress.show_test_status:
                            emoji = (
                                "🧪 " if self.global_config.progress.use_emojis else ""
                            )
                            self.logger.info(
                                f"{emoji}Starting: {test_case.test_config.name}"
                            )
                        self.logger.info(
                            "Running test case: %s", test_case.test_config.name
                        )

                        # Get test-specific emitter for this test case
                        test_specific_emitter = self.emitter_registry.get_test_emitter(
                            test_case.test_config.name
                        )

                        # Emit test execution started event
                        test_specific_emitter.emit_execution_started(
                            steps=["setup", "execute", "assertions", "teardown"]
                        )

                        try:
                            self.logger.info(
                                "Executing test case: %s", test_case.test_config.name
                            )
                            test_result = test_case.run()
                            
                            # Check if test actually passed (returns None or True for success, False for failure)
                            if test_result is False:
                                failed_tests += 1
                                if self.global_config.progress.show_test_status:
                                    emoji = (
                                        "❌ "
                                        if self.global_config.progress.use_emojis
                                        else ""
                                    )
                                    self.logger.info(
                                        f"{emoji}Failed: {test_case.test_config.name} - Test analysis failed"
                                    )
                                # Emit test failed event
                                test_specific_emitter.emit_failed(
                                    error_message="Test analysis failed",
                                    error_type="TestAnalysisFailure",
                                    phase="analysis",
                                    summary={
                                        "test_name": test_case.test_config.name,
                                        "reason": "Tester analysis determined test failure"
                                    }
                                )
                                continue
                                
                            successful_tests += 1
                            if self.global_config.progress.show_test_status:
                                emoji = (
                                    "✅ "
                                    if self.global_config.progress.use_emojis
                                    else ""
                                )
                                self.logger.info(
                                    f"{emoji}Completed: {test_case.test_config.name}"
                                )

                            # Emit test completed successfully event
                            test_specific_emitter.emit_completed(
                                summary={
                                    "status": "success",
                                    "test_name": test_case.test_config.name,
                                }
                            )

                        except (KeyboardInterrupt, SystemExit):
                            # Emit interrupted test event
                            self.logger.warning(
                                "Test interrupted: %s",
                                test_case.test_config.name,
                                exc_info=True,
                            )
                            test_specific_emitter.emit_failed(
                                error_message="Test interrupted",
                                error_type="KeyboardInterrupt",
                                phase="execution",
                            )
                            raise  # Re-raise to break out of the loop

                        except (
                            TestCaseInitializationError,
                            TestExecutionError,
                            ValueError,
                            TypeError,
                            AttributeError,
                            RuntimeError,
                            OSError,
                            PantherExperimentError,
                            subprocess.CalledProcessError,
                            DockerComposeException,
                            PortConflictException,
                            IvyCompilationException,
                            ResourceExhaustionException,
                            CertificateException,
                            ConfigurationException,
                            TimeoutCascadeException,
                        ) as test_error:
                            # Handle all expected error types with a single handler
                            failed_tests += 1
                            if self.global_config.progress.show_test_status:
                                emoji = (
                                    "❌ "
                                    if self.global_config.progress.use_emojis
                                    else ""
                                )
                                self.logger.info(
                                    f"{emoji}Failed: {test_case.test_config.name} - {str(test_error)[:50]}..."
                                )

                            # Check for critical errors that should terminate experiment
                            if isinstance(
                                test_error,
                                (
                                    DockerComposeException,
                                    PortConflictException,
                                    IvyCompilationException,
                                    ResourceExhaustionException,
                                    CertificateException,
                                ),
                            ):
                                # Use fast-fail handler to determine if we should continue
                                should_continue = self.fast_fail_handler.handle_error(
                                    test_error, raise_on_critical=False
                                )
                                if not should_continue:
                                    self.logger.critical(
                                        "Critical %s error in test %s, terminating experiment",
                                        test_error.category.value,
                                        test_case.test_config.name,
                                    )
                                    # Emit experiment failure and re-raise to stop execution
                                    self.experiment_emitter.emit_finished_early(
                                        reason=f"Critical {test_error.category.value} Failure",
                                        details={
                                            "test_name": test_case.test_config.name,
                                            "error_type": type(test_error).__name__,
                                            "error_category": test_error.category.value,
                                            "error_context": test_error.context,
                                        },
                                    )
                                    raise test_error  # This will break out of the test loop

                            # Add recursion protection for AttributeError
                            if isinstance(
                                test_error, AttributeError
                            ) and "emit_service_setup_completed" in str(test_error):
                                self.logger.error(
                                    "Test case %s failed due to missing event emitter method: %s",
                                    test_case.test_config.name,
                                    str(test_error),
                                )
                                # Emit a simple failed event without triggering more errors
                                try:
                                    test_specific_emitter.emit_failed(
                                        error_message=str(test_error),
                                        error_type="AttributeError",
                                        phase="setup",
                                    )
                                except Exception:  # pylint: disable=broad-except
                                    pass  # Ignore any secondary errors
                            else:
                                self._handle_test_error(test_case, test_error)
                            # Continue with other tests unless critical error occurred

                        # We have to catch Exception to ensure the test loop continues
                        # for all test cases even if one fails unexpectedly
                        except Exception as test_error:  # pylint: disable=broad-except
                            # Generic error handling as a fallback
                            # This is necessary to ensure all tests run even if some fail
                            failed_tests += 1
                            self._handle_test_error(test_case, test_error)
                            self.logger.warning(
                                "Unexpected error type %s caught. Consider adding specific handling.",
                                type(test_error).__name__,
                            )

                        finally:
                            # Clean up test-specific observers after each test completes
                            # This prevents observer duplication when multiple tests run
                            try:
                                self.event_manager.cleanup_scoped_observers("test")
                                self.logger.debug(
                                    "Cleaned up test-scoped observers for test: %s",
                                    test_case.test_config.name,
                                )
                            except (
                                Exception
                            ) as cleanup_error:  # pylint: disable=broad-except
                                self.logger.warning(
                                    "Failed to cleanup test observers for %s: %s",
                                    test_case.test_config.name,
                                    cleanup_error,
                                )

                        # progress_bar.set_postfix({"Running": f"{test_case}"})

            # tqdm.write("")  # Ensures the bar stays at the bottom after completion

            # Experiment-level summary is handled by experiment_emitter
            self.logger.info(
                "Experiment execution summary - Total: %d, Success: %d, Failed: %d",
                len(self.test_cases),
                successful_tests,
                failed_tests,
            )

            self.logger.info(
                "All experiment tests completed. Success: %s, Failed: %s",
                successful_tests,
                failed_tests,
            )
            
            return successful_tests > 0

        except (KeyboardInterrupt, SystemExit):
            self.logger.warning(
                "Experiment execution interrupted by user", exc_info=True
            )
            # Just re-raise these exceptions
            raise

        except Exception as e:
            # Emit test execution failed event with all necessary information for metrics
            self.experiment_emitter.emit_finished_early(
                reason=f"Test Execution Error: {type(e).__name__}",
                details={
                    "phase": "test_execution",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "component": "experiment_manager",
                    "experiment_name": self.experiment_name,
                },
            )
            self.logger.error("Failed during test execution: %s", e, exc_info=True)
            raise TestExecutionError(f"Failed during test execution: {str(e)}") from e

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
        """Load and configure logging for the experiment manager."""
        # Set up the logger

        # Configure formatter based on color preference
        if getattr(self.global_config.logging, "enable_colors", True):
            formatter = ColoredFormatter(
                "%(log_color)s" + self.log_format,
                datefmt="%Y-%m-%d %H:%M:%S",
                reset=True,
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                },
                style="%",
            )
        else:
            formatter = logging.Formatter(self.log_format, datefmt="%Y-%m-%d %H:%M:%S")

        # Create a directory for logs if it doesn't exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        # Create file handler for logging
        file_handler = logging.FileHandler(self.logs_dir / "experiment.log")
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)

        # Add a stream handler to output logs to console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)

        # Configure logger directly instead of using basicConfig to avoid conflicts
        if not self.logger.hasHandlers():
            self.logger.propagate = False
        else:
            # Clear existing handlers to avoid duplicates
            self.logger.handlers.clear()

        # Add both handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.info(
            "ExperimentManager initialized for experiment: %s", self.experiment_name
        )

    def _setup_log_statistics(self):
        """Setup log statistics collection if enabled in configuration."""
        try:
            stats_config = getattr(self.global_config.logging, "statistics", None)
            if not stats_config or not stats_config.enabled:
                return

            from panther.core.utils.log_statistics_display import create_display
            from panther.core.utils.logger_factory import LoggerFactory

            # Enable statistics in LoggerFactory
            stats_dict = {
                "enabled": stats_config.enabled,
                "buffer_size": stats_config.buffer_size,
                "track_performance": stats_config.track_performance,
                "handler_type": stats_config.handler_type,
                "handler_buffer_size": stats_config.handler_buffer_size,
                "flush_interval": stats_config.flush_interval,
            }
            LoggerFactory.enable_statistics(stats_dict)

            # Setup real-time display if enabled
            if stats_config.real_time_display and hasattr(
                LoggerFactory, "_statistics_collector"
            ):
                self.log_statistics_display = create_display(
                    collector=LoggerFactory._statistics_collector,
                    display_mode="detailed",  # Could be configurable
                    interval=stats_config.collection_interval,
                    auto_clear=True,
                )

                # Start display in background
                if self.log_statistics_display.start_display():
                    self.logger.info("Started real-time log statistics display")
                else:
                    self.logger.warning("Failed to start log statistics display")

            self.logger.debug("Log statistics collection enabled")

        except Exception as e:
            self.logger.warning("Failed to setup log statistics: %s", e)

    def _generate_final_log_report(self):
        """Generate final logging statistics report."""
        try:
            stats_config = getattr(self.global_config.logging, "statistics", None)
            if (
                not stats_config
                or not stats_config.enabled
                or not stats_config.generate_reports
            ):
                return

            from panther.core.utils.log_statistics_reporter import LogStatisticsReporter
            from panther.core.utils.logger_factory import LoggerFactory

            if not hasattr(LoggerFactory, "_statistics_collector"):
                return

            collector = LoggerFactory._statistics_collector
            reporter = LogStatisticsReporter(collector)

            # Generate reports in requested formats
            report_dir = self.experiment_dir / "log_statistics"
            report_dir.mkdir(exist_ok=True)

            base_filename = f"log_statistics_{self.experiment_name}"

            for format_type in stats_config.export_formats:
                try:
                    if format_type.lower() == "json":
                        filepath = report_dir / f"{base_filename}.json"
                        if reporter.export_to_file(filepath, "json", pretty=True):
                            self.logger.info(
                                "Generated JSON log statistics report: %s", filepath
                            )

                    elif format_type.lower() == "text":
                        filepath = report_dir / f"{base_filename}.txt"
                        if reporter.export_to_file(filepath, "text"):
                            self.logger.info(
                                "Generated text log statistics report: %s", filepath
                            )

                    elif format_type.lower() == "csv":
                        filepath = report_dir / f"{base_filename}.csv"
                        if reporter.export_to_file(filepath, "csv"):
                            self.logger.info(
                                "Generated CSV log statistics report: %s", filepath
                            )

                except Exception as e:
                    self.logger.warning(
                        "Failed to generate %s log statistics report: %s",
                        format_type,
                        e,
                    )

            # Also save a real-time snapshot for comparison purposes
            try:
                snapshot_path = report_dir / f"{base_filename}_final_snapshot.json"
                if reporter.save_real_time_snapshot(snapshot_path):
                    self.logger.debug(
                        "Saved final log statistics snapshot: %s", snapshot_path
                    )
            except Exception as e:
                self.logger.debug("Failed to save final snapshot: %s", e)

            # Log summary statistics to console
            try:
                stats = collector.get_real_time_stats()
                session = stats["session_info"]
                errors = stats["error_statistics"]

                self.logger.info("📊 Final Logging Statistics Summary:")
                self.logger.info("   Total Messages: %d", session["total_messages"])
                self.logger.info(
                    "   Duration: %.1f seconds", session["duration_seconds"]
                )
                self.logger.info(
                    "   Average Rate: %.2f messages/second",
                    session["messages_per_second"],
                )
                self.logger.info(
                    "   Total Errors: %d (%.2f%%)",
                    errors["total_errors"],
                    errors["error_rate_percent"],
                )

                # Show top features if available
                top_features = stats["message_distribution"]["by_feature"]
                if top_features:
                    top_3 = list(top_features.items())[:3]
                    self.logger.info(
                        "   Top Features: %s",
                        ", ".join([f"{name}({count})" for name, count in top_3]),
                    )

            except Exception as e:
                self.logger.debug("Failed to log statistics summary: %s", e)

        except Exception as e:
            self.logger.warning("Failed to generate final log statistics report: %s", e)

    def _generate_experiment_report(self):
        """Generate comprehensive experiment status report."""
        try:
            from panther.core.reporting.experiment_reporter import ExperimentReporter

            reporter = ExperimentReporter(self.experiment_dir, self.experiment_name)

            # Generate quick summary for logging
            quick_summary = reporter.generate_quick_summary()
            if quick_summary:
                self.logger.info("Experiment Summary: %s", quick_summary)

            # Generate all report formats
            results = reporter.generate_reports()

            # Log success/failure for each format
            if results.get("json"):
                self.logger.info(
                    "Generated machine-readable experiment summary: experiment_summary.json"
                )

            if results.get("markdown"):
                self.logger.info(
                    "Generated human-readable experiment report: EXPERIMENT_REPORT.md"
                )

            if results.get("text"):
                self.logger.info(
                    "Generated text experiment summary: experiment_summary.txt"
                )

            # Log if any reports failed
            failed_reports = [fmt for fmt, success in results.items() if not success]
            if failed_reports:
                self.logger.warning(
                    "Failed to generate reports: %s", ", ".join(failed_reports)
                )

        except Exception as e:
            self.logger.error(
                "Failed to generate experiment report: %s", e, exc_info=True
            )
            # Don't raise - this is best-effort during cleanup

    def _setup_observers(self):  # pylint: disable=unused-argument
        """Sets up the observers for the experiment manager."""
        try:
            # Register StateEventObserver to sync state with events
            from panther.core.observer.impl import (  # pylint: disable=import-outside-toplevel
                StateEventObserver,
            )

            self.state_observer = StateEventObserver(
                self.workflow_tracker, priority=50
            )  # Higher priority
            self.event_manager.register_observer(self.state_observer)
            self.logger.info(
                "Registered StateEventObserver for event-driven state management"
            )

            # File Handler for logging
            if self.global_config.observers.logger.enabled:
                # Create  logger observer
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
                    observer_level_numeric = getattr(logging, observer_log_level.upper(), logging.INFO)
                    global_level_numeric = getattr(logging, global_log_level.upper(), logging.INFO)
                    log_level = (
                        global_log_level 
                        if global_level_numeric >= observer_level_numeric 
                        else observer_log_level
                    )
                    
                    if global_level_numeric > observer_level_numeric:
                        self.logger.debug(
                            f"Using global log level '{global_log_level}' instead of observer level '{observer_log_level}' (more restrictive)"
                        )

                    # Use the standalone function to create an  logger
                    create_logger(
                        name="experiment_logger",
                        global_config=self.global_config,
                        auto_register=True,
                        log_level=log_level,  # Use observer-specific log level
                        output_file=str(self.logs_dir / "event_log.log"),
                        enable_colors=True,
                        include_event_id=True,
                    )
                    self.logger.info("Registered  LoggerObserver")
                except (
                    Exception
                ) as logger_error:  # pylint: disable=broad-exception-caught
                    self.logger.warning(
                        "Failed to create  logger observer: %s. Falling back to basic observer.",
                        logger_error,
                    )

            # Register metrics observer if metrics collector is available
            if self.global_config.observers.metrics.enabled:
                try:
                    self.logger.info("Creating  metrics observer")
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
                    observer_level_numeric = getattr(logging, observer_metrics_log_level.upper(), logging.INFO)
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

                    # Use the standalone function to create an  metrics observer
                    create_metrics(
                        name="experiment_metrics",
                        global_config=self.global_config,
                        auto_register=True,
                        output_dir=str(self.logs_dir),
                        metrics_collector=self.metrics_collector,
                        log_level=metrics_log_level,  # Use observer-specific log level
                    )
                    self.logger.info("Registered  metrics observer")
                except (
                    Exception
                ) as metrics_error:  # pylint: disable=broad-exception-caught
                    self.logger.warning(
                        "Failed to create  metrics observer: %s. Using default configuration instead.",
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
                try:
                    from panther.core.observer import (  # pylint: disable=import-outside-toplevel
                        LoggerObserver,
                    )

                    debug_observer = LoggerObserver(
                        output_file=str(self.logs_dir / "event_debug.log"),
                        log_level="DEBUG",
                        debug_mode=True,
                        track_event_history=True,
                        max_history_size=2000,
                    )
                    self.event_manager.register_observer(debug_observer)
                    self.logger.info(
                        "Registered LoggerObserver with debug mode for detailed event tracking"
                    )
                except (
                    Exception
                ) as debug_error:  # pylint: disable=broad-exception-caught
                    self.logger.warning(
                        "Failed to create debug observer: %s. Event debugging will be limited.",
                        debug_error,
                    )

            self.logger.info(
                "Observers set up for experiment: %s", self.experiment_name
            )
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

    def cleanup(self):
        """Clean up resources including observers and event handlers."""
        self.logger.info("Starting experiment cleanup")

        try:
            # Generate final log statistics report if enabled
            self._generate_final_log_report()

            # Stop log statistics display if running
            if self.log_statistics_display and self.log_statistics_display.running:
                self.log_statistics_display.stop_display()
                self.logger.info("Stopped log statistics display")

            # Clean up state observer
            if hasattr(self, "state_observer"):
                self.event_manager.unregister_observer(self.state_observer)
                self.logger.debug("Unregistered StateEventObserver")

            # Clean up other observers through factory
            factory = get_observer_factory()

            # List of observer names we created
            observer_names = [
                "experiment_logger",
                "experiment_metrics",
                "experiment_observer",
            ]

            for observer_name in observer_names:
                if factory.unregister_observer(observer_name):
                    self.logger.debug("Unregistered %s", observer_name)
                else:
                    self.logger.debug(
                        "%s was not registered or already removed", observer_name
                    )

            # Clear workflow tracker states for this experiment
            if hasattr(self, "workflow_tracker"):
                self.workflow_tracker.clear_workflow_state(self.experiment_name)
                self.logger.debug("Cleared workflow state for experiment")

            # Generate experiment report
            self._generate_experiment_report()

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error during cleanup: %s", e, exc_info=True)
            # Don't raise - we want cleanup to be best-effort

    def __enter__(self):
        """Context manager entry - return self for use in with statements."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup happens."""
        self.cleanup()
        # Don't suppress exceptions
        return False
