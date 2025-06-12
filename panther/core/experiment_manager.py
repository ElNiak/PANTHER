from datetime import datetime
import logging
from pathlib import Path
import re
from omegaconf import OmegaConf
from colorlog import ColoredFormatter
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from panther.core.metrics.metrics_collector import MetricsCollector
from panther.config.config_experiment_schema import ExperimentConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.plugins.plugin_manager import PluginManager
from panther.core.test_cases.test_case_impl import TestCase
from panther.core.observer.management.event_manager import EventManager
from panther.core.events import (
    ExperimentEventEmitter,
    TestEventEmitter,
    ServiceEventEmitter,
    EnvironmentEventEmitter,
    MetricsEventEmitter,
    PluginEventEmitter,
)
from panther.core.observer.factory import ObserverFactory, get_observer_factory
from panther.core.observer.factory.factory_builders import (
    create_logger,
    create_metrics,
    create_experiment_observer,
)
from panther.core.exceptions.experiment_exceptions import (
    PantherExperimentError,
    ExperimentInitializationError,
    TestCaseInitializationError,
    TestExecutionError,
    PluginValidationError,
)
import sys


# TODO implement errors management strategy (e.g., retry, fail, etc.)
class ExperimentManager:
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
        plugin_loader (PluginLoader): Loader for experiment plugins.
        plugin_manager (PluginManager): Manager for experiment plugins.
        test_cases (list[ITestCase]): List of test cases to be executed.

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
        metrics_collector: MetricsCollector | None = None,
    ):
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
        self.experiment_dir = Path(global_config.paths.output_dir) / self.experiment_name
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        self.log_level = getattr(logging, self.global_config.logging.level.name, logging.INFO)
        self.log_format = self.global_config.logging.format

        self.logs_dir = self.experiment_dir
        self.plugin_dir = plugin_dir
        self.logger = logger or logging.getLogger("ExperimentManager")
        self._load_logging()
        self.plugin_dir = Path(plugin_dir)

        # Initialize event manager for experiment-level events
        self.event_manager = EventManager()
        factory = get_observer_factory(self.global_config)
        factory.set_event_manager(self.event_manager)

        # Initialize entity-specific emitters for type-safe event emission
        self.experiment_emitter = ExperimentEventEmitter(self.event_manager, self.experiment_name)
        # Note: TestEventEmitter instances are created per test case in _initialize_test_cases() and run_tests()
        self.service_emitter = ServiceEventEmitter(self.event_manager)
        self.environment_emitter = EnvironmentEventEmitter(self.event_manager)
        self.metrics_emitter = MetricsEventEmitter(self.event_manager)
        self.plugin_emitter = PluginEventEmitter(self.event_manager)

        # Setup plugin loader with event manager
        self.plugin_loader = PluginLoader(plugin_dir, global_config=self.global_config)
        self.plugin_loader.event_manager = self.event_manager

        # Setup plugin manager with the plugin loader that has the event manager
        self.plugin_manager = PluginManager(
            plugin_loader=self.plugin_loader,
            plugin_directories=[str(self.plugin_dir)],
            event_manager=self.event_manager,
        )

        self._setup_observers(factory)
        self.test_cases: list[ITestCase] = []

    def initialize_experiments(self, experiment_config: ExperimentConfig):
        """Initializes plugins, environment, and validates configuration."""
        try:
            self.experiment_config = experiment_config
            self._save_configuration()

            # Emit experiment initialized event using the experiment emitter
            self.experiment_emitter.emit_initialized(
                config={
                    "experiment_name": self.experiment_name,
                    "test_count": len(experiment_config.tests),
                }
            )

            # Validate plugins before loading
            self._validate_plugins()

            # Load plugins and initialize test cases
            self.plugin_loader.load_plugins()
            self._initialize_test_cases()

        except PluginValidationError as e:
            # Handle plugin validation errors specifically
            self.logger.error("Plugin validation failed: %s", e)
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

            self.logger.error("Initialization failed due to import error: %s", e, exc_info=True)
            raise ExperimentInitializationError(f"Import error: {str(e)}") from e

        # We need to catch all exceptions to properly handle them as initialization errors
        except Exception as e:  # pylint: disable=broad-except
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
            raise ExperimentInitializationError(f"Failed to initialize experiment: {str(e)}") from e

    def _validate_plugins(self):
        """
        Validate that all required plugins are available and compatible
        before attempting to run the experiment.
        """
        self.logger.info("Validating plugins for experiment...")

        # Use PluginManager's validation method
        is_valid, errors = self.plugin_manager.validate_experiment_plugins(self.experiment_config)

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
            config_file.write(OmegaConf.to_yaml(self.global_config))
            config_file.write(OmegaConf.to_yaml(self.experiment_config))

    def _initialize_test_cases(self):
        """Initializes the test cases from the experiment configuration."""
        try:
            test_count = len(self.experiment_config.tests)
            test_names = [test.name for test in self.experiment_config.tests]

            for test_config in self.experiment_config.tests:
                self.logger.info("Initializing test case: %s", test_config.name)

                # Create a test-specific emitter for this test case
                test_specific_emitter = TestEventEmitter(self.event_manager, test_config.name)

                # Emit test initialization start event with test-specific emitter
                test_specific_emitter.emit_created(
                    test_name=test_config.name,
                    description=test_config.description,
                    config={"phase": "initialization"},
                )

                # Create the test case
                test_case = TestCase(
                    test_config=test_config,
                    global_config=self.global_config,
                    plugin_manager=self.plugin_manager,
                    experiment_dir=self.experiment_dir,
                    metrics_collector=self.metrics_collector,
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
            raise TestCaseInitializationError(f"Failed to initialize test cases: {str(e)}") from e

    def run_tests(self):
        """Runs the tests defined in the experiment configuration."""
        try:
            # Experiment-level execution tracking is handled by experiment_emitter
            self.logger.info("Starting test execution for experiment: %s", self.experiment_name)

            # Use tqdm.write to log messages so the progress bar is not overwritten by logs
            with logging_redirect_tqdm(
                # loggers=[self.logger]
            ):
                with tqdm(
                    self.test_cases,
                    total=len(self.test_cases),
                    desc="Number of Tests",
                    position=1,
                    leave=True,
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                    dynamic_ncols=False,
                    file=sys.stdout,
                ) as progress_bar:
                    successful_tests = 0
                    failed_tests = 0

                    for test_case in progress_bar:
                        self.logger.info("Running test case: %s", test_case.test_config.name)

                        # Create a test-specific emitter for this test case
                        test_specific_emitter = TestEventEmitter(
                            self.event_manager, test_case.test_config.name
                        )

                        # Emit test execution started event
                        test_specific_emitter.emit_execution_started(
                            steps=["setup", "execute", "assertions", "teardown"]
                        )

                        try:
                            self.logger.info("Executing test case: %s", test_case.test_config.name)
                            test_case.run()
                            successful_tests += 1

                            # Emit test completed successfully event
                            test_specific_emitter.emit_completed(
                                summary={
                                    "status": "success",
                                    "test_name": test_case.test_config.name,
                                }
                            )

                        except (KeyboardInterrupt, SystemExit) as e:
                            # Emit interrupted test event
                            self.logger.warning(
                                "Test interrupted: %s", test_case.test_config.name, exc_info=True
                            )
                            test_specific_emitter.emit_failed(
                                error_message="Test interrupted",
                                error_type=type(e).__name__,
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
                        ) as test_error:
                            # Handle all expected error types with a single handler
                            failed_tests += 1
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
                                except:
                                    pass  # Ignore any secondary errors
                            else:
                                self._handle_test_error(test_case, test_error)
                            # Continue with other tests

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

                        progress_bar.set_postfix({"Running": f"{test_case}"})

            tqdm.write("")  # Ensures the bar stays at the bottom after completion

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

        except (KeyboardInterrupt, SystemExit):
            self.logger.warning("Experiment execution interrupted by user", exc_info=True)
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
        # Create a test-specific emitter for this test case
        test_specific_emitter = TestEventEmitter(self.event_manager, test_case.test_config.name)

        # Emit test failed event
        test_specific_emitter.emit_failed(
            error_message=str(test_error),
            error_type=type(test_error).__name__,
            phase="execution",
            summary={"test_name": test_case.test_config.name},
        )
        self.logger.error(
            "Test case %s failed: %s", test_case.test_config.name, test_error, exc_info=True
        )

    def _load_logging(self):
        """Load and configure logging for the experiment manager."""
        # Set up the logger

        # Create a formatter with colors if available
        formatter = ColoredFormatter(
            "%(log_color)s" + self.log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )

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

        logging.basicConfig(
            level=self.log_level, format=self.log_format, handlers=[file_handler, console_handler]
        )
        self.logger.info("ExperimentManager initialized for experiment: %s", self.experiment_name)

    def _setup_observers(self, factory: ObserverFactory):
        """Sets up the observers for the experiment manager."""
        try:
            # File Handler for logging
            if self.global_config.observers.logger.enabled:
                # Create enhanced logger observer
                try:
                    self.logger.debug("Creating enhanced logger observer")
                    # Get log level from observer config if available, otherwise fallback to global log level
                    log_level = (
                        self.global_config.observers.logger.log_level
                        if hasattr(self.global_config, "observers")
                        and hasattr(self.global_config.observers, "logger")
                        else logging.getLevelName(self.log_level)
                    )

                    # Use the standalone function to create an enhanced logger
                    create_logger(
                        name="experiment_logger",
                        global_config=self.global_config,
                        auto_register=True,
                        log_level=log_level,  # Use observer-specific log level
                        output_file=str(self.logs_dir / "event_log.log"),
                        enable_colors=True,
                        include_event_id=True,
                    )
                    self.logger.info("Registered enhanced LoggerObserver")
                except Exception as logger_error:
                    self.logger.warning(
                        f"Failed to create enhanced logger observer: {logger_error}. Falling back to basic observer."
                    )

            # Register metrics observer if metrics collector is available
            if self.global_config.observers.metrics.enabled:
                try:
                    self.logger.info("Creating enhanced metrics observer")
                    # Get metrics observer log level if available
                    metrics_log_level = (
                        self.global_config.observers.metrics.log_level
                        if hasattr(self.global_config, "observers")
                        and hasattr(self.global_config.observers, "metrics")
                        else "INFO"
                    )

                    # Use the standalone function to create an enhanced metrics observer
                    create_metrics(
                        name="experiment_metrics",
                        global_config=self.global_config,
                        auto_register=True,
                        output_dir=str(self.logs_dir),
                        metrics_collector=self.metrics_collector,
                        log_level=metrics_log_level,  # Use observer-specific log level
                    )
                    self.logger.info("Registered enhanced metrics observer")
                except Exception as metrics_error:
                    self.logger.warning(
                        "Failed to create enhanced metrics observer: %s. Using default configuration instead.",
                        metrics_error,
                    )

            # Create an experiment observer to handle experiment-specific events
            create_experiment_observer(
                name="experiment_observer",
                global_config=self.global_config,
                auto_register=True,
                priority=10,  # Higher priority to ensure it gets events first
                output_dir=str(self.logs_dir),
                test_name=self.experiment_name,
                track_timing=True,
                track_steps=True,
            )
            self.logger.info("Registered ExperimentObserver")

            # Create a logger observer with debug mode if debug logging is enabled
            if self.log_level <= logging.DEBUG:
                try:
                    from panther.core.observer.logger.logger_observer import LoggerObserver

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
                except Exception as debug_error:
                    self.logger.warning(
                        f"Failed to create debug observer: {debug_error}. Event debugging will be limited."
                    )

            self.logger.info("Observers set up for experiment: %s", self.experiment_name)
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
