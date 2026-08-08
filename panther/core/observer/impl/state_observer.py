"""State Event Observer Module.

This module provides a simplified observer that focuses on workflow coordination
and state history recording. Entity-specific state management is now handled
by the event-based state managers in EmitterRegistry.
"""

import logging

from panther.core.events.base.event_base import BaseEvent
from panther.core.events.service.events import DockerBuildStartedEvent
from panther.core.observer.base.typed_observer_interface import ITypedObserver
from panther.core.observer.workflow import WorkflowState, WorkflowStateTracker


class StateEventObserver(ITypedObserver):
    """Simplified observer focused on workflow coordination and state history.

    This observer:
    - Tracks experiment-level workflow states for coordination
    - Records state history for debugging and analysis
    - Maintains compatibility with legacy StateManager
    - Lets event-based state managers handle entity-specific transitions
    """

    def __init__(self, workflow_tracker: WorkflowStateTracker, priority: int = 100):
        """Initialize the simplified state event observer.

        Args:
            workflow_tracker: The WorkflowStateTracker instance for workflow coordination
            priority: Observer priority (higher = processed earlier)
        """
        super().__init__()
        self.workflow_tracker = workflow_tracker
        self.priority = priority
        self.logger = logging.getLogger(self.__class__.__name__)

        # Track current experiment for workflow coordination
        self.current_experiment_id = None

    def get_priority(self) -> int:
        """Get the priority for this observer."""
        return self.priority

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer is interested in workflow coordination events."""
        # Focus only on workflow-level events for coordination
        workflow_event_types = [
            "experiment.initialized",
            "experiment.plugin_loading_started",
            "experiment.plugin_loading_failed",
            "experiment.execution_started",
            "experiment.completed",
            "experiment.failed",
            "command_generation.started",
            "docker_build.started",
            "environment.setup_started",
            "test.execution_started",
            "test.setup_started",
            "test.teardown_started",
            "output_collection.started",
            "output_collection.completed",
            "tester_analysis.started",
        ]

        return event_type in workflow_event_types

    # Workflow coordination event handlers (simplified)

    def on_experiment_initialized(self, event: BaseEvent) -> bool:
        """Handle experiment initialized - set workflow tracking."""
        try:
            self.current_experiment_id = event.entity_id
            self.workflow_tracker.set_workflow_state(
                event.entity_id, WorkflowState.CREATED
            )
            self.logger.debug(
                f"Workflow coordination: experiment {event.entity_id} initialized"
            )
        except Exception as e:
            self.logger.error(
                f"Error setting experiment initialized state for {event.entity_id}: {e}"
            )
        return True

    def on_experiment_plugin_loading_started(self, event: BaseEvent) -> bool:
        """Handle plugin loading phase."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.LOADING_PLUGINS
                )
        except Exception as e:
            self.logger.error(
                f"Error setting plugin loading state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_command_generation_started(self, event: BaseEvent) -> bool:
        """Handle command generation phase."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.GENERATING_COMMANDS
                )
        except Exception as e:
            self.logger.error(
                f"Error setting command generation state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_docker_build_started(self, event: DockerBuildStartedEvent) -> bool:
        """Handle Docker build phase."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.BUILDING_DOCKER
                )
        except Exception as e:
            self.logger.error(
                f"Error setting docker build state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_environment_setup_started(self, event: BaseEvent) -> bool:
        """Handle deployment phase."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.DEPLOYING
                )
        except Exception as e:
            self.logger.error(
                f"Error setting deployment state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_test_execution_started(self, event: BaseEvent) -> bool:
        """Handle test execution phase."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.RUNNING
                )
        except Exception as e:
            self.logger.error(
                f"Error setting test execution state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_output_collection_started(self, event: BaseEvent) -> bool:
        """Handle output collection phase."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.COLLECTING_OUTPUTS
                )
        except Exception as e:
            self.logger.error(
                f"Error setting output collection state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_output_collection_completed(self, event: BaseEvent) -> bool:
        """Handle transition to analysis phase."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.ANALYZING_RESULTS
                )
        except Exception as e:
            self.logger.error(
                f"Error setting analysis state after output collection for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_tester_analysis_started(self, event: BaseEvent) -> bool:
        """Handle analysis phase."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.ANALYZING_RESULTS
                )
        except Exception as e:
            self.logger.error(
                f"Error setting tester analysis state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_experiment_execution_started(self, event: BaseEvent) -> bool:
        """Handle experiment execution started."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.set_workflow_state(
                    self.current_experiment_id, WorkflowState.RUNNING
                )
        except Exception as e:
            self.logger.error(
                f"Error setting execution started state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def on_experiment_completed(self, event: BaseEvent) -> bool:
        """Handle experiment completion."""
        try:
            self.workflow_tracker.set_workflow_state(
                event.entity_id, WorkflowState.COMPLETED
            )
            self.logger.debug(
                f"Workflow coordination: experiment {event.entity_id} completed"
            )
        except Exception as e:
            self.logger.error(
                f"Error setting completed state for experiment {event.entity_id}: {e}"
            )
        return True

    def on_experiment_failed(self, event: BaseEvent) -> bool:
        """Handle experiment failure."""
        try:
            self.workflow_tracker.set_workflow_state(
                event.entity_id, WorkflowState.FAILED
            )
            self.logger.debug(
                f"Workflow coordination: experiment {event.entity_id} failed"
            )
        except Exception as e:
            self.logger.error(
                f"Error setting failed state for experiment {event.entity_id}: {e}"
            )
        return True

    def on_experiment_plugin_loading_failed(self, event: BaseEvent) -> bool:
        """Handle plugin loading failure."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.force_fail_workflow(
                    self.current_experiment_id, "Plugin loading failed"
                )
        except Exception as e:
            self.logger.error(
                f"Error setting plugin loading failure state for experiment {self.current_experiment_id}: {e}"
            )
        return True

    def get_state_history(self, experiment_id: str = None):
        """Get workflow state transition history for debugging."""
        return self.workflow_tracker.get_state_history(experiment_id)
