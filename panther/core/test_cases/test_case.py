from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

from core.test_cases.test_interface import ITestCase
from core.observer.event_manager import EventManager
from core.observer.event import Event
from core.observer.logger_observer import LoggerObserver
from core.observer.experiment_observer import ExperimentObserver
from config.config_experiment_schema import TestConfig
from config.config_global_schema import GlobalConfig
from panther.core.results.result_collector import ResultCollector
from panther.core.results.result_handlers.storage_handler import StorageHandler
from plugins.services.services_interface import IServiceManager
from plugins.plugin_manager import PluginManager
from plugins.environments.environment_interface import IEnvironmentPlugin
from plugins.services.iut.config_schema import ImplementationType

class TestCase(ITestCase):
    def __init__(self, 
                 test_config:   TestConfig, 
                 global_config: GlobalConfig,
                 plugin_manager: PluginManager,
                 experiment_dir: Path):
        
        super().__init__(test_config, global_config)
        
        self.test_name = test_config.name.replace(" ", "_")
        self.test_experiment_dir = experiment_dir / test_config.name.replace(" ", "_")
        
        self.logger.debug(f"Creating test case '{self.test_name}' with experiment directory '{self.test_experiment_dir}' and test configuration '{test_config}'")
        self.result_collectors = ResultCollector()
        self.result_collectors.register_handler(f"storage_{self.test_name})",  
                                                 StorageHandler(experiment_dir, self.test_name))
         
        self.service_managers: List[IServiceManager] = []
        
        self.environment_plugin_manager : List[IEnvironmentPlugin] = []
        self.event_manager = EventManager()
        
        net_environment_type = test_config.network_environment
        self.logger.info(f"Loading network environment: {net_environment_type}")
        
        self.exectution_environment = []
        self.plugin_manager = plugin_manager
        
        self.services = test_config.services
        self.deployment_commands = []
        
    def __str__(self):
        return (f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"network_environments={self.test_config.network_environment}, "
            f"execution_environments={self.test_config.execution_environments}, "
            f"test_experiment_dir={self.test_experiment_dir})")
        
    def __repr__(self):
        return (f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
             f"network_environments={self.test_config.network_environment}, "
            f"execution_environments={self.test_config.execution_environments}, "
            f"test_experiment_dir={self.test_experiment_dir})")

    def run(self):
        """Runs the test case based on the provided configuration."""
        try:
            self.logger.info(f"Starting Test: {self.test_config.name}")
            self.logger.info(f"Description:   {self.test_config.description}")
            self.register_default_observers()
            self.setup_services()
            self.setup_environment()
            self.deploy_services()
            self.execute_steps()
            self.validate_assertions()
            self.logger.info(f"Test '{self.test_config.name}' completed successfully.")
            self.event_manager.notify(Event("test_completed", {"test": self.test_config.name}))
        except Exception as e:
            self.logger.error(f"Test '{self.test_config.name}' failed: {e}")
            raise
        finally:
            self.teardown_environment()

    def setup_testers(self):
        """
        We have as input the services details extracted from the test configuration file.
        We need to:
        - Extract the required testers from the services details.
        - Load the testers plugins.
            - Should be in the plugins/services/testers directory.
            - Each tester should have a directory with the same name as the tester.
        - In the end, we should have a list of service managers that will be used to deploy the services.
        """
        self.logger.debug("Setup Testers plugins ...")
        self.testers_path = Path(self.global_config.paths.plugin_dir) / Path(self.global_config.paths.services_dir) / Path(self.global_config.paths.testers_dir)
        self.logger.debug(f"Looking for testers plugins at '{self.testers_path}'")
        self.available_testers = [p.name for p in self.testers_path.iterdir() if p.is_dir() and not p.name.startswith("__")]
        self.logger.debug(f"Available testers: {self.available_testers}")
        self.test_defined_testers = [service_details for service_details in self.services.values() if service_details.implementation.type == ImplementationType.testers]
        if len(self.test_defined_testers) == 0:
            self.logger.warning("No testers specified in the test configuration.")
            return
        self.logger.debug(f"Test defined testers: {self.test_defined_testers}")
        if self.testers_path.exists() and self.testers_path.is_dir():
            self.logger.debug(f"Found testers plugin at '{self.testers_path}'")
            # Discover and load implementations under this protocol using PluginFactory
            available_testers = self.plugin_manager.plugins_loader.get_testers()
            for tester_config in self.test_defined_testers:
                if tester_config.implementation.name in available_testers:
                    implementation_dir = self.testers_path / tester_config.implementation.name
                    # Create service manager using PluginFactory
                    self.logger.debug(f"Creating service manager for tester '{tester_config}' under protocol '{tester_config.protocol}' found at '{implementation_dir}'")
                    service_manager = self.plugin_manager.create_service_manager(
                        protocol=tester_config.protocol, # TODO: Now duplication in config
                        implementation=tester_config.implementation,
                        implementation_dir=implementation_dir,
                        service_config_to_test=tester_config,
                    )
                    self.service_managers.append(service_manager)
                    self.logger.debug(f"Added service manager for testers '{tester_config.name}' under protocol '{'quic'}'")
                else:
                    self.logger.warning(f"Tester '{tester_config.name}' for protocol '{'quic'}' not found. Skipping.")
        else:
            self.logger.warning(f"Tester plugin not found at '{self.testers_path}'. Skipping.")
        
    def setup_implementations(self):
        """
        We have as input the services details extracted from the test configuration file.
        We need to:
        - Extract the required implementations from the services details.
        - Load the protocol plugins. 
            - Should be in the plugins/services/iut directory.
            - Each protocol should have a directory with the same name as the protocol.
        - In the end, we should have a list of service managers that will be used to deploy the services.
        """
        self.logger.debug("Setup Implementation Under Tests plugins ...")
        self.iut_path = Path(self.global_config.paths.plugin_dir) / Path(self.global_config.paths.services_dir) / Path(self.global_config.paths.iut_dir)
        self.logger.debug(f"Looking for IUT plugins at '{self.iut_path}'")
        self.available_protocols = [p.name for p in self.iut_path.iterdir() if p.is_dir() and not p.name.startswith("__")]
        self.logger.debug(f"Available protocols: {self.available_protocols}")  
        self.available_implementations_per_protocol = {}
        for protocol in self.available_protocols:
            self.available_implementations_per_protocol[protocol] = self.plugin_manager.plugins_loader.get_implementations_for_protocol(protocol)
                
        self.test_defined_implementation = [service_details for service_details in self.services.values() if service_details.implementation.type == ImplementationType.iut]
        self.logger.debug(f"Test defined implementations: {self.test_defined_implementation}")
        
        for service_name, service_details in self.services.items():
            self.logger.debug(f"Service '{service_name}' uses implementation '{service_details.implementation}' with details: {service_details}")
        
        for protocol in self.available_protocols:
            protocol_plugin_path = self.iut_path / protocol
            if protocol_plugin_path.exists() and protocol_plugin_path.is_dir():
                self.logger.debug(f"Found protocol plugin at '{protocol_plugin_path}' - checking implementations")
                # Discover and load implementations under this protocol using PluginFactory
                for implementation_config in self.test_defined_implementation:
                    self.logger.debug(f"Checking implementation '{implementation_config}' for protocol '{protocol}'")
                    if implementation_config.implementation.name in self.available_implementations_per_protocol[protocol]:
                        # Question: transfert the global config to the plugin manager ?
                        implementation_dir = protocol_plugin_path / implementation_config.implementation.name
                        # Create service manager using PluginFactory
                        
                        self.logger.debug(f"Creating service manager for implementation '{implementation_config}' under protocol '{implementation_config.protocol}' found at '{implementation_dir}'")                        
                        service_manager = self.plugin_manager.create_service_manager(
                            protocol=implementation_config.protocol,
                            implementation=implementation_config.implementation,
                            implementation_dir=implementation_dir,
                            service_config_to_test=implementation_config,
                        )
                        self.service_managers.append(service_manager)
                        self.logger.debug(f"Added service manager for implementation '{implementation_config}' under protocol '{implementation_config.protocol}'")
                    else:
                        self.logger.warning(f"Implementation '{implementation_config}' for protocol '{protocol}' not found. Skipping.")
                        # exit()
            else:
                self.logger.warning(f"Protocol plugin '{protocol}' not found at '{protocol_plugin_path}'. Skipping.")
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
        for exec_env in self.test_config.execution_environments:
            self.logger.debug(f"Setting up execution environment type with environments '{exec_env}'")
            self.logger.debug(f"Setting up environment '{exec_env}'")
            subtype = exec_env.type
            settings = exec_env
            environment_dir = self.plugin_manager.plugins_loader.plugins_base_dir / "environments" /  f"execution_environment"
            self.logger.debug(f"Creating environment manager for execution environment with {subtype} and settings {settings}")
            environment_manager = self.plugin_manager.create_environment_manager(environment=subtype, 
                                                                                 test_config=self.test_config, 
                                                                                 environment_dir=environment_dir, 
                                                                                 output_dir=self.test_experiment_dir,
                                                                                 event_manager=self.event_manager)
            self.environment_plugin_manager.append(environment_manager)
            self.exectution_environment.append(environment_manager)
            self.logger.debug(f"Added environment manager for environment execution - {environment_manager}")
            
        # Only one network environment is supported for now
        self.logger.debug(f"Setting up network environments '{self.test_config.network_environment.type}'")
        settings = self.test_config.network_environment
        environment_dir = self.plugin_manager.plugins_loader.plugins_base_dir / "environments" /  f"network_environment"
        self.logger.debug(f"Creating environment manager for net environment with {self.test_config.network_environment.type} and settings {settings}")
        environment_manager = self.plugin_manager.create_environment_manager(environment=self.test_config.network_environment.type, 
                                                                             test_config=self.test_config, 
                                                                             environment_dir=environment_dir, 
                                                                             output_dir=self.test_experiment_dir,
                                                                             event_manager=self.event_manager)
        self.environment_plugin_manager.append(environment_manager)
        self.logger.debug(f"Added environment manager for environment network")
        
        try:
            if environment_manager.is_network_environment(): # Always True for now (maybe mix network envs in the future)
                environment_manager.setup_environment(self.service_managers, 
                                                      self.test_config, 
                                                      self.global_config,
                                                      datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                                                      self.plugin_manager.plugins_loader,
                                                      self.exectution_environment)
                self.logger.info(f"Environment '{environment_manager.__class__.__name__}' setup successfully.")
                self.event_manager.notify(Event("environment_setup", {"environment": environment_manager}))
        except Exception as e:
            self.logger.error(f"Failed to setup environment '{environment_manager.__class__.__name__}': {e}")
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
        self.logger.debug("Registering default observers")
        logging_observer = LoggerObserver()
        self.event_manager.register_observer(logging_observer)
        experiment_observer = ExperimentObserver()
        self.event_manager.register_observer(experiment_observer)
        self.logger.debug("Registered LoggingObserver as a default observer")
        
    def setup_services(self):
        """_summary_
        """
        self.logger.debug("Setting up services ...")
        self.setup_implementations()
        self.setup_testers()
