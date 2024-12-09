# PANTHER-SCP/panther/core/experiment_manager.py

from datetime import datetime
import logging
from pathlib import Path
import subprocess
from typing import List
from omegaconf import DictConfig


from plugins.plugin_loader import PluginLoader
from core.results.result_handlers.storage_handler import StorageHandler
from core.test_cases.test_interface import ITestCase
from core.results.result_collector import ResultCollector
from plugins.plugin_manager import PluginManager
from core.test_cases.test_case import TestCase

# TODO implement errors management strategy (e.g., retry, fail, etc.)

class ExperimentManager:
    def __init__(
        self,
        experiment_config: DictConfig,
        experiment_name: str = None,
        plugin_dir: str = "plugins",
        logger: logging.Logger = None,
    ):
        self.experiment_config = experiment_config
        self.experiment_name = (
            f"{experiment_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}" if experiment_name
            else f"experiment_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        )
        
        self.experiment_dir = Path(experiment_config.paths.output_dir) / self.experiment_name
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        
        # Save the experiment configuration file in the experiment folder
        config_file_path = self.experiment_dir / "experiment_config.yaml"
        with open(config_file_path, 'w') as config_file:
            config_file.write(str(self.experiment_config))
            
        self.logs_dir = self.experiment_dir
        
        self.plugin_dir = plugin_dir
        self.logger = logger or logging.getLogger("ExperimentManager")
        
        self.plugin_dir = Path(plugin_dir)
        self.plugin_loader = PluginLoader(plugin_dir)
        self.plugin_manager = PluginManager(self.plugin_loader)
                
        self.result_collectors = ResultCollector()
        
        self.test_cases: List[ITestCase] = []

        self._initialize_experiment()

    def _initialize_experiment(self):
        """Initializes plugins, environment, and validates configuration."""
        try:
            self._load_logging()
            self._validate_configuration()
            self.plugin_loader.load_plugins()
            self._initialize_test_cases()
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            raise


    def _validate_configuration(self):
        """Validates the experiment configuration."""
        if not self.experiment_config.tests:
            raise ValueError("Experiment configuration must include at least one test.")
        self.logger.info("Experiment configuration validated.")

    def _initialize_test_cases(self):
        """Initializes the test cases from the experiment configuration."""
        try:
            for test_config in self.experiment_config.tests:
                self.logger.info(f"Initializing test case: {test_config.name}")
                net_environment_type = test_config.network_environment
                self.logger.info(f"Loading network environment: {net_environment_type}")
                # if not net_environment_type:
                #     raise ValueError(f"Unknown environment type: {net_environment_type}")
                execution_environment_types = []
                exec_environment_types = test_config.execution_environment
                for exec_env in exec_environment_types:
                    self.logger.info(f"Loading execution environment: {exec_env}")
                    execution_environment_types.append(exec_env)
                # if not exec_environment_type:
                #     raise ValueError(f"Unknown environment type: {exec_environment_type}")
                test_experiment_dir = self.experiment_dir / test_config.name.replace(" ", "_")
                self.result_collectors.register_handler(f"storage_{test_config.name.replace(' ', '_')})",  
                                                        StorageHandler(self.experiment_dir, 
                                                                       test_config.name.replace(" ", "_")))
                
                environment_types = {
                    "network": [net_environment_type],
                    "execution": execution_environment_types 
                }
                self.logger.info(f"Initializing environment_types '{environment_types}'")
                test_case = TestCase(test_config=test_config, 
                                     logger=self.logger, 
                                     result_collector=self.result_collectors, 
                                     environment_types=environment_types, 
                                     plugin_manager=self.plugin_manager,
                                     test_experiment_dir=test_experiment_dir,
                                     paths=self.experiment_config.paths)
                
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
                test_case.run()
            self.logger.info("All experiment tests completed.")
        except Exception as e:
            self.logger.error(f"Failed during test execution: {e}")
            raise

    
    def _load_logging(self):
        """
        Configures logging to output to both console and a log file.
        """
        log_level = getattr(logging, self.experiment_config.logging.level.upper(), logging.INFO)
        log_format = self.experiment_config.logging.format
       
        # TODO 2024-11-15 09:17:22,857 [ERROR] - docker_builder - Unexpected error during build of 'picoquic_rfc9000_panther:latest': 'dict' object has no attribute 'decode' 
        # if log_level == logging.DEBUG:
        #     self.plugin_loader.docker_builder.build_log_file = self.logs_dir / "docker_build.log"

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