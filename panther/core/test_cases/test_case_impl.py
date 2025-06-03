from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Literal
import requests
import re
from urllib.parse import urljoin

from panther.core.test_cases.test_interface_impl import ITestCase
from panther.core.observer.event_manager import EventManager
from panther.core.observer.event import Event
from panther.core.observer.logger_observer import LoggerObserver
from panther.core.observer.experiment_observer import ExperimentObserver
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.results.result_collector import ResultCollector
from panther.core.results.result_handlers.storage_handler import StorageHandler
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.plugin_manager import PluginManager
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.services.iut.config_schema import ImplementationType
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)

# Import metrics components
try:
    from panther.core.metrics import Phase
except ImportError:
    # Fallback if metrics are not available
    class Phase:
        TEST_EXECUTION = "test_execution"


class TestCase(ITestCase):
    """
    TestCase class represents a test case that is configured and executed based on the provided configurations.

    Attributes:
        available_implementations_per_protocol (dict): Available implementations per protocol.
        iut_path (Path): Path to the implementation under test (IUT) directory.
        test_defined_testers (list): List of testers defined in the test configuration.
        testers_path (Path): Path to the testers directory.
        available_testers (list): List of available testers.
        available_protocols (list): List of available protocols.
        test_defined_implementation (list): List of implementations defined in the test configuration.
        test_name (str): Name of the test case.
        test_experiment_dir (Path): Directory for the test experiment.
        result_collectors (ResultCollector): Collector for test results.
        service_managers (list): List of service managers.
        environment_plugin_manager (list): List of environment plugin managers.
        event_manager (EventManager): Manager for handling events.
        exectution_environment (list): List of execution environments.
        plugin_manager (PluginManager): Manager for handling plugins.
        services (dict): Dictionary of services defined in the test configuration.

    Methods:
        __str__(): Returns a string representation of the test case.
        __repr__(): Returns a string representation of the test case.
        run(): Runs the test case based on the provided configuration.
        setup_testers(): Sets up the testers based on the test configuration.
        setup_implementations(): Sets up the implementations based on the test configuration.
        teardown_services(): Stops all services managed by the service managers.
        setup_environment(): Sets up the test environment using the plugin.
        teardown_environment(): Tears down the test environment using the plugin.
        deploy_services(): Deploys services through environment managers.
        execute_steps(): Executes the defined steps of a test.
        validate_assertions(): Validates assertions defined in the test configuration.
        check_service_responsiveness(service_name, endpoint, expected_status): Checks if a service's endpoint is responsive and returns the expected status code.
        register_default_observers(): Registers default observers to listen to events.
        setup_services(): Sets up the services based on the test configuration.
    """

    def __init__(
        self,
        test_config: TestConfig,
        global_config: GlobalConfig,
        plugin_manager: PluginManager,
        experiment_dir: Path,
        metrics_collector=None,
    ):
        super().__init__(test_config, global_config)

        self.metrics_collector = metrics_collector
        self.available_implementations_per_protocol = None
        self.iut_path = None
        self.test_defined_testers = None
        self.testers_path = None
        self.available_testers = None
        self.available_protocols = None
        self.test_defined_implementation = None
        self.test_name = re.sub(r'[^a-zA-Z0-9_]', '_', test_config.name.strip())
        # Do not allow 2 "_" in a row
        self.test_name = re.sub(r'_+', '_', self.test_name)
        self.test_experiment_dir = experiment_dir / self.test_name

        self.logger.debug(
            "Creating test case '%s' with experiment directory '%s' and test configuration '%s'",
            self.test_name,
            self.test_experiment_dir,
            test_config
        )
        self.result_collectors = ResultCollector()
        self.result_collectors.register_handler(
            f"storage_{self.test_name})", StorageHandler(experiment_dir, self.test_name)
        )

        # File Handler
        panther_log_file = self.test_experiment_dir / "experiment.log"
        panther_log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(panther_log_file)
        self.logger.addHandler(file_handler)

        self.service_managers: list[IServiceManager] = []

        self.environment_plugin_manager: list[IEnvironmentPlugin] = []
        self.event_manager = EventManager()

        net_environment_type = test_config.network_environment
        self.logger.info("Loading network environment: %s", net_environment_type)

        self.exectution_environment = []
        self.plugin_manager = plugin_manager

        self.services = test_config.services

        self._fail_on_error = global_config.features.fast_fail

        self._panther_dir = Path(os.path.dirname(__file__)).parent.parent.parent

        self.state: Literal["PENDING", "RUNNING", "COLLECTING", "DONE", "ERROR"] = "PENDING"

    def __str__(self):
        return (
            f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"network_environments={self.test_config.network_environment}, "
            f"execution_environments={self.test_config.execution_environments}, "
            f"test_experiment_dir={self.test_experiment_dir})"
        )

    def __repr__(self):
        return (
            f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"network_environments={self.test_config.network_environment}, "
            f"execution_environments={self.test_config.execution_environments}, "
            f"test_experiment_dir={self.test_experiment_dir})"
        )

    def run(self):
        """
        Runs the test case based on the provided configuration.

        This method performs the following steps:
        1. Logs the start of the test case.
        2. Registers default observers.
        3. Sets up necessary services.
        4. Sets up the test enviironment.
        5. Deploys the required services.
        6. Executes the test steps.
        7. Validates the assertions.
        8. Logs the successful completion of the test case.
        9. Notifies the event manager about the test completion.

        If any exception occurs during the execution, it logs the error and raises the exception.
        Finally, it tears down the test environment.

        Raises:
            Exception: If any error occurs during the execution of the test case.
        """
        """Runs the test case based on the provided configuration."""
        try:
            self.state = "RUNNING"
            self.logger.info("Starting Test: %s", self.test_config.name)
            self.logger.info("Description:   %s", self.test_config.description)

            test_case_timer = None
            if self.metrics_collector:
                test_case_timer = self.metrics_collector.start_timing(
                    f"test_case_total_{self.test_name}"
                )

            self.register_default_observers()

            # Setup services with timing
            if self.metrics_collector:
                with self.metrics_collector.time_operation(f"setup_services_{self.test_name}"):
                    self.setup_services()
            else:
                self.setup_services()

            # Setup environment with timing
            if self.metrics_collector:
                with self.metrics_collector.time_operation(f"setup_environment_{self.test_name}"):
                    self.setup_environment()
            else:
                self.setup_environment()

            # Deploy services with timing
            if self.metrics_collector:
                with self.metrics_collector.time_operation(f"deploy_services_{self.test_name}"):
                    self.deploy_services()
            else:
                self.deploy_services()

            # Execute steps with timing
            if self.metrics_collector:
                with self.metrics_collector.time_operation(f"execute_steps_{self.test_name}"):
                    self.execute_steps()
            else:
                self.execute_steps()

            # Validate assertions with timing
            if self.metrics_collector:
                with self.metrics_collector.time_operation(f"validate_assertions_{self.test_name}"):
                    self.validate_assertions()
            else:
                self.validate_assertions()

            # Check if service tests actually passed
            self._check_service_test_results()

            self.state = "DONE"
            self.logger.info("Test '%s' completed successfully.", self.test_config.name)

            if self.metrics_collector:
                if test_case_timer:
                    test_case_timer.stop()
                # Record artifact metrics
                self._record_artifact_metrics()
                # Save test-specific metrics
                self.save_test_metrics()

            self.event_manager.notify(Event("test_completed", {"test": self.test_config.name}))

        except Exception as e:
            self.state = "ERROR"

            if self.metrics_collector:
                self.metrics_collector.record_error(
                    phase=Phase.TEST_EXECUTION,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    component="test_case",
                    test_case=self.test_config.name,
                    metadata={"test_phase": str(self.state)},
                )
                if test_case_timer:
                    test_case_timer.stop()
            self.logger.error("Test '%s' failed: %s", self.test_config.name, e)
            raise
        finally:
            self.state = "COLLECTING"

            # Teardown environment with timing
            if self.metrics_collector:
                with self.metrics_collector.time_operation(
                    f"teardown_envi ronment_{self.test_name}"
                ):
                    self.teardown_environment()
            else:
                self.teardown_environment()

    def setup_testers(self):
        """
        Sets up the testers based on the services details extracted from the test configuration file.

        This method performs the following steps:
        - Extracts the required testers from the services details.
        - Loads the testers plugins from the plugins/services/testers directory.
        - Creates a list of service managers that will be used to deploy the services.

        The method logs the progress and any issues encountered during the setup process.

        Returns:
            None
        """
        self.logger.debug("Setup Testers plugins ...")
        self.testers_path = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / Path(self.global_config.paths.services_dir)
            / Path(self.global_config.paths.testers_dir)
        )
        self.logger.debug("Looking for testers plugins at '%s'", self.testers_path)
        self.available_testers = [
            p.name
            for p in self.testers_path.iterdir()
            if p.is_dir() and not p.name.startswith("__")
        ]
        self.logger.debug("Available testers: %s", self.available_testers)
        self.test_defined_testers = [
            service_details
            for service_details in self.services.values()
            if service_details.implementation.type == ImplementationType.testers
        ]
        if len(self.test_defined_testers) == 0:
            self.logger.warning("No testers specified in the test configuration.")
            return
        self.logger.debug("Test defined testers: %s", self.test_defined_testers)
        if self.testers_path.exists() and self.testers_path.is_dir():
            self.logger.debug("Found testers plugin at '%s'", self.testers_path)
            # Discover and load implementations under this protocol using PluginFactory
            available_testers = self.plugin_manager.plugins_loader.get_testers()
            for tester_config in self.test_defined_testers:
                if tester_config.implementation.name in available_testers:
                    implementation_dir = self.testers_path / tester_config.implementation.name
                    # Create service manager using PluginFactory
                    self.logger.debug(
                        "Creating service manager for tester '%s' under protocol '%s' found at '%s'",
                        tester_config,
                        tester_config.protocol,
                        implementation_dir
                    )
                    service_manager = self.plugin_manager.create_service_manager(
                        protocol=tester_config.protocol,  # TODO: Now duplication in config
                        implementation=tester_config.implementation,
                        implementation_dir=implementation_dir,
                        service_config_to_test=tester_config,
                    )
                    self.service_managers.append(service_manager)
                    self.logger.debug(
                        "Added service manager for testers '%s' under protocol '%s'",
                        tester_config.name,
                        'quic'
                    )
                else:
                    self.logger.warning(
                        "Tester '%s' for protocol '%s' not found. Skipping.",
                        tester_config.name,
                        'quic'
                    )
        else:
            self.logger.warning("Tester plugin not found at '%s'. Skipping.", self.testers_path)

    def setup_implementations(self):
        """
        Sets up the implementations for the services defined in the test configuration file.

        This method performs the following steps:
        - Extracts the required implementations from the services details.
        - Loads the protocol plugins from the plugins/services/iut directory.
        - Creates a list of service managers that will be used to deploy the services.

        Note:
            Some part of this function should be in the plugin loader module I think ?

        The method logs the progress and details at each step, including:
        - The path where it looks for IUT plugins.
        - The available protocols found.
        - The implementations defined in the test configuration.
        - The details of each service and its implementation.
        - The creation of service managers for each implementation under the respective protocol.

        If a protocol plugin or an implementation is not found, appropriate warnings are logged, and the method may exit.

        Raises:
            SystemExit: If a protocol plugin is not found at the expected path.
        """
        self.logger.debug("Setup Implementation Under Tests plugins ...")
        self.iut_path = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / Path(self.global_config.paths.services_dir)
            / Path(self.global_config.paths.iut_dir)
        )
        self.logger.debug("Looking for IUT plugins at '%s'", self.iut_path)
        self.available_protocols = [
            p.name for p in self.iut_path.iterdir() if p.is_dir() and not p.name.startswith("__")
        ]
        self.logger.debug("Available protocols: %s", self.available_protocols)
        self.available_implementations_per_protocol = {}
        for protocol in self.available_protocols:
            self.available_implementations_per_protocol[protocol] = (
                self.plugin_manager.plugins_loader.get_implementations_for_protocol(protocol)
            )

        self.test_defined_implementation = [
            service_details
            for service_details in self.services.values()
            if service_details.implementation.type == ImplementationType.iut
        ]
        self.logger.debug("Test defined implementations: %s", self.test_defined_implementation)

        for service_name, service_details in self.services.items():
            self.logger.debug(
                "Service '%s' uses implementation '%s' with details: %s",
                service_name,
                service_details.implementation,
                service_details
            )

        for protocol in self.available_protocols:
            protocol_plugin_path = self.iut_path / protocol
            if protocol_plugin_path.exists() and protocol_plugin_path.is_dir():
                self.logger.debug(
                    "Found protocol plugin at '%s' - checking implementations",
                    protocol_plugin_path
                )
                # Discover and load implementations under this protocol using PluginFactory
                for implementation_config in self.test_defined_implementation:
                    self.logger.debug(
                        "Checking implementation '%s' for protocol '%s'",
                        implementation_config,
                        protocol
                    )
                    if (
                        implementation_config.implementation.name
                        in self.available_implementations_per_protocol[protocol]
                    ):
                        # Question: transfert the global config to the plugin manager ?
                        implementation_dir = (
                            protocol_plugin_path / implementation_config.implementation.name
                        )
                        # Create service manager using PluginFactory

                        self.logger.debug(
                            "Creating service manager for implementation '%s' under protocol '%s' found at '%s'",
                            implementation_config,
                            implementation_config.protocol,
                            implementation_dir
                        )
                        service_manager = self.plugin_manager.create_service_manager(
                            protocol=implementation_config.protocol,
                            implementation=implementation_config.implementation,
                            implementation_dir=implementation_dir,
                            service_config_to_test=implementation_config,
                        )
                        self.service_managers.append(service_manager)
                        self.logger.debug(
                            "Added service manager for implementation '%s' under protocol '%s'",
                            implementation_config,
                            implementation_config.protocol
                        )
                    else:
                        self.logger.warning(
                            "Implementation '%s' for protocol '%s' not found. Skipping.",
                            implementation_config,
                            protocol
                        )
                        # exit()
            else:
                self.logger.warning(
                    "Protocol plugin '%s' not found at '%s'. Skipping.",
                    protocol,
                    protocol_plugin_path
                )
                exit()

    def teardown_services(self):
        """
        Stops all services managed by the service managers.
        This method iterates through all service managers and attempts to stop each service
        if the manager has a 'stop_service' method. It logs the stopping process and notifies
        the event manager when a service is stopped. If stopping a service fails, it logs an error.
        Raises:
            Exception: If stopping a service manager fails.
        """

        self.logger.info("Stopping all services")
        for manager in self.service_managers:
            if hasattr(manager, "stop_service"):
                try:
                    manager.stop_service()
                    self.logger.info("Service '%s' stopped.", manager.__class__.__name__)
                    self.event_manager.notify(Event("service_stopped", {"service": manager}))
                except Exception as e:
                    self.logger.error(
                        "Failed to stop service manager '%s': %s",
                        manager.__class__.__name__,
                        e
                    )

    def setup_environment(self):
        """
        Setup the test environment using the plugin.

        This method sets up both execution and network environments as specified in the test configuration.
        It iterates through the execution environments defined in the test configuration, creates environment managers
        for each, and appends them to the environment plugin manager and execution environment list.

        For the network environment, it creates an environment manager and appends it to the environment plugin manager.
        It then attempts to set up the network environment, logging the success or failure of the setup process.

        Raises:
            Exception: If the environment setup fails.

        Logs:
            Debug: Information about the setup process for each environment.
            Info: Successful setup of the environment.
            Error: Failure to setup the environment.
        """
        for exec_env in self.test_config.execution_environments:
            self.logger.debug(
                "Setting up execution environment type with environments '%s'",
                exec_env
            )
            self.logger.debug("Setting up environment '%s'", exec_env)
            subtype = exec_env.type
            settings = exec_env
            environment_dir = (
                self._panther_dir
                / self.plugin_manager.plugins_loader.plugins_base_dir
                / "environments"
                / "execution_environment"
            )
            self.logger.debug(
                "Creating environment manager for execution environment with %s and settings %s",
                subtype,
                settings
            )
            environment_manager = self.plugin_manager.create_environment_manager(
                environment=subtype,
                test_config=self.test_config,
                environment_dir=environment_dir,
                output_dir=self.test_experiment_dir,
                event_manager=self.event_manager,
            )
            self.environment_plugin_manager.append(environment_manager)
            self.exectution_environment.append(environment_manager)
            self.logger.debug(
                "Added environment manager for environment execution - %s",
                environment_manager
            )

        # Only one network environment is supported for now
        self.logger.debug(
            "Setting up network environments '%s'",
            self.test_config.network_environment.type
        )
        settings = self.test_config.network_environment
        environment_dir = (
            self._panther_dir
            / self.plugin_manager.plugins_loader.plugins_base_dir
            / "environments"
            / "network_environment"
        )
        self.logger.debug(
            "Creating environment manager for net environment with %s and settings %s",
            self.test_config.network_environment.type,
            settings
        )
        environment_manager = self.plugin_manager.create_environment_manager(
            environment=self.test_config.network_environment.type,
            test_config=self.test_config,
            environment_dir=environment_dir,
            output_dir=self.test_experiment_dir,
            event_manager=self.event_manager,
        )
        self.environment_plugin_manager.append(environment_manager)
        self.logger.debug("Added environment manager for environment network")

        try:
            if isinstance(
                environment_manager, INetworkEnvironment
            ):  # Always True for now (maybe mix network envs in the future)
                environment_manager.setup_environment(
                    self.service_managers,
                    self.test_config,
                    self.global_config,
                    datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                    self.plugin_manager.plugins_loader,
                    self.exectution_environment,
                )
                self.logger.info(
                    "Environment '%s' setup successfully.",
                    environment_manager.__class__.__name__
                )
                self.event_manager.notify(
                    Event("environment_setup", {"environment": environment_manager})
                )
        except Exception as e:

            self.logger.error(
                "Failed to setup environment '%s': %s",
                environment_manager.__class__.__name__,
                e
            )
            raise e

    def teardown_environment(self):
        """
        Teardown all network environments managed by the environment plugin manager.
        This method iterates through all environment managers in the environment plugin manager.
        If an environment manager has a `teardown_environment` method and is identified as a
        network environment, it attempts to teardown the environment. Logs the success or
        failure of each teardown attempt and notifies the event manager upon successful teardown.
        Raises:
            Exception: If an error occurs during the teardown of an environment.
        """
        self.logger.info("Tearing down all environments")
        for env_manager in self.environment_plugin_manager:
            if (
                hasattr(env_manager, "teardown_environment")
                and env_manager.is_network_environment()
            ):
                try:
                    env_manager.teardown_environment()
                    self.logger.info(
                        "Environment '%s' torn down successfully.",
                        env_manager.__class__.__name__
                    )
                    self.event_manager.notify(
                        Event("environment_teardown", {"environment": env_manager})
                    )
                except Exception as e:

                    self.logger.error(
                        "Failed to teardown environment '%s': %s",
                        env_manager.__class__.__name__,
                        e
                    )
            else:
                self.logger.debug(
                    "No teardown_environment method for '%s'. Skipping.",
                    env_manager.__class__.__name__
                )

    def deploy_services(self):
        """
        Deploys services through environment managers.
        This method iterates over the environment plugin managers and attempts to deploy services
        using each manager that is an instance of INetworkEnvironment. It logs the deployment process
        and notifies the event manager upon successful deployment. If an error occurs during the
        deployment, it logs the error and raises the exception.
        Raises:
            Exception: If the deployment of services fails for any environment manager.
        """
        self.logger.info("Deploying services through environment managers")
        for env_manager in self.environment_plugin_manager:
            try:
                if isinstance(env_manager, INetworkEnvironment):
                    env_manager.deploy_services()
                    self.logger.info("Services deployed via '%s'", env_manager.__class__.__name__)
                    self.event_manager.notify(
                        Event("services_deployed", {"environment": env_manager})
                    )
            except Exception as e:

                self.logger.error(
                    "Failed to deploy services via '%s': %s",
                    env_manager.__class__.__name__,
                    e
                )
                raise e

    def execute_steps(self):
        """
        Executes the steps defined in the test configuration.
        This method iterates over the steps specified in the test configuration and
        executes them accordingly. Currently, it supports the following steps:
        - "wait": Pauses execution for a specified duration, periodically checking
          if an early termination event has occurred.
        For the "wait" step:
        - Logs the start and completion of the wait period.
        - Periodically logs the progress of the wait.
        - Notifies the event manager of step progress and completion.
        - Stops waiting early if an "experiment_finished_early" event is detected.
        TODO:
        - Assert that the wait duration is greater than or equal to the timeout of the services.
        - Stop the wait if the services are not failing/ending.
        Raises:
            Any exceptions raised by the underlying step execution logic.
        """

        steps = self.test_config.steps
        for step_name, step_details in steps.items():
            if step_name == "wait":
                # TODO assert that wait is >= timeout of the services
                # TODO stop the wait if the services are not failding/ending
                duration = step_details
                self.logger.info("Executing step 'wait' for %s seconds.", duration)
                import time

                current_duration = 0
                steps_duration = duration / 10
                while current_duration < duration:
                    time.sleep(steps_duration)
                    current_duration += steps_duration
                    self.logger.debug("Waiting for %s/%s seconds.", current_duration, duration)
                    self.event_manager.notify(
                        Event(
                            "step_progress",
                            {"step": "wait", "duration": current_duration},
                        )
                    )
                    if self.event_manager.has_event_occurred(
                        Event("experiment_finished_early", {})
                    ):
                        self.logger.info("Experiment finished early. Stopping wait.")
                        self.event_manager.notify(
                            Event("step_completed", {"step": "wait", "duration": duration})
                        )
                        return
                self.logger.info("Completed step 'wait' for %s seconds.", duration)
                self.event_manager.notify(
                    Event("step_completed", {"step": "wait", "duration": duration})
                )
            # Add more step handlers as needed

    def validate_assertions(self):
        """
        This method iterates over the assertions specified in the test configuration
        and performs validation based on the type of assertion. Currently, it supports
        the "service_responsive" assertion type, which checks if a specified service
        endpoint is responsive and returns the expected status code.

        Note:
            This method should be moved to a separate module.

        Raises:
            Exception: If any assertion fails during validation.

        Logs:
            Info: If no assertions are defined in the test configuration.
            Error: If an assertion fails during validation.

        Assertion Types:
            - service_responsive: Validates if a service endpoint is responsive.
                - service: The service to check.
                - endpoint: The endpoint of the service to check.
                - expected_status: The expected HTTP status code (default is 200).
        """
        assertions = self.test_config.assertions
        if not assertions:
            self.logger.info("No assertions to validate.")
            return
        for assertion in assertions:
            try:
                if assertion["type"] == "service_responsive":
                    service = assertion["service"]
                    endpoint = assertion["endpoint"]
                    expected_status = assertion.get("expected_status", 200)
                    self.check_service_responsiveness(service, endpoint, expected_status)
            except Exception as e:

                self.logger.error("Assertion failed: %s", e)
                raise

    def check_service_responsiveness(self, service_name: str, endpoint: str, expected_status: int):
        """
        Checks the responsiveness of a specified service by sending a GET request to a given endpoint and
        comparing the response status code to the expected status code.
        Args:
            service_name (str): The name of the service to check.
            endpoint (str): The endpoint to send the GET request to.
            expected_status (int): The expected HTTP status code of the response.
        Returns:
            None
        Logs:
            - Debug: When starting the check and the constructed URL.
            - Info: If the service responds with the expected status code.
            - Error: If the service manager is not found, the service responds with an unexpected status code,
              or if there is an exception during the request.
        """
        self.logger.debug("Checking responsiveness of '%s' at '%s'", service_name, endpoint)
        service_manager = None
        for curent_service_name, service_details in self.services.items():
            if curent_service_name == service_name:
                # Find the appropriate service manager based on implementation
                implementation = service_details.implementation
                service_manager = next(
                    (
                        m
                        for m in self.service_managers
                        if m.get_implementation_name() == implementation
                    ),
                    None,
                )
                break

        if not service_manager:
            self.logger.error("Service manager for '%s' not found.", service_name)
            return

        # Assuming service manager provides the base URL or IP
        base_url = service_manager.get_base_url(
            service_name
        )  # Implement this method in IImplementationManager and concrete classes
        url = urljoin(base_url, endpoint)
        self.logger.debug("Checking responsiveness of '%s' at '%s'", service_name, url)

        try:
            response = requests.get(url)
            if response.status_code == expected_status:
                self.logger.info(
                    "Assertion Passed: '%s' responded with status code %s.",
                    service_name,
                    expected_status
                )
            else:
                self.logger.error(
                    "Assertion Failed: '%s' responded with status code %s, expected %s.",
                    service_name,
                    response.status_code,
                    expected_status
                )
        except Exception as e:
            self.logger.error(
                "Assertion Failed: Could not reach '%s' at '%s': %s",
                service_name,
                url,
                e
            )

    def register_default_observers(self):
        """
        Registers the default observers for the event manager.
        This method registers two default observers:
        1. LoggerObserver: Logs events for debugging purposes.
        2. ExperimentObserver: Observes events related to experiments.
        The method logs the registration process for debugging.
        """
        self.logger.debug("Registering default observers")
        logging_observer = LoggerObserver()
        self.event_manager.register_observer(logging_observer)
        experiment_observer = ExperimentObserver()
        self.event_manager.register_observer(experiment_observer)
        self.logger.debug("Registered LoggingObserver as a default observer")

    def setup_services(self):
        """
        Sets up the necessary services for the test case.
        This method performs the following actions:
        1. Logs the initiation of service setup.
        2. Sets up the implementations required for the test case.
        3. Sets up the testers required for the test case.
        """
        self.logger.debug("Setting up services ...")
        self.setup_implementations()
        self.setup_testers()

    def _record_artifact_metrics(self):
        """
        Record metrics about artifacts generated during test execution.
        """
        if not self.metrics_collector:
            return

        try:
            # Count log files in test directory
            log_files = list(self.test_experiment_dir.glob("**/*.log"))
            self.metrics_collector.increment_counter("logs_generated", len(log_files))

            # Count result files
            result_files = (
                list(self.test_experiment_dir.glob("**/*.json"))
                + list(self.test_experiment_dir.glob("**/*.xml"))
                + list(self.test_experiment_dir.glob("**/*.csv"))
            )
            self.metrics_collector.increment_counter("reports_generated", len(result_files))

            # Calculate total artifact size
            total_size = 0
            for file_path in self.test_experiment_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size

            total_size_mb = total_size / (1024 * 1024)  # Convert to MB
            self.metrics_collector.set_gauge("total_artifact_size_mb", total_size_mb)
            self.metrics_collector.increment_counter(
                "artifacts_total", len(log_files) + len(result_files)
            )

        except Exception as e:
            self.logger.warning("Failed to record artifact metrics: %s", e)

    def save_test_metrics(self):
        """
        Save test-specific metrics to the test's experiment directory.
        This includes test execution times, resource usage, and other metrics.
        """
        if not self.metrics_collector:
            return

        try:
            # Create metrics directory within the test directory
            test_metrics_dir = self.test_experiment_dir / "metrics"
            test_metrics_dir.mkdir(parents=True, exist_ok=True)

            # Generate timestamp for files
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save metrics data for this test
            from panther.core.metrics import MetricsExporter, MetricsReporter

            # Create exporters for the test-specific metrics
            metrics_exporter = MetricsExporter(self.metrics_collector)
            metrics_reporter = MetricsReporter(self.metrics_collector)

            # Export test-specific metrics in JSON format
            export_path = test_metrics_dir / f"test_metrics_{timestamp}.json"
            metrics_exporter.export_to_json(export_path)

            # Generate a human-readable report
            report_path = test_metrics_dir / f"test_metrics_report_{timestamp}.txt"
            metrics_reporter.generate_report(str(report_path))

            self.logger.info("Test metrics saved to %s", test_metrics_dir)

        except Exception as e:
            self.logger.error("Failed to save test metrics: %s", e)

    def _check_service_test_results(self):
        """
        Checks if the service tests actually passed or failed.

        This method queries each service manager to determine if their tests were successful.
        If any service test failed, it raises an exception to mark the overall test as failed.

        Raises:
            Exception: If any service test failed or if test results cannot be determined.
        """
        self.logger.debug("Checking service test results...")

        failed_services = []
        for service_manager in self.service_managers:
            try:
                # Check if the service manager has a method to check test success
                if hasattr(service_manager, "test_success"):
                    is_successful = service_manager.test_success()
                    self.logger.debug(
                        "Service '%s' test result: %s",
                        service_manager.__class__.__name__,
                        'PASS' if is_successful else 'FAIL'
                    )

                    if not is_successful:
                        failed_services.append(service_manager.__class__.__name__)

                elif hasattr(service_manager, "get_test_results"):
                    # Alternative method to get test results
                    results = service_manager.get_test_results()
                    if results and not results.get("success", False):
                        failed_services.append(service_manager.__class__.__name__)
                        self.logger.debug(
                            "Service '%s' test result: FAIL",
                            service_manager.__class__.__name__
                        )
                    else:
                        self.logger.debug(
                            "Service '%s' test result: PASS",
                            service_manager.__class__.__name__
                        )

                else:
                    # If no test result method available, log a warning
                    self.logger.warning(
                        "Service '%s' does not provide test result information",
                        service_manager.__class__.__name__
                    )

            except Exception as e:
                self.logger.error(
                    "Failed to check test results for service '%s': %s",
                    service_manager.__class__.__name__,
                    e
                )

                failed_services.append(f"{service_manager.__class__.__name__} (check failed)")

        if failed_services:
            failure_msg = (
                f"Test failed: Service test failures detected in: {', '.join(failed_services)}"
            )
            self.logger.error(failure_msg, exc_info=True)
            raise Exception(failure_msg)

        self.logger.info("All service tests passed successfully.")