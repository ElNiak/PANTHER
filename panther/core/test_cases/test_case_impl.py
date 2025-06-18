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

from panther.config.core.models import GlobalConfig, TestConfig
from panther.core.events.emitter_registry import EmitterRegistry
from panther.core.exceptions.fast_fail import FastFailHandler, TimeoutCascadeException
from panther.core.observer.management.event_manager import EventManager
from panther.core.results.result_collector import ResultCollector
from panther.core.results.result_handlers.storage_handler import StorageHandler
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.core.test_cases.base.test_case_base import TestCaseBase
from panther.core.test_cases.mixins.service_management import ServiceManagementMixin
from panther.core.test_cases.mixins.environment_management import EnvironmentManagementMixin
from panther.core.test_cases.mixins.test_execution import TestExecutionMixin
from panther.core.test_cases.mixins.metrics import MetricsMixin
from panther.core.test_cases.mixins.observer_management import ObserverManagementMixin
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.plugin_manager import PluginManager
from panther.config.core.models.service import ImplementationType
from panther.plugins.services.services_interface import IServiceManager


class TestCase(TestCaseBase, ServiceManagementMixin, EnvironmentManagementMixin, TestExecutionMixin, MetricsMixin, ObserverManagementMixin):
    """
    TestCase class represents a test case that is configured and executed based on the provided configurations.
    
    This class combines functionality from multiple base classes and mixins:
    - TestCaseBase: Core initialization and configuration
    - ServiceManagementMixin: Service setup, preparation, and teardown
    - EnvironmentManagementMixin: Environment setup, deployment, and teardown
    - TestExecutionMixin: Test step execution, output collection, and tester analysis
    - MetricsMixin: Timing and metrics collection capabilities
    - ObserverManagementMixin: Observer lifecycle management

    Attributes:
        test_name (str): Name of the test case.
        test_experiment_dir (Path): Directory for the test experiment.
        result_collectors (ResultCollector): Collector for test results.
        service_managers (list): List of service managers.
        environment_plugin_manager (list): List of environment plugin managers.
        event_manager (EventManager): Manager for handling events.
        execution_environment (list): List of execution environments.
        plugin_manager (PluginManager): Manager for handling plugins.
        services (dict): Dictionary of services defined in the test configuration.
        test_executor (TestExecutor): Executor for test steps and assertions.
        emitter_registry (EmitterRegistry): Registry for event emitters.
        state (str): Current state of the test case.

    Key Methods (from mixins):
        From ServiceManagementMixin:
        - setup_services(): Sets up the services based on the test configuration.
        - setup_testers(): Sets up the testers based on the test configuration.
        - setup_implementations(): Sets up the implementations based on the test configuration.
        - prepare_services(): Prepares services (builds Docker images).
        - teardown_services(): Stops all services managed by the service managers.
        
        From EnvironmentManagementMixin:
        - setup_environment(): Sets up the test environment using the plugin.
        - teardown_environment(): Tears down the test environment using the plugin.
        - deploy_services(): Deploys services through environment managers.
        
        From TestExecutionMixin:
        - execute_steps(): Executes the defined steps of a test.
        - validate_assertions(): Validates assertions defined in the test configuration.
        - check_service_responsiveness(): Checks if a service's endpoint is responsive.
        
        From TestCaseBase:
        - _setup_observers(): Registers default observers to listen to events.
        - get_experiment_observer(): Gets the experiment observer instance.

    Main Method:
        run(): Runs the test case based on the provided configuration.
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
        # Initialize mixin attributes before calling super()
        # This ensures all mixins have what they need during initialization
        self._test_executor = None
        self._output_analyzer = None
        self._operation_timers = {}
        self.registered_observers = []
        
        # Call parent class which handles most initialization
        super().__init__(
            test_config, 
            global_config,
            plugin_manager,
            experiment_dir,
            metrics_collector,
            emitter_registry,
            workflow_tracker
        )

        # Timeout cascade detection
        self.timeout_history: deque = deque(maxlen=10)  # Track last 10 timeouts

        # Additional logging for TestCase
        self.logger.debug(
            "Creating test case '%s' with experiment directory '%s' and test configuration '%s'",
            self.test_name,
            self.test_experiment_dir,
            test_config,
        )

        # Initialize result collectors
        self.result_collectors = ResultCollector()
        self.result_collectors.register_handler(
            f"storage_{self.test_name}", StorageHandler(experiment_dir, self.test_name)
        )

        # Use provided emitter registry or create a new one
        if not self.emitter_registry:
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

        net_environment_type = test_config.network_environment
        self.logger.info("Loading network environment: %s", net_environment_type)

        self._panther_dir = Path(os.path.dirname(__file__)).parent.parent.parent

        self.state: Literal["PENDING", "RUNNING", "COLLECTING", "DONE", "ERROR"] = (
            "PENDING"
        )

        # Initialize mixin compatibility
        self.initialize_mixin_compatibility()

    def __str__(self):
        return (
            f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"network_environments={self.test_config.network_environment}, "
            f"execution_environments={self.test_config.execution_environment}, "
            f"test_experiment_dir={self.test_experiment_dir})"
        )

    def __repr__(self):
        return (
            f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"network_environments={self.test_config.network_environment}, "
            f"execution_environments={self.test_config.execution_environment}, "
            f"test_experiment_dir={self.test_experiment_dir})"
        )

    # Implement abstract methods by delegating to mixins
    def deploy_services(self):
        """Deploy services through environment managers."""
        # This method is provided by EnvironmentManagementMixin
        # Call the mixin method directly instead of super() to avoid calling ITestCase's NotImplementedError
        from panther.core.test_cases.mixins.environment_management import EnvironmentManagementMixin
        return EnvironmentManagementMixin.deploy_services(self)

    def execute_steps(self):
        """Execute the defined steps of a test case."""
        # This method is provided by TestExecutionMixin
        # Call the mixin method directly instead of super() to avoid calling ITestCase's NotImplementedError
        from panther.core.test_cases.mixins.test_execution import TestExecutionMixin
        return TestExecutionMixin.execute_steps(self)

    def validate_assertions(self):
        """Validate assertions defined in test configuration."""
        # This method is provided by TestExecutionMixin
        # Call the mixin method directly instead of super() to avoid calling ITestCase's NotImplementedError
        from panther.core.test_cases.mixins.test_execution import TestExecutionMixin
        return TestExecutionMixin.validate_assertions(self)

    def _create_service_manager(
        self, service_name: str, service_details: Any
    ) -> Optional[IServiceManager]:
        """Create a service manager for the given service configuration."""
        implementation = service_details.implementation
        impl_name = implementation.name
        impl_type = implementation.type
        protocol = service_details.protocol
        protocol_name = protocol.name

        self.logger.debug(
            f"Creating service manager for {service_name}: "
            f"impl={impl_name}, type={impl_type}, protocol={protocol_name}"
        )

        try:
            # Get the implementation directory from plugin catalog
            # Handle both enum and string types
            if hasattr(impl_type, 'value'):
                type_str = impl_type.value
            else:
                type_str = str(impl_type).lower()
            
            # Map TESTERS to tester for plugin catalog lookup
            if type_str == "testers":
                type_str = "tester"
            elif type_str == "iut":
                type_str = "iut"  # Keep as is
                
            plugin_id = f"{type_str}:{impl_name}"
            plugin_manifest = self.plugin_manager.plugin_catalog.catalog.get(plugin_id)
            
            if not plugin_manifest:
                self.logger.error(f"Plugin not found in catalog: {plugin_id}")
                return None
                
            implementation_dir = (
                Path(plugin_manifest.file_path)
                if plugin_manifest.file_path
                else None
            )
            
            if not implementation_dir:
                self.logger.error(f"No implementation directory found for {plugin_id}")
                return None
            
            self.logger.debug(f"Plugin manifest file_path: {plugin_manifest.file_path}")
            self.logger.debug(f"Implementation dir: {implementation_dir}")
            
            # Use plugin manager to create service manager with correct parameters
            service_manager = self.plugin_manager.create_service_manager(
                protocol=protocol,
                implementation=implementation,
                implementation_dir=implementation_dir,
                service_config_to_test=service_details,
                event_manager=self.event_manager,
                emitter_registry=self.emitter_registry,
            )

            if service_manager:
                # Set service name and additional attributes
                service_manager.service_name = service_name
                service_manager.timeout = service_details.timeout
                service_manager.ports = service_details.ports if hasattr(service_details, 'ports') else []

                # Set protocol details
                service_manager.protocol_name = protocol_name
                service_manager.protocol_role = protocol.role
                service_manager.protocol_target = getattr(protocol, 'target', None)
                
                # Set test context if the service manager supports it
                if hasattr(service_manager, "set_test_context"):
                    service_manager.set_test_context(self.test_name)

                return service_manager
            else:
                self.logger.error(
                    f"Failed to create service manager for {service_name}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Error creating service manager for {service_name}: {e}")
            raise

    def get_service_names_and_metadata(self):
        """Get service names and metadata for deployment events."""
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
            # Handle both enum and string types for implementation.type
            service_type = "unknown"
            if hasattr(s.service_config_to_test.implementation, "type"):
                impl_type = s.service_config_to_test.implementation.type
                if hasattr(impl_type, "value"):
                    # Enum type (old system)
                    service_type = impl_type.value
                else:
                    # String type (new system)
                    service_type = str(impl_type).lower()

            # Handle both enum and string types for protocol.role
            protocol_role = "unknown"
            if (hasattr(s.service_config_to_test, "protocol") and 
                hasattr(s.service_config_to_test.protocol, "role")):
                role = s.service_config_to_test.protocol.role
                if hasattr(role, "value"):
                    # Enum type (old system)
                    protocol_role = role.value
                else:
                    # String type (new system)
                    protocol_role = str(role).lower()

            metadata = {
                "service_type": service_type,
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
                    "role": protocol_role,
                },
            }
            service_metadata.append(metadata)

        # Emit service setup started event
        if hasattr(self, 'service_emitter') and self.service_emitter:
            self.service_emitter.emit_service_setup_started(
                test_case=self.test_name,
                service_count=len(self.service_managers),
                service_names=service_names,
                service_metadata=service_metadata,
            )
        
        return service_names

    @property
    def execution_environments(self):
        """Compatibility property for execution_environments (provides backward compatibility for execution_environment)."""
        # Handle both execution_environment (singular) and execution_environments (plural)
        if hasattr(self.test_config, 'execution_environments'):
            return self.test_config.execution_environments
        elif hasattr(self.test_config, 'execution_environment'):
            # Convert singular to list for compatibility
            env = self.test_config.execution_environment
            if env is None:
                return []
            elif isinstance(env, list):
                return env
            else:
                return [env]
        else:
            return []

    def initialize_mixin_compatibility(self):
        """Initialize compatibility for mixins."""
        # Ensure execution_environments compatibility
        if not hasattr(self.test_config, 'execution_environments'):
            self.test_config.execution_environments = self.execution_environments






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
            self.setup_observers()

            # Register services with observers for better tracking
            experiment_observer = self.get_experiment_observer()
            if experiment_observer:
                self.logger.debug("Registering components with experiment observer")

            # Emit test execution started event according to workflow
            self.test_emitter.emit_execution_started(
                steps=(
                    ["pre_commands", "wait", "post_commands"]
                    if self.test_config.steps
                    else None
                )
            )

            # State transitions are handled automatically by StateEventObserver

            # Setup services with timing
            self.start_timer("setup_services")
            self.setup_services()
            self.stop_timer("setup_services")

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
            self.start_timer("prepare_services")
            self.prepare_services()
            self.stop_timer("prepare_services")

            # Emit Docker build started event for workflow coordination
            self.service_emitter.emit_docker_build_started(
                service_id="experiment",
                service_name="experiment_services",
                dockerfile_path="experiment_dockerfile",  # Placeholder for workflow coordination
                implementation="experiment",
            )

            # Setup environment with timing
            self.start_timer("setup_environment")
            self.setup_environment()
            self.stop_timer("setup_environment")

            # State transitions are handled automatically by StateEventObserver

            # Deploy services with timing
            self.start_timer("deploy_services")
            self.deploy_services()
            self.stop_timer("deploy_services")

            # State transitions are handled automatically by StateEventObserver

            # Execute steps with timing
            self.start_timer("execute_steps")
            self.execute_steps()
            self.stop_timer("execute_steps")

            # Validate assertions with timing
            self.start_timer("validate_assertions")
            self.validate_assertions()
            self.stop_timer("validate_assertions")

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

            # Emit timing metric for overall test case execution
            self._emit_timing_metric("test_case_total", total_duration)

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
            
            # Return True to indicate successful test completion
            return True

        except Exception as e:
            self.state = "ERROR"

            # State transitions are handled automatically by StateEventObserver

            # Emit error metric event
            self.emit_counter_metric(
                counter_name="test_error",
                value=1,
                increment=True,
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
            self.start_timer("teardown_environment")
            self.teardown_environment()
            self.stop_timer("teardown_environment")
            
            # Unregister observers
            self.teardown_observers()

