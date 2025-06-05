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
    MetricCollectedEvent,
    TimingMetricEvent,
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
                stack_trace=error_type,
                error_message=error_message,
                error_details=details or {},
            )
        )

    def emit_environment_setup_started(
        self, environment_type: str, details: dict[str, Any] = None
    ) -> None:
        """
        Emit an environment setup started event.

        Args:
            environment_type: Type of environment
            details: Additional setup details
        """
        self.emit_event(
            EnvironmentSetupStartedEvent(environment_type=environment_type, details=details or {})
        )

    def emit_environment_setup_completed(
        self, environment_type: str, success: bool, details: dict[str, Any] = None
    ) -> None:
        """
        Emit an environment setup completed event.

        Args:
            environment_type: Type of environment
            success: Whether setup was successful
            details: Additional completion details
        """
        self.emit_event(
            EnvironmentSetupCompletedEvent(
                environment_type=environment_type, success=success, details=details or {}
            )
        )

    def emit_environment_teardown(
        self, environment_type: str, success: bool, details: dict[str, Any] = None
    ) -> None:
        """
        Emit an environment teardown event.

        Args:
            environment_type: Type of environment
            success: Whether teardown was successful
            details: Additional teardown details
        """
        self.emit_event(
            EnvironmentTeardownEvent(
                environment_type=environment_type, success=success, details=details or {}
            )
        )

    def emit_service_event(self, name: str, data: dict[str, Any] = None) -> None:
        """
        Emit a service lifecycle event.

        Args:
            name: Event name (e.g., "service.setup", "service.deployed", "services_deployed")
            data: Event data with service details
        """
        event_data = data or {}

        self.emit_event(ServiceEvent(name=name, data=event_data))

    def emit_step_progress(
        self, step_id: str, progress: float, details: dict[str, Any] = None
    ) -> None:
        """
        Emit a step progress event.

        Args:
            step_id: Step identifier
            progress: Progress value (0.0 to 1.0)
            details: Additional progress details
        """
        self.emit_event(
            StepProgressEvent(step_id=step_id, progress=progress, details=details or {})
        )

    def emit_step_completed(
        self, step_id: str, success: bool, result: dict[str, Any] = None
    ) -> None:
        """
        Emit a step completed event.

        Args:
            step_id: Step identifier
            success: Whether the step completed successfully
            result: Step execution result
        """
        self.emit_event(StepCompletedEvent(step_id=step_id, success=success, result=result or {}))

    def emit_timing_metric(
        self,
        metric_name: str,
        duration_ms: int,
        step_id: str = None,
        test_id: str = None,
        details: dict[str, Any] = None,
    ) -> None:
        """
        Emit a timing metric event.

        Args:
            metric_name: Name of the timing metric
            duration_ms: Duration in milliseconds
            step_id: Optional step identifier
            test_id: Optional test identifier
            details: Additional metric details
        """
        data = {"metric_name": metric_name, "duration": duration_ms}
        if step_id:
            data["step_id"] = step_id
        if test_id:
            data["test_case"] = test_id
        if details:
            data["metadata"] = details

        self.emit_event(TimingMetricEvent(**data))

    def emit_metric(
        self,
        metric_type: str,
        metric_name: str,
        value: Any,
        step_id: str = None,
        test_id: str = None,
        details: dict[str, Any] = None,
    ) -> None:
        """
        Emit a metric collected event.

        Args:
            metric_type: Type of the metric
            metric_name: Name of the metric
            value: Metric value
            step_id: Optional step identifier
            test_id: Optional test identifier
            details: Additional metric details
        """
        data = {"metric_type": metric_type, "metric_name": metric_name, "value": value}
        if step_id:
            data["step_id"] = step_id
        if test_id:
            data["test_case"] = test_id
        if details:
            data["metadata"] = details

        self.emit_event(MetricCollectedEvent(**data))
