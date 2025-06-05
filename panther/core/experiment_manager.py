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
from panther.core.observer.event_manager import EventManager
from panther.core.observer.observer_factory import ObserverFactory, get_observer_factory
from panther.core.observer.events import (
    ExperimentEvent,
    ExperimentInitializedEvent,
    TestCaseInitializedEvent,
    TestExecutionStartedEvent,
    TestExecutionCompletedEvent,
    TestStartedEvent,
    TestCompletedEvent,
)
from panther.core.exceptions.experiment_exceptions import (
    PantherExperimentError,
    ExperimentInitializationError,
    TestCaseInitializationError,
    TestExecutionError,
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
        self.plugin_loader = PluginLoader(plugin_dir, global_config=self.global_config)
        self.plugin_manager = PluginManager(self.plugin_loader)

        # Initialize event manager for experiment-level events
        self.event_manager = EventManager()
        factory = get_observer_factory(self.global_config)
        factory.set_event_manager(self.event_manager)
        self._setup_observers(factory)
        self.test_cases: list[ITestCase] = []

    def initialize_experiments(self, experiment_config: ExperimentConfig):
        """Initializes plugins, environment, and validates configuration."""
        try:
            self.experiment_config = experiment_config
            self._save_configuration()

            # Emit experiment initialized event
            self.event_manager.notify(
                ExperimentInitializedEvent(
                    experiment_id=self.experiment_name,
                    config={"test_count": len(experiment_config.tests)},
                )
            )

            # Load plugins and initialize test cases
            self.plugin_loader.load_plugins()
            self._initialize_test_cases()

        except (ImportError, ModuleNotFoundError) as e:
            # Handle import-related errors separately
            # Emit error event
            self.event_manager.notify(
                ExperimentEvent(
                    "error",
                    {
                        "phase": "initialization",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "details": "Failed to import a required module",
                    },
                )
            )

            self.logger.error("Initialization failed due to import error: %s", e, exc_info=True)
            raise ExperimentInitializationError(f"Import error: {str(e)}") from e

        # We need to catch all exceptions to properly handle them as initialization errors
        except Exception as e:  # pylint: disable=broad-except
            # Emit error event
            self.event_manager.notify(
                ExperimentEvent(
                    "error",
                    {
                        "phase": "initialization",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )
            )

            self.logger.error("Initialization failed: %s", e, exc_info=True)
            raise ExperimentInitializationError(f"Failed to initialize experiment: {str(e)}") from e

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

                # Emit test initialization start event
                self.event_manager.notify(
                    TestStartedEvent(test_config.name, {"phase": "initialization"})
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

                # Emit test initialization complete event
                self.event_manager.notify(
                    TestCompletedEvent(
                        test_config.name, success=True, result={"phase": "initialization"}
                    )
                )

            # Emit summary event for all test cases initialized
            self.event_manager.notify(TestCaseInitializedEvent(test_count, test_names))

            self.logger.info("Initialized %s test cases.", len(self.test_cases))

        # We need to catch all exceptions to properly handle them as test initialization errors
        except Exception as e:  # pylint: disable=broad-except
            # Emit error event
            self.event_manager.notify(
                ExperimentEvent(
                    "error",
                    {
                        "phase": "test_case_initialization",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )
            )

            self.logger.error("Failed to initialize test cases: %s", e, exc_info=True)
            raise TestCaseInitializationError(f"Failed to initialize test cases: {str(e)}") from e

    def run_tests(self):
        """Runs the tests defined in the experiment configuration."""
        try:
            # Emit test execution started event with all necessary metrics information
            self.event_manager.notify(
                TestExecutionStartedEvent(
                    test_name=self.experiment_name, test_id=self.experiment_name  # TODO
                )
            )

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

                        # Emit test started event
                        self.event_manager.notify(
                            TestStartedEvent(
                                test_case.test_config.name,
                                {"config": {"name": test_case.test_config.name}},
                            )
                        )

                        try:
                            self.logger.info("Executing test case: %s", test_case.test_config.name)
                            test_case.run()
                            successful_tests += 1

                            # Emit test completed successfully event
                            self.event_manager.notify(
                                TestCompletedEvent(test_case.test_config.name, success=True)
                            )

                        except (KeyboardInterrupt, SystemExit) as e:
                            # Emit interrupted test event
                            self.logger.warning(
                                "Test interrupted: %s", test_case.test_config.name, exc_info=True
                            )
                            self.event_manager.notify(
                                TestCompletedEvent(
                                    test_case.test_config.name,
                                    success=False,
                                    result={
                                        "error_type": type(e).__name__,
                                        "error_message": "Test interrupted",
                                    },
                                )
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

                        # progress_bar.set_postfix({f"Running": f"{test_case}"})

            tqdm.write("")  # Ensures the bar stays at the bottom after completion

            # Emit test execution completed event with summary
            self.event_manager.notify(
                TestExecutionCompletedEvent(
                    test_id="experiment-summary",
                    test_name=self.experiment_name,
                    success=(failed_tests == 0),
                    results={
                        "success_count": successful_tests,
                        "failure_count": failed_tests,
                        "total_count": len(self.test_cases),
                    },
                    duration_ms=None,  # We're not tracking overall duration here
                )
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
            # Emit error event with all necessary information for metrics
            self.event_manager.notify(
                ExperimentEvent(
                    "error",
                    {
                        "phase": "test_execution",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "component": "experiment_manager",
                        "experiment_name": self.experiment_name,
                    },
                )
            )
            self.logger.error("Failed during test execution: %s", e, exc_info=True)
            raise TestExecutionError(f"Failed during test execution: {str(e)}") from e

    def _handle_test_error(self, test_case, test_error):
        """Helper method to handle test errors consistently."""
        # Emit test failed event
        self.event_manager.notify(
            TestCompletedEvent(
                test_case.test_config.name,
                success=False,
                result={"error_type": type(test_error).__name__, "error_message": str(test_error)},
            )
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

                    # Use the factory to create an enhanced logger
                    factory.create_logger(
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

                    # Use the factory to create an enhanced metrics observer
                    factory.create_metrics(
                        name="experiment_metrics",
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

            self.logger.info("Observers set up for experiment: %s", self.experiment_name)
        except Exception as e:
            # Emit error event with all necessary information for metrics
            self.event_manager.notify(
                ExperimentEvent(
                    "error",
                    {
                        "phase": "observer_setup",
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "component": "experiment_manager",
                        "experiment_name": self.experiment_name,
                    },
                )
            )
            self.logger.error("Failed to set up observers: %s", e, exc_info=True)
            raise
