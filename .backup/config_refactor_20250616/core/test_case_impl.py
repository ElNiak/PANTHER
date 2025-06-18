import logging
import os
import re
import subprocess
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from urllib.parse import urljoin

import requests
from colorlog import ColoredFormatter

from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.events.emitter_registry import EmitterRegistry
from panther.core.exceptions.fast_fail import FastFailHandler, TimeoutCascadeException
from panther.core.observer.factory import get_observer_factory
from panther.core.observer.factory.factory_builders import (
    create_logger,
    create_metrics,
    create_storage,
)
from panther.core.observer.impl.experiment_observer import ExperimentObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.output_aggregator import OutputAggregator
from panther.core.results.result_collector import ResultCollector
from panther.core.results.result_handlers.storage_handler import StorageHandler
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.plugin_manager import PluginManager
from panther.plugins.services.iut.config_schema import ImplementationType
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.services.testers.tester_interface import ITesterManager


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
        emitter_registry=None,
        workflow_tracker=None,
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

        # Timeout cascade detection
        self.timeout_history: deque = deque(maxlen=10)  # Track last 10 timeouts
        self.log_level = getattr(
            logging, self.global_config.logging.level.name, logging.INFO
        )
        self.log_format = self.global_config.logging.format

        self.test_name = re.sub(r"[^a-zA-Z0-9_]", "_", test_config.name.strip())
        self.test_name = re.sub(
            r"_+", "_", self.test_name
        )  # Do not allow 2 "_" in a row
        self.test_experiment_dir = experiment_dir / self.test_name
        self._load_logging()
        self.logger.debug(
            "Creating test case '%s' with experiment directory '%s' and test configuration '%s'",
            self.test_name,
            self.test_experiment_dir,
            test_config,
        )

        self.result_collectors = ResultCollector()
        self.result_collectors.register_handler(
            f"storage_{self.test_name}", StorageHandler(experiment_dir, self.test_name)
        )

        self.service_managers: List[IServiceManager] = []

        self.environment_plugin_manager: List[IEnvironmentPlugin] = []
        # Always use the event_manager passed from the plugin_manager
        # This ensures a single EventManager is shared across the system
        if (
            not plugin_manager
            or not hasattr(plugin_manager, "event_manager")
            or plugin_manager.event_manager is None
        ):
            self.logger.warning(
                "No EventManager provided by plugin_manager, creating a new one. This may lead to event propagation issues."
            )
            self.event_manager = EventManager.get_instance()
        else:
            self.event_manager = plugin_manager.event_manager
            self.logger.debug("Using shared EventManager from plugin_manager")

        # Use provided emitter registry or create a new one
        if emitter_registry:
            self.emitter_registry = emitter_registry
            self.logger.debug("Using shared EmitterRegistry")
        else:
            # Initialize centralized emitter registry using shared event manager
            self.emitter_registry = EmitterRegistry(self.event_manager)
            self.logger.debug("Created new EmitterRegistry")

        # Access emitters through the registry
        self.test_emitter = self.emitter_registry.get_test_emitter(self.test_name)
        self.service_emitter = self.emitter_registry.service_emitter
        self.environment_emitter = self.emitter_registry.environment_emitter
        self.step_emitter = self.emitter_registry.step_emitter
        self.experiment_emitter = self.emitter_registry.experiment_emitter
        self.assertion_emitter = self.emitter_registry.assertion_emitter
        self.metrics_emitter = self.emitter_registry.metrics_emitter

        # Get workflow tracker for experiment coordination
        self.workflow_tracker = workflow_tracker

        net_environment_type = test_config.network_environment
        self.logger.info("Loading network environment: %s", net_environment_type)

        self.execution_environment = []
        self.plugin_manager = plugin_manager

        self.services = test_config.services

        # Initialize test-level fast-fail behavior
        self._init_fast_fail_handler(test_config, global_config)

        self._panther_dir = Path(os.path.dirname(__file__)).parent.parent.parent

        self.state: Literal["PENDING", "RUNNING", "COLLECTING", "DONE", "ERROR"] = (
            "PENDING"
        )

        self.registered_observers: List[str] = []

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

    def _init_fast_fail_handler(
        self, test_config: TestConfig, global_config: GlobalConfig
    ):
        """Initialize test-level fast-fail handler based on configuration."""
        fast_fail_config = global_config.fast_fail

        # Determine if fast-fail should be enabled for this test
        if fast_fail_config.test_level and test_config.fast_fail_enabled is not None:
            # Test-level override is active and test specifies its preference
            fast_fail_enabled = test_config.fast_fail_enabled
            self.logger.debug(
                "Using test-level fast-fail setting: %s for test '%s'",
                fast_fail_enabled,
                test_config.name,
            )
        else:
            # Use global setting
            fast_fail_enabled = fast_fail_config.enabled
            if fast_fail_config.test_level:
                self.logger.debug(
                    "Test-level fast-fail enabled but test '%s' has no override, using global: %s",
                    test_config.name,
                    fast_fail_enabled,
                )

        # Initialize fast-fail handler for this test
        self.fast_fail_handler = FastFailHandler(
            enabled=fast_fail_enabled, logger=self.logger
        )

        # Keep backward compatibility
        self._fail_on_error = fast_fail_enabled

        self.logger.debug(
            "Initialized fast-fail handler for test '%s': enabled=%s",
            test_config.name,
            fast_fail_enabled,
        )

    def deploy_services(self):
        """
        Deploys services through environment managers.
        This method iterates over the environment plugin managers and attempts to deploy services
        using each manager that is an instance of INetworkEnvironment. It logs the deployment process
        and notifies the event manager and observers upon successful deployment. If an error occurs during the
        deployment, it logs the error and raises the exception.

        Raises:
            Exception: If the deployment of services fails for any environment manager.
        """
        self.logger.info("Deploying services through environment managers")
        # Update service states to indicate deployment is starting
        for service_manager in self.service_managers:
            service_name = (
                service_manager.service_name
                if hasattr(service_manager, "service_name")
                else service_manager.get_implementation_name()
            )
            # State tracking happens through events
            self.logger.debug(f"Service '{service_name}' deployment starting")

        # Emit service deployment started event
        service_names = []
        service_metadata = []

        for s in self.service_managers:
            # Get service name
            service_name = (
                s.service_name
                if hasattr(s, "service_name")
                else s.get_implementation_name()
            )
            service_names.append(service_name)

            # Build metadata for each service
            metadata = {
                "service_type": (
                    s.get_service_type()
                    if hasattr(s, "get_service_type")
                    else s.service_config_to_test.implementation.type.value
                ),
                "implementation": (
                    s.get_implementation_name()
                    if hasattr(s, "get_implementation_name")
                    else s.service_config_to_test.implementation.name
                ),
                "config": {
                    "test_case": self.test_name,
                    "protocol": (
                        s.service_config_to_test.protocol.name
                        if hasattr(s.service_config_to_test, "protocol")
                        else "unknown"
                    ),
                    "role": (
                        s.service_config_to_test.protocol.role
                        if hasattr(s.service_config_to_test, "protocol")
                        and hasattr(s.service_config_to_test.protocol, "role")
                        else "unknown"
                    ),
                },
            }
            service_metadata.append(metadata)

        self.service_emitter.emit_service_setup_started(
            test_case=self.test_name,
            service_count=len(self.service_managers),
            service_names=service_names,
            service_metadata=service_metadata,
        )
        self.logger.debug("Emitted service_setup_started event")

        successful_deployment = False

        for env_manager in self.environment_plugin_manager:
            if isinstance(env_manager, INetworkEnvironment):
                env_name = f"{env_manager.__class__.__name__}_{self.test_name}"
                self.logger.info(
                    "Deploying services through environment manager: %s",
                    env_manager.__class__.__name__,
                )

                # Environment readiness is tracked by StateManager, not ExperimentObserver
                # Just proceed with deployment

                # Emit environment deployment started event
                self.environment_emitter.emit_environment_deployment_started(
                    environment_id=env_name,
                    environment_name=self.test_name,
                    environment_type=env_manager.__class__.__name__,
                    services=service_names,
                    deployment_config={"test_case": self.test_name},
                )
                self.logger.debug("Emitted environment_deployment_started event")

                if not env_manager.plugin_setup:
                    self.logger.error(f"Environment manager '{env_name}' not set up")
                    # State tracking happens through events
                    raise RuntimeError(
                        f"Environment manager {env_manager.__class__.__name__} not set up"
                    )

                try:
                    deployment_start_time = time.time()

                    # Deploy services through the network environment
                    env_manager.run()

                    # Mark deployment as successful
                    successful_deployment = True

                    # State tracking happens through events

                    # Update all service states to indicate they're deployed
                    for service_manager in self.service_managers:
                        service_name = (
                            service_manager.service_name
                            if hasattr(service_manager, "service_name")
                            else service_manager.get_implementation_name()
                        )
                        # State tracking happens through events
                        self.logger.debug(f"Service '{service_name}' deployed")

                    # Emit services deployed event
                    service_names = [
                        (
                            s.service_name
                            if hasattr(s, "service_name")
                            else s.get_implementation_name()
                        )
                        for s in self.service_managers
                    ]
                    service_instances = {
                        name: s for name, s in zip(service_names, self.service_managers)
                    }
                    self.service_emitter.emit_service_deployed(
                        environment=env_manager.__class__.__name__,
                        service_instances=service_instances,
                    )
                    self.logger.debug("Emitted service_deployed event")

                    # Calculate deployment duration and emit environment deployment completed event
                    deployment_duration = time.time() - deployment_start_time
                    deployed_services_dict = {
                        name: "deployed" for name in service_names
                    }

                    self.environment_emitter.emit_environment_deployment_completed(
                        environment_id=env_name,
                        environment_name=self.test_name,
                        environment_type=env_manager.__class__.__name__,
                        success=True,
                        deployed_services=deployed_services_dict,
                        duration=deployment_duration,
                        deployment_details={
                            "service_count": len(self.service_managers)
                        },
                    )
                    self.logger.debug("Emitted environment_deployment_completed event")

                    self.logger.info("Services successfully deployed")

                except FileNotFoundError as file_error:
                    self.logger.error(
                        "Service deployment failed due to missing file: %s",
                        str(file_error),
                    )

                    # Update environment and service states to failed
                    # State tracking happens through events
                    for service_manager in self.service_managers:
                        service_name = (
                            service_manager.service_name
                            if hasattr(service_manager, "service_name")
                            else service_manager.get_implementation_name()
                        )
                        # State tracking happens through events

                    # Emit specific file not found failure event for each service
                    for service_manager in self.service_managers:
                        service_name = (
                            service_manager.service_name
                            if hasattr(service_manager, "service_name")
                            else service_manager.get_implementation_name()
                        )
                        service_id = f"{self.test_name}_{service_name}"
                        self.service_emitter.emit_service_deployment_failed(
                            service_id=service_id,
                            service_name=service_name,
                            environment=env_manager.__class__.__name__,
                            error_message=str(file_error),
                            error_type="FileNotFoundError",
                        )
                    self.logger.debug(
                        "Emitted service_deployment_failed event for file not found"
                    )

                    # Emit environment deployment failed event
                    failed_services = [name for name in service_names]
                    self.environment_emitter.emit_environment_deployment_failed(
                        environment_id=env_name,
                        environment_name=self.test_name,
                        environment_type=env_manager.__class__.__name__,
                        error_message=str(file_error),
                        error_type="FileNotFoundError",
                        failed_services=failed_services,
                        error_details={"file_path": str(file_error)},
                    )
                    self.logger.debug(
                        "Emitted environment_deployment_failed event for file not found"
                    )

                    # Re-raise the exception
                    raise

                except Exception as e:
                    self.logger.error("Failed to deploy services: %s", e, exc_info=True)

                    # Update environment and service states to failed
                    # State tracking happens through events
                    for service_manager in self.service_managers:
                        service_name = (
                            service_manager.service_name
                            if hasattr(service_manager, "service_name")
                            else service_manager.get_implementation_name()
                        )
                        # State tracking happens through events

                    # Emit service deployment failure event for each service
                    for service_manager in self.service_managers:
                        service_name = (
                            service_manager.service_name
                            if hasattr(service_manager, "service_name")
                            else service_manager.get_implementation_name()
                        )
                        service_id = f"{self.test_name}_{service_name}"
                        self.service_emitter.emit_service_deployment_failed(
                            service_id=service_id,
                            service_name=service_name,
                            environment=env_manager.__class__.__name__,
                            error_message=str(e),
                            error_type=type(e).__name__,
                        )
                    self.logger.debug("Emitted service_deployment_failed event")

                    # Emit environment deployment failed event
                    failed_services = [name for name in service_names]
                    self.environment_emitter.emit_environment_deployment_failed(
                        environment_id=env_name,
                        environment_name=self.test_name,
                        environment_type=env_manager.__class__.__name__,
                        error_message=str(e),
                        error_type=type(e).__name__,
                        failed_services=failed_services,
                        error_details={"exception": str(e)},
                    )
                    self.logger.debug("Emitted environment_deployment_failed event")

                    # Re-raise the exception to be handled by the calling method
                    raise

        # If we get here with no successful deployment and no exceptions raised
        if not successful_deployment:
            self.logger.error(
                "No suitable network environment found for service deployment"
            )
            raise RuntimeError(
                "No suitable network environment found for service deployment"
            )

    def execute_steps(self):
        """
        Executes the defined steps of a test case.

        This method processes each step defined in the test configuration.
        Currently, it only handles 'wait' steps, but could be extended to support other step types.

        During execution, it periodically checks if the experiment should be finished early,
        and if so, it stops the execution and returns.
        """
        if not self.test_config.steps:
            self.logger.info(
                "No steps defined in test configuration, skipping step execution"
            )
            return

        self.logger.info("Executing steps: %s", self.test_config.steps)

        # Emit step execution started event using the typed event emitter
        step_names = list(self.test_config.steps.keys())
        self.step_emitter.emit_step_execution_started(
            step_id="execute_steps",
            step_name="Execute test steps",
            test_case_id=self.test_name,
            step_config={"steps": step_names},
        )
        try:
            for step_name, step_details in self.test_config.steps.items():
                # Check if the experiment should be finished early
                should_terminate = False
                for env_manager in self.environment_plugin_manager:
                    if hasattr(env_manager, "should_terminate_early") and callable(
                        env_manager.should_terminate_early
                    ):
                        should_terminate = env_manager.should_terminate_early()
                        if should_terminate:
                            self.logger.warning(
                                "Early termination requested by environment manager"
                            )
                            # Emit early termination event using the typed event emitter
                            self.experiment_emitter.emit_finished_early(
                                reason="Environment requested early termination",
                                details={
                                    "step": step_name,
                                    "environment": env_manager.__class__.__name__,
                                },
                            )
                            break

                if should_terminate:
                    break

                # Check for observers that might request early termination
                experiment_observer = self.event_manager.get_observer_by_type(
                    ExperimentObserver
                )
                if experiment_observer and hasattr(
                    experiment_observer, "should_terminate_early"
                ):
                    should_terminate = experiment_observer.should_terminate_early()
                    if should_terminate:
                        self.teardown_environment()
                        return

                # Handle different step types
                if step_name == "wait" and isinstance(step_details, (int, float)):
                    self.logger.info("Executing wait step for %s seconds", step_details)

                    # Emit step progress event before starting using the typed event emitter
                    self.step_emitter.emit_step_progress(
                        step_id=step_name,
                        step_name=step_name,
                        test_case_id=self.test_name,
                        progress_percentage=0.0,
                        progress_message=f"Starting wait for {step_details} seconds",
                    )

                    # Split the wait into smaller intervals to allow checking for early termination
                    interval = min(
                        1.0, step_details / 10.0
                    )  # Check at least 10 times during wait
                    wait_time_remaining = step_details
                    while wait_time_remaining > 0:
                        # Calculate wait time for this iteration
                        iteration_wait = min(interval, wait_time_remaining)

                        # Sleep for the calculated interval
                        time.sleep(iteration_wait)
                        wait_time_remaining -= iteration_wait

                        # Calculate progress percentage
                        progress_percentage = (
                            (step_details - wait_time_remaining) / step_details
                        ) * 100

                        # Emit progress event using the typed event emitter
                        self.step_emitter.emit_step_progress(
                            step_id=step_name,
                            step_name=step_name,
                            test_case_id=self.test_name,
                            progress_percentage=progress_percentage,
                            progress_message=f"Waiting: {wait_time_remaining:.1f} seconds remaining",
                        )

                        # Check for early termination
                        should_terminate = False
                        for env_manager in self.environment_plugin_manager:
                            if hasattr(
                                env_manager, "should_terminate_early"
                            ) and callable(env_manager.should_terminate_early):
                                should_terminate = env_manager.should_terminate_early()
                                if should_terminate:
                                    self.teardown_environment()
                                    return

                    # Emit step completed event using the typed event emitter
                    result = {
                        "completed": not should_terminate,
                        "duration_s": (
                            step_details - wait_time_remaining
                            if should_terminate
                            else step_details
                        ),
                    }
                    self.step_emitter.emit_step_execution_completed(
                        step_id=step_name,
                        step_name=step_name,
                        test_case_id=self.test_name,
                        duration=result.get("duration_s"),
                        result=result,
                    )

                    if should_terminate:
                        break
                else:
                    self.logger.warning(
                        "Unknown step type: %s = %s", step_name, step_details
                    )
                    # Emit unsupported step event using the typed event emitter
                    self.step_emitter.emit_step_unsupported(
                        step_id=step_name,
                        step_name=step_name,
                        test_case_id=self.test_name,
                        reason=f"Unsupported step type: {step_name} = {step_details}",
                    )
        except Exception as e:
            self.logger.error("Error occurred during step execution: %s", e)
        finally:
            # Emit step execution completed event using the typed event emitter
            self.step_emitter.emit_step_execution_completed(
                step_id="execute_steps",
                step_name="Execute test steps",
                test_case_id=self.test_name,
                result={"completed_steps": list(self.test_config.steps.keys())},
            )

    def setup_services(self):
        """
        Sets up the services based on the test configuration.

        This method iterates through the defined services in the test configuration and sets up
        implementation and tester services as required. It emits events for service setup
        progress and completion. It also registers services with observers for better coordination.

        Raises:
            Exception: If service setup fails.
        """
        self.logger.info("Setting up services based on test configuration")

        # Emit workflow-level command generation started event to trigger state transition
        # This should happen before service setup to ensure proper workflow state management
        self.service_emitter.emit_command_generation_started(
            service_id="workflow_setup",
            service_name="Command Generation Workflow",
            phase="setup",
            config={"test_case": self.test_name, "service_count": len(self.services)},
        )

        # Emit service setup started event using the typed event emitter
        service_names = list(self.services.keys())
        service_metadata = []

        # Build metadata from service configurations
        for service_name, service_config in self.services.items():
            metadata = {
                "service_type": (
                    service_config.implementation.type.value
                    if hasattr(service_config.implementation, "type")
                    else "unknown"
                ),
                "implementation": (
                    service_config.implementation.name
                    if hasattr(service_config.implementation, "name")
                    else "unknown"
                ),
                "config": {
                    "test_case": self.test_name,
                    "protocol": (
                        service_config.protocol.name
                        if hasattr(service_config, "protocol")
                        else "unknown"
                    ),
                    "role": (
                        service_config.protocol.role
                        if hasattr(service_config, "protocol")
                        and hasattr(service_config.protocol, "role")
                        else "unknown"
                    ),
                },
            }
            service_metadata.append(metadata)

        self.service_emitter.emit_service_setup_started(
            test_case=self.test_name,
            service_count=len(self.services),
            service_names=service_names,
            service_metadata=service_metadata,
        )

        # Initialize the list of service managers
        self.service_managers = []

        try:
            # Set up the testers first if defined
            self.setup_testers()

            # Set up the implementations
            self.setup_implementations()

            # Services are tracked through events, no need for direct registration
            for service_manager in self.service_managers:
                service_name = (
                    service_manager.service_name
                    if hasattr(service_manager, "service_name")
                    else service_manager.get_implementation_name()
                )
                # State is managed by StateManager, not through direct updates
                self.logger.debug(f"Service '{service_name}' initialized")

            # Emit service setup completed event using the typed event emitter
            self.service_emitter.emit_service_setup_completed(
                test_case=self.test_name,
                services=[
                    sm.name if hasattr(sm, "name") else sm.get_implementation_name()
                    for sm in self.service_managers
                ],
                success=True,
            )

        except Exception as e:
            # Emit service setup failed event using the typed event emitter
            self.service_emitter.emit_service_setup_failed(
                test_case=self.test_name,
                error_message=str(e),
                error_type=type(e).__name__,
            )
            self.logger.error("Service setup failed: %s", e, exc_info=True)
            raise

    def prepare_services(self):
        """
        Prepares all service managers by calling their prepare() method to build Docker images.

        This method should be called after setup_services() but before setup_environment()
        to ensure Docker images are built when build_docker_image is enabled.
        """
        self.logger.info("Preparing services (building Docker images if required)")

        if not hasattr(self, "service_managers") or not self.service_managers:
            # Check if services are actually configured
            if hasattr(self, "services") and self.services:
                self.logger.warning(
                    "Services are configured but no service managers were created. Check plugin paths and service configurations."
                )
                self.logger.debug(
                    "Configured services: %s",
                    list(self.services.keys()) if self.services else "None",
                )
            else:
                self.logger.debug("No services configured for this test")
            return

        # Reset base image flag for this test run to ensure base image is built once per experiment
        from panther.core.docker_builder.service_manager_docker_mixin import (
            ServiceManagerDockerMixin,
        )

        ServiceManagerDockerMixin.reset_base_image_flag()
        self.logger.debug("Reset base Docker image flag for new test run")

        plugin_manager = self.plugin_manager

        for service_manager in self.service_managers:
            try:
                service_name = (
                    service_manager.service_name
                    if hasattr(service_manager, "service_name")
                    else service_manager.get_implementation_name()
                )

                self.logger.debug("Preparing service manager: %s", service_name)

                # Call prepare method if it exists
                if hasattr(service_manager, "prepare") and callable(
                    getattr(service_manager, "prepare")
                ):
                    service_manager.prepare(plugin_manager)
                    self.logger.debug("Successfully prepared service: %s", service_name)
                else:
                    self.logger.debug(
                        "Service manager %s has no prepare method, skipping",
                        service_name,
                    )

            except Exception as e:
                self.logger.error(
                    "Failed to prepare service manager %s: %s",
                    service_name if "service_name" in locals() else "unknown",
                    e,
                    exc_info=True,
                )
                raise

    def setup_testers(self):
        """
        Sets up the testers based on the services details extracted from the test configuration file.

        This method performs the following steps:
        - Extracts the required testers from the services details.
        - Uses the plugin catalog to discover available testers.
        - Creates a list of service managers that will be used to deploy the services.

        The method logs the progress and any issues encountered during the setup process.
        """
        self.logger.debug("Setup Testers plugins ...")

        # Get available testers using the plugin catalog
        if hasattr(self.plugin_manager, "get_testers"):
            self.available_testers = self.plugin_manager.get_testers()
        else:
            self.available_testers = []

        self.logger.debug(
            "Available testers from plugin catalog: %s", self.available_testers
        )
        self.test_defined_testers = [
            service_details
            for service_details in self.services.values()
            if service_details.implementation.type == ImplementationType.TESTERS
        ]

        if len(self.test_defined_testers) == 0:
            self.logger.warning("No testers specified in the test configuration.")
            return

        self.logger.debug("Test defined testers: %s", self.test_defined_testers)

        # Process each tester using the plugin catalog
        for tester_config in self.test_defined_testers:
            tester_name = tester_config.implementation.name

            # Use plugin catalog to find the tester
            plugin_id = f"tester:{tester_name}"
            plugin_manifest = self.plugin_manager.plugin_catalog.catalog.get(plugin_id)

            if plugin_manifest and tester_name in self.available_testers:
                # Get implementation directory from the manifest
                implementation_dir = (
                    Path(plugin_manifest.file_path)
                    if plugin_manifest.file_path
                    else None
                )

                if implementation_dir:
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
                        event_manager=self.event_manager,  # Pass event_manager to avoid duplicate emitters
                        emitter_registry=self.emitter_registry,  # Pass EmitterRegistry for state-aware events
                    )

                    # Set test context if the service manager supports it
                    if hasattr(service_manager, "set_test_context"):
                        service_manager.set_test_context(self.test_name)
                    self.service_managers.append(service_manager)
                    self.logger.debug(
                        "Added service manager for tester '%s' under protocol '%s'",
                        tester_config.name,
                        tester_config.protocol.name,
                    )
                else:
                    self.logger.error(
                        "Tester plugin manifest found for '%s' but no file path available",
                        tester_name,
                    )
            else:
                self.logger.warning(
                    "Tester plugin not found: %s (available: %s)",
                    plugin_id,
                    self.available_testers,
                )

                # Emit tester plugin not found event for better debugging
                if hasattr(self, "plugin_emitter"):
                    self.plugin_emitter.emit_plugin_loading_failed(
                        plugin_id=plugin_id,
                        plugin_name=tester_name,
                        plugin_type="tester",
                        error_message=f"Tester plugin not found: {tester_name}",
                        error_details={"available_testers": self.available_testers},
                    )

    def setup_implementations(self):
        """
        Sets up the implementations for the services defined in the test configuration file.

        This method performs the following steps:
        - Extracts the required implementations from the services details.
        - Uses the plugin catalog to discover available IUT implementations.
        - Creates a list of service managers that will be used to deploy the services.

        The method logs the progress and details at each step, including:
        - The implementations available from the plugin catalog.
        - The implementations defined in the test configuration.
        - The details of each service and its implementation.
        - The creation of service managers for each implementation under the respective protocol.

        If a protocol plugin or an implementation is not found, appropriate warnings are logged.
        """
        self.logger.debug("Setup Implementation Under Tests plugins ...")

        # Get available protocols and implementations from plugin catalog

        # Extract protocol names from IUT plugins in catalog
        self.available_protocols = []
        self.available_implementations_per_protocol = {}

        for plugin_id, manifest in self.plugin_manager.plugin_catalog.catalog.items():
            if manifest.type.value == "iut":
                for protocol in manifest.supported_protocols:
                    if protocol not in self.available_protocols:
                        self.available_protocols.append(protocol)
                    if protocol not in self.available_implementations_per_protocol:
                        self.available_implementations_per_protocol[protocol] = []
                    self.available_implementations_per_protocol[protocol].append(
                        manifest.name
                    )

        self.logger.debug(
            "Available protocols from plugin catalog: %s", self.available_protocols
        )
        self.logger.debug(
            "Available implementations per protocol: %s",
            self.available_implementations_per_protocol,
        )

        # Get implementations defined in the test
        self.test_defined_implementation = [
            service_details
            for service_details in self.services.values()
            if service_details.implementation.type == ImplementationType.IUT
        ]

        self.logger.debug(
            "Test defined implementations: %s", self.test_defined_implementation
        )

        # Process each implementation using the plugin catalog
        for implementation_config in self.test_defined_implementation:
            protocol_name = implementation_config.protocol.name
            impl_name = implementation_config.implementation.name

            # Use plugin catalog to find the implementation
            plugin_id = f"iut:{impl_name}"
            plugin_manifest = self.plugin_manager.plugin_catalog.catalog.get(plugin_id)

            if plugin_manifest and protocol_name in plugin_manifest.supported_protocols:
                # Get implementation directory from the manifest
                implementation_dir = (
                    Path(plugin_manifest.file_path)
                    if plugin_manifest.file_path
                    else None
                )

                if implementation_dir:
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
                        event_manager=self.event_manager,  # Pass event_manager to avoid duplicate emitters
                        emitter_registry=self.emitter_registry,  # Pass EmitterRegistry for state-aware events
                    )

                    # Set test context if the service manager supports it
                    if hasattr(service_manager, "set_test_context"):
                        service_manager.set_test_context(self.test_name)
                    self.service_managers.append(service_manager)
                    self.logger.debug(
                        "Added service manager for implementation '%s' under protocol '%s'",
                        implementation_config,
                        implementation_config.protocol,
                    )
                else:
                    self.logger.error(
                        "IUT plugin manifest found for '%s' but no file path available",
                        impl_name,
                    )
            else:
                self.logger.warning(
                    "IUT plugin not found: %s for protocol %s (available implementations for %s: %s)",
                    plugin_id,
                    protocol_name,
                    protocol_name,
                    self.available_implementations_per_protocol.get(protocol_name, []),
                )

                # Emit IUT plugin not found event for better debugging
                if hasattr(self, "plugin_emitter"):
                    self.plugin_emitter.emit_plugin_loading_failed(
                        plugin_id=plugin_id,
                        plugin_name=impl_name,
                        plugin_type="iut",
                        error_message=f"IUT plugin not found: {impl_name} for protocol {protocol_name}",
                        error_details={
                            "protocol": protocol_name,
                            "available_for_protocol": self.available_implementations_per_protocol.get(
                                protocol_name, []
                            ),
                        },
                    )

    def validate_assertions(self):
        pass

    def setup_environment(self):
        """
        Sets up the test environment using the appropriate environment plugins.

        This method configures and initializes the network environment and execution environments
        based on the test configuration. It emits events for environment setup progress and completion.
        It also directly registers environments with observers for better coordination.

        Raises:
            Exception: If environment setup fails.
        """
        self.logger.info("Setting up environment based on test configuration")

        # TODO; should these event emitted from the environment themself ? same for service etc.
        # First emit environment created event
        env_id = f"{self.test_config.network_environment.type}_{self.test_name}"
        self.environment_emitter.emit_environment_created(
            environment_id=env_id,
            environment_name=self.test_name,
            environment_type=self.test_config.network_environment.type,
            environment_config={"test_case": self.test_name},
        )

        # Then emit environment setup started event using the typed event emitter
        self.environment_emitter.emit_environment_setup_started(
            environment_id=env_id,
            environment_name=self.test_name,
            environment_type=self.test_config.network_environment.type,
            setup_config={"test_case": self.test_name},
        )

        try:
            # Get the network environment plugin
            network_environment_plugin = (
                self.plugin_manager.get_network_environment_plugin(
                    self.test_config.network_environment.type
                )
            )

            if not network_environment_plugin:
                raise ValueError(
                    f"Network environment plugin not found for type: {self.test_config.network_environment.type}"
                )

            # Initialize the network environment
            self.logger.info(
                "Initializing network environment: %s",
                network_environment_plugin.__class__.__name__,
            )

            # Ensure we're passing a string for output_dir, not a Path object
            output_dir = (
                str(self.test_experiment_dir)
                if isinstance(self.test_experiment_dir, Path)
                else self.test_experiment_dir
            )

            # No need to register with observers - they observe through events
            env_name = (
                f"{network_environment_plugin.__class__.__name__}_{self.test_name}"
            )
            # State tracking happens through events

            # Call initialize method on the plugin
            network_environment_plugin.initialize(
                self.test_config,
                self.test_experiment_dir,
                self.event_manager,
                self.global_config,
            )

            # Add to list of environment plugins
            self.environment_plugin_manager.append(network_environment_plugin)

            # State tracking happens through events

            # Emit network environment initialized event using the typed event emitter
            self.environment_emitter.emit_environment_initialized(
                environment_type=self.test_config.network_environment.type,
                environment_name=self.test_name,
                config={"plugin_name": network_environment_plugin.name},
            )

            # Get the execution environment plugins if defined
            execution_environments = []
            if self.test_config.execution_environments:
                self.logger.info(
                    "Setting up execution environments: %s",
                    self.test_config.execution_environments,
                )

                for env_config in self.test_config.execution_environments:
                    env_type = env_config.type
                    self.logger.info(
                        "Getting execution environment plugin: %s", env_type
                    )

                    execution_environment_plugin = (
                        self.plugin_manager.get_execution_environment_plugin(
                            env_type,
                            output_dir=str(self.test_experiment_dir),
                            event_manager=self.event_manager,
                        )
                    )

                    if not execution_environment_plugin:
                        self.logger.warning(
                            "Execution environment plugin not found for type: %s",
                            env_type,
                        )
                        continue

                    # Register execution environment with observers for tracking
                    exec_env_name = f"{execution_environment_plugin.__class__.__name__}_{self.test_name}"
                    # No need to register with observers - they observe through events
                    # State tracking happens through events

                    # Initialize the execution environment
                    # self.logger.info( USLESS
                    #     "Initializing execution environment: %s",
                    #     execution_environment_plugin.name,
                    # )

                    # Add to list of environment plugins
                    self.environment_plugin_manager.append(execution_environment_plugin)
                    execution_environments.append(execution_environment_plugin)

                    # Emit execution environment initialized event using the typed event emitter
                    self.environment_emitter.emit_environment_initialized(
                        environment_type="execution",
                        environment_name=exec_env_name,
                        config={
                            "plugin_name": execution_environment_plugin.name,
                            "plugin_type": env_type,
                        },
                    )

            # Setup network environment with timestamp and verify files
            if isinstance(network_environment_plugin, INetworkEnvironment):
                self.logger.info("Setting up network environment with service managers")
                try:
                    # Use current timestamp for the Network Env file naming
                    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

                    # Call setup_environment method with all required parameters
                    network_environment_plugin.setup_environment(
                        services_managers=self.service_managers,
                        test_config=self.test_config,
                        global_config=self.global_config,
                        timestamp=timestamp,
                        plugin_manager=self.plugin_manager,
                        execution_environment=execution_environments,
                    )

                    # Verify the environment is actually ready by checking for required files
                    self.logger.info(
                        "Verifying network environment setup completed successfully"
                    )

                    self.logger.info(
                        f"Environment {env_name} setup completed successfully"
                    )
                    if hasattr(
                        network_environment_plugin,
                        "rendered_services_network_config_file_path",
                    ):
                        self.logger.info(
                            f"Network Env file created at: {network_environment_plugin.rendered_services_network_config_file_path}"
                        )

                except Exception as setup_error:
                    self.logger.error(
                        "Network environment setup failed: %s",
                        setup_error,
                        exc_info=True,
                    )
                    # State tracking happens through events

                    # Emit environment setup failed event with detailed error information
                    self.environment_emitter.emit_environment_setup_failed(
                        environment_id=f"{self.test_config.network_environment.type}_{self.test_name}",
                        environment_name=self.test_name,
                        environment_type=self.test_config.network_environment.type,
                        error_message=str(setup_error),
                        error_type=type(setup_error).__name__,
                    )
                    raise setup_error

            # Emit environment setup completed event using the typed event emitter
            execution_env_names = [
                plugin.name
                for plugin in self.environment_plugin_manager
                if plugin != network_environment_plugin
            ]
            self.environment_emitter.emit_environment_setup_completed(
                environment_id=f"{self.test_config.network_environment.type}_{self.test_name}",
                environment_name=self.test_name,
                environment_type=self.test_config.network_environment.type,
                setup_details={
                    "network_environment": network_environment_plugin.name,
                    "execution_environments": execution_env_names,
                    "test_case": self.test_name,  # Add test case name to setup details
                },
            )

        except Exception as e:
            # Emit environment setup failed event using the typed event emitter
            self.environment_emitter.emit_environment_setup_failed(
                environment_id=f"{self.test_config.network_environment.type}_{self.test_name}",
                environment_name=self.test_name,
                environment_type=self.test_config.network_environment.type,
                error_message=str(e),
                error_type=type(e).__name__,
            )
            self.logger.error("Environment setup failed: %s", e, exc_info=True)
            raise

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
                        "Test environment torn down via '%s'",
                        env_manager.__class__.__name__,
                    )
                    # Use the typed event emitter for environment teardown event
                    self.environment_emitter.emit_environment_teardown_completed(
                        environment_id=f"{env_manager.__class__.__name__}_{self.test_name}",
                        environment_name=self.test_name,
                        environment_type=env_manager.__class__.__name__,
                        cleanup_details={"test_name": self.test_config.name},
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
        """Load and configure logging for the test case."""
        # Set up the logger
        self.logger = logging.getLogger(self.test_name)
        self.logger.setLevel(self.log_level)

        # Configure formatter based on color preference
        if getattr(self.global_config.logging, "enable_colors", True):
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
                style="%",
            )
        else:
            formatter = logging.Formatter(self.log_format, datefmt="%Y-%m-%d %H:%M:%S")

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

        # Add console handler for colored output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)

        # Add both handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

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

        Each observer is created with proper error handling.
        """
        self.logger.debug("Registering default observers using enhanced registry")

        # Get the observer factory
        factory = get_observer_factory()

        # Ensure output directory exists
        if not self.test_experiment_dir.exists():
            self.test_experiment_dir.mkdir(parents=True, exist_ok=True)

        # Create and register enhanced logger observer (test-scoped)
        if self.global_config.observers.logger.enabled:
            try:
                logger_id = f"test_logger_{self.test_name}"

                # Check if observer already exists to prevent duplication
                if not self.event_manager.has_observer(logger_id):
                    self.logger.debug("Creating enhanced logger observer")
                    # Get log level from observer config if available, otherwise fallback to global log level
                    log_level = (
                        self.global_config.observers.logger.log_level
                        if hasattr(self.global_config, "observers")
                        and hasattr(self.global_config.observers, "logger")
                        else logging.getLevelName(self.log_level)
                    )

                    observer = create_logger(
                        name=logger_id,
                        global_config=self.global_config,
                        auto_register=False,  # We handle registration manually
                        log_level=log_level,  # Use observer-specific log level
                        enable_colors=True,
                        output_file=str(self.test_experiment_dir / "event_log.log"),
                        correlation_tracking=True,
                    )

                    # Register the created observer with scope tracking
                    self.event_manager.register_observer_once(
                        observer=observer,
                        observer_id=logger_id,
                        scope="test",
                        event_types=None,
                        priority=0,
                    )

                    self.registered_observers.append(logger_id)
                    self.logger.debug(
                        "Registered enhanced logger observer with scope tracking"
                    )
                else:
                    self.logger.debug(
                        "Logger observer already exists, reusing existing instance"
                    )

            except Exception as e:
                self.logger.warning(
                    "Failed to create enhanced logger observer: %s. ", e
                )

        # Create and register enhanced metrics observer (test-scoped)
        if self.global_config.observers.metrics.enabled:
            try:
                metrics_id = f"test_metrics_{self.test_name}"

                # Check if observer already exists to prevent duplication
                if not self.event_manager.has_observer(metrics_id):
                    self.logger.info("Creating enhanced metrics observer")
                    # Get metrics observer log level if available
                    metrics_log_level = (
                        self.global_config.observers.metrics.log_level
                        if hasattr(self.global_config, "observers")
                        and hasattr(self.global_config.observers, "metrics")
                        else "INFO"
                    )

                    # Ensure metrics directory exists
                    metrics_dir = self.test_experiment_dir / "metrics"
                    metrics_dir.mkdir(parents=True, exist_ok=True)

                    observer = create_metrics(
                        name=metrics_id,
                        global_config=self.global_config,
                        auto_register=False,  # We handle registration manually
                        publish_metrics=True,
                        collect_system_metrics=True,
                        output_dir=str(metrics_dir),
                        publish_interval=30,
                        enable_real_time_monitoring=True,
                        log_level=metrics_log_level,  # Use observer-specific log level
                    )

                    # Register the created observer with scope tracking
                    self.event_manager.register_observer_once(
                        observer=observer,
                        observer_id=metrics_id,
                        scope="test",
                        event_types=None,
                        priority=10,
                    )

                    self.registered_observers.append(metrics_id)
                    self.logger.debug(
                        "Registered enhanced metrics observer with scope tracking"
                    )
                else:
                    self.logger.debug(
                        "Metrics observer already exists, reusing existing instance"
                    )

            except Exception as e:
                self.logger.warning("Failed to create enhanced metrics observer: %s", e)

        # Create and register enhanced storage observer (test-scoped)
        if self.global_config.observers.storage.enabled:
            try:
                storage_id = f"test_storage_{self.test_name}"

                # Check if observer already exists to prevent duplication
                if not self.event_manager.has_observer(storage_id):
                    self.logger.info("Creating enhanced storage observer")
                    observer = create_storage(
                        name=storage_id,
                        global_config=self.global_config,
                        auto_register=False,  # We handle registration manually
                        storage_path=str(
                            self.test_experiment_dir
                        ),  # Changed output_dir to storage_path
                        enable_compression=True,  # Changed compression to enable_compression
                        auto_backup=True,
                        retention_days=30,
                        batch_size=100,
                        # Removed result_collectors as it's not in StorageObserver constructor
                    )

                    # Register the created observer with scope tracking
                    self.event_manager.register_observer_once(
                        observer=observer,
                        observer_id=storage_id,
                        scope="test",
                        event_types=None,
                        priority=20,
                    )

                    self.registered_observers.append(storage_id)
                    self.logger.debug(
                        "Registered enhanced storage observer with scope tracking"
                    )
                else:
                    self.logger.debug(
                        "Storage observer already exists, reusing existing instance"
                    )

            except Exception as e:
                self.logger.warning("Failed to create enhanced storage observer: %s", e)
                # No fallback for storage as it requires ResultsManager integration

        # Note: ExperimentObserver is registered at the experiment level to avoid duplication.
        # Individual test cases should not create their own ExperimentObserver instances.
        self.logger.debug(
            "ExperimentObserver is managed at experiment level - no test-level observer needed"
        )

    def _run_tester_analysis(self) -> bool:
        """
        Run analysis on collected outputs using tester service managers.

        This method identifies tester service managers and provides them with
        collected outputs for analysis to determine test outcomes.

        Returns:
            bool: True if all tester analyses passed, False otherwise
        """
        self.logger.info("Starting tester analysis phase")
        start_time = time.time()
        analysis_results = []
        all_passed = True

        self.organized_outputs = self._collect_outputs()

        try:
            # Get organized outputs (should be set by _collect_outputs)
            if not hasattr(self, "organized_outputs"):
                self.logger.warning(
                    "No organized outputs available for tester analysis"
                )
                return True  # Don't fail the test if no outputs to analyze

            # Find all tester service managers
            tester_managers = []
            for service_manager in self.service_managers:
                if isinstance(service_manager, ITesterManager):
                    tester_managers.append(service_manager)

            if not tester_managers:
                self.logger.info("No tester service managers found, skipping analysis")
                return True

            self.logger.info(
                f"Found {len(tester_managers)} tester service managers for analysis"
            )

            # Run analysis for each tester
            for tester in tester_managers:
                tester_name = getattr(tester, "service_name", tester.__class__.__name__)
                self.logger.info(f"Running analysis with tester: {tester_name}")

                try:
                    tester_start_time = time.time()

                    # Emit tester analysis started event
                    self.service_emitter.emit_tester_analysis_started(
                        service_id=f"{self.test_name}_{tester_name}",
                        service_name=tester_name,
                        test_name=self.test_name,
                        output_types=list(self.organized_outputs.keys()),
                        tester_config={},
                    )

                    # Provide collected outputs to the tester
                    tester.set_collected_outputs(self.organized_outputs)

                    # Run the analysis
                    analysis_result = tester.analyze_outputs()

                    # Get final test results from the tester
                    test_results = tester.get_test_results()

                    # Store results
                    analysis_results.append(
                        {
                            "tester_name": tester_name,
                            "analysis_result": analysis_result,
                            "test_results": test_results,
                            "passed": test_results.get("passed", False),
                        }
                    )

                    # Update overall pass status
                    if not test_results.get("passed", False):
                        all_passed = False
                        self.logger.warning(
                            f"Tester {tester_name} analysis failed: {test_results.get('summary', 'No summary')}"
                        )
                    else:
                        self.logger.info(
                            f"Tester {tester_name} analysis passed: {test_results.get('summary', 'No summary')}"
                        )

                    # Calculate actual duration
                    tester_duration = time.time() - tester_start_time

                    # Emit tester analysis completed event
                    self.service_emitter.emit_tester_analysis_completed(
                        service_id=f"{self.test_name}_{tester_name}",
                        service_name=tester_name,
                        test_name=self.test_name,
                        analysis_passed=test_results.get("passed", False),
                        findings=analysis_result,
                        summary=test_results.get("summary", ""),
                        duration=tester_duration,
                    )

                except Exception as e:
                    self.logger.error(
                        f"Error running analysis with tester {tester_name}: {e}",
                        exc_info=True,
                    )

                    # Mark this tester as failed
                    analysis_results.append(
                        {
                            "tester_name": tester_name,
                            "analysis_result": {"passed": False, "error": str(e)},
                            "test_results": {
                                "passed": False,
                                "summary": f"Analysis error: {str(e)}",
                            },
                            "passed": False,
                        }
                    )
                    all_passed = False

            # Store analysis results for potential later use
            self.analysis_results = analysis_results

            analysis_duration = time.time() - start_time

            # Emit timing metric for tester analysis
            if self.metrics_collector:
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"tester_analysis_{self.test_name}",
                    duration=analysis_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            # Emit summary of analysis results
            passed_count = sum(1 for result in analysis_results if result["passed"])
            failed_count = len(analysis_results) - passed_count

            self.logger.info(
                f"Tester analysis completed in {analysis_duration:.2f}s. Results: {passed_count} passed, {failed_count} failed"
            )

            return all_passed

        except Exception as e:
            self.logger.error(f"Failed to run tester analysis: {e}", exc_info=True)
            return False

    def _collect_outputs(self) -> Dict[str, Dict[str, str]]:
        """
        Collect outputs from all execution environments for analysis.

        This method aggregates outputs from execution environments that implement
        IOutputCollector and prepares them for tester analysis.

        Returns:
            Dict[str, Dict[str, str]]: Collected outputs organized by type
        """
        self.logger.info("Starting output collection phase")

        start_time = time.time()

        try:
            # Create output aggregator
            aggregator = OutputAggregator(
                experiment_dir=self.test_experiment_dir,
                environment_emitter=self.emitter_registry.environment_emitter,
            )

            # Collect outputs from all environments (both network and execution environments)
            all_environments = self.environment_plugin_manager.copy()

            # Debug: Log which environments we're attempting to collect from
            self.logger.info(
                f"Attempting output collection from {len(all_environments)} environments:"
            )
            for env in all_environments:
                env_type = env.__class__.__name__
                implements_collector = hasattr(env, "collect_outputs") and hasattr(
                    env, "get_output_metadata"
                )
                self.logger.info(
                    f"  - {env_type} (implements IOutputCollector: {implements_collector})"
                )

            collected_outputs = aggregator.collect_from_environments(all_environments)

            # Prepare outputs for testers (reorganize by output type)
            organized_outputs = aggregator.prepare_for_testers(collected_outputs)

            # Store collected outputs for potential later use
            self.collected_outputs = collected_outputs
            self.organized_outputs = organized_outputs

            collection_duration = time.time() - start_time

            # Emit timing metric for output collection
            if self.metrics_collector:
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"collect_outputs_{self.test_name}",
                    duration=collection_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            self.logger.info(
                f"Output collection completed in {collection_duration:.2f}s"
            )
            return organized_outputs

        except Exception as e:
            self.logger.error(f"Failed to collect outputs: {e}", exc_info=True)

            # Emit error event
            self.environment_emitter.emit_output_collection_failed(
                environment_id="all_environments",
                environment_name="Output Collection",
                environment_type="aggregator",
                error_message=str(e),
            )

            # Return empty dict to allow test to continue
            return {}

    def run(self):
        """
        Runs the test case based on the provided configuration.

        This method performs the following steps:
        1. Logs the start of the test case.
        2. Registers default observers.
        3. Sets up necessary services.
        4. Prepares services (builds Docker images if required).
        5. Sets up the test environment.
        6. Deploys the required services.
        7. Executes the test steps.
        8. Collects outputs from execution environments.
        9. Runs tester analysis on collected outputs.
        10. Validates the assertions.
        11. Logs the successful completion of the test case.
        12. Notifies the event manager about the test completion.

        If any exception occurs during the execution, it logs the error and raises the exception.
        Finally, it tears down the test environment.

        Raises:
            Exception: If any error occurs during the execution of the test case.
        """
        try:
            self.state = "RUNNING"
            self.logger.info("Starting Test: %s", self.test_config.name)
            self.logger.info("Description:   %s", self.test_config.description)

            # State tracking now happens automatically through events
            # The StateEventObserver will update states when events are emitted

            start_time = time.time()
            # Set up observers first to ensure proper tracking
            self._setup_observers()

            # Register services with observers for better tracking
            experiment_observer = self.get_experiment_observer()
            if experiment_observer:
                self.logger.debug("Registering components with experiment observer")

            # Emit test execution started event according to workflow
            self.test_emitter.emit_execution_started(
                steps=(
                    list(self.test_config.steps.keys())
                    if self.test_config.steps
                    else None
                )
            )

            # State transitions are handled automatically by StateEventObserver

            # Setup services with timing
            setup_services_start = time.time()
            self.setup_services()
            setup_services_duration = time.time() - setup_services_start

            # Emit timing metric event for service setup
            if self.metrics_collector:  # Check if metrics are enabled
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"setup_services_{self.test_name}",
                    duration=setup_services_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            # State transitions are handled automatically by StateEventObserver

            # Emit command generation started event for workflow coordination
            self.service_emitter.emit_command_generation_started(
                service_id="experiment",
                service_name="experiment_services",
                phase="command_generation",
                protocol="all",
                config={"test_case": self.test_name},
            )

            # Prepare services (build Docker images) with timing
            prepare_services_start = time.time()
            self.prepare_services()
            prepare_services_duration = time.time() - prepare_services_start

            # Emit timing metric event for service preparation
            if self.metrics_collector:
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"prepare_services_{self.test_name}",
                    duration=prepare_services_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            # Emit Docker build started event for workflow coordination
            self.service_emitter.emit_docker_build_started(
                service_id="experiment",
                service_name="experiment_services",
                dockerfile_path="experiment_dockerfile",  # Placeholder for workflow coordination
                implementation="experiment",
            )

            # Setup environment with timing
            setup_env_start = time.time()
            self.setup_environment()
            setup_env_duration = time.time() - setup_env_start

            # Emit timing metric event for environment setup
            if self.metrics_collector:
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"setup_environment_{self.test_name}",
                    duration=setup_env_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            # State transitions are handled automatically by StateEventObserver

            # Deploy services with timing
            deploy_services_start = time.time()
            self.deploy_services()
            deploy_services_duration = time.time() - deploy_services_start

            # Emit timing metric event for service deployment
            if self.metrics_collector:
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"deploy_services_{self.test_name}",
                    duration=deploy_services_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            # State transitions are handled automatically by StateEventObserver

            # Execute steps with timing
            execute_steps_start = time.time()
            self.execute_steps()
            execute_steps_duration = time.time() - execute_steps_start

            # Emit timing metric event for steps execution
            if self.metrics_collector:
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"execute_steps_{self.test_name}",
                    duration=execute_steps_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            # Validate assertions with timing
            validate_assertions_start = time.time()
            self.validate_assertions()
            validate_assertions_duration = time.time() - validate_assertions_start

            # Emit timing metric event for assertions validation
            if self.metrics_collector:
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"validate_assertions_{self.test_name}",
                    duration=validate_assertions_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            tester_analysis_passed = self._run_tester_analysis()

            # Update test state based on tester analysis results
            if not tester_analysis_passed:
                self.state = "FAILED"
                self.logger.error(
                    "Test '%s' failed due to tester analysis failures.",
                    self.test_config.name,
                )

                # Emit test failed event
                self.test_emitter.emit_failed(
                    error_message="Tester analysis failed",
                    summary={"analysis_results": getattr(self, "analysis_results", [])},
                )
                return False

            # Calculate total test duration
            total_duration = time.time() - start_time

            self.state = "DONE"
            self.logger.info("Test '%s' completed successfully.", self.test_config.name)

            # State transitions are handled automatically by StateEventObserver

            if self.metrics_collector:
                # Emit timing metric for overall test case execution
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"test_case_total_{self.test_name}",
                    duration=total_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            # Use event emitter for test completion notification instead of direct event_manager
            self.test_emitter.emit_completed(
                total_duration_seconds=total_duration,
                summary={
                    "duration_ms": int(total_duration * 1000),
                    "test_state": self.state,
                },
            )

            # Emit test execution completed event according to workflow
            self.test_emitter.emit_execution_completed(
                duration_seconds=total_duration, assertions_passed=True
            )

            # State transitions are handled automatically by StateEventObserver

        except Exception as e:
            self.state = "ERROR"

            # State transitions are handled automatically by StateEventObserver

            if self.metrics_collector:
                # Emit error metric event using event emitter
                self.metrics_emitter.emit_counter_metric(
                    counter_name="test_error",
                    value=1,  # 1 to count the error
                    increment=True,  # increment counter
                    test_case=self.test_config.name,
                    metadata={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "test_phase": str(self.state),
                        "component": "test_case",
                    },
                )

            # Emit test failed event using event emitter
            self.test_emitter.emit_failed(
                error_message=str(e),
                error_type=type(e).__name__,
                phase=str(self.state),
                summary={"test_name": self.test_config.name},
            )

            # Emit test execution failed event according to workflow
            self.test_emitter.emit_execution_failed(
                error_message=str(e), error_type=type(e).__name__, phase=str(self.state)
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
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"teardown_environment_{self.test_name}",
                    duration=teardown_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )
            # Unregister observers
            try:
                factory = get_observer_factory()
                for observer_name in self.registered_observers:
                    if factory.unregister_observer(observer_name):
                        self.logger.debug("Unregistered observer '%s'", observer_name)
                    else:
                        self.logger.warning(
                            "Failed to unregister observer '%s'", observer_name
                        )
                self.registered_observers.clear()  # Clear the list after unregistration
                self.logger.debug("Unregistered all observers after test completion")
            except Exception as e:
                self.logger.error("Error during observer cleanup: %s", e)
                # Continue with cleanup even if observer unregistration fails

    def _check_timeout_cascade(self, service_name: str) -> None:
        """Check for timeout cascade and raise exception if detected."""
        now = datetime.now()
        self.timeout_history.append((now, service_name))

        # Check recent timeouts (within 5 minutes)
        cutoff_time = now - timedelta(minutes=5)
        recent_timeouts = [(t, s) for t, s in self.timeout_history if t > cutoff_time]

        threshold = self.global_config.fast_fail.timeout_cascade_threshold
        if len(recent_timeouts) >= threshold:
            services = list(set(s for _, s in recent_timeouts))
            raise TimeoutCascadeException(
                f"Timeout cascade detected in test '{self.test_config.name}'",
                len(recent_timeouts),
                services,
            )

    def get_experiment_observer(self):
        """
        Get the ExperimentObserver instance from the event_manager.

        Returns:
            ExperimentObserver or None: The experiment observer instance if found, None otherwise
        """
        if not hasattr(self, "event_manager") or self.event_manager is None:
            self.logger.warning(
                "No event_manager available for getting experiment observer"
            )
            return None

        experiment_observer = self.event_manager.get_observer_by_type(
            ExperimentObserver
        )
        if experiment_observer is None:
            self.logger.warning("No ExperimentObserver found in event_manager")

        return experiment_observer
