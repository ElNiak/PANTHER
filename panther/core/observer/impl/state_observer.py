"""State Event Observer Module.

This module provides a simplified observer that focuses on workflow coordination
and state history recording. Entity-specific state management is now handled
by the event-based state managers in EmitterRegistry.
"""

import logging
from typing import Dict, Optional, Tuple

from panther.core.events.base.event_base import BaseEvent
from panther.core.events.service.events import DockerBuildStartedEvent
from panther.core.observer.base.typed_observer_interface import ITypedObserver
from panther.core.observer.workflow import WorkflowState, WorkflowStateTracker

# Maps (entity_prefix, event_name) -> (WorkflowState, use_entity_id)
# use_entity_id=True means use event.entity_id; False means use self.current_experiment_id
_EVENT_STATE_MAP: Dict[Tuple[str, str], Tuple[WorkflowState, bool]] = {
    ("experiment", "execution_started"): (WorkflowState.RUNNING, False),
    ("experiment", "completed"): (WorkflowState.COMPLETED, True),
    ("experiment", "failed"): (WorkflowState.FAILED, True),
    ("experiment", "plugin_loading_started"): (WorkflowState.LOADING_PLUGINS, False),
    ("service", "preparation_started"): (WorkflowState.GENERATING_COMMANDS, False),
    ("environment", "setup_started"): (WorkflowState.DEPLOYING, False),
    ("test", "execution_started"): (WorkflowState.RUNNING, False),
    ("test", "setup_started"): (WorkflowState.RUNNING, False),
    ("test", "teardown_started"): (WorkflowState.RUNNING, False),
    ("environment", "output_collection_started"): (
        WorkflowState.COLLECTING_OUTPUTS,
        False,
    ),
    ("environment", "output_collection_completed"): (
        WorkflowState.ANALYZING_RESULTS,
        False,
    ),
    ("service", "test_results"): (WorkflowState.ANALYZING_RESULTS, False),
}


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
        self.current_experiment_id: Optional[str] = None

    def get_priority(self) -> int:
        """Get the priority for this observer."""
        return self.priority

    def is_interested(self, event_type: str) -> bool:
        """Check if this observer is interested in workflow coordination events."""
        workflow_event_types = [
            "experiment.initialized",
            "experiment.plugin_loading_started",
            "experiment.plugin_loading_failed",
            "experiment.execution_started",
            "experiment.completed",
            "experiment.failed",
            "service.preparation_started",
            "service.docker_build_started",
            "environment.setup_started",
            "test.execution_started",
            "test.setup_started",
            "test.teardown_started",
            "environment.output_collection_started",
            "environment.output_collection_completed",
            "service.test_results",
        ]
        return event_type in workflow_event_types

    def on_event(self, event: BaseEvent) -> bool:
        """Route events to workflow state transitions via lookup table."""
        # Let ITypedObserver handle dedup
        if hasattr(event, "id"):
            if event.id in self.processed_events_uuids:
                return True
            self.processed_events_uuids.add(event.id)

        # Special case: experiment initialized (also sets current_experiment_id)
        if event.entity_type.value == "experiment" and event.name == "initialized":
            return self._handle_experiment_initialized(event)

        # Special case: plugin loading failed (uses force_fail_workflow)
        if (
            event.entity_type.value == "experiment"
            and event.name == "plugin_loading_failed"
        ):
            return self._handle_plugin_loading_failed(event)

        # Special case: docker_build_started (typed event)
        if isinstance(event, DockerBuildStartedEvent):
            return self._set_state(
                self.current_experiment_id, WorkflowState.BUILDING_DOCKER
            )

        # Generic dispatch via mapping
        key = (event.entity_type.value, event.name)
        mapping = _EVENT_STATE_MAP.get(key)
        if mapping is None:
            self.logger.debug(
                "No state mapping for (%s, %s)", event.entity_type.value, event.name
            )
            return self.on_unknown_event(event)

        state, use_entity_id = mapping
        experiment_id = event.entity_id if use_entity_id else self.current_experiment_id
        return self._set_state(experiment_id, state)

    def _handle_experiment_initialized(self, event: BaseEvent) -> bool:
        """Handle experiment initialized — also sets current_experiment_id."""
        self.current_experiment_id = event.entity_id
        result = self._set_state(event.entity_id, WorkflowState.CREATED)
        self.logger.debug(
            "Workflow coordination: experiment %s initialized", event.entity_id
        )
        return result

    def _handle_plugin_loading_failed(self, event: BaseEvent) -> bool:
        """Handle plugin loading failure — uses force_fail_workflow."""
        try:
            if self.current_experiment_id:
                self.workflow_tracker.force_fail_workflow(
                    self.current_experiment_id, "Plugin loading failed"
                )
        except Exception as e:
            self.logger.error(
                "Error setting plugin loading failure state for experiment %s: %s",
                self.current_experiment_id,
                e,
            )
        return True

    def _set_state(self, experiment_id: Optional[str], state: WorkflowState) -> bool:
        """Set workflow state for an experiment, with error handling."""
        try:
            if experiment_id:
                self.workflow_tracker.set_workflow_state(experiment_id, state)
        except Exception as e:
            self.logger.error(
                "Error setting %s state for experiment %s: %s",
                state.value,
                experiment_id,
                e,
            )
        return True

    def get_state_history(self, experiment_id: str = None):
        """Get workflow state transition history for debugging."""
        return self.workflow_tracker.get_state_history(experiment_id)
