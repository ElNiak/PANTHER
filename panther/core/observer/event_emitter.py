"""
Event Emitter Module

This module provides standardized functions for emitting events across the PANTHER framework.
"""

from typing import Any, TypeVar

from panther.core.observer.events import (
    Event,
    ExperimentInitializedEvent,
    ExperimentFinishedEvent,
    ExperimentFinishedEarlyEvent,
    TestCaseInitializedEvent,
    TestStartedEvent,
    TestCompletedEvent,
    TestExecutionStartedEvent,
    TestExecutionCompletedEvent,
    TestExecutionFailedEvent,
    EnvironmentSetupStartedEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentTeardownEvent,
    ServiceEvent,
    StepProgressEvent,
    StepCompletedEvent,
    ServiceSetupStartedEvent,
    ServiceSetupCompletedEvent,
    ServiceSetupFailedEvent,
    ServiceDeploymentEvent,
    ServiceDeploymentFailedEvent,
    # Environment events
    EnvironmentInitializedEvent,
    EnvironmentSetupFailedEvent,
    # Step events
    StepExecutionStartedEvent,
    StepExecutionCompletedEvent,
    StepUnsupportedEvent,
    # Assertion events
    AssertionsValidationStartedEvent,
    AssertionProgressEvent,
    AssertionResultEvent,
    AssertionUnknownEvent,
    AssertionErrorEvent,
    AssertionsValidationCompletedEvent,
)
from panther.core.observer.event_manager import EventManager

# Type variable for generic event types
T = TypeVar("T", bound=Event)


class EventEmitter:
    """
    Provides standardized methods for emitting events across the PANTHER framework.

    This class ensures consistent event emission patterns and parameter handling
    throughout the framework.
    """

    def __init__(self, event_manager: EventManager):
        """
        Initialize the event emitter.

        Args:
            event_manager: Event manager instance to use for event emission
        """
        self.event_manager = event_manager

    def emit_event(self, event: Event) -> None:
        """
        Emit an event through the event manager.

        Args:
            event: The event to emit
        """
        self.event_manager.notify(event)

    def emit_experiment_initialized(
        self, experiment_id: str, config: dict[str, Any] = None
    ) -> None:
        """
        Emit an experiment initialized event.

        Args:
            experiment_id: Unique identifier for the experiment
            config: Experiment configuration details
        """
        self.emit_event(
            ExperimentInitializedEvent(experiment_id=experiment_id, config=config or {})
        )

    def emit_experiment_finished(
        self, experiment_id: str, success: bool = True, summary: dict[str, Any] = None
    ) -> None:
        """
        Emit an experiment finished event.

        Args:
            experiment_id: Unique identifier for the experiment
            success: Whether the experiment completed successfully
            summary: Experiment execution summary
        """
        self.emit_event(
            ExperimentFinishedEvent(
                experiment_id=experiment_id, success=success, summary=summary or {}
            )
        )

    def emit_experiment_finished_early(
        self, experiment_id: str, reason: str, details: dict[str, Any] = None
    ) -> None:
        """
        Emit an experiment finished early event.

        Args:
            experiment_id: Unique identifier for the experiment
            reason: Reason for early termination
            details: Additional details about the termination
        """
        details = details or {}
        # Include action to distinguish between notification and check
        if "action" not in details:
            details["action"] = "notify"

        self.emit_event(
            ExperimentFinishedEarlyEvent(
                experiment_id=experiment_id, reason=reason, details=details
            )
        )

    def emit_test_case_initialized(self, test_count: int, test_names: list[str]) -> None:
        """
        Emit a test case initialized event.

        Args:
            test_count: Number of test cases initialized
            test_names: List of test case names
        """
        self.emit_event(
            TestCaseInitializedEvent(
                test_id="summary",
                test_name="test_cases_initialized",
                parameters={"test_count": test_count, "test_names": test_names},
            )
        )

    def emit_test_started(self, test_id: str, details: dict[str, Any] = None) -> None:
        """
        Emit a test started event.

        Args:
            test_id: Test identifier
            details: Additional test details
        """
        self.emit_event(TestStartedEvent(test_name=test_id, config=details or {}))

    def emit_test_completed(
        self, test_id: str, success: bool = True, result: dict[str, Any] = None
    ) -> None:
        """
        Emit a test completed event.

        Args:
            test_id: Test identifier
            success: Whether the test completed successfully
            result: Test execution result
        """
        self.emit_event(TestCompletedEvent(test_name=test_id, success=success, result=result or {}))

    def emit_test_execution_started(self, test_id: str, test_name: str) -> None:
        """
        Emit a test execution started event.

        Args:
            test_id: Test identifier
            test_name: Test name
        """
        self.emit_event(TestExecutionStartedEvent(test_id=test_id, test_name=test_name))

    def emit_test_execution_completed(
        self,
        test_id: str,
        test_name: str,
        success: bool,
        results: dict[str, Any],
        duration_ms: int | None = None,
    ) -> None:
        """
        Emit a test execution completed event.

        Args:
            test_id: Test identifier
            test_name: Test name
            success: Whether execution was successful
            results: Execution results
            duration_ms: Execution duration in milliseconds
        """
        data = {"test_id": test_id, "test_name": test_name, "success": success, "results": results}
        if duration_ms is not None:
            data["duration_ms"] = duration_ms

        self.emit_event(TestExecutionCompletedEvent(**data))

    def emit_test_execution_failed(
        self,
        test_id: str,
        test_name: str,
        error_type: str,
        error_message: str,
        details: dict[str, Any] = None,
    ) -> None:
        """
        Emit a test execution failed event.

        Args:
            test_id: Test identifier
            test_name: Test name
            error_type: Type of error encountered
            error_message: Error message
            details: Additional error details
        """
        self.emit_event(
            TestExecutionFailedEvent(
                test_id=test_id,
                test_name=test_name,
                error_message=error_message,
                stack_trace=None,
                error_details=details or {"error_type": error_type},
            )
        )

    # Service Events
    def emit_service_setup_started(
        self, test_case: str, service_count: int, service_names: list[str] | None = None
    ) -> None:
        """
        Emit a service setup started event.

        Args:
            test_case: Name of the test case
            service_count: Number of services to set up
            service_names: Names of the services being set up
        """
        self.emit_event(
            ServiceSetupStartedEvent(
                test_case=test_case, service_count=service_count, service_names=service_names
            )
        )

    def emit_service_setup_completed(
        self, test_case: str, services: list[str], success: bool = True
    ) -> None:
        """
        Emit a service setup completed event.

        Args:
            test_case: Name of the test case
            services: List of service names that were set up
            success: Whether setup was successful
        """
        self.emit_event(
            ServiceSetupCompletedEvent(test_case=test_case, services=services, success=success)
        )

    def emit_service_setup_failed(
        self, test_case: str, error_message: str, error_type: str
    ) -> None:
        """
        Emit a service setup failed event.

        Args:
            test_case: Name of the test case
            error_message: Error message from the failure
            error_type: Type of error that occurred
        """
        self.emit_event(
            ServiceSetupFailedEvent(
                test_case=test_case, error_message=error_message, error_type=error_type
            )
        )

    def emit_service_deployed(self, environment: str, service_instances: dict[str, Any]) -> None:
        """
        Emit a service deployment event.

        Args:
            environment: Name of the deployment environment
            service_instances: Dictionary of service name to service instance
        """
        self.emit_event(
            ServiceDeploymentEvent(environment=environment, service_instances=service_instances)
        )

    def emit_service_deployment_failed(self, environment: str, error: str, error_type: str) -> None:
        """
        Emit a service deployment failed event.

        Args:
            environment: Name of the deployment environment
            error: Error message
            error_type: Type of error
        """
        self.emit_event(
            ServiceDeploymentFailedEvent(
                environment=environment, error=error, error_type=error_type
            )
        )

    # Environment Events
    def emit_environment_initialized(
        self,
        environment_type: str,
        plugin_name: str,
        plugin_type: str,
        details: dict[str, Any] = None,
    ) -> None:
        """
        Emit an environment initialized event.

        Args:
            environment_type: Type of environment (network or execution)
            plugin_name: Name of the plugin
            plugin_type: Type of the plugin
            details: Additional details about the environment (optional)
        """
        event_data = {
            "environment_type": environment_type,
            "plugin_name": plugin_name,
            "plugin_type": plugin_type,
        }

        # Include details if provided
        if details:
            event_data.update(details)

        self.emit_event(EnvironmentInitializedEvent(**event_data))

    def emit_environment_setup_started(self, test_case: str, network_environment: str) -> None:
        """
        Emit an environment setup started event.

        Args:
            test_case: Name of the test case
            network_environment: Type of network environment
        """
        self.emit_event(
            EnvironmentSetupStartedEvent(
                environment_type=network_environment, details={"test_case": test_case}
            )
        )

    def emit_environment_setup_completed(
        self,
        test_case: str,
        network_environment: str,
        execution_environments: list[str],
        success: bool = True,
    ) -> None:
        """
        Emit an environment setup completed event.

        Args:
            test_case: Name of the test case
            network_environment: Name of the network environment
            execution_environments: List of execution environment names
            success: Whether setup was successful
        """
        self.emit_event(
            EnvironmentSetupCompletedEvent(
                environment_type="combined",
                success=success,
                details={
                    "test_case": test_case,
                    "network_environment": network_environment,
                    "execution_environments": execution_environments,
                },
            )
        )

    def emit_environment_setup_failed(
        self, test_case: str, error_message: str, error_type: str
    ) -> None:
        """
        Emit an environment setup failed event.

        Args:
            test_case: Name of the test case
            error_message: Error message from the failure
            error_type: Type of error that occurred
        """
        # Use the test_case as environment_name and "test_environment" as the environment_type
        self.emit_event(
            EnvironmentSetupFailedEvent(
                environment_name=test_case,
                environment_type="test_environment",
                error=f"{error_type}: {error_message}",
            )
        )

    def emit_environment_teardown(
        self, environment_type: str, success: bool = True, details: dict[str, Any] | None = None
    ) -> None:
        """
        Emit an environment teardown event.

        Args:
            environment_type: Type of environment being torn down
            success: Whether teardown was successful
            details: Additional teardown details
        """
        self.emit_event(
            EnvironmentTeardownEvent(
                environment_type=environment_type, success=success, details=details or {}
            )
        )

    # Step Events
    def emit_step_execution_started(self, test_case: str, steps: list[str]) -> None:
        """
        Emit a step execution started event.

        Args:
            test_case: Name of the test case
            steps: List of step names to execute
        """
        self.emit_event(StepExecutionStartedEvent(test_case=test_case, steps=steps))

    def emit_step_progress(self, step_id: str, progress: float, message: str | None = None) -> None:
        """
        Emit a step progress event.

        Args:
            step_id: Identifier for the step
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        self.emit_event(StepProgressEvent(step_id=step_id, progress=progress, message=message))

    def emit_step_completed(
        self, step_id: str, success: bool, result: dict[str, Any] | None = None
    ) -> None:
        """
        Emit a step completed event.

        Args:
            step_id: Identifier for the step
            success: Whether the step completed successfully
            result: Result data from the step
        """
        self.emit_event(StepCompletedEvent(step_id=step_id, success=success, result=result or {}))

    def emit_step_execution_completed(self, test_case: str, completed_steps: list[str]) -> None:
        """
        Emit a step execution completed event.

        Args:
            test_case: Name of the test case
            completed_steps: List of steps that were completed
        """
        self.emit_event(
            StepExecutionCompletedEvent(test_case=test_case, completed_steps=completed_steps)
        )

    def emit_step_unsupported(self, step_id: str, step_details: str, message: str) -> None:
        """
        Emit an unsupported step event.

        Args:
            step_id: Identifier for the step
            step_details: Details about the step
            message: Message describing the issue
        """
        self.emit_event(
            StepUnsupportedEvent(step_id=step_id, step_details=step_details, message=message)
        )

    # Assertion Events
    def emit_assertions_validation_started(
        self, test_case: str, assertions: list[dict[str, Any]]
    ) -> None:
        """
        Emit an assertions validation started event.

        Args:
            test_case: Name of the test case
            assertions: List of assertions to validate
        """
        self.emit_event(
            AssertionsValidationStartedEvent(test_case=test_case, assertions=assertions)
        )

    def emit_assertion_progress(
        self, assertion_type: str, service: str, endpoint: str, expected_status: int, status: str
    ) -> None:
        """
        Emit an assertion progress event.

        Args:
            assertion_type: Type of assertion being validated
            service: Service being validated
            endpoint: Endpoint being validated
            expected_status: Expected status code
            status: Current status of the validation
        """
        self.emit_event(
            AssertionProgressEvent(
                assertion_type=assertion_type,
                service=service,
                endpoint=endpoint,
                expected_status=expected_status,
                status=status,
            )
        )

    def emit_assertion_result(
        self,
        assertion_type: str,
        service: str,
        endpoint: str,
        expected_status: int,
        success: bool,
        actual_status: int | None = None,
        message: str = "",
    ) -> None:
        """
        Emit an assertion result event.

        Args:
            assertion_type: Type of assertion
            service: Service that was validated
            endpoint: Endpoint that was validated
            expected_status: Expected status code
            success: Whether the assertion passed
            actual_status: Actual status code received
            message: Additional message
        """
        self.emit_event(
            AssertionResultEvent(
                assertion_type=assertion_type,
                service=service,
                endpoint=endpoint,
                expected_status=expected_status,
                success=success,
                actual_status=actual_status,
                message=message,
            )
        )

    def emit_assertion_unknown(self, assertion_type: str, details: dict[str, Any]) -> None:
        """
        Emit an unknown assertion type event.

        Args:
            assertion_type: Type of the unknown assertion
            details: Details about the assertion
        """
        self.emit_event(AssertionUnknownEvent(assertion_type=assertion_type, details=details))

    def emit_assertion_error(
        self, assertion_type: str, error_message: str, error_type: str, details: dict[str, Any]
    ) -> None:
        """
        Emit an assertion error event.

        Args:
            assertion_type: Type of assertion
            error_message: Error message
            error_type: Type of error
            details: Assertion details
        """
        self.emit_event(
            AssertionErrorEvent(
                assertion_type=assertion_type,
                error_message=error_message,
                error_type=error_type,
                details=details,
            )
        )

    def emit_assertions_validation_completed(
        self, test_case: str, all_passed: bool, results: dict[str, Any]
    ) -> None:
        """
        Emit an assertions validation completed event.

        Args:
            test_case: Name of the test case
            all_passed: Whether all assertions passed
            results: Results of the assertion validation
        """
        self.emit_event(
            AssertionsValidationCompletedEvent(
                test_case=test_case, all_passed=all_passed, results=results
            )
        )

    def emit_service_event(self, name: str, data: dict[str, Any] = None) -> None:
        """
        Emit a service event.

        Args:
            name: Name of the service event
            data: Event details
        """
        self.emit_event(ServiceEvent(name=name, data=data or {}))

    def emit_service_started(self, service_name: str, details: dict[str, Any] = None) -> None:
        """
        Emit a service started event.

        Args:
            service_name: Name of the service that started
            details: Additional details about the service start
        """
        self.emit_service_event(
            name="service_started", data={"service_name": service_name, **(details or {})}
        )

    def emit_service_stopped(
        self, service_name: str, success: bool = True, details: dict[str, Any] = None
    ) -> None:
        """
        Emit a service stopped event.

        Args:
            service_name: Name of the service that stopped
            success: Whether the service stopped cleanly
            details: Additional details about the service stop
        """
        self.emit_service_event(
            name="service_stopped",
            data={"service_name": service_name, "success": success, **(details or {})},
        )

    def emit_service_error(
        self, service_name: str, error_type: str, error_message: str, details: dict[str, Any] = None
    ) -> None:
        """
        Emit a service error event.

        Args:
            service_name: Name of the service with the error
            error_type: Type of error
            error_message: Error message
            details: Additional error details
        """
        self.emit_service_event(
            name="service_error",
            data={
                "service_name": service_name,
                "error_type": error_type,
                "error_message": error_message,
                **(details or {}),
            },
        )
