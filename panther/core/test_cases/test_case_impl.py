"""Test case implementation combining all execution mixins."""

import logging
import os
import re
import subprocess
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from panther.config.core.models import GlobalConfig, TestConfig
from panther.core.events.emitter_registry import EmitterRegistry
from panther.core.results.result_collector import ResultCollector
from panther.core.results.result_handlers.storage_handler import StorageHandler
from panther.core.test_cases.base.test_case_base import TestCaseBase
from panther.core.test_cases.mixins.environment_management import (
    EnvironmentManagementMixin,
)
from panther.core.test_cases.mixins.metrics import MetricsMixin
from panther.core.test_cases.mixins.observer_management import ObserverManagementMixin
from panther.core.test_cases.mixins.service_management import ServiceManagementMixin
from panther.core.test_cases.mixins.test_execution import TestExecutionMixin
from panther.core.test_cases.test_interface_impl import ITestCase
from panther.plugins.plugin_manager import PluginManager


class TestCase(
    TestCaseBase,
    ServiceManagementMixin,
    EnvironmentManagementMixin,
    TestExecutionMixin,
    MetricsMixin,
    ObserverManagementMixin,
):
    """Composite test case combining service, environment, execution, metrics, and observer mixins.

    Orchestrates the full test lifecycle: service setup, environment deployment,
    test execution, result analysis, and cleanup. State transitions follow
    PENDING -> RUNNING -> COLLECTING -> DONE/ERROR.

    Attributes:
        test_name: Name of the test case.
        test_experiment_dir: Directory for the test experiment.
        result_collectors: Collector for test results.
        service_managers: List of service managers.
        environment_plugin_manager: List of environment plugin managers.
        event_manager: Manager for handling events.
        execution_environment: List of execution environments.
        plugin_manager: Manager for handling plugins.
        services: Dictionary of services defined in the test configuration.
        test_executor: Executor for test steps and assertions.
        emitter_registry: Registry for event emitters.
        state: Current state (PENDING, RUNNING, COLLECTING, DONE, ERROR).
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
        test_index: Optional[int] = None,
    ):
        """Initialize TestCase."""
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
            workflow_tracker,
            test_index,
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

    def __str__(self):
        """Return string representation of the test case."""
        return (
            f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"network_environments={self.test_config.network_environment}, "
            f"execution_environment={self.test_config.execution_environment}, "
            f"test_experiment_dir={self.test_experiment_dir})"
        )

    def __repr__(self):
        """Return detailed representation of the test case."""
        return (
            f"TestCase(name={self.test_config.name}, "
            f"description={self.test_config.description}, "
            f"services={self.services}, "
            f"network_environments={self.test_config.network_environment}, "
            f"execution_environment={self.test_config.execution_environment}, "
            f"test_experiment_dir={self.test_experiment_dir})"
        )

    # Implement abstract methods by delegating to mixins
    def deploy_services(self):
        """Deploy services through environment managers.

        This method is provided by EnvironmentManagementMixin
        Call the mixin method directly instead of super() to avoid calling ITestCase's NotImplementedError
        """
        from panther.core.test_cases.mixins.environment_management import (
            EnvironmentManagementMixin,
        )

        return EnvironmentManagementMixin.deploy_services(self)

    def execute_steps(self):
        """Execute the defined steps of a test case.

        This method is provided by TestExecutionMixin
        Call the mixin method directly instead of super() to avoid calling ITestCase's NotImplementedError
        """
        from panther.core.test_cases.mixins.test_execution import TestExecutionMixin

        return TestExecutionMixin.execute_steps(self)

    def validate_assertions(self):
        """Validate assertions defined in test configuration.

        This method is provided by TestExecutionMixin
        Call the mixin method directly instead of super() to avoid calling ITestCase's NotImplementedError
        """
        from panther.core.test_cases.mixins.test_execution import TestExecutionMixin

        return TestExecutionMixin.validate_assertions(self)

    def run(self):
        """Execute the full test lifecycle with error handling and cleanup.

        Runs: observer setup -> service orchestration -> environment deployment ->
        test execution -> analysis & validation -> resource cleanup.
        All phases emit events for observability. Cleanup runs even on failure.

        Returns:
            True if test completed successfully, False on tester analysis failure.

        Raises:
            TestExecutionError: If test execution steps fail.
            EnvironmentSetupError: If environment deployment fails.
            ServiceSetupError: If service preparation fails.
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
            self.test_emitter.emit_setup_started(
                service_count=len(self.services) if self.services else 0,
                service_names=list(self.services.keys()) if self.services else [],
            )
            self.start_timer("setup_services")
            try:
                self.setup_services()
            except Exception as setup_err:
                self.stop_timer("setup_services")
                self.test_emitter.emit_setup_failed(
                    error_message=str(setup_err),
                    failed_component="setup_services",
                )
                raise
            setup_duration = self.stop_timer("setup_services")
            self.test_emitter.emit_setup_completed(
                services=list(self.services.keys()) if self.services else [],
                duration_seconds=setup_duration,
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
            env_type = (
                str(self.test_config.network_environment.type)
                if self.test_config.network_environment
                else "unknown"
            )
            self.test_emitter.emit_environment_setup_started(
                environment_type=env_type,
                environment_config={"test_case": self.test_name},
            )
            self.start_timer("setup_environment")
            try:
                self.setup_environment()
            except Exception as env_err:
                self.stop_timer("setup_environment")
                self.test_emitter.emit_environment_setup_failed(
                    environment_type=env_type,
                    error_message=str(env_err),
                    error_type=type(env_err).__name__,
                )
                raise
            env_duration = self.stop_timer("setup_environment")
            self.test_emitter.emit_environment_setup_completed(
                environment_type=env_type,
                environment_details={"duration_seconds": env_duration},
            )

            # State transitions are handled automatically by StateEventObserver

            # Deploy services with timing
            service_names_to_deploy = [
                sm.service_name
                for sm in self.service_managers
                if hasattr(sm, "service_name")
            ]
            self.test_emitter.emit_deployment_started(
                services_to_deploy=service_names_to_deploy,
            )
            self.start_timer("deploy_services")
            try:
                self.deploy_services()
            except Exception as deploy_err:
                self.stop_timer("deploy_services")
                self.test_emitter.emit_deployment_failed(
                    error_message=str(deploy_err),
                    failed_services=service_names_to_deploy,
                    error_type=type(deploy_err).__name__,
                )
                raise
            deploy_duration = self.stop_timer("deploy_services")
            self.test_emitter.emit_deployment_completed(
                deployed_services=service_names_to_deploy,
                deployment_details={"duration_seconds": deploy_duration},
            )

            # State transitions are handled automatically by StateEventObserver

            # Execute steps with timing
            self.start_timer("execute_steps")
            self.execute_steps()
            self.stop_timer("execute_steps")

            # Validate assertions with timing
            self.start_timer("validate_assertions")
            self.validate_assertions()
            self.stop_timer("validate_assertions")

            # CRITICAL: Run tester analysis BEFORE any teardown to ensure environments are available
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
                # CRITICAL: Teardown after analysis, even on failure
                self._perform_teardown()
                return False

            # Calculate total test duration
            total_duration = time.time() - start_time

            self.state = "DONE"
            self.logger.info("Test '%s' completed successfully.", self.test_config.name)

            # CRITICAL: Teardown after successful analysis
            self._perform_teardown()

            # State transitions are handled automatically by StateEventObserver

            # Emit timing metric for overall test case execution
            self._emit_timing_metric("test_case_total", total_duration)

            # Emit metrics summary for the completed test
            if self.metrics_emitter:
                self.metrics_emitter.emit_metrics_summary(
                    metrics={
                        "total_duration_s": total_duration,
                        "test_state": self.state,
                        "service_count": (
                            len(self.service_managers) if self.service_managers else 0
                        ),
                    },
                    test_case=self.test_name,
                    period="test_execution",
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

            # CRITICAL: Teardown after exception to ensure cleanup
            self._perform_teardown()
            raise
        finally:
            # Only observer cleanup in finally block - environment teardown moved to _perform_teardown
            self.teardown_observers()

    def _perform_teardown(self):
        """Perform environment teardown with proper timing and state management.

        This method is called after tester analysis to ensure environments
        are available for output collection before being torn down.
        """
        self.state = "COLLECTING"

        # Emit teardown started event
        self.test_emitter.emit_teardown_started()

        # Teardown environment with timing
        self.start_timer("teardown_environment")
        self.teardown_environment()
        teardown_duration = self.stop_timer("teardown_environment")

        # Emit teardown completed event
        self.test_emitter.emit_teardown_completed(
            duration_seconds=teardown_duration,
        )

        # Clean up empty directories left by Docker bind mounts / entrypoint mkdir -p
        try:
            from panther.core.outputs.output_cleanup import remove_empty_directories

            removed = remove_empty_directories(self.test_experiment_dir)
            if removed:
                self.logger.info(
                    "Cleaned %d empty directories from %s",
                    removed,
                    self.test_experiment_dir,
                )
        except Exception as e:
            self.logger.debug("Empty directory cleanup skipped: %s", e)

    def perform_dry_run(self) -> bool:
        """Performs a dry-run analysis of the test case configuration without executing commands.

        This method analyzes what would be executed during a normal run without actually:
        - Building Docker images
        - Starting containers
        - Running commands
        - Deploying services

        Returns:
            bool: True if configuration is valid, False if issues detected
        """
        try:
            self.logger.info("  📋 DRY-RUN: Analyzing test configuration...")

            # Analyze basic test configuration
            self._analyze_test_configuration()

            # Analyze service configurations
            config_valid = self._analyze_service_configurations()

            # Analyze environment configuration
            env_valid = self._analyze_environment_configuration()

            # Analyze steps configuration
            steps_valid = self._analyze_steps_configuration()

            # Show what commands would be executed
            self._show_dry_run_execution_plan()

            overall_valid = config_valid and env_valid and steps_valid

            if overall_valid:
                self.logger.info("  ✅ DRY-RUN: All configurations valid")
            else:
                self.logger.info("  ❌ DRY-RUN: Configuration issues found")

            return overall_valid

        except Exception as e:
            self.logger.error("  ❌ DRY-RUN: Analysis failed: %s", e)
            return False

    def _show_dry_run_execution_plan(self):
        """Show what would be executed in a real run."""
        self.logger.info("    🔄 DRY-RUN Execution Plan:")
        service_count = len(getattr(self.test_config, "services", {}))
        self.logger.info(
            "      1. Setup services → Would configure %d services", service_count
        )
        self.logger.info("      2. Prepare services → Would build Docker images")
        self.logger.info(
            "      3. Setup environment → Would configure network/execution environment"
        )
        self.logger.info("      4. Deploy services → Would start containers")

        # Handle steps more robustly
        if hasattr(self.test_config, "steps") and self.test_config.steps:
            if hasattr(self.test_config.steps, "wait"):
                self.logger.info(
                    "      5. Execute steps → Would wait %s seconds",
                    self.test_config.steps.wait,
                )
            else:
                try:
                    step_count = (
                        len(self.test_config.steps)
                        if hasattr(self.test_config.steps, "__len__")
                        else 1
                    )
                    self.logger.info(
                        "      5. Execute %d test steps → Would run commands",
                        step_count,
                    )
                except:
                    self.logger.info(
                        "      5. Execute steps → Would run configured steps"
                    )
        else:
            self.logger.info("      5. Execute steps → No steps configured")

        self.logger.info("      6. Validate assertions → Would check test results")
        self.logger.info("      7. Teardown → Would clean up resources")
