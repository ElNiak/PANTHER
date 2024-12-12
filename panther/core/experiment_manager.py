from datetime import datetime
import logging
from pathlib import Path
from omegaconf import OmegaConf


from panther.config.config_experiment_schema import ExperimentConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.plugin_loader import PluginLoader
from panther.core.test_cases.test_interface import ITestCase
from panther.plugins.plugin_manager import PluginManager
from panther.core.test_cases.test_case import TestCase


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
    ):
        self.experiment_config = None
        self.global_config = global_config
        self.experiment_name = (
            f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{experiment_name}"
            if experiment_name
            else f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_unnamed_experiment"
        )
        self.experiment_dir = (
            Path(global_config.paths.output_dir) / self.experiment_name
        )
        self.experiment_dir.mkdir(parents=True, exist_ok=True)

        self.logs_dir = self.experiment_dir
        self.plugin_dir = plugin_dir
        self.logger = logger or logging.getLogger("ExperimentManager")
        self.plugin_dir = Path(plugin_dir)
        self.plugin_loader = PluginLoader(plugin_dir)
        self.plugin_manager = PluginManager(self.plugin_loader)

        self.test_cases: list[ITestCase] = []
        self._load_logging()

    def initialize_experiments(self, experiment_config: ExperimentConfig):
        """Initializes plugins, environment, and validates configuration."""
        try:
            self.experiment_config = experiment_config
            self._save_configuration()
            self.plugin_loader.load_plugins()
            self._initialize_test_cases()
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
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
            for test_config in self.experiment_config.tests:
                self.logger.info(f"Initializing test case: {test_config.name}")
                test_case = TestCase(
                    test_config=test_config,
                    global_config=self.global_config,
                    plugin_manager=self.plugin_manager,
                    experiment_dir=self.experiment_dir,
                )

                self.logger.info(f"Initialized test case '{test_case}'")
                self.test_cases.append(test_case)
            self.logger.info(f"Initialized {len(self.test_cases)} test cases.")
        except Exception as e:
            self.logger.error(f"Failed to initialize test cases: {e}")
            raise

    def run_tests(self):
        """Runs the tests defined in the experiment configuration."""
        try:
            self.logger.info("Starting experiment tests...")
            for test_case in self.test_cases:
                self.logger.debug(f"Starting test: {test_case}")
                test_case.run()
            self.logger.info("All experiment tests completed.")
        except Exception as e:
            self.logger.error(f"Failed during test execution: {e}")
            raise

    def _load_logging(self):
        """
        Configures logging to output to both console and a log file.
        # TODO add this behavior into the observer pattern
        """
        log_level = getattr(
            logging, self.global_config.logging.level.upper(), logging.INFO
        )
        log_format = self.global_config.logging.format
        # File Handler
        panther_log_file = self.logs_dir / "experiment.log"
        panther_log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(panther_log_file),
            ],
        )
