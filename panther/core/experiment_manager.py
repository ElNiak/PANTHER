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


class ExperimentManager:
    def __init__(
        self,
        global_config: DictConfig,
        experiment_config: DictConfig,
        experiment_name: str = None,
        plugin_dir: str = "plugins",
    ):
        self.logger = logging.getLogger("ExperimentManager")

        self.global_config     = global_config
        self.experiment_config = experiment_config
        self.experiment_name = (
            f"{experiment_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}" if experiment_name
            else f"experiment_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        )
        
        # TODO sometime logs dir is not used directly in inv -> assume it is used in the future
        self.experiment_dir = Path(global_config.paths.output_dir) / self.experiment_name
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
        log_level = getattr(logging, self.global_config.logging.level.upper(), logging.INFO)
        log_format = self.global_config.logging.format
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

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
        # for manager in self.service_managers:
        #     if hasattr(manager, "build_image"):
        #         try:
        #             manager.build_image()
        #             self.logger.info(f"Built Docker image for '{manager.__class__.__name__}'")
        #             self.event_manager.notify(Event("docker_image_built", {"manager": manager}))
        #         except Exception as e:
        #             self.logger.error(f"Failed to build Docker image for '{manager.__class__.__name__}': {e}")
        #     else:
        #         self.logger.debug(f"No build_image method for '{manager.__class__.__name__}'. Skipping.")

    def setup_environments(self, services: Dict[str, Dict[str, Any]], deployment_commands: Dict[str, str]):
        """
        Sets up all environments managed by the environment managers, providing service configurations and deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_commands: Dictionary of deployment commands generated by service managers.
        """
        self.logger.info("Setting up all environments")
        for env_manager in self.environment_managers:
            try:
                env_manager.setup_environment(services, deployment_commands)
                self.logger.info(f"Environment '{env_manager.__class__.__name__}' setup successfully.")
                self.event_manager.notify(Event("environment_setup", {"environment": env_manager}))
            except Exception as e:
                self.logger.error(f"Failed to setup environment '{env_manager.__class__.__name__}': {e}")

    def generate_deployment_commands(self) -> Dict[str, str]:
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
                command_dict = manager.generate_deployment_commands(service_details)
                deployment_commands.update(command_dict)
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

        service_manager = next((sm for sm in self.service_managers if sm.__class__.__name__ == f"{service_name.capitalize()}ServiceManager"), None)
        if not service_manager:
            self.logger.error(f"Service manager for '{service_name}' not found.")
            return

        # Assuming service manager provides the base URL or IP
        base_url = service_manager.get_base_url()  # Implement this method in IServiceManager and concrete classes
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
            if step_name == "wait":
                duration = step_details.get("duration", 0)
                self.logger.info(f"Executing step 'wait' for {duration} seconds.")
                import time
                time.sleep(duration)
                self.logger.info(f"Completed step 'wait' for {duration} seconds.")
                self.event_manager.notify(Event("step_completed", {"step": "wait", "duration": duration}))
            # Add more step handlers as needed


    def run_tests(self):
        """
        Orchestrates the entire experiment workflow.
        """
        try:
            tests = self.experiment_config.get("tests", [])

            for test in tests:
                self.logger.info(f"Starting Test: {test.get('name', 'Unnamed Test')}")
                self.logger.info(f"Description: {test.get('description', '')}")

                protocol = test.get("protocol")
                environment = test.get("network_environment")  # Ensure consistent naming
                services = test.get("services", {})
                self.current_test_services = services
                steps = test.get("steps", {})
                assertions = test.get("assertions", [])

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

                deployment_commands = self.generate_deployment_commands()

                # Step 5: Setup environments with services
                self.setup_environments(services,deployment_commands)

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
            

    # def run_experiment(self):
    #     for test in self.experiment.tests:
    #         self.log.info(f"Running Test: {test.name}")
    #         protocol_name = test.protocol
    #         environment_name = test.environment

    #         protocol_plugin = self.protocol_plugins.get(protocol_name)
    #         if not protocol_plugin:
    #             self.log.error(f"Protocol plugin '{protocol_name}' not found.")
    #             continue

    #         self.log.info(f"Setting up Environment: {environment_name}")
    #         try:
    #             # Extract service configurations
    #             services_config = {}
    #             for service_name, service_details in test.services.items():
    #                 implementation_name = service_details.get("implementation")
    #                 version = service_details.get("version")
    #                 service_manager = protocol_plugin.get_service_manager(
    #                     implementation_name
    #                 )
    #                 if not service_manager:
    #                     self.log.error(
    #                         f"Service manager for implementation '{implementation_name}' not found."
    #                     )
    #                     continue
    #                 image_name = f"{implementation_name}_{version}_panther:latest"  # Adjust if using different tagging
    #                 ports = service_details.get("ports", [])
    #                 depends_on = service_details.get("depends_on", [])
    #                 environment_vars = service_details.get("environment", {})
    #                 services_config[service_name] = {
    #                     "image": image_name,
    #                     "ports": ports,
    #                     "depends_on": depends_on,
    #                     "environment": environment_vars,
    #                 }
    #                 self.log.debug(
    #                     f"Service '{service_name}' configured with image '{image_name}'"
    #                 )

    #             self.env_manager.setup_environment(environment_name, services_config)
    #         except Exception as e:
    #             self.log.error(
    #                 f"Failed to set up environment '{environment_name}': {e}"
    #             )
    #             continue

    #         self.log.info("Services are up and running.")

    #         # Execute Test Steps
    #         self.log.info("Executing Test Steps")
    #         wait_step = test.steps.get("wait", {})
    #         wait_duration = wait_step.get("duration", 10)
    #         self.log.info(
    #             f"Waiting for {wait_duration} seconds to allow communication..."
    #         )
    #         time.sleep(wait_duration)

    #         # Perform Assertions
    #         self.log.info("Performing Assertions")
    #         assertions = test.assertions if "assertions" in test else []
    #         test_result = {"test_name": test.name, "success": True, "assertions": []}
    #         for assertion in assertions:
    #             assertion_outcome = self.perform_assertion(assertion)
    #             test_result["assertions"].append(assertion_outcome)
    #             if not assertion_outcome["passed"]:
    #                 test_result["success"] = False

    #         self.results.append(test_result)
    #         self.log.info(
    #             f"Test '{test.name}' Completed with {'Success' if test_result['success'] else 'Failure'}\n"
    #         )

    #         # Stop Services
    #         self.log.info("Stopping Services")
    #         try:
    #             self.env_manager.teardown_environment(environment_name)
    #             self.log.info("Services stopped successfully.")
    #         except Exception as e:
    #             self.log.error(f"Failed to stop services: {e}")

    #     # After all tests, generate the report
    #     self.generate_report()

    # def perform_assertion(self, assertion):
    #     assertion_type = assertion.type
    #     passed = False
    #     details = ""
    #     if assertion_type == "service_responsive":
    #         service = assertion.service
    #         endpoint = assertion.endpoint  # Format: "port/path"
    #         expected_status = assertion.expected_status
    #         try:
    #             port, path = endpoint.split("/", 1)
    #             url = f"http://localhost:{port}/{path}"
    #             self.log.info(f"Performing health check on {service} at {url}")
    #             response = requests.get(url, timeout=5)
    #             if response.status_code == expected_status:
    #                 passed = True
    #                 details = f"Service '{service}' responded with expected status {expected_status}."
    #                 self.log.info(details)
    #             else:
    #                 details = f"Service '{service}' responded with status {response.status_code}, expected {expected_status}."
    #                 self.log.error(details)
    #         except Exception as e:
    #             details = f"Service '{service}' health check failed: {e}"
    #             self.log.error(details)
    #     elif assertion_type == "performance_metrics":
    #         # Implement performance metrics validation
    #         service = assertion.service
    #         metric = assertion.metric
    #         expected_min = assertion.expected_min
    #         # Placeholder implementation
    #         details = f"Performance metrics for '{service}' not implemented yet."
    #         self.log.warning(details)
    #     else:
    #         details = f"Unknown assertion type: {assertion_type}"
    #         self.log.warning(details)

    #     return {"type": assertion_type, "passed": passed, "details": details}

    # def generate_report(self):
    #     """
    #     Generates a simple textual report summarizing test results.
    #     """
    #     report_path = os.path.join(
    #         self.global_config.paths.output_dir, "experiment_report.txt"
    #     )
    #     os.makedirs(os.path.dirname(report_path), exist_ok=True)
    #     with open(report_path, "w") as report_file:
    #         for result in self.results:
    #             report_file.write(f"Test: {result['test_name']}\n")
    #             report_file.write(f"Success: {'Yes' if result['success'] else 'No'}\n")
    #             for assertion in result["assertions"]:
    #                 status = "PASSED" if assertion["passed"] else "FAILED"
    #                 report_file.write(f"  Assertion: {assertion['type']} - {status}\n")
    #                 report_file.write(f"    Details: {assertion['details']}\n")
    #             report_file.write("\n")
    #     self.log.info(f"Experiment report generated at {report_path}")
