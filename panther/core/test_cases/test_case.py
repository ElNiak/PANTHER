from datetime import datetime
import logging
from pathlib import Path
import subprocess
import time
from typing import Any, Dict, List, Set

import requests
from omegaconf import DictConfig

from core.test_cases.test_interface import ITestCase
from core.observer.event_manager import EventManager
from core.observer.event import Event
from core.observer.logger_observer import LoggerObserver
from core.results.result_collector import ResultCollector
from plugins.implementations.service_manager_interface import IServiceManager
from plugins.plugin_manager import PluginManager
from plugins.environments.environment_interface import IEnvironmentPlugin


class TestCase(ITestCase):
    def __init__(self, test_config: DictConfig, logger: logging.Logger, result_collector: ResultCollector, 
                 environment_types: Dict, event_manager: EventManager, plugin_manager: PluginManager,
                 test_experiment_dir: Path):
        super().__init__(test_config, logger)
        self.result_collector = result_collector
        self.service_managers: List[IServiceManager] = []
        self.environment_plugin_manager : List[IEnvironmentPlugin] = []
        self.event_manager = event_manager
        self.environments = environment_types
        self.plugin_manager = plugin_manager
        self.test_experiment_dir = test_experiment_dir
        self.services = test_config.get("services", {})
        self.deployment_commands = []
    
    def __str__(self):
        return (f"TestCase(name={self.test_config.get('name', 'Unnamed Test')}, "
            f"description={self.test_config.get('description', '')}, "
            f"services={self.services}, "
            f"environments={self.environments}, "
            f"test_experiment_dir={self.test_experiment_dir})")

    def run(self):
        """Runs the test case based on the provided configuration."""
        try:
            self.logger.info(f"Starting Test: {self.test_config.get('name', 'Unnamed Test')}")
            self.logger.info(f"Description:   {self.test_config.get('description', '')}")
            self.setup_environments()
            self.deploy_services()
            self.execute_steps()
            self.validate_assertions()
            self.logger.info(f"Test '{self.test_config.name}' completed successfully.")
            # self.result_collector["storage"].save_test_result(self.test_config.name, {
            #     "status": "completed",
            #     "test_config": self.test_config,
            #     "details": "Test completed successfully."
            # })
            self.event_manager.notify(Event("test_completed", {"test": self.test_config.get("name", "Unnamed Test")}))
        except Exception as e:
            self.logger.error(f"Test '{self.test_config.get('name', 'Unnamed Test')}' failed: {e}")
            # self.result_collector["storage"].save_test_result(self.test_config.name, {
            #     "status": "failed",
            #     "test_config": self.test_config,
            #     "error": str(e)
            # })
            raise
        finally:
            self.teardown_environment()

    def setup_testers(self):
        """
        
        """
        def get_required_testers(services: Dict[str, Dict[str, Any]]) -> Set[str]:
            """_summary_

            Args:
                services (Dict[str, Dict[str, Any]]): _description_

            Returns:
                Set[str]: _description_
            """
            required_implementations = set()
            for service_name, service_details in services.items():
                implementation = service_details.get("implementation")
                if implementation and service_details.get("type") == "tester":
                    required_implementations.add(implementation)
                else:
                    self.logger.warning(f"Service '{service_name}' does not specify an implementation.")

            if not required_implementations:
                self.logger.error("No tester specified for services. Aborting test. ?")
                # Skip to the next test
            return required_implementations
        
        testers = get_required_testers(self.services)
        if len(testers) == 0:
            self.logger.warning("No testers specified in the test configuration.")
            return
        testers_plugin_path = Path(f"plugins/testers")
        if testers_plugin_path.exists() and testers_plugin_path.is_dir():
            self.logger.debug(f"Found tester plugin at '{testers_plugin_path}'")
            # Discover and load implementations under this protocol using PluginFactory
            available_testers = self.plugin_manager.plugins_loaders.get_testers()
            for impl in testers:
                if impl in available_testers:
                    implementation_dir = testers_plugin_path / impl
                    protocol_templates_dir = testers_plugin_path / impl /"templates"
                    # Create service manager using PluginFactory
                    service_manager = self.plugin_manager.create_service_manager(
                        protocol="quic", # TODO 
                        implementation=impl,
                        implementation_dir=implementation_dir,
                        protocol_templates_dir=protocol_templates_dir
                    )
                    self.service_managers.append(service_manager)
                    self.logger.debug(f"Added service manager for tester '{impl}' under protocol '{'quic'}'")
                else:
                    self.logger.warning(f"Tester '{impl}' for protocol '{'quic'}' not found. Skipping.")
        else:
            self.logger.warning(f"Tester plugin not found at '{testers_plugin_path}'. Skipping.")
        
    def setup_services(self):
        """
        Initializes protocol managers based on the specified protocols and required implementations.

        :param protocols: List of protocol names.
        :param implementations: Set of implementation names to initialize.
        """
        def get_required_implementations(services: Dict[str, Dict[str, Any]]) -> Set[str]:
            """
            Extracts the required implementations from a dictionary of services.

            :param services: Dictionary of services with their configurations.
            :return: Set of implementation names.
            """
            required_implementations = set()
            for service_name, service_details in services.items():
                implementation = service_details.get("implementation")
                if implementation and service_details.get("type") != "tester":
                    required_implementations.add(implementation)
                else:
                    self.logger.warning(f"Service '{service_name}' does not specify an implementation.")

            if not required_implementations:
                self.logger.error("No implementations specified for services. Aborting test. ?")
                raise Exception # Skip to the next test
            return required_implementations
        
        # TODO
        protocols       = self.test_config.get("protocol", [])
        implementations = get_required_implementations(self.services)
        
        for proto in protocols:
            protocol_plugin_path = Path(f"plugins/implementations/{proto}")
            if protocol_plugin_path.exists() and protocol_plugin_path.is_dir():
                self.logger.debug(f"Found protocol plugin at '{protocol_plugin_path}'")
                # Discover and load implementations under this protocol using PluginFactory
                available_implementations = self.plugin_manager.plugins_loaders.get_implementations_for_protocol(proto)
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
                        exit()
            else:
                self.logger.warning(f"Protocol plugin '{proto}' not found at '{protocol_plugin_path}'. Skipping.")
                exit()

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


    def setup_environment(self):
        """Setup the test environment using the plugin."""
        for type, env in self.environments.items():
            if env:
                self.logger.debug(f"Creating environment manager for environment '{env}'")
                environment_manager = self.plugin_manager.create_environment_manager(environment=env, environment_dir=self.plugin_manager.plugins_loaders.plugins_base_dir / "environments" /  f"{type}_environment", 
                                                                                     output_dir=self.test_experiment_dir)
                self.environment_plugin_manager.append(environment_manager)
                self.logger.debug(f"Added environment manager for environment '{env}'")

    def teardown_environment(self):
        """Tears down the test environment using the plugin."""
        self.logger.info("Tearing down all environments")
        for env_manager in self.environment_plugin_manager:
            if hasattr(env_manager, "teardown_environment"):
                try:
                    env_manager.teardown_environment()
                    self.logger.info(f"Environment '{env_manager.__class__.__name__}' torn down successfully.")
                    self.event_manager.notify(Event("environment_teardown", {"environment": env_manager}))
                except Exception as e:
                    self.logger.error(f"Failed to teardown environment '{env_manager.__class__.__name__}': {e}")
            else:
                self.logger.debug(f"No teardown_environment method for '{env_manager.__class__.__name__}'. Skipping.")

    def deploy_services(self):
        """
        Delegates service deployment to each environment manager.
        """
        self.logger.info("Deploying services through environment managers")
        for env_manager in self.environment_plugin_manager:
            try:
                env_manager.deploy_services()
                self.logger.info(f"Services deployed via '{env_manager.__class__.__name__}'")
                self.event_manager.notify(Event("services_deployed", {"environment": env_manager}))
            except Exception as e:
                self.logger.error(f"Failed to deploy services via '{env_manager.__class__.__name__}': {e}")
                
    def execute_steps(self):
        """
        Executes the defined steps of a test.

        :param steps: Dictionary of steps to execute.
        """
        steps = self.test_config.get("steps", {})
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

    def validate_assertions(self):
        """Validates assertions defined in the test configuration."""
        assertions = self.test_config.get("assertions", [])
        for assertion in assertions:
            try:
                if assertion["type"] == "service_responsive":
                    service = assertion["service"]
                    endpoint = assertion["endpoint"]
                    expected_status = assertion.get("expected_status", 200)
                    self.check_service_responsiveness(service, endpoint, expected_status)
            except Exception as e:
                self.logger.error(f"Assertion failed: {e}")
                raise
            
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
        for cuurent_service_name, service_details in self.services.items():
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
    
 
    def setup_environments(self):
        """
        Sets up all environments managed by the environment managers, providing service configurations and deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_commands: Dictionary of deployment commands generated by service managers.
        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        self.logger.info("Setting up all environments")
        self.setup_environment()
        self.setup_services()
        self.setup_testers()
        self.generate_deployment_commands(self.test_config.get("network_environment", "docker_compose"))
        for env_manager in self.environment_plugin_manager:
            try:
                env_manager.setup_environment(self.services, 
                                              self.deployment_commands, 
                                              self.test_config.get('paths', {}), 
                                              datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
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
        for service_name, service_details in self.services.items():
            self.logger.debug(f"Generating deployment commands for '{service_name}'")
            # Find the appropriate service manager based on implementation
            implementation = service_details.get("implementation")
            self.logger.debug(f"Service '{service_name}' uses implementation '{implementation}' with details: {service_details} - checking service managers {self.service_managers}")
            manager = next((m for m in self.service_managers if m.get_implementation_name() == implementation), None)
            if not manager:
                self.logger.error(f"No service manager found for implementation '{implementation}'")
                exit(1)
            try:
                # Ensure 'name' key exists
                if 'name' not in service_details:
                    service_details['name'] = service_name
                info_commands = manager.generate_deployment_commands(service_details,environment)
                deployment_commands.update(info_commands)
            except Exception as e:
                self.logger.error(f"Failed to generate deployment command for service '{service_name}': {e}")
        self.logger.debug(f"Collected deployment commands: {deployment_commands}")
        self.deployment_commands = deployment_commands
