# PANTHER-SCP/panther/core/experiment_manager.py

from datetime import datetime
import logging
from pathlib import Path
import subprocess
from typing import List
from omegaconf import DictConfig


from core.utils.plugin_loader import PluginLoader
from core.results.result_handlers.storage_handler import StorageHandler
from core.test_cases.test_interface import ITestCase
from core.results.result_collector import ResultCollector
from plugins.environments.environment_interface import IEnvironmentPlugin
from plugins.environments.environment_manager import EnvironmentManager
from plugins.plugin_manager import PluginManager
from core.observer.event_manager import EventManager
from core.observer.event import Event
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
            
        self.logs_dir = self.experiment_dir / "logs"
        
        self.plugin_dir = plugin_dir
        self.logger = logger or logging.getLogger("ExperimentManager")
        self.event_manager = EventManager()
        
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
        if not self.experiment_config.get("tests"):
            raise ValueError("Experiment configuration must include at least one test.")
        self.logger.info("Experiment configuration validated.")

    def _initialize_test_cases(self):
        """Initializes the test cases from the experiment configuration."""
        try:
            for test_config in self.experiment_config.get("tests", []):
                net_environment_type = test_config.get("network_environment", "localhost")
                # if not net_environment_type:
                #     raise ValueError(f"Unknown environment type: {net_environment_type}")
                exec_environment_type = test_config.get("execution_environment", [])
                # if not exec_environment_type:
                #     raise ValueError(f"Unknown environment type: {exec_environment_type}")
                test_experiment_dir = self.experiment_dir / test_config.get("name", "Unnamed Test").replace(" ", "_")
                self.result_collectors.register_handler(f"storage_{test_config.get('name', 'Unnamed Test').replace(' ', '_')})",  
                                                        StorageHandler(self.experiment_dir, 
                                                                       test_config.get("name", "Unnamed Test").replace(" ", "_")))
                test_case = TestCase(test_config, 
                                     self.logger, 
                                     self.result_collectors, 
                                     {"network":net_environment_type,
                                      "execution":exec_environment_type}, 
                                     self.event_manager,
                                     self.plugin_manager,
                                     test_experiment_dir)
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
                # Check if new certificates should be generated
                if self.experiment_config.get('generate_new_certificates', False):
                    subprocess.run(["bash", 'generate_certificates.sh'])
                test_case.run()
            self.logger.info("All experiment tests completed.")
        except Exception as e:
            self.logger.error(f"Failed during test execution: {e}")
            raise

    def teardown(self):
        """Tears down the environment and releases resources."""
        try:
            if self.environment_manager:
                self.environment_manager.teardown_all()
                self.logger.info("Environment torn down successfully.")
        except Exception as e:
            self.logger.error(f"Failed to teardown environment: {e}")
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

    def teardown_experiment(self):
        """
        Tears down the experiment by stopping all services and environments.
        """
        self.logger.info("Tearing down the experiment")
        self.teardown_services()
        self.teardown_environments()
        self.logger.info("Experiment torn down successfully")
        self.event_manager.notify(Event("experiment_teardown", {"experiment": self.experiment_name}))

    def teardown_services(self):
        """
        Stops all services managed by the service managers.
        """
        self.logger.info("Stopping all services")
        for manager in self.service_managers:
            if hasattr(manager, "stop_service"):
                try:
                    manager.stop_service()
                    self.logger.info(f"Service '{manager.__class__.__name__}' stopped.")
                    self.event_manager.notify(Event("service_stopped", {"service": manager}))
                except Exception as e:
                    self.logger.error(f"Failed to stop service manager '{manager.__class__.__name__}': {e}")

    def teardown_environments(self):
        """
        Tears down all environments managed by the environment managers.
        """
        self.logger.info("Tearing down all environments")
        for env_manager in self.environment_manager:
            if hasattr(env_manager, "teardown_environment"):
                try:
                    env_manager.teardown_environment()
                    self.logger.info(f"Environment '{env_manager.__class__.__name__}' torn down successfully.")
                    self.event_manager.notify(Event("environment_teardown", {"environment": env_manager}))
                except Exception as e:
                    self.logger.error(f"Failed to teardown environment '{env_manager.__class__.__name__}': {e}")
            else:
                self.logger.debug(f"No teardown_environment method for '{env_manager.__class__.__name__}'. Skipping.")
    
    # def run_tests(self):
    #     """
    #     Orchestrates the entire experiment workflow.
    #     """
    #     try:
    #         tests = self.experiment_config.get("tests", [])

    #         for test in tests:
    #             # TODO create subtest folder for each test
    #             self.logger.info(f"Starting Test: {test.get('name', 'Unnamed Test')}")
    #             self.logger.info(f"Description:   {test.get('description', '')}")

    #             protocol    = test.get("protocol")
    #             environment = test.get("network_environment")  # Ensure consistent naming
    #             services    = test.get("services", {})
    #             self.current_test_services = services
    #             steps      = test.get("steps", {})
    #             assertions = test.get("assertions", [])
                
    #             # Check if new certificates should be generated
    #             if self.experiment_config.get('generate_new_certificates', False):
    #                 subprocess.run(["bash", 'generate_certificates.sh'])

    #             # Step 1: Extract required implementations from services
    #             required_implementations = set()
    #             for service_name, service_details in services.items():
    #                 implementation = service_details.get("implementation")
    #                 if implementation:
    #                     required_implementations.add(implementation)
    #                 else:
    #                     self.logger.warning(f"Service '{service_name}' does not specify an implementation.")

    #             if not required_implementations:
    #                 self.logger.error("No implementations specified for services. Aborting test.")
    #                 continue  # Skip to the next test

    #             self.logger.debug(f"Required implementations for this test: {required_implementations}")

    #             # Step 2: Initialize only the required protocol managers
    #             self.initialize_protocol_managers([protocol], required_implementations)

    #             # Step 3: Initialize environment managers
    #             self.initialize_environment_managers([environment])

    #             # Step 4: Build Docker images if necessary
    #             self.build_docker_images()

    #             deployment_commands = self.generate_deployment_commands(environment)

    #             # Step 5: Setup environments with services
    #             # Generate timestamp and paths
    #             timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    #             paths = self.experiment_config.get('paths', {})
            
    #             self.setup_environments(services,deployment_commands, paths, timestamp)

    #             # Step 6: Deploy services
                
    #             self.deploy_services()

    #             # Step 7: Execute test steps
    #             self.execute_steps(steps)

    #             # Step 8: Perform assertions
    #             self.perform_assertions(assertions)

    #             # Step 9: Teardown for the test
    #             self.teardown_experiment()

    #             self.logger.info(f"Completed Test: {test.get('name', 'Unnamed Test')}")
    #             self.event_manager.notify(Event("test_completed", {"test": test.get("name", "Unnamed Test")}))
    #     except Exception as e:
    #         self.logger.error(f"Experiment encountered an error: {e}")
    #         self.teardown_experiment()
        