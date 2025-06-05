from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Literal
import requests
import re
import time
from urllib.parse import urljoin
from colorlog import ColoredFormatter

from panther.core.test_cases.test_interface_impl import ITestCase
from panther.core.observer.event_manager import EventManager
from panther.core.observer.event_emitter import EventEmitter
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.core.observer.observer_factory import get_observer_factory
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.results.result_collector import ResultCollector
from panther.core.results.result_handlers.storage_handler import StorageHandler
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.plugin_manager import PluginManager
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.services.iut.config_schema import ImplementationType


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
        execution_environment (list): List of execution environments.
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
        _setup_observers(): Registers default observers to listen to events.
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
        self.log_level = getattr(logging, self.global_config.logging.level.name, logging.INFO)
        self.log_format = self.global_config.logging.format

        self.test_name = re.sub(r"[^a-zA-Z0-9_]", "_", test_config.name.strip())
        self.test_name = re.sub(r"_+", "_", self.test_name)  # Do not allow 2 "_" in a row
        self.test_experiment_dir = experiment_dir / self.test_name
        self._load_logging()
        self.logger.debug(
            "Creating test case '%s' with experiment directory '%s' and test configuration '%s'",
            self.test_name,
            self.test_experiment_dir,
            test_config,
        )

        # TODO Create too early the experiment directory
        self.result_collectors = ResultCollector()
        self.result_collectors.register_handler(
            f"storage_{self.test_name}", StorageHandler(experiment_dir, self.test_name)
        )

        self.service_managers: list[IServiceManager] = []

        self.environment_plugin_manager: list[IEnvironmentPlugin] = []
        self.event_manager = EventManager()
        factory = get_observer_factory(self.global_config)
        factory.set_event_manager(self.event_manager)

        # Initialize event emitter for standardized event emission
        self.event_emitter = EventEmitter(self.event_manager)

        net_environment_type = test_config.network_environment
        self.logger.info("Loading network environment: %s", net_environment_type)

        self.execution_environment = []  # TODO
        self.plugin_manager = plugin_manager

        self.services = test_config.services

        self._fail_on_error = global_config.features.fast_fail  # TODO

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
                    # Use EventEmitter for service deployment events
                    self.event_emitter.emit_service_event(
                        name="services_deployed",
                        data={
                            "environment": env_manager.__class__.__name__,
                            "test_name": self.test_config.name,
                            # Pass all service instances in a dictionary
                            "service_instances": {
                                manager.get_service_name(): manager
                                for manager in self.service_managers
                            },
                        },
                    )
            except Exception as e:
                self.logger.error(
                    "Failed to deploy services via '%s': %s", env_manager.__class__.__name__, e
                )
                raise e

    def execute_steps(self):
        """
        Executes the defined steps of a test case.

        This method processes each step defined in the test configuration.
        Currently, it only handles 'wait' steps, but could be extended to support other step types.

        During execution, it periodically checks if the experiment should be finished early,
        and if so, it stops the execution and returns.
        """
        if not self.test_config.steps:
            self.logger.info("No steps defined for this test case.")
            return

        for step_name, step_details in self.test_config.steps.items():
            self.logger.info("Executing step: %s", step_name)

            factory = get_observer_factory()
            experiment_observer = factory.get_observer("test_experiment")
            if experiment_observer and experiment_observer.should_terminate_early():
                self.logger.info("Experiment finished early. Stopping step execution.")
                self.event_emitter.emit_step_completed(
                    step_id=step_name,
                    success=False,
                    result={"message": "Experiment finished early"},
                )
                # Emit experiment finished early event
                self.event_emitter.emit_experiment_finished_early(
                    experiment_id=self.test_config.name,
                    reason="Early termination requested by experiment observer",
                    details={"step": step_name},
                )
                return  # Exit step execution early

            if step_name == "wait":
                # Handle wait step - just wait for the specified duration
                duration = step_details

                current_duration = 0
                steps_duration = duration / 10
                while current_duration < duration:
                    time.sleep(steps_duration)
                    current_duration += steps_duration
                    self.logger.debug("Waiting for %s/%s seconds.", current_duration, duration)
                    self.event_emitter.emit_step_progress(
                        step_id="wait",
                        progress=min(1.0, current_duration / duration),
                        details={
                            "message": "Waiting...",
                            "duration": duration,
                            "current_duration": current_duration,
                        },
                    )
                    if experiment_observer and experiment_observer.should_terminate_early():
                        self.logger.info("Experiment finished early. Stopping wait step.")
                        self.event_emitter.emit_step_completed(
                            step_id="wait",
                            success=False,
                            result={"message": "Experiment finished early"},
                        )
                        # Emit experiment finished early event
                        self.event_emitter.emit_experiment_finished_early(
                            experiment_id=self.test_config.name,
                            reason="Early termination during wait step",
                            details={"step": "wait", "current_duration": current_duration},
                        )
                        return  # Exit the method early
                    elif self._fail_on_error and current_duration >= duration:
                        self.logger.error("Wait step exceeded maximum duration. Failing the test.")
                        self.event_emitter.emit_step_completed(
                            step_id="wait",
                            success=False,
                            result={"message": "Wait step exceeded maximum duration"},
                        )
                        return

                # If we get here, the wait step completed successfully
                self.event_emitter.emit_step_completed(
                    step_id="wait",
                    success=True,
                    result={"message": "Wait step completed successfully", "duration": duration},
                )

            else:
                self.logger.warning("Unknown step type: %s. Skipping.", step_name)

    def validate_assertions(self):
        """
        Validates assertions defined in the test configuration.

        Currently, it only handles 'service_responsive' assertions, but could be extended
        to support other types of assertions.

        Raises:
            Exception: If any assertion fails.
        """
        if not hasattr(self.test_config, "assertions") or not self.test_config.assertions:
            self.logger.info("No assertions defined for this test case.")
            return

        for assertion in self.test_config.assertions:
            try:
                if assertion["type"] == "service_responsive":
                    service = assertion["service"]
                    endpoint = assertion["endpoint"]
                    expected_status = assertion.get("expected_status", 200)
                    self.check_service_responsiveness(service, endpoint, expected_status)
                else:
                    self.logger.warning("Unknown assertion type: %s. Skipping.", assertion["type"])
            except Exception as e:
                self.logger.error("Assertion failed: %s", e, exc_info=True)
                raise

    def setup_services(self):
        """
        Sets up the services defined in the test configuration.

        This method goes through the test configuration and sets up the necessary services
        by configuring testers and implementations.
        """
        self.logger.debug("Setting up services...")
        self.setup_testers()
        self.setup_implementations()

    def setup_testers(self):
        """
        Sets up the testers based on the services details extracted from the test configuration file.

        This method performs the following steps:
        - Extracts the required testers from the services details.
        - Loads the testers plugins from the plugins/services/testers directory.
        - Creates a list of service managers that will be used to deploy the services.

        The method logs the progress and any issues encountered during the setup process.
        """
        self.logger.debug("Setup Testers plugins ...")
        self.testers_path = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / Path(self.global_config.paths.services_dir)
            / Path(self.global_config.paths.testers_dir)
        )
        self.logger.debug("Looking for testers plugins at '%s'", self.testers_path)

        # Get available testers
        if hasattr(self.plugin_manager.plugins_loader, "get_testers"):
            self.available_testers = self.plugin_manager.plugins_loader.get_testers()
        else:
            self.available_testers = []
            if self.testers_path.exists() and self.testers_path.is_dir():
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

            # Process each tester
            for tester_config in self.test_defined_testers:
                if tester_config.implementation.name in self.available_testers:
                    implementation_dir = self.testers_path / tester_config.implementation.name

                    # Create service manager
                    self.logger.debug(
                        "Creating service manager for tester '%s' under protocol '%s' found at '%s'",
                        tester_config,
                        tester_config.protocol,
                        implementation_dir,
                    )
                    service_manager = self.plugin_manager.create_service_manager(
                        protocol=tester_config.protocol,
                        implementation=tester_config.implementation,
                        implementation_dir=implementation_dir,
                        service_config_to_test=tester_config,
                    )
                    service_manager.event_emitter = self.event_emitter  # TODO make cleaner
                    self.service_managers.append(service_manager)
                    self.logger.debug(
                        "Added service manager for tester '%s' under protocol '%s'",
                        tester_config.name,
                        tester_config.protocol.name,
                    )
                else:
                    self.logger.warning(
                        "Tester '%s' for protocol '%s' not found. Skipping.",
                        tester_config.name,
                        tester_config.protocol.name,
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

        The method logs the progress and details at each step, including:
        - The path where it looks for IUT plugins.
        - The available protocols found.
        - The implementations defined in the test configuration.
        - The details of each service and its implementation.
        - The creation of service managers for each implementation under the respective protocol.

        If a protocol plugin or an implementation is not found, appropriate warnings are logged.
        """
        self.logger.debug("Setup Implementation Under Tests plugins ...")
        self.iut_path = (
            self._panther_dir
            / Path(self.global_config.paths.plugin_dir)
            / Path(self.global_config.paths.services_dir)
            / Path(self.global_config.paths.iut_dir)
        )
        self.logger.debug("Looking for IUT plugins at '%s'", self.iut_path)

        # Get available protocols
        if self.iut_path.exists() and self.iut_path.is_dir():
            self.available_protocols = [
                p.name
                for p in self.iut_path.iterdir()
                if p.is_dir() and not p.name.startswith("__")
            ]
        else:
            self.available_protocols = []

        self.logger.debug("Available protocols: %s", self.available_protocols)

        # Get implementations per protocol
        self.available_implementations_per_protocol = {}
        for protocol in self.available_protocols:
            if hasattr(self.plugin_manager.plugins_loader, "get_implementations_for_protocol"):
                self.available_implementations_per_protocol[protocol] = (
                    self.plugin_manager.plugins_loader.get_implementations_for_protocol(protocol)
                )
            else:
                protocol_path = self.iut_path / protocol
                if protocol_path.exists() and protocol_path.is_dir():
                    self.available_implementations_per_protocol[protocol] = [
                        p.name
                        for p in protocol_path.iterdir()
                        if p.is_dir() and not p.name.startswith("__")
                    ]
                else:
                    self.available_implementations_per_protocol[protocol] = []

        # Get implementations defined in the test
        self.test_defined_implementation = [
            service_details
            for service_details in self.services.values()
            if service_details.implementation.type == ImplementationType.iut
        ]

        self.logger.debug("Test defined implementations: %s", self.test_defined_implementation)

        # Process each implementation
        for protocol in self.available_protocols:
            protocol_plugin_path = self.iut_path / protocol
            if protocol_plugin_path.exists() and protocol_plugin_path.is_dir():
                self.logger.debug(
                    "Found protocol plugin at '%s' - checking implementations", protocol_plugin_path
                )

                for implementation_config in self.test_defined_implementation:
                    if implementation_config.protocol.name == protocol:
                        self.logger.debug(
                            "Checking implementation '%s' for protocol '%s'",
                            implementation_config,
                            protocol,
                        )

                        if (
                            implementation_config.implementation.name
                            in self.available_implementations_per_protocol[protocol]
                        ):
                            implementation_dir = (
                                protocol_plugin_path / implementation_config.implementation.name
                            )

                            # Create service manager
                            self.logger.debug(
                                "Creating service manager for implementation '%s' under protocol '%s' found at '%s'",
                                implementation_config,
                                implementation_config.protocol,
                                implementation_dir,
                            )
                            service_manager = self.plugin_manager.create_service_manager(
                                protocol=implementation_config.protocol,
                                implementation=implementation_config.implementation,
                                implementation_dir=implementation_dir,
                                service_config_to_test=implementation_config,
                            )
                            service_manager.event_emitter = self.event_emitter  # TODO make cleaner
                            self.service_managers.append(service_manager)
                            self.logger.debug(
                                "Added service manager for implementation '%s' under protocol '%s'",
                                implementation_config,
                                implementation_config.protocol,
                            )
                        else:
                            self.logger.warning(
                                "Implementation '%s' for protocol '%s' not found. Skipping.",
                                implementation_config,
                                protocol,
                            )
            else:
                self.logger.warning(
                    "Protocol plugin '%s' not found at '%s'. Skipping.",
                    protocol,
                    protocol_plugin_path,
                )

    def setup_environment(self):
        """
        Sets up the test environment using the plugin.

        This method sets up both execution environments and network environments
        based on the configuration. It loads the appropriate plugins and initializes them.
        """
        self.logger.info("Setting up test environment")

        # Emit environment setup started event
        self.event_emitter.emit_environment_setup_started(
            environment_type="test_environment", details={"test_name": self.test_config.name}
        )

        # Setup execution environments
        for environment in self.test_config.execution_environments:
            subtype = environment.type
            settings = environment

            environment_dir = (
                self._panther_dir
                / Path(self.plugin_manager.plugins_loader.plugins_base_dir)
                / "environments"
                / "execution_environment"
            )

            self.logger.debug(
                "Creating environment manager for execution environment with %s and settings %s",
                subtype,
                settings,
            )

            environment_manager = self.plugin_manager.create_environment_manager(
                environment=subtype,
                test_config=self.test_config,
                environment_dir=environment_dir,
                output_dir=self.test_experiment_dir,
                event_manager=self.event_manager,
            )

            self.environment_plugin_manager.append(environment_manager)
            self.execution_environment.append(environment_manager)
            self.logger.debug(
                "Added environment manager for execution environment - %s", environment_manager
            )

        # Setup network environment
        self.logger.debug(
            "Setting up network environment '%s'", self.test_config.network_environment.type
        )

        settings = self.test_config.network_environment
        environment_dir = (
            self._panther_dir
            / Path(self.plugin_manager.plugins_loader.plugins_base_dir)
            / "environments"
            / "network_environment"
        )

        self.logger.debug(
            "Creating environment manager for network environment with %s and settings %s",
            self.test_config.network_environment.type,
            settings,
        )

        environment_manager = self.plugin_manager.create_environment_manager(
            environment=self.test_config.network_environment.type,
            test_config=self.test_config,
            environment_dir=environment_dir,
            output_dir=self.test_experiment_dir,
            event_manager=self.event_manager,
        )
        environment_manager.event_emitter = self.event_emitter  # TODO make cleaner
        self.environment_plugin_manager.append(environment_manager)
        self.logger.debug("Added environment manager for network environment")

        try:
            if isinstance(environment_manager, INetworkEnvironment):
                environment_manager.setup_environment(
                    self.service_managers,
                    self.test_config,
                    self.global_config,
                    datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                    self.plugin_manager.plugins_loader,
                    self.execution_environment,
                )
                self.logger.info(
                    "Test environment set up via '%s'", environment_manager.__class__.__name__
                )
                # Use EventEmitter for environment setup event
                self.event_emitter.emit_environment_setup_completed(
                    environment_type=environment_manager.__class__.__name__,
                    success=True,
                    details={
                        "test_name": self.test_config.name,
                        "environment_name": (
                            environment_manager.env_name
                            if hasattr(environment_manager, "env_name")
                            else environment_manager.__class__.__name__
                        ),
                        # Pass the actual environment instance
                        "environment_instance": environment_manager,
                    },
                )

        except Exception as e:
            self.logger.error(
                "Failed to set up test environment via '%s': %s",
                environment_manager.__class__.__name__,
                e,
                exc_info=True,
            )
            raise e

    def teardown_environment(self):
        """
        Tears down the test environment using the plugin.

        This method stops all services and tears down the environment.
        It is called in the finally block of the run method to ensure cleanup.
        """
        try:
            self.teardown_services()

            for env_manager in self.environment_plugin_manager:
                try:
                    env_manager.teardown_environment()
                    self.logger.info(
                        "Test environment torn down via '%s'", env_manager.__class__.__name__
                    )
                    # Use EventEmitter for environment teardown event
                    self.event_emitter.emit_environment_teardown(
                        environment_type=env_manager.__class__.__name__,
                        success=True,
                        details={"test_name": self.test_config.name},
                    )
                except Exception as e:
                    self.logger.error(
                        "Failed to tear down test environment via '%s': %s",
                        env_manager.__class__.__name__,
                        e,
                        exc_info=True,
                    )
        except Exception as e:
            self.logger.error("Error during environment teardown: %s", e, exc_info=True)
            # No re-raise to allow cleanup to continue

    def teardown_services(self):
        """
        Stops all services managed by the service managers.

        This method iterates through all service managers and stops their services.
        """
        for service_manager in self.service_managers:
            try:
                if hasattr(service_manager, "stop"):
                    # Call stop, service will notify events via mixin
                    service_manager.stop()
                else:
                    self.logger.warning(
                        "Service manager '%s' does not support stopping services",
                        service_manager.get_implementation_name(),
                    )
            except Exception as e:
                self.logger.error(
                    "Failed to stop service '%s': %s",
                    service_manager.get_implementation_name(),
                    e,
                    exc_info=True,
                )

    def _load_logging(self):
        """Load and configure logging for the experiment manager."""
        # Set up the logger
        self.logger.setLevel(self.log_level)

        # Create a formatter with colors if available
        formatter = ColoredFormatter(
            "%(log_color)s" + self.log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )

        if not self.logger.hasHandlers():
            # Prevent duplicate handlers if logger is already configured
            self.logger.propagate = False
        else:
            # Clear existing handlers to avoid duplicates
            self.logger.handlers.clear()

        # Create file handler for logging
        self.test_experiment_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug("Creating log directory at '%s'", self.test_experiment_dir)
        file_handler = logging.FileHandler(self.test_experiment_dir / "test.log")
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)

        self.registered_observers: list[str] = []

        # Add the file handler to the logger
        self.logger.addHandler(file_handler)

    def _setup_observers(self):
        """
        Registers default observers to listen to events.

        This method sets up the standard observers for logging, metrics, storage,
        and experiment tracking using the enhanced observer registry system.

        It creates and registers:
        - Enhanced logger observer for color-coded event logging
        - Enhanced metrics observer for comprehensive metrics collection
        - Enhanced storage observer integrated with ResultsManager
        - Experiment observer for tracking test progress

        Each observer is created with proper error handling and fallbacks
        for backward compatibility.
        """
        self.logger.debug("Registering default observers using enhanced registry")

        # Get the observer factory
        factory = get_observer_factory()

        # Ensure output directory exists
        if not self.test_experiment_dir.exists():
            self.test_experiment_dir.mkdir(parents=True, exist_ok=True)

        # Create and register enhanced logger observer
        if self.global_config.observers.logger.enabled:
            try:
                self.logger.debug("Creating enhanced logger observer")
                # Get log level from observer config if available, otherwise fallback to global log level
                log_level = (
                    self.global_config.observers.logger.log_level
                    if hasattr(self.global_config, "observers")
                    and hasattr(self.global_config.observers, "logger")
                    else logging.getLevelName(self.log_level)
                )

                factory.create_logger(
                    name="test_logger",
                    auto_register=True,
                    log_level=log_level,  # Use observer-specific log level
                    enable_colors=True,
                    output_file=str(self.test_experiment_dir / "event_log.log"),
                    correlation_tracking=True,
                    global_config=self.global_config,
                )
                self.registered_observers.append("test_logger")
                self.logger.debug("Registered enhanced logger observer")
            except Exception as e:
                self.logger.warning("Failed to create enhanced logger observer: %s. ", e)

        # Create and register enhanced metrics observer
        if self.global_config.observers.metrics.enabled:
            try:
                self.logger.info("Creating enhanced metrics observer")
                # Get metrics observer log level if available
                metrics_log_level = (
                    self.global_config.observers.metrics.log_level
                    if hasattr(self.global_config, "observers")
                    and hasattr(self.global_config.observers, "metrics")
                    else "INFO"
                )

                factory.create_metrics(
                    name="test_metrics",
                    auto_register=True,
                    publish_metrics=True,
                    collect_system_metrics=True,
                    publish_interval=30,
                    enable_real_time_monitoring=True,
                    log_level=metrics_log_level,  # Use observer-specific log level
                )
                self.registered_observers.append("test_metrics")
                self.logger.debug("Registered enhanced metrics observer")
            except Exception as e:
                self.logger.warning("Failed to create enhanced metrics observer: %s", e)

        # Create and register enhanced storage observer
        if self.global_config.observers.storage.enabled:
            try:
                self.logger.info("Creating enhanced storage observer")
                factory.create_storage(
                    name="test_storage",
                    auto_register=True,
                    storage_path=str(
                        self.test_experiment_dir
                    ),  # Changed output_dir to storage_path
                    enable_compression=True,  # Changed compression to enable_compression
                    auto_backup=True,
                    retention_days=30,
                    batch_size=100,
                    # Removed result_collectors as it's not in StorageObserver constructor
                )
                self.registered_observers.append("test_storage")
                self.logger.debug("Registered enhanced storage observer")
            except Exception as e:
                self.logger.warning("Failed to create enhanced storage observer: %s", e)
                # No fallback for storage as it requires ResultsManager integration

        # Create and register experiment observer (always enabled for tracking)
        try:
            self.logger.debug("Creating experiment observer")
            factory.create_experiment_observer(
                name="test_experiment",
                auto_register=True,
                output_dir=str(self.test_experiment_dir),
                test_name=self.test_name,
                track_timing=True,
                track_steps=True,
                global_config=self.global_config,
            )
            self.registered_observers.append("test_experiment")
            self.logger.debug("Registered experiment observer")
        except Exception as e:
            self.logger.warning("Failed to create experiment observer: %s.", e)

    def check_service_responsiveness(self, service_name: str, endpoint: str, expected_status: int):
        """
        Checks if a service's endpoint is responsive and returns the expected status code.

        Args:
            service_name (str): The name of the service to check.
            endpoint (str): The endpoint to check on the service.
            expected_status (int): The expected status code to be returned (default is 200).

        Raises:
            Exception: If the service is not responsive or returns a status code other than the expected.
        """
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
            self.logger.error("Service manager for '%s' not found.", service_name, exc_info=True)
            return

        # Assuming service manager provides the base URL or IP
        base_url = service_manager.get_base_url(service_name)
        url = urljoin(base_url, endpoint)
        self.logger.debug("Checking responsiveness of '%s' at '%s'", service_name, url)

        try:
            response = requests.get(url)
            if response.status_code == expected_status:
                self.logger.info(
                    "Assertion Passed: '%s' responded with status code %s.",
                    service_name,
                    expected_status,
                )
            else:
                self.logger.warning(
                    "Assertion Failed: '%s' responded with status code %s, expected %s.",
                    service_name,
                    response.status_code,
                    expected_status,
                )
                raise Exception(
                    f"Service {service_name} returned unexpected status code {response.status_code}"
                )
        except Exception as e:
            self.logger.error(
                "Assertion Failed: Could not reach '%s' at '%s': %s",
                service_name,
                url,
                e,
                exc_info=True,
            )
            raise Exception(f"Could not reach service {service_name} at {url}: {str(e)}")

    def _check_service_test_results(self):
        """
        Checks the results of the services tests by collecting test results from all tester services.

        This method iterates through all service managers, identifies testers, and collects their
        test results. It uses the event emitter to report progress and final results.

        Returns:
            bool: True if all service tests passed, False otherwise
        """
        self.logger.info("Checking service test results...")

        # Record the test result check through event system
        self.event_emitter.emit_step_progress(
            step_id="service_test_results",
            progress=0.9,  # Almost done with the test
            details={"status": "checking", "test_name": self.test_config.name},
        )

        # Initialize aggregated test results
        aggregated_results = {
            "tester_count": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_total": 0,
            "testers": {},
            "overall_success": True,
            "services_checked": len(self.service_managers),
        }

        # Iterate through service managers to check test results
        tester_count = 0

        for service_manager in self.service_managers:
            # Check if this service manager is a tester
            is_tester = (
                hasattr(service_manager, "is_tester")
                and callable(getattr(service_manager, "is_tester"))
                and service_manager.is_tester()
            )

            if not is_tester:
                self.logger.debug(
                    "Service manager '%s' is not a tester. Skipping.",
                    service_manager.get_implementation_name(),
                )
                continue

            tester_count += 1
            service_name = getattr(service_manager, "service_name", f"tester_{tester_count}")

            self.logger.debug("Collecting test results from tester: %s", service_name)

            # Report progress for current tester
            self.event_emitter.emit_step_progress(
                step_id="service_test_results",
                progress=0.9 + (0.1 * (tester_count / len(self.service_managers))),
                details={
                    "status": "checking_tester",
                    "tester": service_name,
                    "test_name": self.test_config.name,
                },
            )

            # Check if service has test results
            if hasattr(service_manager, "get_test_results") and callable(
                getattr(service_manager, "get_test_results")
            ):
                try:
                    # Get test results from the service
                    test_results = service_manager.get_test_results()

                    # Process the test results
                    if test_results:
                        # Initialize tester entry in results
                        service_success = False

                        # Different testers might return results in different formats
                        # Handle common formats or add custom handling for specific testers
                        if isinstance(test_results, bool):
                            # Simple pass/fail result
                            service_success = test_results
                            result_info = {
                                "passed": 1 if service_success else 0,
                                "failed": 0 if service_success else 1,
                            }
                        elif isinstance(test_results, dict):
                            # Dictionary with detailed results
                            # Example format: {"passed": 5, "failed": 2, "details": []}
                            passed_count = test_results.get("passed", 0)
                            failed_count = test_results.get("failed", 0)
                            service_success = failed_count == 0
                            result_info = {"passed": passed_count, "failed": failed_count}
                        elif isinstance(test_results, list):
                            # List of test results, count passes and failures
                            passed_count = sum(1 for r in test_results if r.get("passed", False))
                            failed_count = len(test_results) - passed_count
                            service_success = failed_count == 0
                            result_info = {"passed": passed_count, "failed": failed_count}
                        else:
                            # Unknown format, assume success for now but log a warning
                            self.logger.warning(
                                "Unknown test result format from %s: %s",
                                service_name,
                                type(test_results),
                            )
                            service_success = True
                            result_info = {"passed": 1, "failed": 0, "format_warning": True}

                        # Update aggregated results
                        aggregated_results["tests_passed"] += result_info.get("passed", 0)
                        aggregated_results["tests_failed"] += result_info.get("failed", 0)
                        aggregated_results["tests_total"] += result_info.get(
                            "passed", 0
                        ) + result_info.get("failed", 0)
                        aggregated_results["testers"][service_name] = {
                            "success": service_success,
                            **result_info,
                            "raw_results": test_results,
                        }

                        # If any tester fails, the overall test fails
                        if not service_success:
                            aggregated_results["overall_success"] = False

                        # Emit metric for this tester's results
                        self.event_emitter.emit_metric(
                            metric_type="test_results",
                            metric_name=f"{service_name}_tests_passed",
                            value=result_info.get("passed", 0),
                            test_id=self.test_config.name,
                            details={"tester": service_name, "service_success": service_success},
                        )

                        # Emit service test results event
                        self.event_emitter.emit_service_event(
                            name="service_test_results",
                            data={
                                "service_name": service_name,
                                "service_type": getattr(service_manager, "service_type", "tester"),
                                "success": service_success,
                                "results": result_info,
                            },
                        )
                    else:
                        # No test results available
                        self.logger.warning("No test results available from %s", service_name)
                        aggregated_results["testers"][service_name] = {
                            "success": False,
                            "passed": 0,
                            "failed": 0,
                            "error": "No test results available",
                        }
                except Exception as e:
                    # Error getting test results
                    self.logger.error("Error getting test results from %s: %s", service_name, e)
                    aggregated_results["testers"][service_name] = {
                        "success": False,
                        "passed": 0,
                        "failed": 0,
                        "error": str(e),
                    }
                    aggregated_results["overall_success"] = False

                    # Emit error event
                    self.event_emitter.emit_service_event(
                        name="service_test_error",
                        data={
                            "service_name": service_name,
                            "service_type": getattr(service_manager, "service_type", "tester"),
                            "error_type": "test_results_failed",
                            "error_message": str(e),
                        },
                    )
            else:
                self.logger.warning("Service %s does not provide test results", service_name)

        # Update tester count
        aggregated_results["tester_count"] = tester_count

        # If no testers were found, log a warning
        if tester_count == 0:
            self.logger.warning("No tester services found to check results")

        # Determine overall success status
        success = aggregated_results["overall_success"]

        # Emit completion metric
        self.event_emitter.emit_metric(
            metric_type="test_results",
            metric_name="total_tests_passed",
            value=aggregated_results["tests_passed"],
            test_id=self.test_config.name,
            details={
                "total_tests": aggregated_results["tests_total"],
                "total_failed": aggregated_results["tests_failed"],
            },
        )

        # Emit step completed event for service result checking
        self.event_emitter.emit_step_completed(
            step_id="service_test_results", success=success, result=aggregated_results
        )

        return success

    def _record_artifact_metrics(self):
        """
        Records metrics about artifacts generated during test execution.

        This is a placeholder method that would emit metrics about test artifacts.
        """
        self.logger.debug("Recording artifact metrics...")
        # Implementation would depend on what artifacts need to be measured
        # This is just a placeholder

    def save_test_metrics(self):
        """
        Saves metrics specific to this test case.

        This is a placeholder method that would save test-specific metrics.
        """
        self.logger.debug("Saving test metrics...")
        # Implementation would depend on what metrics need to be saved
        # This is just a placeholder

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
        try:
            self.state = "RUNNING"
            self.logger.info("Starting Test: %s", self.test_config.name)
            self.logger.info("Description:   %s", self.test_config.description)

            start_time = time.time()
            self._setup_observers()

            # Emit test execution started event according to workflow
            self.event_emitter.emit_test_execution_started(
                test_id=self.test_config.name, test_name=self.test_config.name
            )

            # Setup services with timing
            setup_services_start = time.time()
            self.setup_services()
            setup_services_duration = time.time() - setup_services_start

            # Emit timing metric event for service setup
            if self.metrics_collector:  # Check if metrics are enabled
                self.event_emitter.emit_timing_metric(
                    metric_name=f"setup_services_{self.test_name}",
                    duration_ms=int(setup_services_duration * 1000),
                    test_id=self.test_config.name,
                    details={"phase": "TEST_EXECUTION", "component": "test_case"},
                )

            # Setup environment with timing
            setup_env_start = time.time()
            self.setup_environment()
            setup_env_duration = time.time() - setup_env_start

            # Emit timing metric event for environment setup
            if self.metrics_collector:
                self.event_emitter.emit_timing_metric(
                    metric_name=f"setup_environment_{self.test_name}",
                    duration_ms=int(setup_env_duration * 1000),
                    test_id=self.test_config.name,
                    details={"phase": "TEST_EXECUTION", "component": "test_case"},
                )

            # Deploy services with timing
            deploy_services_start = time.time()
            self.deploy_services()
            deploy_services_duration = time.time() - deploy_services_start

            # Emit timing metric event for service deployment
            if self.metrics_collector:
                self.event_emitter.emit_timing_metric(
                    metric_name=f"deploy_services_{self.test_name}",
                    duration_ms=int(deploy_services_duration * 1000),
                    test_id=self.test_config.name,
                    details={"phase": "TEST_EXECUTION", "component": "test_case"},
                )

            # Execute steps with timing
            execute_steps_start = time.time()
            self.execute_steps()
            execute_steps_duration = time.time() - execute_steps_start

            # Emit timing metric event for steps execution
            if self.metrics_collector:
                self.event_emitter.emit_timing_metric(
                    metric_name=f"execute_steps_{self.test_name}",
                    duration_ms=int(execute_steps_duration * 1000),
                    test_id=self.test_config.name,
                    details={"phase": "TEST_EXECUTION", "component": "test_case"},
                )

            # Validate assertions with timing
            validate_assertions_start = time.time()
            self.validate_assertions()
            validate_assertions_duration = time.time() - validate_assertions_start

            # Emit timing metric event for assertions validation
            if self.metrics_collector:
                self.event_emitter.emit_timing_metric(
                    metric_name=f"validate_assertions_{self.test_name}",
                    duration_ms=int(validate_assertions_duration * 1000),
                    test_id=self.test_config.name,
                    details={"phase": "TEST_EXECUTION", "component": "test_case"},
                )

            # Check if service tests actually passed
            self._check_service_test_results()

            # Calculate total test duration
            total_duration = time.time() - start_time

            self.state = "DONE"
            self.logger.info("Test '%s' completed successfully.", self.test_config.name)

            if self.metrics_collector:
                # Emit timing metric for overall test case execution
                self.event_emitter.emit_timing_metric(
                    metric_name=f"test_case_total_{self.test_name}",
                    duration_ms=int(total_duration * 1000),
                    test_id=self.test_config.name,
                    details={"phase": "TEST_EXECUTION", "component": "test_case"},
                )

                # Record artifact metrics through event system
                self._record_artifact_metrics()
                # Save test-specific metrics
                self.save_test_metrics()

            # Use event emitter for test completion notification instead of direct event_manager
            self.event_emitter.emit_test_completed(
                test_id=self.test_config.name,
                success=True,
                result={"duration_ms": int(total_duration * 1000), "test_state": self.state},
            )

            # Emit test execution completed event according to workflow
            self.event_emitter.emit_test_execution_completed(
                test_id=self.test_config.name,
                test_name=self.test_config.name,
                success=True,
                results={"test_state": self.state},
                duration_ms=int(total_duration * 1000),
            )

        except Exception as e:
            self.state = "ERROR"

            if self.metrics_collector:
                # Emit error metric event using event emitter
                self.event_emitter.emit_metric(
                    metric_type="status",
                    metric_name="error",
                    value=0,  # 0 for error/failure
                    test_id=self.test_config.name,
                    details={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "test_phase": str(self.state),
                        "component": "test_case",
                    },
                )

            # Emit test failed event using event emitter
            self.event_emitter.emit_test_completed(
                test_id=self.test_config.name,
                success=False,
                result={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "test_phase": str(self.state),
                },
            )

            # Emit test execution failed event according to workflow
            self.event_emitter.emit_test_execution_failed(
                test_id=self.test_config.name,
                test_name=self.test_config.name,
                error_type=type(e).__name__,
                error_message=str(e),
                details={"test_phase": str(self.state), "component": "test_case"},
            )

            self.logger.error("Test '%s' failed: %s", self.test_config.name, e)
            raise
        finally:
            self.state = "COLLECTING"

            # Teardown environment with timing
            teardown_start = time.time()
            self.teardown_environment()
            teardown_duration = time.time() - teardown_start

            # Emit timing metric for teardown
            if self.metrics_collector:
                self.event_emitter.emit_timing_metric(
                    metric_name=f"teardown_environment_{self.test_name}",
                    duration_ms=int(teardown_duration * 1000),
                    test_id=self.test_config.name,
                    details={"phase": "TEST_EXECUTION", "component": "test_case"},
                )
            # Unregister observers
            factory = get_observer_factory()
            for observer in self.registered_observers:
                factory.unregister_observer(observer)
            self.logger.debug("Unregistered all observers after test completion")
