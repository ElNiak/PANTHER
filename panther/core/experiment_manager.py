# PANTHER-SCP/panther/core/experiment_manager.py

from datetime import datetime
import logging
from pathlib import Path
import subprocess
from typing import List
from omegaconf import OmegaConf


from config.config_experiment_schema import ExperimentConfig
from config.config_global_schema import GlobalConfig
from plugins.plugin_loader import PluginLoader
from core.test_cases.test_interface import ITestCase
from plugins.plugin_manager import PluginManager
from core.test_cases.test_case import TestCase

# TODO implement errors management strategy (e.g., retry, fail, etc.)
class ExperimentManager:
    def __init__(
        self,
        global_config: GlobalConfig,
        experiment_name: str = None,
        plugin_dir: str = "plugins",
        logger: logging.Logger = None,
    ):
        self.global_config = global_config
        self.experiment_name = (
            f"{experiment_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}" if experiment_name
            else f"experiment_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        )
        self.experiment_dir = Path(global_config.paths.output_dir) / self.experiment_name
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        
        
        self.logs_dir   = self.experiment_dir
        self.plugin_dir = plugin_dir
        self.logger = logger or logging.getLogger("ExperimentManager")
        self.plugin_dir     = Path(plugin_dir)
        self.plugin_loader  = PluginLoader(plugin_dir)
        self.plugin_manager = PluginManager(self.plugin_loader)
        
        self.test_cases: List[ITestCase] = []
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
        with open(config_file_path, 'w') as config_file:
            config_file.write(OmegaConf.to_yaml(self.global_config))
            config_file.write(OmegaConf.to_yaml(self.experiment_config))
            
    def _initialize_test_cases(self):
        """Initializes the test cases from the experiment configuration."""
        try:
            for test_config in self.experiment_config.tests:
                self.logger.info(f"Initializing test case: {test_config.name}")
                test_case = TestCase(test_config=test_config, 
                                     global_config=self.global_config,
                                     plugin_manager=self.plugin_manager,
                                     experiment_dir=self.experiment_dir)
                
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
        # TODO add this behavior into the observer pattern
        """
        log_level = getattr(logging, self.global_config.logging.level.upper(), logging.INFO)
        log_format = self.global_config.logging.format
       
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