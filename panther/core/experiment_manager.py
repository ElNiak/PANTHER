# PANTHER-SCP/panther/core/experiment_manager.py

from datetime import datetime
import logging
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Set
from omegaconf import DictConfig
import requests
import yaml

from utils.plugin_loader import PluginLoader
from core.interfaces.protocol_interface import IProtocolPlugin
from core.interfaces.environments.environment_interface import IEnvironmentPlugin
from core.interfaces.service_manager_interface import IServiceManager
from core.observer.logger_observer import LoggerObserver
from core.factories.environment_manager import EnvironmentManager
from core.factories.plugin_manager import PluginManager
from core.observer.event_manager import EventManager
from core.observer.event import Event
# from core.test import Test


class ExperimentManager:
    def __init__(
        self,
        experiment_config: DictConfig,
        experiment_name: str = None,
        plugin_dir: str = "plugins",
    ):
        self.logger = logging.getLogger("ExperimentManager")

        self.experiment_config = experiment_config
        self.experiment_name = (
            f"{experiment_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}" if experiment_name
            else f"experiment_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        )
        
        # TODO sometime logs dir is not used directly in inv -> assume it is used in the future
        # TODO split experiment parameters and test parameters + move some parameters to the test level
        self.experiment_dir = Path(experiment_config.paths.output_dir) / self.experiment_name
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir = self.experiment_dir / "logs"
        self.docker_compose_logs_dir = self.experiment_dir / "docker_compose_logs"
        self.container_logs_dir = self.experiment_dir / "container_logs"
        self.other_artifacts_dir = self.experiment_dir / "other_artifacts"

        # Manage configuration
        self.service_managers: List[IServiceManager] = []
        self.environment_managers: List[IEnvironmentPlugin] = []
        self.event_manager = EventManager()

        # Load experiment configuration + Plugins
        self.plugin_dir = Path(plugin_dir)
        self.plugin_loader  = PluginLoader(plugin_dir)
        self.plugin_manager = PluginManager(self.plugin_loader)
        
        self.current_test_services = {}

        self.load_logging()
        self.register_default_observers()
        
    def load_logging(self):
        """
        Configures logging to output to both console and a log file.
        """
        log_level = getattr(logging, self.experiment_config.logging.level.upper(), logging.INFO)
        log_format = self.experiment_config.logging.format

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

    def register_default_observers(self):
        """
        Registers default observers to listen to events.
        """
        # Register the LoggingObserver
        logging_observer = LoggerObserver()
        self.event_manager.register_observer(logging_observer)
        self.logger.debug("Registered LoggingObserver as a default observer")
    
    def get_implementations_for_protocol(self, protocol_plugin_path: Path) -> List[str]:
        """
        Retrieves a list of implementations under a given protocol plugin.

        :param protocol_plugin_path: Path to the protocol plugin directory.
        :return: List of implementation names.
        """
        implementations = []
        for item in protocol_plugin_path.iterdir():
            if item.is_dir() and not item.name.startswith('__') and item.name != "templates":
                implementations.append(item.name)
        self.logger.debug(f"Found implementations for protocol '{protocol_plugin_path.name}': {implementations}")
        return implementations
    
    def initialize_protocol_managers(self, protocols: List[str], implementations: Set[str]):
        """
        Initializes protocol managers based on the specified protocols and required implementations.

        :param protocols: List of protocol names.
        :param implementations: Set of implementation names to initialize.
        """
        for proto in protocols:
            protocol_plugin_path = Path(f"plugins/implementations/{proto}")
            if protocol_plugin_path.exists() and protocol_plugin_path.is_dir():
                self.logger.debug(f"Found protocol plugin at '{protocol_plugin_path}'")
                # Discover and load implementations under this protocol using PluginFactory
                available_implementations = self.plugin_loader.get_implementations_for_protocol(proto)
                for impl in implementations:
                    if impl in available_implementations:
                        implementation_dir = protocol_plugin_path / impl
                        protocol_templates_dir = protocol_plugin_path / impl /"templates"
                        # Create service manager using PluginFactory
                        service_manager = self.plugin_manager.create_service_manager(
                            protocol=proto,
                            implementation=impl,
                            implementation_dir=implementation_dir,
                            protocol_templates_dir=protocol_templates_dir
                        )
                        self.service_managers.append(service_manager)
                        self.logger.debug(f"Added service manager for implementation '{impl}' under protocol '{proto}'")
                    else:
                        self.logger.warning(f"Implementation '{impl}' for protocol '{proto}' not found. Skipping.")
            else:
                self.logger.warning(f"Protocol plugin '{proto}' not found at '{protocol_plugin_path}'. Skipping.")

    def initialize_environment_managers(self, environments: List[str], type: str = "network"):
        """
        Initializes environment managers based on the specified environments.

        :param environments: List of environment names.
        """
        for env in environments:
            if env:
                self.logger.debug(f"Creating environment manager for environment '{env}'")
                environment_manager = self.plugin_manager.create_environment_manager(environment=env, environment_dir=self.plugin_dir / "environments" /  f"{type}_environment", output_dir=self.experiment_dir)
                self.environment_managers.append(environment_manager)
                self.logger.debug(f"Added environment manager for environment '{env}'")

    def build_docker_images(self):
        """
        Builds Docker images for all service managers.
        """
        self.logger.info("Building Docker images for implementations")
        self.plugin_loader.build_all_docker_images()
        
    def setup_environments(self, services: Dict[str, Dict[str, Any]], deployment_commands: Dict[str, str], paths: Dict[str, str], timestamp: str):
        """
        Sets up all environments managed by the environment managers, providing service configurations and deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_commands: Dictionary of deployment commands generated by service managers.
        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        self.logger.info("Setting up all environments")
        for env_manager in self.environment_managers:
            try:
                env_manager.setup_environment(services, deployment_commands, paths, timestamp)
                self.logger.info(f"Environment '{env_manager.__class__.__name__}' setup successfully.")
                self.event_manager.notify(Event("environment_setup", {"environment": env_manager}))
            except Exception as e:
                self.logger.error(f"Failed to setup environment '{env_manager.__class__.__name__}': {e}")


    def generate_deployment_commands(self, environment:str) -> Dict[str, str]:
        """
        Collects deployment commands from all service managers based on the services defined in the tests.

        :return: A dictionary mapping service names to their respective command strings.
        """
        deployment_commands = {}
        for service_name, service_details in self.current_test_services.items():
            self.logger.debug(f"Generating deployment commands for '{service_name}'")
            # Find the appropriate service manager based on implementation
            implementation = service_details.get("implementation")
            manager = next((m for m in self.service_managers if m.get_implementation_name() == implementation), None)
            if not manager:
                self.logger.error(f"No service manager found for implementation '{implementation}'")
                continue
            try:
                # Ensure 'name' key exists
                if 'name' not in service_details:
                    service_details['name'] = service_name
                info_commands = manager.generate_deployment_commands(service_details,environment)
                deployment_commands.update(info_commands)
            except Exception as e:
                self.logger.error(f"Failed to generate deployment command for service '{service_name}': {e}")
        self.logger.debug(f"Collected deployment commands: {deployment_commands}")
        return deployment_commands


    def deploy_services(self):
        """
        Delegates service deployment to each environment manager.
        """
        self.logger.info("Deploying services through environment managers")
        for env_manager in self.environment_managers:
            try:
                env_manager.deploy_services()
                self.logger.info(f"Services deployed via '{env_manager.__class__.__name__}'")
                self.event_manager.notify(Event("services_deployed", {"environment": env_manager}))
            except Exception as e:
                self.logger.error(f"Failed to deploy services via '{env_manager.__class__.__name__}': {e}")

    def perform_assertions(self, assertions: List[Dict[str, Any]]):
        """
        Performs assertions as defined in the experiment configuration.

        :param assertions: List of assertion dictionaries.
        """
        self.logger.info("Performing assertions")
        for assertion in assertions:
            assertion_type = assertion.get("type")
            if assertion_type == "service_responsive":
                service_name = assertion.get("service")
                endpoint = assertion.get("endpoint")
                expected_status = assertion.get("expected_status", 200)
                self.check_service_responsiveness(service_name, endpoint, expected_status)
            else:
                self.logger.warning(f"Unknown assertion type '{assertion_type}'. Skipping.")

    def check_service_responsiveness(self, service_name: str, endpoint: str, expected_status: int):
        """
        Checks if a service's endpoint is responsive and returns the expected status code.

        :param service_name: Name of the service to check.
        :param endpoint: The endpoint to send the request to.
        :param expected_status: The expected HTTP status code.
        """
        import requests
        from urllib.parse import urljoin
        self.logger.debug(f"Checking responsiveness of '{service_name}' at '{endpoint}'")
        for cuurent_service_name, service_details in self.current_test_services.items():
            if cuurent_service_name == service_name:
                # Find the appropriate service manager based on implementation
                implementation = service_details.get("implementation")
                service_manager = next((m for m in self.service_managers if m.get_implementation_name() == implementation), None)
                break

        if not service_manager:
            self.logger.error(f"Service manager for '{service_name}' not found.")
            return

        # Assuming service manager provides the base URL or IP
        base_url = service_manager.get_base_url(service_name)  # Implement this method in IServiceManager and concrete classes
        url = urljoin(base_url, endpoint)
        self.logger.debug(f"Checking responsiveness of '{service_name}' at '{url}'")

        try:
            response = requests.get(url)
            if response.status_code == expected_status:
                self.logger.info(f"Assertion Passed: '{service_name}' responded with status code {expected_status}.")
            else:
                self.logger.error(f"Assertion Failed: '{service_name}' responded with status code {response.status_code}, expected {expected_status}.")
        except Exception as e:
            self.logger.error(f"Assertion Failed: Could not reach '{service_name}' at '{url}': {e}")

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
        for env_manager in self.environment_managers:
            if hasattr(env_manager, "teardown_environment"):
                try:
                    env_manager.teardown_environment()
                    self.logger.info(f"Environment '{env_manager.__class__.__name__}' torn down successfully.")
                    self.event_manager.notify(Event("environment_teardown", {"environment": env_manager}))
                except Exception as e:
                    self.logger.error(f"Failed to teardown environment '{env_manager.__class__.__name__}': {e}")
            else:
                self.logger.debug(f"No teardown_environment method for '{env_manager.__class__.__name__}'. Skipping.")
    
    def execute_steps(self, steps: Dict[str, Any]):
        """
        Executes the defined steps of a test.

        :param steps: Dictionary of steps to execute.
        """
        for step_name, step_details in steps.items():
            if step_name == "record_pcap":
                pass
            if step_name == "wait":
                duration = step_details.get("duration", 0)
                self.logger.info(f"Executing step 'wait' for {duration} seconds.")
                import time
                time.sleep(duration)
                self.logger.info(f"Completed step 'wait' for {duration} seconds.")
                self.event_manager.notify(Event("step_completed", {"step": "wait", "duration": duration}))
            # Add more step handlers as needed

    def load_tests(self):
        """
        Loads tests from the experiment configuration and initializes Test instances.
        """
        tests_config = self.experiment_config.get('tests', [])
        self.tests = []
        for test_config in tests_config:
            test = Test(test_config, self)
            self.tests.append(test)

    def run_tests(self):
        """
        Orchestrates the entire experiment workflow.
        """
        try:
            tests = self.experiment_config.get("tests", [])

            for test in tests:
                # TODO create subtest folder for each test
                self.logger.info(f"Starting Test: {test.get('name', 'Unnamed Test')}")
                self.logger.info(f"Description:   {test.get('description', '')}")

                protocol    = test.get("protocol")
                environment = test.get("network_environment")  # Ensure consistent naming
                services    = test.get("services", {})
                self.current_test_services = services
                steps      = test.get("steps", {})
                assertions = test.get("assertions", [])
                
                # Check if new certificates should be generated
                if self.experiment_config.get('generate_new_certificates', False):
                    subprocess.run(["bash", 'generate_certificates.sh'])

                # Step 1: Extract required implementations from services
                required_implementations = set()
                for service_name, service_details in services.items():
                    implementation = service_details.get("implementation")
                    if implementation:
                        required_implementations.add(implementation)
                    else:
                        self.logger.warning(f"Service '{service_name}' does not specify an implementation.")

                if not required_implementations:
                    self.logger.error("No implementations specified for services. Aborting test.")
                    continue  # Skip to the next test

                self.logger.debug(f"Required implementations for this test: {required_implementations}")

                # Step 2: Initialize only the required protocol managers
                self.initialize_protocol_managers([protocol], required_implementations)

                # Step 3: Initialize environment managers
                self.initialize_environment_managers([environment])

                # Step 4: Build Docker images if necessary
                self.build_docker_images()

                deployment_commands = self.generate_deployment_commands(environment)

                # Step 5: Setup environments with services
                # Generate timestamp and paths
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                paths = self.experiment_config.get('paths', {})
            
                self.setup_environments(services,deployment_commands, paths, timestamp)

                # Step 6: Deploy services
                
                self.deploy_services()

                # Step 7: Execute test steps
                self.execute_steps(steps)

                # Step 8: Perform assertions
                self.perform_assertions(assertions)

                # Step 9: Teardown for the test
                self.teardown_experiment()

                self.logger.info(f"Completed Test: {test.get('name', 'Unnamed Test')}")
                self.event_manager.notify(Event("test_completed", {"test": test.get("name", "Unnamed Test")}))
        except Exception as e:
            self.logger.error(f"Experiment encountered an error: {e}")
            self.teardown_experiment()
        