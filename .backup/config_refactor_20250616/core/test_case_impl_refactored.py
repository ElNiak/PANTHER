"""Refactored TestCase implementation using modular components."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.events.test.states import TestState
from panther.core.test_cases.analysis.output_analyzer import OutputAnalyzer
from panther.core.test_cases.base.test_case_base import TestCaseBase
from panther.core.test_cases.execution.test_executor import TestExecutor
from panther.core.test_cases.mixins.environment_management import (
    EnvironmentManagementMixin,
)
from panther.core.test_cases.mixins.service_management import ServiceManagementMixin
from panther.plugins.plugin_manager import PluginManager


class TestCaseImplRefactored(
    TestCaseBase, 
    ServiceManagementMixin, 
    EnvironmentManagementMixin
):
    """
    Refactored TestCase implementation using modular components.

    This class coordinates between specialized components for different responsibilities:
    - TestCaseBase: Core initialization and configuration
    - ServiceManagementMixin: Service lifecycle management
    - EnvironmentManagementMixin: Environment setup and teardown
    - TestExecutor: Test execution and step handling
    - OutputAnalyzer: Output collection and analysis
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
        """Initialize with modular components."""
        super().__init__(
            test_config,
            global_config,
            plugin_manager,
            experiment_dir,
            metrics_collector,
            emitter_registry,
            workflow_tracker,
        )

        # Initialize specialized components
        self.test_executor = TestExecutor(self)

        # Initialize event emitters if available
        if self.emitter_registry:
            self.service_emitter = self.emitter_registry.service_emitter
            self.environment_emitter = self.emitter_registry.environment_emitter
            self.step_emitter = self.emitter_registry.step_emitter
            self.experiment_emitter = self.emitter_registry.experiment_emitter
            self.metrics_emitter = self.emitter_registry.metrics_emitter
        else:
            self.service_emitter = None
            self.environment_emitter = None
            self.step_emitter = None
            self.experiment_emitter = None
            self.metrics_emitter = None
        self.output_analyzer = OutputAnalyzer(self)

        # Initialize test state tracking
        self.test_state = TestState.CREATED
        self.test_results = {}
        self.execution_start_time = None
        self.execution_end_time = None

    def run(self) -> Dict[str, Any]:
        """
        Execute the complete test workflow using modular components.

        Returns:
            Dictionary containing test execution results
        """
        self.logger.info(f"Starting test execution: {self.test_name}")

        # Get test emitter if available
        if self.emitter_registry: 
            test_emitter = self.emitter_registry.get_emitter("test")
        else:
            test_emitter = None
        try:
            # Emit test started event
            test_emitter.emit_execution_started(
                steps=(
                    ["wait", "record_pcap"]  # StepConfig dataclass fields
                    if self.test_config.steps
                    else None
                )
            )


            self.execution_start_time = time.time()
            self.test_state = TestState.EXECUTING

            # Phase 1: Service setup and preparation
            self._setup_phase()

            # Phase 2: Environment deployment
            self._deployment_phase()

            # Phase 3: Test execution
            self._execution_phase()

            # Phase 4: Output collection and analysis
            self._analysis_phase()

            # Phase 5: Cleanup
            self._cleanup_phase()

            # Calculate execution time
            self.execution_end_time = time.time()
            execution_duration = self.execution_end_time - self.execution_start_time

                        # Emit timing metrics
            if hasattr(self, 'metrics_emitter') and self.metrics_collector:
                # Setup services timing
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"setup_services_{self.test_name}",
                    duration=getattr(self, '_setup_duration', 0),
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )
                
                # Deployment timing
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"deploy_services_{self.test_name}",
                    duration=getattr(self, '_deployment_duration', 0),
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )
                
                # Execution timing
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"execute_steps_{self.test_name}",
                    duration=getattr(self, '_execution_duration', 0),
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )
                
                # Total test timing
                self.metrics_emitter.emit_timing_metric(
                    operation_name=f"test_case_total_{self.test_name}",
                    duration=execution_duration,
                    phase="TEST_EXECUTION",
                    test_case=self.test_config.name,
                    component="test_case",
                )

            # Prepare final results
            self.test_results.update(
                {
                    "test_name": self.test_name,
                    "state": TestState.COMPLETED,
                    "execution_time": execution_duration,
                    "success": True,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

            # Emit test completed event
            total_duration_seconds = time.time() - self.execution_start_time
            if test_emitter:
                test_emitter.emit_completed(
                    total_duration_seconds=total_duration_seconds,
                    summary={
                        "duration_ms": int(total_duration_seconds * 1000),
                        "test_state": str(self.test_state),
                    } 
                )

            self.logger.info(
                f"Test {self.test_name} completed successfully in {execution_duration:.2f}s"
            )
            return self.test_results

        except Exception as e:
            self.test_state = TestState.FAILED
            error_msg = f"Test {self.test_name} failed: {str(e)}"
            self.logger.error(error_msg)

            # Emit test failed event
            if test_emitter:
                test_emitter.emit_failed(
                    error_message=str(e),
                    error_type=type(e).__name__,
                    phase=str(self.test_state),
                    summary={"test_name": self.test_config.name},
                )

            # Ensure cleanup runs even on failure
            try:
                self._cleanup_phase()
            except Exception as cleanup_error:
                self.logger.error(f"Cleanup failed: {cleanup_error}")

            # Return failure results
            self.test_results = {
                "test_name": self.test_name,
                "state": TestState.FAILED,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            return self.test_results

    def _setup_phase(self) -> None:
        """Phase 1: Service setup and preparation using service management mixin."""
        self.logger.info("=== Phase 1: Service Setup ===")

        self._setup_start_time = time.time()
        try:
            # Setup services using service management mixin
            self.setup_services()

            # Prepare services (build Docker images, etc.)
            self.prepare_services()

            # Emit command generation started event for workflow coordination
            if hasattr(self, 'service_emitter') and self.service_emitter:
                self.service_emitter.emit_command_generation_started(
                    service_id="workflow_setup",
                    service_name="Command Generation Workflow", 
                    phase="setup",
                    config={"test_case": self.test_name, "service_count": len(self.services) if hasattr(self, 'services') else 0}
                )

            self._setup_duration = time.time() - self._setup_start_time
            self.logger.info("Service setup phase completed")

        except Exception as e:
            self.logger.error(f"Service setup phase failed: {e}")
            raise

    
    def prepare_services(self) -> None:
        """Prepare services including Docker image builds."""
        self.logger.info("Preparing services (building Docker images if required)")
        
        if not hasattr(self, "service_managers") or not self.service_managers:
            self.logger.debug("No services to prepare")
            return
            
        try:
            # Reset base image flag for this test run
            from panther.core.docker_builder.service_manager_docker_mixin import (
                ServiceManagerDockerMixin,
            )
            ServiceManagerDockerMixin.reset_base_image_flag()
            
            for service_manager in self.service_managers:
                service_name = (
                    service_manager.service_name
                    if hasattr(service_manager, "service_name")
                    else service_manager.get_implementation_name()
                )
                
                if hasattr(service_manager, "prepare") and callable(
                    getattr(service_manager, "prepare")
                ):
                    service_manager.prepare(self.plugin_manager)
                    self.logger.debug("Successfully prepared service: %s", service_name)
                    
            # Emit Docker build started event for workflow coordination
            if hasattr(self, 'service_emitter'):
                self.service_emitter.emit_docker_build_started(
                    service_id="experiment",
                    service_name="experiment_services",
                    dockerfile_path="experiment_dockerfile",  # Placeholder for workflow coordination
                    implementation="experiment",
                )
                    
        except Exception as e:
            self.logger.error("Failed to prepare services: %s", e)
            raise

    def _deployment_phase(self) -> None:
        """Phase 2: Environment deployment using environment management mixin."""
        self.logger.info("=== Phase 2: Environment Deployment ===")

        try:
            # Setup test environment using environment management mixin
            
            self._deployment_start_time = time.time()
            
            # Get service info for events
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
                        else (
                            s.service_config_to_test.implementation.type
                            if isinstance(s.service_config_to_test.implementation.type, str)
                            else s.service_config_to_test.implementation.type.value
                        )
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

            # Emit service setup started event
            if hasattr(self, 'service_emitter'):
                self.service_emitter.emit_service_setup_started(
                    test_case=self.test_name,
                    service_count=len(self.service_managers),
                    service_names=service_names,
                    service_metadata=service_metadata,
                )
            
            # Emit environment deployment started for each environment
            for env_manager in self.environment_plugin_manager:
                env_name = f"{env_manager.__class__.__name__}_{self.test_name}"
                if hasattr(self, 'environment_emitter'):
                    self.environment_emitter.emit_environment_deployment_started(
                        environment_id=env_name,
                        environment_name=self.test_name,
                        environment_type=env_manager.__class__.__name__,
                        services=service_names,
                        deployment_config={"test_case": self.test_name},
                    )

            self.setup_environment()

            # Deploy services through environment managers
            self.deploy_services()

            self._deployment_duration = time.time() - self._deployment_start_time
            
            # Emit completion events
            if hasattr(self, 'environment_plugin_manager') and self.environment_plugin_manager:
                env_manager = self.environment_plugin_manager[-1]  # Use last env manager
                
                if hasattr(self, 'service_emitter') and self.service_emitter:
                    service_instances = {
                        (s.service_name if hasattr(s, "service_name") else s.get_implementation_name()): s
                        for s in self.service_managers
                    }
                    self.service_emitter.emit_service_deployed(
                        environment=env_manager.__class__.__name__,
                        service_instances=service_instances,
                    )
                    
                # Emit environment deployment completed
                if hasattr(self, 'environment_emitter') and self.environment_emitter:
                    deployed_services_dict = {
                        (s.service_name if hasattr(s, "service_name") else s.get_implementation_name()): "deployed"
                        for s in self.service_managers
                    }
                    
                    self.environment_emitter.emit_environment_deployment_completed(
                        environment_id=f"{env_manager.__class__.__name__}_{self.test_name}",
                        environment_name=self.test_name,
                        environment_type=env_manager.__class__.__name__,
                        success=True,
                        deployed_services=deployed_services_dict,
                        duration=self._deployment_duration,
                        deployment_details={
                            "service_count": len(self.service_managers)
                        },
                    )

            self.logger.info("Environment deployment phase completed")

        except Exception as e:
            self.logger.error(f"Environment deployment phase failed: {e}")
            raise

    def _execution_phase(self) -> None:
        """Phase 3: Test execution using test executor component."""
        self.logger.info("=== Phase 3: Test Execution ===")

        self._execution_start_time = time.time()
        try:
            # Execute test steps using test executor component
            self.test_executor.execute_steps()

            # Validate assertions if defined
            self.test_executor.validate_assertions()

            self._execution_duration = time.time() - self._execution_start_time
            self.logger.info("Test execution phase completed")

        except Exception as e:
            self.logger.error(f"Test execution phase failed: {e}")
            raise

    def _analysis_phase(self) -> None:
        """Phase 4: Output collection and analysis using output analyzer component."""
        self.logger.info("=== Phase 4: Output Analysis ===")

        try:
            # Collect outputs from execution environments
            collected_outputs = self.output_analyzer.collect_outputs()

            # Store collected outputs in test results
            self.test_results["outputs"] = collected_outputs

            # Run tester analysis on collected outputs
            analysis_results = self.output_analyzer.run_tester_analysis(
                collected_outputs
            )

            # Store analysis results
            self.test_results["analysis"] = analysis_results

            self.logger.info("Output analysis phase completed")

        except Exception as e:
            self.logger.error(f"Output analysis phase failed: {e}")
            # Don't raise - analysis failure shouldn't fail the entire test
            self.test_results["analysis_error"] = str(e)

    def _cleanup_phase(self) -> None:
        """Phase 5: Cleanup using management mixins."""
        self.logger.info("=== Phase 5: Cleanup ===")

        try:
            # Teardown services using service management mixin
            self.teardown_services()

            # Teardown environment using environment management mixin
            self.teardown_environment()

            self.logger.info("Cleanup phase completed")

        except Exception as e:
            self.logger.error(f"Cleanup phase failed: {e}")
            # Don't raise - cleanup failures shouldn't fail the test result

    # Legacy API compatibility methods

    def prepare(self) -> None:
        """Legacy method - delegates to service preparation."""
        self.logger.info("Preparing test case")
        self.prepare_services()

    def execute(self) -> Dict[str, Any]:
        """Legacy method - delegates to run()."""
        return self.run()

    def teardown(self) -> None:
        """Legacy method - delegates to cleanup."""
        self._cleanup_phase()

    def get_results(self) -> Dict[str, Any]:
        """Get test execution results."""
        return self.test_results

    def get_state(self) -> TestState:
        """Get current test state."""
        return self.test_state

    def get_execution_time(self) -> Optional[float]:
        """Get test execution time in seconds."""
        if self.execution_start_time and self.execution_end_time:
            return self.execution_end_time - self.execution_start_time
        return None

    def is_successful(self) -> bool:
        """Check if test completed successfully."""
        return self.test_state == TestState.COMPLETED and self.test_results.get(
            "success", False
        )

    def get_error_info(self) -> Optional[Dict[str, str]]:
        """Get error information if test failed."""
        if self.test_state == TestState.FAILED:
            return {
                "error": self.test_results.get("error", "Unknown error"),
                "error_type": self.test_results.get("error_type", "Unknown"),
                "timestamp": self.test_results.get("timestamp", ""),
            }
        return None

    # Abstract method implementations (required by ITestCase interface)

    def deploy_services(self) -> None:
        """Deploy services using environment management mixin."""
        self.logger.info("Deploying services via environment managers")
        try:
            # Track deployment timing
            deploy_start = time.time()
            
            # Use the environment management mixin to deploy services
            if hasattr(self, 'environment_plugin_manager'):
                for env_manager in self.environment_plugin_manager:
                    if hasattr(env_manager, "run"):
                        env_manager.run()
                        
            self._deployment_duration = time.time() - deploy_start
        except Exception as e:
            self.logger.error(f"Service deployment failed: {e}")
            
            # Emit failure events
            if hasattr(self, 'service_emitter'):
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
                        environment="deployment",
                        error_message=str(e),
                        error_type=type(e).__name__,
                    )
            raise


    def execute_steps(self) -> None:
        """Execute test steps using test executor component."""
        self.logger.info("Executing test steps via test executor")
                # Emit step execution started event if not already done
        if hasattr(self, 'step_emitter'):
            step_names = list(self.test_config.steps.keys()) if self.test_config.steps else []
            self.step_emitter.emit_step_execution_started(
                step_id="execute_steps",
                step_name="Execute test steps",
                test_case_id=self.test_name,
                step_config={"steps": step_names},
            )

        try:
            # Delegate to the test executor component
            self.test_executor.execute_steps()
        except Exception as e:
            self.logger.error(f"Step execution failed: {e}")
            raise

    def validate_assertions(self) -> None:
        """Validate test assertions using test executor component."""
        self.logger.info("Validating test assertions via test executor")
        try:
            # Delegate to the test executor component
            self.test_executor.validate_assertions()
        except Exception as e:
            self.logger.error(f"Assertion validation failed: {e}")
            raise

    # Metrics integration methods

    def record_metrics(self, phase: str, metrics: Dict[str, Any]) -> None:
        """Record metrics for a specific test phase."""
        if self.metrics_collector:
            for metric_name, metric_value in metrics.items():
                self.metrics_collector.record_timing(
                    name=f"{self.test_name}_{phase}_{metric_name}",
                    value=metric_value,
                    test_case=self.test_name,
                    phase=phase,
                )

    def get_service_managers(self) -> List[Any]:
        """Get list of configured service managers."""
        return self.service_managers

    def get_environment_managers(self) -> List[Any]:
        """Get list of configured environment managers."""
        return self.environment_plugin_manager

    def get_execution_environments(self) -> List[Any]:
        """Get list of configured execution environments."""
        return self.execution_environment

    # String representation

    def __str__(self) -> str:
        return f"TestCaseImplRefactored(name={self.test_name}, state={self.test_state})"

    def __repr__(self) -> str:
        return f"TestCaseImplRefactored(name='{self.test_name}', services={len(self.service_managers)}, environments={len(self.environment_plugin_manager)})"


# Compatibility alias
TestCaseImpl = TestCaseImplRefactored
