from datetime import datetime
import logging
from pathlib import Path
import re
from typing import Optional
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
import sys

# Import metrics components
try:
    from panther.core.metrics import Phase
except ImportError:
    # Fallback if metrics are not available
    class Phase:
        EXPERIMENT_INITIALIZATION = "experiment_initialization"
        TEST_CASE_INITIALIZATION = "test_case_initialization"
        TEST_EXECUTION = "test_execution"


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
        metrics_collector: Optional[MetricsCollector] = None,
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

        self.logs_dir = self.experiment_dir
        self.plugin_dir = plugin_dir
        self.logger = logger or logging.getLogger("ExperimentManager")
        self.plugin_dir = Path(plugin_dir)
        self.plugin_loader = PluginLoader(plugin_dir, global_config=self.global_config)
        self.plugin_manager = PluginManager(self.plugin_loader)

        self.test_cases: list[ITestCase] = []
        self._load_logging()

    def initialize_experiments(self, experiment_config: ExperimentConfig):
        """Initializes plugins, environment, and validates configuration."""
        try:
            if self.metrics_collector:
                self.metrics_collector.increment_counter("experiment_initializations_total")
                with self.metrics_collector.time_operation("plugin_loading"):
                    self.experiment_config = experiment_config
                    self._save_configuration()
                    self.plugin_loader.load_plugins()

                with self.metrics_collector.time_operation("test_case_initialization"):
                    self._initialize_test_cases()
            else:
                self.experiment_config = experiment_config
                self._save_configuration()
                self.plugin_loader.load_plugins()
                self._initialize_test_cases()
        except Exception as e:
            if self.metrics_collector:
                self.metrics_collector.record_error(
                    phase=Phase.EXPERIMENT_INITIALIZATION,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    component="experiment_manager",
                    metadata={"experiment_name": self.experiment_name},
                )
            self.logger.error("Initialization failed: %s", e)
            raise

    def _save_configuration(self):
        # Save the experiment configuration file in the experiment folder
        config_file_path = self.experiment_dir / "experiment_config.yaml"
        with open(config_file_path, "w") as config_file:
            config_file.write(OmegaConf.to_yaml(self.global_config))
            config_file.write(OmegaConf.to_yaml(self.experiment_config))

    def _initialize_test_cases(self):
        """Initializes the test cases from the experiment configuration."""
        try:
            if self.metrics_collector:
                self.metrics_collector.set_gauge(
                    "test_cases_configured", len(self.experiment_config.tests)
                )

            for test_config in self.experiment_config.tests:
                self.logger.info("Initializing test case: %s", test_config.name)

                if self.metrics_collector:
                    with self.metrics_collector.time_operation(
                        f"test_case_init_{test_config.name}"
                    ):
                        test_case = TestCase(
                            test_config=test_config,
                            global_config=self.global_config,
                            plugin_manager=self.plugin_manager,
                            experiment_dir=self.experiment_dir,
                            metrics_collector=self.metrics_collector,
                        )
                else:
                    test_case = TestCase(
                        test_config=test_config,
                        global_config=self.global_config,
                        plugin_manager=self.plugin_manager,
                        experiment_dir=self.experiment_dir,
                        metrics_collector=self.metrics_collector,
                    )

                self.logger.info("Initialized test case '%s'", test_case)
                self.test_cases.append(test_case)

            if self.metrics_collector:
                self.metrics_collector.set_gauge("test_cases_initialized", len(self.test_cases))

            self.logger.info("Initialized %s test cases.", len(self.test_cases))
        except Exception as e:
            if self.metrics_collector:
                self.metrics_collector.record_error(
                    phase=Phase.TEST_CASE_INITIALIZATION,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    component="experiment_manager",
                    metadata={"experiment_name": self.experiment_name},
                )
            self.logger.error("Failed to initialize test cases: %s", e)
            raise

    def run_tests(self):
        """Runs the tests defined in the experiment configuration."""
        try:
            self.logger.info("Starting experiment tests...")
            test_timer = None
            if self.metrics_collector:
                self.metrics_collector.increment_counter("test_execution_sessions_total")
                self.metrics_collector.set_gauge("test_cases_to_run", len(self.test_cases))

            # Use tqdm.write to log messages so the progress bar is not overwritten by logs
            with logging_redirect_tqdm():
                with tqdm(
                    self.test_cases,
                    total=len(self.test_cases),
                    desc="Number of Tests",
                    position=1,
                    leave=True,
                    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
                    dynamic_ncols=True,
                    file=sys.stdout,
                ) as progress_bar:
                    successful_tests = 0
                    failed_tests = 0

                    for test_case in progress_bar:
                        self.logger.info("Running: %s", test_case)

                        if self.metrics_collector:
                            self.metrics_collector.increment_counter("test_cases_total")
                            test_timer = self.metrics_collector.start_timing(
                                f"test_case_duration_{test_case.test_config.name}"
                            )

                        try:
                            test_case.run()
                            successful_tests += 1

                            if self.metrics_collector:
                                self.metrics_collector.increment_counter("test_cases_successful")

                        except Exception as test_error:
                            failed_tests += 1

                            if self.metrics_collector:
                                self.metrics_collector.increment_counter("test_cases_failed")
                                self.metrics_collector.record_error(
                                    phase=Phase.TEST_EXECUTION,
                                    error_type=type(test_error).__name__,
                                    error_message=str(test_error),
                                    component="experiment_manager",
                                    test_case=test_case.test_config.name,
                                    metadata={"experiment_name": self.experiment_name},
                                )

                            self.logger.error(
                                "Test case %s failed: %s",
                                test_case.test_config.name,
                                test_error
                            )
                            # Continue with other tests instead of failing completely

                        finally:
                            if self.metrics_collector and "test_timer" in locals():
                                test_timer.stop()

                        progress_bar.set_postfix_str(f"Running: {test_case}")

            tqdm.write("")  # Ensures the bar stays at the bottom after completion

            if self.metrics_collector:
                self.metrics_collector.set_gauge("test_cases_successful_final", successful_tests)
                self.metrics_collector.set_gauge("test_cases_failed_final", failed_tests)
                success_rate = successful_tests / len(self.test_cases) if self.test_cases else 0
                self.metrics_collector.set_gauge("test_success_rate", success_rate)

            self.logger.info(
                "All experiment tests completed. Success: %s, Failed: %s",
                successful_tests,
                failed_tests
            )

        except Exception as e:
            if self.metrics_collector:
                self.metrics_collector.record_error(
                    phase=Phase.TEST_EXECUTION,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    component="experiment_manager",
                    metadata={"experiment_name": self.experiment_name},
                )
            self.logger.error("Failed during test execution: %s", e)
            raise

    def _load_logging(self, logger: logging.Logger = None, path: Path = None):
        """
        Configures logging to output to both console and a log file.
        # TODO add this behavior into the observer pattern
        """
        log_level = getattr(logging, self.global_config.logging.level.name, logging.INFO)
        log_format = self.global_config.logging.format
        # File Handler
        if path is None:
            panther_log_file = self.logs_dir / "experiment.log"
            panther_log_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            panther_log_file = path / "experiment.log"
            panther_log_file.parent.mkdir(parents=True, exist_ok=True)

        # Define a colored formatter
        colored_formatter = ColoredFormatter(
            "%(log_color)s" + log_format,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )

        # Console Handler with color
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(colored_formatter)

        # File Handler without color
        file_handler = logging.FileHandler(panther_log_file)

        # Configure logging
        if logger is not None:
            logger.setLevel(log_level)
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
        else:
            logging.basicConfig(
                level=log_level,
                format=log_format,
                handlers=[
                    console_handler,
                    file_handler,
                ],
            )