"""
State Event Observer Module

This module provides an observer that listens to workflow and entity events
and updates the StateManager accordingly.
"""

import logging

from panther.core.observer.base.typed_observer_interface import ITypedObserver
from panther.core.state.state_manager import StateManager, WorkflowState, EntityState
from panther.core.events import (
    BaseEvent,
    # Experiment events
    ExperimentInitializedEvent,
    ExperimentPluginLoadingStartedEvent,
    ExperimentPluginLoadingFailedEvent,
    ExperimentCompletedEvent,
    ExperimentFailedEvent,
    # Test events
    TestCreatedEvent,
    TestSetupStartedEvent,
    TestSetupFailedEvent,
    TestDeploymentFailedEvent,
    TestExecutionStartedEvent,
    TestExecutionCompletedEvent,
    TestExecutionFailedEvent,
    TestCompletedEvent,
    TestFailedEvent,
    # Service events
    ServiceCreatedEvent,
    ServicePreparationStartedEvent,
    ServiceDeploymentCompletedEvent,
    ServiceStartedEvent,
    ServiceStoppedEvent,
    ServiceErrorEvent,
    ServiceDestroyedEvent,
    CommandGenerationStartedEvent,
    DockerBuildStartedEvent,
    TesterAnalysisStartedEvent,
    EnvironmentCreatedEvent,
    EnvironmentSetupStartedEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentSetupFailedEvent,
    EnvironmentTeardownCompletedEvent,
    EnvironmentErrorEvent,
    OutputCollectionStartedEvent,
)


class StateEventObserver(ITypedObserver):
    """
    Observer that updates StateManager based on workflow and entity events.

    This observer:
    - Subscribes to workflow events (experiment and test lifecycle)
    - Subscribes to entity events (service, environment lifecycle)
    - Updates StateManager when events indicate state changes
    - Maps event types to appropriate workflow/entity states
    - Handles errors gracefully
    """

    def __init__(self, state_manager: StateManager, priority: int = 100):
        """
        Initialize the state event observer.

        Args:
            state_manager: The StateManager instance to update
            priority: Observer priority (higher = processed earlier)
        """
        super().__init__()
        self.state_manager = state_manager
        self.priority = priority
        self.logger = logging.getLogger(self.__class__.__name__)

        # Track current experiment/workflow name
        self.current_experiment_id = None

    def get_priority(self) -> int:
        """Get the priority for this observer."""
        return self.priority

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer is interested in an event type."""
        # We're interested in most events that indicate state changes
        interesting_prefixes = [
            "experiment",
            "test",
            "service",
            "environment",
            "plugin_loading",
            "command_generation",
            "docker_build",
            "output_collection",
            "tester_analysis",
        ]

        event_type_lower = event_type.lower()
        return any(prefix in event_type_lower for prefix in interesting_prefixes)

    # Experiment/Workflow event handlers

    def on_experiment_initialized(self, event: ExperimentInitializedEvent) -> bool:
        """Handle experiment initialized event."""
        try:
            self.current_experiment_id = event.entity_id
            self.state_manager.set_workflow_state(event.entity_id, WorkflowState.CREATED)
            self.logger.debug(f"Set workflow state to CREATED for experiment {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling experiment initialized event: {e}")
        return True

    def on_experiment_plugin_loading_started(
        self, event: ExperimentPluginLoadingStartedEvent
    ) -> bool:
        """Handle plugin loading started event."""
        try:
            if self.current_experiment_id:
                self.state_manager.set_workflow_state(
                    self.current_experiment_id, WorkflowState.LOADING_PLUGINS
                )
                self.logger.debug(
                    f"Set workflow state to LOADING_PLUGINS for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling plugin loading started event: {e}")
        return True

    def on_command_generation_started(self, event: CommandGenerationStartedEvent) -> bool:
        """Handle command generation started event."""
        try:
            if self.current_experiment_id:
                self.state_manager.set_workflow_state(
                    self.current_experiment_id, WorkflowState.GENERATING_COMMANDS
                )
                self.logger.debug(
                    f"Set workflow state to GENERATING_COMMANDS for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling command generation started event: {e}")
        return True

    def on_docker_build_started(self, event: DockerBuildStartedEvent) -> bool:
        """Handle Docker build started event."""
        try:
            if self.current_experiment_id:
                self.state_manager.set_workflow_state(
                    self.current_experiment_id, WorkflowState.BUILDING_DOCKER
                )
                self.logger.debug(
                    f"Set workflow state to BUILDING_DOCKER for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling docker build started event: {e}")
        return True

    def on_environment_setup_started(self, event: EnvironmentSetupStartedEvent) -> bool:
        """Handle environment deployment started event."""
        try:
            if self.current_experiment_id:
                self.state_manager.set_workflow_state(
                    self.current_experiment_id, WorkflowState.DEPLOYING
                )
                self.logger.debug(
                    f"Set workflow state to DEPLOYING for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling environment setup started event: {e}")
        return True

    def on_test_execution_started(self, event: TestExecutionStartedEvent) -> bool:
        """Handle test execution started event."""
        try:
            if self.current_experiment_id:
                self.state_manager.set_workflow_state(
                    self.current_experiment_id, WorkflowState.RUNNING
                )
                self.logger.debug(
                    f"Set workflow state to RUNNING for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling test execution started event: {e}")
        return True

    def on_output_collection_started(self, event: OutputCollectionStartedEvent) -> bool:
        """Handle output collection started event."""
        try:
            if self.current_experiment_id:
                self.state_manager.set_workflow_state(
                    self.current_experiment_id, WorkflowState.COLLECTING_OUTPUTS
                )
                self.logger.debug(
                    f"Set workflow state to COLLECTING_OUTPUTS for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling output collection started event: {e}")
        return True

    def on_tester_analysis_started(self, event: TesterAnalysisStartedEvent) -> bool:
        """Handle tester analysis started event."""
        try:
            if self.current_experiment_id:
                self.state_manager.set_workflow_state(
                    self.current_experiment_id, WorkflowState.ANALYZING_RESULTS
                )
                self.logger.debug(
                    f"Set workflow state to ANALYZING_RESULTS for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling tester analysis started event: {e}")
        return True

    def on_test_completed(self, event: TestCompletedEvent) -> bool:
        """Handle test completed event."""
        try:
            if self.current_experiment_id:
                # When a test completes, we move to reporting results
                self.state_manager.set_workflow_state(
                    self.current_experiment_id, WorkflowState.REPORTING_RESULTS
                )
                self.logger.debug(
                    f"Set workflow state to REPORTING_RESULTS for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling test completed event: {e}")
        return True

    def on_experiment_completed(self, event: ExperimentCompletedEvent) -> bool:
        """Handle experiment completed event."""
        try:
            self.state_manager.set_workflow_state(event.entity_id, WorkflowState.COMPLETED)
            self.logger.debug(f"Set workflow state to COMPLETED for experiment {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling experiment completed event: {e}")
        return True

    def on_experiment_failed(self, event: ExperimentFailedEvent) -> bool:
        """Handle experiment failed event."""
        try:
            self.state_manager.set_workflow_state(event.entity_id, WorkflowState.FAILED)
            self.logger.debug(f"Set workflow state to FAILED for experiment {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling experiment failed event: {e}")
        return True

    # Entity state handlers for services

    def on_service_created(self, event: ServiceCreatedEvent) -> bool:
        """Handle service created event."""
        try:
            self.state_manager.set_entity_state("service", event.entity_id, EntityState.CREATED)
            self.logger.debug(f"Set entity state to CREATED for service {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling service created event: {e}")
        return True

    def on_service_initialized(self, event: BaseEvent) -> bool:
        """Handle service initialized event."""
        try:
            # Note: There's no direct ServiceInitializedEvent, but we can infer from preparation
            if hasattr(event, "entity_id"):
                self.state_manager.set_entity_state(
                    "service", event.entity_id, EntityState.INITIALIZED
                )
                self.logger.debug(f"Set entity state to INITIALIZED for service {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling service initialized event: {e}")
        return True

    def on_service_preparation_started(self, event: ServicePreparationStartedEvent) -> bool:
        """Handle service setup/preparation started event."""
        try:
            # First ensure it's initialized
            current_state = self.state_manager.get_entity_state("service", event.entity_id)
            if current_state == EntityState.CREATED:
                self.state_manager.set_entity_state(
                    "service", event.entity_id, EntityState.INITIALIZED
                )

            self.state_manager.set_entity_state("service", event.entity_id, EntityState.PREPARING)
            self.logger.debug(f"Set entity state to PREPARING for service {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling service preparation started event: {e}")
        return True

    def on_service_deployment_completed(self, event: ServiceDeploymentCompletedEvent) -> bool:
        """Handle service deployed event."""
        try:
            # When deployment completes, service is ready to run
            self.state_manager.set_entity_state("service", event.entity_id, EntityState.PREPARED)
            self.logger.debug(f"Set entity state to PREPARED for service {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling service deployment completed event: {e}")
        return True

    def on_service_started(self, event: ServiceStartedEvent) -> bool:
        """Handle service started event."""
        try:
            # First transition to STARTING then RUNNING
            current_state = self.state_manager.get_entity_state("service", event.entity_id)
            if current_state == EntityState.PREPARED:
                self.state_manager.set_entity_state(
                    "service", event.entity_id, EntityState.STARTING
                )

            self.state_manager.set_entity_state("service", event.entity_id, EntityState.RUNNING)
            self.logger.debug(f"Set entity state to RUNNING for service {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling service started event: {e}")
        return True

    def on_service_stopped(self, event: ServiceStoppedEvent) -> bool:
        """Handle service stopped event."""
        try:
            # First transition to STOPPING then STOPPED
            current_state = self.state_manager.get_entity_state("service", event.entity_id)
            if current_state == EntityState.RUNNING:
                self.state_manager.set_entity_state(
                    "service", event.entity_id, EntityState.STOPPING
                )

            self.state_manager.set_entity_state("service", event.entity_id, EntityState.STOPPED)
            self.logger.debug(f"Set entity state to STOPPED for service {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling service stopped event: {e}")
        return True

    def on_service_destroyed(self, event: ServiceDestroyedEvent) -> bool:
        """Handle service completed/destroyed event."""
        try:
            self.state_manager.set_entity_state("service", event.entity_id, EntityState.COMPLETED)
            self.logger.debug(f"Set entity state to COMPLETED for service {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling service destroyed event: {e}")
        return True

    def on_service_error(self, event: ServiceErrorEvent) -> bool:
        """Handle service error event."""
        try:
            self.state_manager.set_entity_state("service", event.entity_id, EntityState.FAILED)
            self.logger.debug(f"Set entity state to FAILED for service {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling service error event: {e}")
        return True

    # Entity state handlers for environments

    def on_environment_created(self, event: EnvironmentCreatedEvent) -> bool:
        """Handle environment created event."""
        try:
            self.state_manager.set_entity_state("environment", event.entity_id, EntityState.CREATED)
            self.logger.debug(f"Set entity state to CREATED for environment {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling environment created event: {e}")
        return True

    def on_environment_setup_completed(self, event: EnvironmentSetupCompletedEvent) -> bool:
        """Handle environment setup completed event."""
        try:
            self.state_manager.set_entity_state("environment", event.entity_id, EntityState.RUNNING)
            self.logger.debug(f"Set entity state to RUNNING for environment {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling environment setup completed event: {e}")
        return True

    def on_environment_teardown_completed(self, event: EnvironmentTeardownCompletedEvent) -> bool:
        """Handle environment teardown completed event."""
        try:
            self.state_manager.set_entity_state(
                "environment", event.entity_id, EntityState.COMPLETED
            )
            self.logger.debug(f"Set entity state to COMPLETED for environment {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling environment teardown completed event: {e}")
        return True

    def on_environment_error(self, event: EnvironmentErrorEvent) -> bool:
        """Handle environment error event."""
        try:
            self.state_manager.set_entity_state("environment", event.entity_id, EntityState.FAILED)
            self.logger.debug(f"Set entity state to FAILED for environment {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling environment error event: {e}")
        return True

    # Entity state handlers for tests

    def on_test_created(self, event: TestCreatedEvent) -> bool:
        """Handle test created event."""
        try:
            self.state_manager.set_entity_state("test", event.entity_id, EntityState.CREATED)
            self.logger.debug(f"Set entity state to CREATED for test {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling test created event: {e}")
        return True

    def on_test_setup_started(self, event: TestSetupStartedEvent) -> bool:
        """Handle test setup started event."""
        try:
            # First ensure it's initialized
            current_state = self.state_manager.get_entity_state("test", event.entity_id)
            if current_state == EntityState.CREATED:
                self.state_manager.set_entity_state(
                    "test", event.entity_id, EntityState.INITIALIZED
                )

            self.state_manager.set_entity_state("test", event.entity_id, EntityState.PREPARING)
            self.logger.debug(f"Set entity state to PREPARING for test {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling test setup started event: {e}")
        return True

    def on_test_execution_completed(self, event: TestExecutionCompletedEvent) -> bool:
        """Handle test execution completed event."""
        try:
            # Test execution completed means the test entity itself is completed
            self.state_manager.set_entity_state("test", event.entity_id, EntityState.COMPLETED)
            self.logger.debug(f"Set entity state to COMPLETED for test {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling test execution completed event: {e}")
        return True

    def on_test_failed(self, event: TestFailedEvent) -> bool:
        """Handle test failed event."""
        try:
            self.state_manager.set_entity_state("test", event.entity_id, EntityState.FAILED)
            self.logger.debug(f"Set entity state to FAILED for test {event.entity_id}")
        except Exception as e:
            self.logger.error(f"Error handling test failed event: {e}")
        return True

    # Handle any error/failed events for workflow state

    def on_experiment_plugin_loading_failed(
        self, event: ExperimentPluginLoadingFailedEvent
    ) -> bool:
        """Handle plugin loading failed event."""
        try:
            if self.current_experiment_id:
                self.state_manager.force_fail_workflow(
                    self.current_experiment_id, "Plugin loading failed"
                )
                self.logger.debug(
                    f"Force failed workflow for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling plugin loading failed event: {e}")
        return True

    def on_test_setup_failed(self, event: TestSetupFailedEvent) -> bool:
        """Handle test setup failed event."""
        try:
            if self.current_experiment_id:
                self.state_manager.force_fail_workflow(
                    self.current_experiment_id, "Test setup failed"
                )
                self.logger.debug(
                    f"Force failed workflow for experiment {self.current_experiment_id}"
                )

            self.state_manager.set_entity_state("test", event.entity_id, EntityState.FAILED)
        except Exception as e:
            self.logger.error(f"Error handling test setup failed event: {e}")
        return True

    def on_environment_setup_failed(self, event: EnvironmentSetupFailedEvent) -> bool:
        """Handle environment setup failed event."""
        try:
            if self.current_experiment_id:
                self.state_manager.force_fail_workflow(
                    self.current_experiment_id, "Environment setup failed"
                )
                self.logger.debug(
                    f"Force failed workflow for experiment {self.current_experiment_id}"
                )

            self.state_manager.set_entity_state("environment", event.entity_id, EntityState.FAILED)
        except Exception as e:
            self.logger.error(f"Error handling environment setup failed event: {e}")
        return True

    def on_test_deployment_failed(self, event: TestDeploymentFailedEvent) -> bool:
        """Handle test deployment failed event."""
        try:
            if self.current_experiment_id:
                self.state_manager.force_fail_workflow(
                    self.current_experiment_id, "Test deployment failed"
                )
                self.logger.debug(
                    f"Force failed workflow for experiment {self.current_experiment_id}"
                )
        except Exception as e:
            self.logger.error(f"Error handling test deployment failed event: {e}")
        return True

    def on_test_execution_failed(self, event: TestExecutionFailedEvent) -> bool:
        """Handle test execution failed event."""
        try:
            if self.current_experiment_id:
                self.state_manager.force_fail_workflow(
                    self.current_experiment_id, "Test execution failed"
                )
                self.logger.debug(
                    f"Force failed workflow for experiment {self.current_experiment_id}"
                )

            self.state_manager.set_entity_state("test", event.entity_id, EntityState.FAILED)
        except Exception as e:
            self.logger.error(f"Error handling test execution failed event: {e}")
        return True
