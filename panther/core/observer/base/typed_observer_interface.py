"""Typed Observer Interface Module - Automatic event routing for PANTHER observers.

This module provides ``ITypedObserver``, an enhanced observer interface that
extends ``IObserver`` with automatic event routing to typed handler methods.
Instead of implementing a single ``on_event()`` with manual type-switching,
subclasses override only the ``on_*`` handler methods they need.

The ``on_event()`` implementation in ``ITypedObserver`` uses an internal
``_event_handlers`` dictionary that maps event classes to handler methods.
Unknown event types fall through to ``on_unknown_event()``.

Handler categories:
    - **Experiment**: ``on_experiment_initialized``, ``on_experiment_completed``, etc.
    - **Test**: ``on_test_created``, ``on_test_execution_started``, ``on_test_failed``, etc.
    - **Service**: ``on_service_created``, ``on_service_deployment_started``, etc.
    - **Environment**: ``on_environment_created``, ``on_network_setup_started``, etc.
    - **Step**: ``on_step_execution_started``, ``on_step_progress``, etc.
    - **Assertion**: ``on_assertions_validation_started``, ``on_assertion_result``, etc.
    - **Metrics**: ``on_metric_collected``, ``on_resource_metric``, etc.
    - **Plugin**: ``on_plugin_loading_started``, ``on_plugin_error``, etc.

Example:
    Create a typed observer that only handles test lifecycle events::

        from panther.core.observer.base.typed_observer_interface import ITypedObserver

        class TestLifecycleObserver(ITypedObserver):
            def on_test_created(self, event):
                print(f"Test created: {event.entity_id}")

            def on_test_completed(self, event):
                print(f"Test completed: {event.entity_id}")

            def on_test_failed(self, event):
                print(f"Test FAILED: {event.entity_id}")

See Also:
    `panther.core.observer.base.observer_interface.IObserver`
"""

import logging
from collections.abc import Callable
from typing import Dict

from panther.core.events.assertion.events import (
    AssertionErrorEvent,
    AssertionProgressEvent,
    AssertionResultEvent,
    AssertionsValidationCompletedEvent,
    AssertionsValidationStartedEvent,
    AssertionUnknownEvent,
)
from panther.core.events.base.event_base import BaseEvent
from panther.core.events.environment.events import (
    EnvironmentCreatedEvent,
    EnvironmentErrorEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentSetupFailedEvent,
    EnvironmentSetupStartedEvent,
    EnvironmentTeardownCompletedEvent,
    EnvironmentTeardownStartedEvent,
    ExecutionEnvironmentLimitExceededEvent,
    ExecutionEnvironmentResourceMonitoringEvent,
    ExecutionEnvironmentSetupCompletedEvent,
    ExecutionEnvironmentSetupStartedEvent,
    NetworkSetupCompletedEvent,
    NetworkSetupFailedEvent,
    NetworkSetupStartedEvent,
    NetworkTeardownCompletedEvent,
    NetworkTeardownStartedEvent,
    OutputCollectionCompletedEvent,
    OutputCollectionStartedEvent,
)
from panther.core.events.experiment.events import (
    ExperimentCompletedEvent,
    ExperimentExecutionCompletedEvent,
    ExperimentExecutionFailedEvent,
    ExperimentExecutionStartedEvent,
    ExperimentFailedEvent,
    ExperimentFinishedEarlyEvent,
    ExperimentInitializedEvent,
    ExperimentPluginLoadingCompletedEvent,
    ExperimentPluginLoadingFailedEvent,
    ExperimentPluginLoadingStartedEvent,
    ExperimentTestCasesInitializedEvent,
)
from panther.core.events.metrics.events import (
    CounterMetricEvent,
    MetricCollectedEvent,
    MetricsSummaryEvent,
    ResourceMetricEvent,
    TimingMetricEvent,
)
from panther.core.events.plugin.events import (
    PluginErrorEvent,
    PluginInitializedEvent,
    PluginLoadingCompletedEvent,
    PluginLoadingFailedEvent,
    PluginLoadingStartedEvent,
    PluginServiceCreatedEvent,
    PluginServiceStartedEvent,
    PluginServiceStoppedEvent,
    PluginStartedEvent,
    PluginStoppedEvent,
)
from panther.core.events.service.events import (
    CommandGeneratedEvent,
    CommandGenerationStartedEvent,
    DockerBuildCompletedEvent,
    DockerBuildStartedEvent,
    ServiceCreatedEvent,
    ServiceDeploymentCompletedEvent,
    ServiceDeploymentFailedEvent,
    ServiceDeploymentStartedEvent,
    ServiceDestroyedEvent,
    ServiceErrorEvent,
    ServiceHealthCheckFailedEvent,
    ServiceHealthCheckPassedEvent,
    ServicePreparationCompletedEvent,
    ServicePreparationFailedEvent,
    ServicePreparationStartedEvent,
    ServiceReadyEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
    ServiceTestResultsEvent,
    TesterAnalysisCompletedEvent,
    TesterAnalysisStartedEvent,
)
from panther.core.events.step.events import (
    StepExecutionCompletedEvent,
    StepExecutionFailedEvent,
    StepExecutionStartedEvent,
    StepProgressEvent,
    StepSkippedEvent,
    StepUnsupportedEvent,
)
from panther.core.events.test.events import (
    TestAssertionCheckedEvent,
    TestAssertionsCompletedEvent,
    TestAssertionsFailedEvent,
    TestAssertionsStartedEvent,
    TestCompletedEvent,
    TestCreatedEvent,
    TestDeploymentCompletedEvent,
    TestDeploymentFailedEvent,
    TestDeploymentStartedEvent,
    TestEnvironmentSetupCompletedEvent,
    TestEnvironmentSetupFailedEvent,
    TestEnvironmentSetupStartedEvent,
    TestExecutionCompletedEvent,
    TestExecutionFailedEvent,
    TestExecutionStartedEvent,
    TestFailedEvent,
    TestSetupCompletedEvent,
    TestSetupFailedEvent,
    TestSetupStartedEvent,
    TestStepCompletedEvent,
    TestStepFailedEvent,
    TestStepStartedEvent,
    TestTeardownCompletedEvent,
    TestTeardownStartedEvent,
)

from .observer_interface import IObserver


class ITypedObserver(IObserver):
    """Enhanced observer interface with automatic event routing to typed handlers.

    Extends ``IObserver`` to provide specific ``on_*`` handler methods for each
    event type in the PANTHER event system. The ``on_event()`` method automatically
    routes events to their typed handler based on ``type(event)``. Subclasses
    override only the handlers they need; all default handlers return ``True``.

    The ``is_interested()`` implementation checks whether any registered handler
    class name contains the queried event type string (partial string matching),
    so registering for ``ExperimentCompletedEvent`` means ``is_interested("Experiment")``
    returns ``True``.

    Error handling:
        - Exceptions in individual handlers are caught and logged without
          propagating to other observers.
        - ``RecursionError`` is caught specially and printed to stderr.
        - Error/failure event handlers (``TestFailedEvent``, ``ServiceErrorEvent``,
          ``ExperimentFailedEvent``) print to stderr to avoid cascading events.

    Attributes:
        _event_handlers: Dict mapping event classes to their handler callables.
            Populated during ``__init__`` with all known PANTHER event types.

    Example:
        Using match-based dispatch in a typed observer::

            class MyTypedObserver(ITypedObserver):
                def on_test_execution_started(self, event):
                    print(f"Test started: {event.entity_id}")
                    return True

                def on_test_execution_completed(self, event):
                    print(f"Test completed: {event.entity_id}")
                    return True
    """

    def __init__(self):
        """Initialize ITypedObserver."""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Event type to handler mapping for automatic routing
        self._event_handlers: Dict[type[BaseEvent], Callable] = {
            # Experiment events
            ExperimentInitializedEvent: self.on_experiment_initialized,
            ExperimentPluginLoadingStartedEvent: self.on_experiment_plugin_loading_started,
            ExperimentPluginLoadingCompletedEvent: self.on_experiment_plugin_loading_completed,
            ExperimentPluginLoadingFailedEvent: self.on_experiment_plugin_loading_failed,
            ExperimentTestCasesInitializedEvent: self.on_experiment_test_cases_initialized,
            ExperimentExecutionStartedEvent: self.on_experiment_execution_started,
            ExperimentExecutionCompletedEvent: self.on_experiment_execution_completed,
            ExperimentExecutionFailedEvent: self.on_experiment_execution_failed,
            ExperimentFinishedEarlyEvent: self.on_experiment_finished_early,
            ExperimentCompletedEvent: self.on_experiment_completed,
            ExperimentFailedEvent: self.on_experiment_failed,
            # Test events
            TestCreatedEvent: self.on_test_created,
            TestSetupStartedEvent: self.on_test_setup_started,
            TestSetupCompletedEvent: self.on_test_setup_completed,
            TestSetupFailedEvent: self.on_test_setup_failed,
            TestEnvironmentSetupStartedEvent: self.on_test_environment_setup_started,
            TestEnvironmentSetupCompletedEvent: self.on_test_environment_setup_completed,
            TestEnvironmentSetupFailedEvent: self.on_test_environment_setup_failed,
            TestDeploymentStartedEvent: self.on_test_deployment_started,
            TestDeploymentCompletedEvent: self.on_test_deployment_completed,
            TestDeploymentFailedEvent: self.on_test_deployment_failed,
            TestExecutionStartedEvent: self.on_test_execution_started,
            TestStepStartedEvent: self.on_test_step_started,
            TestStepCompletedEvent: self.on_test_step_completed,
            TestStepFailedEvent: self.on_test_step_failed,
            TestAssertionsStartedEvent: self.on_test_assertions_started,
            TestAssertionCheckedEvent: self.on_test_assertion_checked,
            TestAssertionsCompletedEvent: self.on_test_assertions_completed,
            TestAssertionsFailedEvent: self.on_test_assertions_failed,
            TestExecutionCompletedEvent: self.on_test_execution_completed,
            TestExecutionFailedEvent: self.on_test_execution_failed,
            TestTeardownStartedEvent: self.on_test_teardown_started,
            TestTeardownCompletedEvent: self.on_test_teardown_completed,
            TestCompletedEvent: self.on_test_completed,
            TestFailedEvent: self.on_test_failed,
            # Service events
            ServiceCreatedEvent: self.on_service_created,
            ServicePreparationStartedEvent: self.on_service_preparation_started,
            ServicePreparationCompletedEvent: self.on_service_preparation_completed,
            ServicePreparationFailedEvent: self.on_service_preparation_failed,
            ServiceDeploymentStartedEvent: self.on_service_deployment_started,
            ServiceDeploymentCompletedEvent: self.on_service_deployment_completed,
            ServiceDeploymentFailedEvent: self.on_service_deployment_failed,
            ServiceStartedEvent: self.on_service_started,
            ServiceReadyEvent: self.on_service_ready,
            ServiceHealthCheckPassedEvent: self.on_service_health_check_passed,
            ServiceHealthCheckFailedEvent: self.on_service_health_check_failed,
            ServiceStoppedEvent: self.on_service_stopped,
            ServiceErrorEvent: self.on_service_error,
            ServiceDestroyedEvent: self.on_service_destroyed,
            ServiceTestResultsEvent: self.on_service_test_results,
            CommandGenerationStartedEvent: self.on_command_generation_started,
            CommandGeneratedEvent: self.on_command_generated,
            DockerBuildStartedEvent: self.on_docker_build_started,
            DockerBuildCompletedEvent: self.on_docker_build_completed,
            TesterAnalysisStartedEvent: self.on_tester_analysis_started,
            TesterAnalysisCompletedEvent: self.on_tester_analysis_completed,
            # Environment events
            EnvironmentCreatedEvent: self.on_environment_created,
            EnvironmentSetupStartedEvent: self.on_environment_setup_started,
            EnvironmentSetupCompletedEvent: self.on_environment_setup_completed,
            EnvironmentSetupFailedEvent: self.on_environment_setup_failed,
            EnvironmentTeardownStartedEvent: self.on_environment_teardown_started,
            EnvironmentTeardownCompletedEvent: self.on_environment_teardown_completed,
            EnvironmentErrorEvent: self.on_environment_error,
            NetworkSetupStartedEvent: self.on_network_setup_started,
            NetworkSetupCompletedEvent: self.on_network_setup_completed,
            NetworkSetupFailedEvent: self.on_network_setup_failed,
            NetworkTeardownStartedEvent: self.on_network_teardown_started,
            NetworkTeardownCompletedEvent: self.on_network_teardown_completed,
            ExecutionEnvironmentSetupStartedEvent: self.on_execution_environment_setup_started,
            ExecutionEnvironmentSetupCompletedEvent: self.on_execution_environment_setup_completed,
            ExecutionEnvironmentResourceMonitoringEvent: self.on_execution_environment_resource_monitoring,
            ExecutionEnvironmentLimitExceededEvent: self.on_execution_environment_limit_exceeded,
            # Step events
            StepExecutionStartedEvent: self.on_step_execution_started,
            StepExecutionCompletedEvent: self.on_step_execution_completed,
            StepExecutionFailedEvent: self.on_step_execution_failed,
            StepProgressEvent: self.on_step_progress,
            StepUnsupportedEvent: self.on_step_unsupported,
            StepSkippedEvent: self.on_step_skipped,
            # Assertion events
            AssertionsValidationStartedEvent: self.on_assertions_validation_started,
            AssertionsValidationCompletedEvent: self.on_assertions_validation_completed,
            AssertionProgressEvent: self.on_assertion_progress,
            AssertionResultEvent: self.on_assertion_result,
            AssertionErrorEvent: self.on_assertion_error,
            AssertionUnknownEvent: self.on_assertion_unknown,
            # Metrics events
            MetricCollectedEvent: self.on_metric_collected,
            ResourceMetricEvent: self.on_resource_metric,
            TimingMetricEvent: self.on_timing_metric,
            CounterMetricEvent: self.on_counter_metric,
            MetricsSummaryEvent: self.on_metrics_summary,
            # Plugin events
            PluginLoadingStartedEvent: self.on_plugin_loading_started,
            PluginLoadingCompletedEvent: self.on_plugin_loading_completed,
            PluginLoadingFailedEvent: self.on_plugin_loading_failed,
            PluginInitializedEvent: self.on_plugin_initialized,
            PluginStartedEvent: self.on_plugin_started,
            PluginStoppedEvent: self.on_plugin_stopped,
            PluginErrorEvent: self.on_plugin_error,
            PluginServiceCreatedEvent: self.on_plugin_service_created,
            PluginServiceStartedEvent: self.on_plugin_service_started,
            PluginServiceStoppedEvent: self.on_plugin_service_stopped,
        }

    def on_event(self, event: BaseEvent):
        """Route an event to its specific typed handler method.

        Looks up ``type(event)`` in ``_event_handlers`` to find the matching
        handler. Falls back to ``on_unknown_event()`` for unregistered event
        types. Catches exceptions per handler to prevent cascading failures.

        Args:
            event: The event to route and handle.

        Returns:
            The return value from the matched handler, or False on error.
        """
        # Track processed event
        if hasattr(event, "event_id"):
            self.processed_events_uuids.append(event.event_id)

        # Get the handler for this event type
        event_type = type(event)
        handler = self._event_handlers.get(event_type)

        if not handler:
            # Fall back to generic handler for unknown event types
            return self.on_unknown_event(event)
        try:
            return handler(event)
        except RecursionError:
            # Special handling for recursion errors - just log to stderr
            import sys

            print(f"RecursionError in {event_type.__name__} handler", file=sys.stderr)
            return False
        except Exception as e:
            # Avoid logging errors that might trigger more events
            if event_type.__name__ in [
                "TestFailedEvent",
                "ServiceErrorEvent",
                "ExperimentFailedEvent",
            ]:
                # For error events, just print to stderr to avoid cascading
                import sys

                print(
                    f"Error handling {event_type.__name__}: {str(e)}",
                    file=sys.stderr,
                )
            else:
                self.logger.error(
                    "Error handling %s event: %s",
                    event_type.__name__,
                    str(e),
                    exc_info=True,
                )
            return False

    def on_unknown_event(self, event: BaseEvent) -> bool:
        """Handle event types not in the ``_event_handlers`` mapping.

        Default implementation logs a debug warning and returns True.
        Override this method to handle custom or unregistered event types.

        Args:
            event: The unrecognized event.

        Returns:
            True by default; override to return False to signal a problem.
        """
        self.logger.debug(
            "Received unknown event type: %s in observer: %s",
            type(event).__name__,
            self.__class__.__name__,
        )
        return True

    # Experiment event handlers
    def on_experiment_initialized(self, event: ExperimentInitializedEvent) -> bool:
        """Handle experiment initialized event."""
        return True

    def on_experiment_plugin_loading_started(
        self, event: ExperimentPluginLoadingStartedEvent
    ) -> bool:
        """Handle experiment plugin loading started event."""
        return True

    def on_experiment_plugin_loading_completed(
        self, event: ExperimentPluginLoadingCompletedEvent
    ) -> bool:
        """Handle experiment plugin loading completed event."""
        return True

    def on_experiment_plugin_loading_failed(
        self, event: ExperimentPluginLoadingFailedEvent
    ) -> bool:
        """Handle experiment plugin loading failed event."""
        return True

    def on_experiment_test_cases_initialized(
        self, event: ExperimentTestCasesInitializedEvent
    ) -> bool:
        """Handle experiment test cases initialized event."""
        return True

    def on_experiment_execution_started(
        self, event: ExperimentExecutionStartedEvent
    ) -> bool:
        """Handle experiment execution started event."""
        return True

    def on_experiment_execution_completed(
        self, event: ExperimentExecutionCompletedEvent
    ) -> bool:
        """Handle experiment execution completed event."""
        return True

    def on_experiment_execution_failed(
        self, event: ExperimentExecutionFailedEvent
    ) -> bool:
        """Handle experiment execution failed event."""
        return True

    def on_experiment_finished_early(self, event: ExperimentFinishedEarlyEvent) -> bool:
        """Handle experiment finished early event."""
        return True

    def on_experiment_completed(self, event: ExperimentCompletedEvent) -> bool:
        """Handle experiment completed event."""
        return True

    def on_experiment_failed(self, event: ExperimentFailedEvent) -> bool:
        """Handle experiment failed event."""
        return True

    # Test event handlers
    def on_test_created(self, event: TestCreatedEvent) -> bool:
        """Handle test created event."""
        return True

    def on_test_setup_started(self, event: TestSetupStartedEvent) -> bool:
        """Handle test setup started event."""
        return True

    def on_test_setup_completed(self, event: TestSetupCompletedEvent) -> bool:
        """Handle test setup completed event."""
        return True

    def on_test_setup_failed(self, event: TestSetupFailedEvent) -> bool:
        """Handle test setup failed event."""
        return True

    def on_test_environment_setup_started(
        self, event: TestEnvironmentSetupStartedEvent
    ) -> bool:
        """Handle test environment setup started event."""
        return True

    def on_test_environment_setup_completed(
        self, event: TestEnvironmentSetupCompletedEvent
    ) -> bool:
        """Handle test environment setup completed event."""
        return True

    def on_test_environment_setup_failed(
        self, event: TestEnvironmentSetupFailedEvent
    ) -> bool:
        """Handle test environment setup failed event."""
        return True

    def on_test_deployment_started(self, event: TestDeploymentStartedEvent) -> bool:
        """Handle test deployment started event."""
        return True

    def on_test_deployment_completed(self, event: TestDeploymentCompletedEvent) -> bool:
        """Handle test deployment completed event."""
        return True

    def on_test_deployment_failed(self, event: TestDeploymentFailedEvent) -> bool:
        """Handle test deployment failed event."""
        return True

    def on_test_execution_started(self, event: TestExecutionStartedEvent) -> bool:
        """Handle test execution started event."""
        return True

    def on_test_step_started(self, event: TestStepStartedEvent) -> bool:
        """Handle test step started event."""
        return True

    def on_test_step_completed(self, event: TestStepCompletedEvent) -> bool:
        """Handle test step completed event."""
        return True

    def on_test_step_failed(self, event: TestStepFailedEvent) -> bool:
        """Handle test step failed event."""
        return True

    def on_test_assertions_started(self, event: TestAssertionsStartedEvent) -> bool:
        """Handle test assertions started event."""
        return True

    def on_test_assertion_checked(self, event: TestAssertionCheckedEvent) -> bool:
        """Handle test assertion checked event."""
        return True

    def on_test_assertions_completed(self, event: TestAssertionsCompletedEvent) -> bool:
        """Handle test assertions completed event."""
        return True

    def on_test_assertions_failed(self, event: TestAssertionsFailedEvent) -> bool:
        """Handle test assertions failed event."""
        return True

    def on_test_execution_completed(self, event: TestExecutionCompletedEvent) -> bool:
        """Handle test execution completed event."""
        return True

    def on_test_execution_failed(self, event: TestExecutionFailedEvent) -> bool:
        """Handle test execution failed event."""
        return True

    def on_test_teardown_started(self, event: TestTeardownStartedEvent) -> bool:
        """Handle test teardown started event."""
        return True

    def on_test_teardown_completed(self, event: TestTeardownCompletedEvent) -> bool:
        """Handle test teardown completed event."""
        return True

    def on_test_completed(self, event: TestCompletedEvent) -> bool:
        """Handle test completed event."""
        return True

    def on_test_failed(self, event: TestFailedEvent) -> bool:
        """Handle test failed event."""
        return True

    # Service event handlers
    def on_service_created(self, event: ServiceCreatedEvent) -> bool:
        """Handle service created event."""
        return True

    def on_service_preparation_started(
        self, event: ServicePreparationStartedEvent
    ) -> bool:
        """Handle service preparation started event."""
        return True

    def on_service_preparation_completed(
        self, event: ServicePreparationCompletedEvent
    ) -> bool:
        """Handle service preparation completed event."""
        return True

    def on_service_preparation_failed(
        self, event: ServicePreparationFailedEvent
    ) -> bool:
        """Handle service preparation failed event."""
        return True

    def on_service_deployment_started(
        self, event: ServiceDeploymentStartedEvent
    ) -> bool:
        """Handle service deployment started event."""
        return True

    def on_service_deployment_completed(
        self, event: ServiceDeploymentCompletedEvent
    ) -> bool:
        """Handle service deployment completed event."""
        return True

    def on_service_deployment_failed(self, event: ServiceDeploymentFailedEvent) -> bool:
        """Handle service deployment failed event."""
        return True

    def on_service_started(self, event: ServiceStartedEvent) -> bool:
        """Handle service started event."""
        return True

    def on_service_ready(self, event: ServiceReadyEvent) -> bool:
        """Handle service ready event."""
        return True

    def on_service_health_check_passed(
        self, event: ServiceHealthCheckPassedEvent
    ) -> bool:
        """Handle service health check passed event."""
        return True

    def on_service_health_check_failed(
        self, event: ServiceHealthCheckFailedEvent
    ) -> bool:
        """Handle service health check failed event."""
        return True

    def on_service_stopped(self, event: ServiceStoppedEvent) -> bool:
        """Handle service stopped event."""
        return True

    def on_service_error(self, event: ServiceErrorEvent) -> bool:
        """Handle service error event."""
        return True

    def on_service_destroyed(self, event: ServiceDestroyedEvent) -> bool:
        """Handle service destroyed event."""
        return True

    def on_service_test_results(self, event: ServiceTestResultsEvent) -> bool:
        """Handle service test results event."""
        return True

    def on_command_generation_started(
        self, event: CommandGenerationStartedEvent
    ) -> bool:
        """Handle command generation started event."""
        return True

    def on_command_generated(self, event: CommandGeneratedEvent) -> bool:
        """Handle command generated event."""
        return True

    def on_docker_build_started(self, event: DockerBuildStartedEvent) -> bool:
        """Handle Docker build started event."""
        return True

    def on_docker_build_completed(self, event: DockerBuildCompletedEvent) -> bool:
        """Handle Docker build completed event."""
        return True

    def on_tester_analysis_started(self, event: TesterAnalysisStartedEvent) -> bool:
        """Handle tester analysis started event."""
        return True

    def on_tester_analysis_completed(self, event: TesterAnalysisCompletedEvent) -> bool:
        """Handle tester analysis completed event."""
        return True

    # Environment event handlers
    def on_environment_created(self, event: EnvironmentCreatedEvent) -> bool:
        """Handle environment created event."""
        return True

    def on_environment_setup_started(self, event: EnvironmentSetupStartedEvent) -> bool:
        """Handle environment setup started event."""
        return True

    def on_environment_setup_completed(
        self, event: EnvironmentSetupCompletedEvent
    ) -> bool:
        """Handle environment setup completed event."""
        return True

    def on_environment_setup_failed(self, event: EnvironmentSetupFailedEvent) -> bool:
        """Handle environment setup failed event."""
        return True

    def on_environment_teardown_started(
        self, event: EnvironmentTeardownStartedEvent
    ) -> bool:
        """Handle environment teardown started event."""
        return True

    def on_environment_teardown_completed(
        self, event: EnvironmentTeardownCompletedEvent
    ) -> bool:
        """Handle environment teardown completed event."""
        return True

    def on_environment_error(self, event: EnvironmentErrorEvent) -> bool:
        """Handle environment error event."""
        return True

    # Network Environment event handlers
    def on_network_setup_started(self, event: NetworkSetupStartedEvent) -> bool:
        """Handle network setup started event."""
        return True

    def on_network_setup_completed(self, event: NetworkSetupCompletedEvent) -> bool:
        """Handle network setup completed event."""
        return True

    def on_network_setup_failed(self, event: NetworkSetupFailedEvent) -> bool:
        """Handle network setup failed event."""
        return True

    def on_network_teardown_started(self, event: NetworkTeardownStartedEvent) -> bool:
        """Handle network teardown started event."""
        return True

    def on_network_teardown_completed(
        self, event: NetworkTeardownCompletedEvent
    ) -> bool:
        """Handle network teardown completed event."""
        return True

    # Execution Environment event handlers
    def on_execution_environment_setup_started(
        self, event: ExecutionEnvironmentSetupStartedEvent
    ) -> bool:
        """Handle execution environment setup started event."""
        return True

    def on_execution_environment_setup_completed(
        self, event: ExecutionEnvironmentSetupCompletedEvent
    ) -> bool:
        """Handle execution environment setup completed event."""
        return True

    def on_execution_environment_resource_monitoring(
        self, event: ExecutionEnvironmentResourceMonitoringEvent
    ) -> bool:
        """Handle execution environment resource monitoring event."""
        return True

    def on_execution_environment_limit_exceeded(
        self, event: ExecutionEnvironmentLimitExceededEvent
    ) -> bool:
        """Handle execution environment limit exceeded event."""
        return True

    # Step event handlers
    def on_step_execution_started(self, event: StepExecutionStartedEvent) -> bool:
        """Handle step execution started event."""
        return True

    def on_step_execution_completed(self, event: StepExecutionCompletedEvent) -> bool:
        """Handle step execution completed event."""
        return True

    def on_step_execution_failed(self, event: StepExecutionFailedEvent) -> bool:
        """Handle step execution failed event."""
        return True

    def on_step_progress(self, event: StepProgressEvent) -> bool:
        """Handle step progress event."""
        return True

    def on_step_unsupported(self, event: StepUnsupportedEvent) -> bool:
        """Handle step unsupported event."""
        return True

    def on_step_skipped(self, event: StepSkippedEvent) -> bool:
        """Handle step skipped event."""
        return True

    # Assertion event handlers
    def on_assertions_validation_started(
        self, event: AssertionsValidationStartedEvent
    ) -> bool:
        """Handle assertions validation started event."""
        return True

    def on_assertions_validation_completed(
        self, event: AssertionsValidationCompletedEvent
    ) -> bool:
        """Handle assertions validation completed event."""
        return True

    def on_assertion_progress(self, event: AssertionProgressEvent) -> bool:
        """Handle assertion progress event."""
        return True

    def on_assertion_result(self, event: AssertionResultEvent) -> bool:
        """Handle assertion result event."""
        return True

    def on_assertion_error(self, event: AssertionErrorEvent) -> bool:
        """Handle assertion error event."""
        return True

    def on_assertion_unknown(self, event: AssertionUnknownEvent) -> bool:
        """Handle assertion unknown event."""
        return True

    # Metrics event handlers
    def on_metric_collected(self, event: MetricCollectedEvent) -> bool:
        """Handle metric collected event."""
        return True

    def on_resource_metric(self, event: ResourceMetricEvent) -> bool:
        """Handle resource metric event."""
        return True

    def on_timing_metric(self, event: TimingMetricEvent) -> bool:
        """Handle timing metric event."""
        return True

    def on_counter_metric(self, event: CounterMetricEvent) -> bool:
        """Handle counter metric event."""
        return True

    def on_metrics_summary(self, event: MetricsSummaryEvent) -> bool:
        """Handle metrics summary event."""
        return True

    # Plugin event handlers
    def on_plugin_loading_started(self, event: PluginLoadingStartedEvent) -> bool:
        """Handle plugin loading started event."""
        return True

    def on_plugin_loading_completed(self, event: PluginLoadingCompletedEvent) -> bool:
        """Handle plugin loading completed event."""
        return True

    def on_plugin_loading_failed(self, event: PluginLoadingFailedEvent) -> bool:
        """Handle plugin loading failed event."""
        return True

    def on_plugin_initialized(self, event: PluginInitializedEvent) -> bool:
        """Handle plugin initialized event."""
        return True

    def on_plugin_started(self, event: PluginStartedEvent) -> bool:
        """Handle plugin started event."""
        return True

    def on_plugin_stopped(self, event: PluginStoppedEvent) -> bool:
        """Handle plugin stopped event."""
        return True

    def on_plugin_error(self, event: PluginErrorEvent) -> bool:
        """Handle plugin error event."""
        return True

    def on_plugin_service_created(self, event: PluginServiceCreatedEvent) -> bool:
        """Handle plugin service created event."""
        return True

    def on_plugin_service_started(self, event: PluginServiceStartedEvent) -> bool:
        """Handle plugin service started event."""
        return True

    def on_plugin_service_stopped(self, event: PluginServiceStoppedEvent) -> bool:
        """Handle plugin service stopped event."""
        return True

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer has a handler matching the event type.

        Uses partial string matching: checks if any handler class name
        contains ``event_type`` (case-insensitive). For example,
        ``is_interested("experiment")`` returns True if any experiment
        event handler is registered.

        Args:
            event_type: Event type string to check interest for.

        Returns:
            True if a matching handler exists.
        """
        # Convert string event type to class if possible
        for event_class in self._event_handlers:
            if event_class.__name__ == event_type:
                return True

        # Also check for partial matches (e.g., "experiment" matches all experiment events)
        event_type_lower = event_type.lower()
        for event_class in self._event_handlers:
            if event_type_lower in event_class.__name__.lower():
                return True

        return False
