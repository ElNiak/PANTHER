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
from core.observer.experiment_observer import ExperimentObserver
from core.results.result_collector import ResultCollector
from plugins.services.services_interface import IServiceManager
from plugins.plugin_manager import PluginManager
from plugins.environments.environment_interface import IEnvironmentPlugin


class TestCase(ITestCase):
    def __init__(self, test_config: DictConfig, logger: logging.Logger, result_collector: ResultCollector, 
                 environment_types: Dict[str,Any],  plugin_manager: PluginManager,
                 test_experiment_dir: Path, paths: Dict[str, Any]):
        
        super().__init__(test_config, logger)
        self.result_collector = result_collector
        self.service_managers: List[IServiceManager] = []
        self.environment_plugin_manager : List[IEnvironmentPlugin] = []
        self.event_manager = EventManager()
        self.environments = environment_types
        self.exectution_environment = []
        self.plugin_manager = plugin_manager
        self.test_experiment_dir = test_experiment_dir
        self.services = test_config.services
        self.deployment_commands = []
        self.paths = paths
        
    def __str__(self):
        return (f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"environments={self.environments}, "
            f"test_experiment_dir={self.test_experiment_dir})")
        
    def __repr__(self):
        return (f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"environments={self.environments}, "
            f"test_experiment_dir={self.test_experiment_dir})")

    def run(self):
        """Runs the test case based on the provided configuration."""
        try:
            self.logger.info(f"Starting Test: {self.test_config.name}")
            self.logger.info(f"Description:   {self.test_config.description}")
            self.register_default_observers()
            self.setup_test()
            self.deploy_services()
            self.execute_steps()
            self.validate_assertions()
            self.logger.info(f"Test '{self.test_config.name}' completed successfully.")
            # self.result_collector["storage"].save_test_result(self.test_config.name, {
            #     "status": "completed",
            #     "test_config": self.test_config,
            #     "details": "Test completed successfully."
            # })
            self.event_manager.notify(Event("test_completed", {"test": self.test_config.name}))
        except Exception as e:
            self.logger.error(f"Test '{self.test_config.name}' failed: {e}")
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
            required_implementations = []
            # TODO add check unicity of the testers [i.e set() like -> unhashable type: 'dict']
            for service_name, service_details in services.items():
                implementation = service_details.implementation
                self.logger.debug(f"Service '{service_name}' uses implementation '{implementation}' with details: {service_details}")
                if implementation and implementation.type == "testers":
                    if implementation not in [impl["implem"] for impl in required_implementations]:
                        print("fuck")
                        required_implementations.append({"implem":  implementation,
                                                         "protocol": service_details.protocol})
                else:
                    self.logger.warning(f"Service '{service_name}' does not specify an implementation.")

            if not required_implementations:
                self.logger.error("No testers specified for services. Aborting test. ?")
                # Skip to the next test
            return required_implementations
        
        testers = get_required_testers(self.services)
        if len(testers) == 0:
            self.logger.warning("No testers specified in the test configuration.")
            return
        self.logger.debug(f"Testers: {testers}")
        testers_plugin_path = Path(f"plugins/services/testers")
        if testers_plugin_path.exists() and testers_plugin_path.is_dir():
            self.logger.debug(f"Found testers plugin at '{testers_plugin_path}'")
            # Discover and load implementations under this protocol using PluginFactory
            available_testers = self.plugin_manager.plugins_loader.get_testers()
            for impl in testers:
                if impl["implem"].name in available_testers:
                    implementation_dir = testers_plugin_path / impl["implem"].name
                    protocol_templates_dir = testers_plugin_path / impl["implem"].name /"templates"
                    # Create service manager using PluginFactory
                    print(impl["protocol"])
                    print(impl["protocol"])
                    service_manager = self.plugin_manager.create_service_manager(
                        protocol=impl["protocol"].name, 
                        implementation=impl["implem"].name,
                        implementation_dir=implementation_dir
                    )
                    self.service_managers.append(service_manager)
                    self.logger.debug(f"Added service manager for testers '{impl['implem']}' under protocol '{impl['protocol'].name}'")
                else:
                    self.logger.warning(f"Tester '{impl['implem']}' for protocol '{impl['protocol'].name}' not found. Skipping.")
        else:
            self.logger.warning(f"Tester plugin not found at '{testers_plugin_path}'. Skipping.")
        
    def setup_implementations(self):
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
            required_implementations = []
            # TODO add check unicity of the testers [i.e set() like -> unhashable type: 'dict']
            for service_name, service_details in services.items():
                implementation = service_details.implementation
                if implementation and implementation.type != "testers":
                    if implementation not in [impl["implem"] for impl in required_implementations]:
                        print("fuck")
                        required_implementations.append({"implem":  implementation,
                                                         "protocol": service_details.protocol})
                else:
                    self.logger.warning(f"Service '{service_name}' does not specify an implementation.")

            if not required_implementations:
                self.logger.error("No testers specified for services. Aborting test. ?")
                # Skip to the next test
            return required_implementations
        
        # TODO
        protocol_path = Path("plugins/services/iut")
        protocols = [p.name for p in protocol_path.iterdir() if p.is_dir() and not p.name.startswith("__")]
        implementations = get_required_implementations(self.services)
        
        for proto in protocols:
            protocol_plugin_path = Path(f"plugins/services/iut/{proto}")
            if protocol_plugin_path.exists() and protocol_plugin_path.is_dir():
                self.logger.debug(f"Found protocol plugin at '{protocol_plugin_path}'")
                # Discover and load implementations under this protocol using PluginFactory
                available_implementations = self.plugin_manager.plugins_loader.get_implementations_for_protocol(proto)
                for impl in implementations:
                    self.logger.debug(f"Checking implementation '{impl}' for protocol '{proto}'")
                    if impl["implem"].name in available_implementations:
                        implementation_dir = protocol_plugin_path / impl["implem"].name
                        protocol_templates_dir = protocol_plugin_path / impl["implem"].name /"templates"
                        # Create service manager using PluginFactory
                        service_manager = self.plugin_manager.create_service_manager(
                            protocol=proto,
                            implementation=impl["implem"].name,
                            implementation_dir=implementation_dir,
                        )
                        self.service_managers.append(service_manager)
                        self.logger.debug(f"Added service manager for implementation '{impl}' under protocol '{proto}'")
                    else:
                        self.logger.warning(f"Implementation '{impl}' for protocol '{proto}' not found. Skipping.")
                        # exit()
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
        self.logger.debug(f"Setting up environments '{self.environments}'")
        for type, env in self.environments.items():
            self.logger.debug(f"Setting up environment type '{type}' with environments '{env}'")
            for environment in self.environments[type]:
                self.logger.debug(f"Setting up environment '{environment}'")
                subtype = environment.type
                settings = environment
                environment_dir = self.plugin_manager.plugins_loader.plugins_base_dir / "environments" /  f"{type}_environment"
                self.logger.debug(f"Creating environment manager for environment '{type}' with {subtype} and settings {settings}")
                environment_manager = self.plugin_manager.create_environment_manager(environment=subtype, 
                                                                                    environment_settings=settings,
                                                                                    environment_dir=environment_dir, 
                                                                                    output_dir=self.test_experiment_dir,
                                                                                    event_manager=self.event_manager)
                self.environment_plugin_manager.append(environment_manager)
                self.logger.debug(f"Added environment manager for environment '{type}'")
            
        for env_manager in self.environment_plugin_manager:
            try:
                if not env_manager.is_network_environment():
                    self.exectution_environment.append(env_manager)
            except Exception as e:
                self.logger.error(f"Failed to setup environment '{env_manager.__class__.__name__}': {e}")
                exit()
        
        for env_manager in self.environment_plugin_manager:
            try:
                if env_manager.is_network_environment():
                    env_manager.setup_environment(self.services, 
                                                 self.deployment_commands, 
                                                self.test_config, 
                                                datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                                                self.plugin_manager.plugins_loader,
                                                self.exectution_environment)
                    self.logger.info(f"Environment '{env_manager.__class__.__name__}' setup successfully.")
                    self.event_manager.notify(Event("environment_setup", {"environment": env_manager}))
            except Exception as e:
                self.logger.error(f"Failed to setup environment '{env_manager.__class__.__name__}': {e}")
                raise e
                exit()

    def teardown_environment(self):
        """Tears down the test environment using the plugin."""
        self.logger.info("Tearing down all environments")
        for env_manager in self.environment_plugin_manager:
            if hasattr(env_manager, "teardown_environment") and env_manager.is_network_environment():
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
                if env_manager.is_network_environment():
                    env_manager.deploy_services()
                    self.logger.info(f"Services deployed via '{env_manager.__class__.__name__}'")
                    self.event_manager.notify(Event("services_deployed", {"environment": env_manager}))
            except Exception as e:
                self.logger.error(f"Failed to deploy services via '{env_manager.__class__.__name__}': {e}")
                raise e
                
    def execute_steps(self):
        """
        Executes the defined steps of a test.

        :param steps: Dictionary of steps to execute.
        """
        steps = self.test_config.steps
        for step_name, step_details in steps.items():
            if step_name == "wait":
                # TODO assert that wait is >= timeout of the services
                # TODO stop the wait if the services are not failding/ending
                duration = step_details
                self.logger.info(f"Executing step 'wait' for {duration} seconds.")
                import time
                current_duration = 0
                steps_duration = duration/10
                while current_duration < duration:
                    time.sleep(steps_duration)
                    current_duration += steps_duration
                    self.logger.debug(f"Waiting for {current_duration}/{duration} seconds.")
                    self.event_manager.notify(Event("step_progress", {"step": "wait", "duration": current_duration}))
                    if self.event_manager.has_event_occurred(Event("experiment_finished_early",{})):
                        self.logger.info("Experiment finished early. Stopping wait.")
                        self.event_manager.notify(Event("step_completed", {"step": "wait", "duration": duration}))
                        return
                self.logger.info(f"Completed step 'wait' for {duration} seconds.")
                self.event_manager.notify(Event("step_completed", {"step": "wait", "duration": duration}))
            # Add more step handlers as needed

    def validate_assertions(self):
        """Validates assertions defined in the test configuration."""
        assertions = self.test_config.assertions
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
        service_manager = None
        for curent_service_name, service_details in self.services.items():
            if curent_service_name == service_name:
                # Find the appropriate service manager based on implementation
                implementation = service_details.implementation
                service_manager = next((m for m in self.service_managers if m.get_implementation_name() == implementation), None)
                break

        if not service_manager:
            self.logger.error(f"Service manager for '{service_name}' not found.")
            return

        # Assuming service manager provides the base URL or IP
        base_url = service_manager.get_base_url(service_name)  # Implement this method in IImplementationManager and concrete classes
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
        # TODO should register event per test
        logging_observer = LoggerObserver()
        self.event_manager.register_observer(logging_observer)
        experiment_observer = ExperimentObserver()
        self.event_manager.register_observer(experiment_observer)
        self.logger.debug("Registered LoggingObserver as a default observer")
    
 
    def setup_test(self):
        """
        Sets up all environments managed by thfrom core.observer.event import Event
        e environment managers, providing service configurations and deployment commands.
        """
        self.logger.info("Setting up all environments and services")
        self.setup_services()
        self.setup_environment()
        
    def setup_services(self):
        """_summary_
        """
        self.setup_implementations()
        self.setup_testers()
        self.generate_deployment_commands(self.test_config.network_environment)

    def generate_deployment_commands(self, environment:str) -> Dict[str, str]:
        """
        Collects deployment commands from all service managers based on the services defined in the tests.

        :return: A dictionary mapping service names to their respective command strings.
        """
        deployment_commands = {}
        for service_name, service_details in self.services.items():
            self.logger.debug(f"Generating deployment commands for '{service_name}'")
            # Find the appropriate service manager based on implementation
            implementation = service_details.implementation.name
            self.logger.debug(f"Service '{service_name}' uses implementation '{implementation}' with details: {service_details} - checking service managers {self.service_managers}")
            manager = next((m for m in self.service_managers if m.get_implementation_name() == implementation), None)
            if not manager:
                self.logger.error(f"No service manager found for implementation '{implementation}'")
                exit(1)
            try:
                # Ensure 'name' key exists
                self.logger.debug(f"Generating deployment commands for service '{service_name}' with details: {service_details}")
                if hasattr(service_details, 'name'):
                    service_details.name = service_name
                info_commands = manager.generate_deployment_commands(service_details, environment)
                deployment_commands.update(info_commands)
            except Exception as e:
                self.logger.error(f"Failed to generate deployment command for service '{service_name}': {e}")
                exit(1)
        self.logger.debug(f"Collected deployment commands: {deployment_commands}")
        self.deployment_commands = deployment_commands
