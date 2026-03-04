"""Workflow State Tracker - Experiment lifecycle state management.

Provides ``WorkflowState`` enum and ``WorkflowStateTracker`` for tracking
experiment workflow progression through validated state transitions.

State machine::

    CREATED
      |
      v
    LOADING_PLUGINS --> GENERATING_COMMANDS --> BUILDING_DOCKER
                                                     |
                                                     v
    COMPLETED <-- REPORTING_RESULTS <-- ANALYZING_RESULTS <-- COLLECTING_OUTPUTS <-- RUNNING <-- DEPLOYING
      (terminal)

    Any state --> FAILED (terminal)

Transitions are validated against ``WORKFLOW_TRANSITIONS``. New experiments
must start in ``CREATED`` state. ``force_fail_workflow()`` bypasses normal
validation for error recovery. All operations are thread-safe via RLock.

See Also:
    :class:`panther.core.observer.management.event_manager.EventManager`
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from threading import RLock
from typing import Dict, List, Optional, Set, Union

from panther.core.utils.logging_mixin import LoggerMixin


class WorkflowState(Enum):
    """Experiment workflow states with validated transitions.

    Defines the ordered phases of experiment execution from creation
    through plugin loading, Docker building, deployment, execution,
    output collection, analysis, and reporting. Terminal states are
    ``COMPLETED`` and ``FAILED``.
    """

    CREATED = "created"
    LOADING_PLUGINS = "loading_plugins"
    GENERATING_COMMANDS = "generating_commands"
    BUILDING_DOCKER = "building_docker"
    DEPLOYING = "deploying"
    RUNNING = "running"
    COLLECTING_OUTPUTS = "collecting_outputs"
    ANALYZING_RESULTS = "analyzing_results"
    REPORTING_RESULTS = "reporting_results"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStateTracker(LoggerMixin):
    """Lightweight tracker for experiment workflow states with validated transitions.

    Replaces the heavy generic StateManager for workflow coordination only.
    Entity-specific state management is handled by event-based state managers.

    Transitions are validated against ``WORKFLOW_TRANSITIONS``. New experiments
    must start with ``WorkflowState.CREATED``. History of all transitions is
    retained (bounded to 1000 entries) for debugging.

    Attributes:
        WORKFLOW_TRANSITIONS: Class-level dict mapping each state to its set
            of allowed next states.

    Example:
        Track an experiment through its workflow::

            tracker = WorkflowStateTracker()
            tracker.set_workflow_state("exp-1", WorkflowState.CREATED)
            tracker.set_workflow_state("exp-1", WorkflowState.LOADING_PLUGINS)
            tracker.get_workflow_state("exp-1")  # WorkflowState.LOADING_PLUGINS
            tracker.is_workflow_in_terminal_state("exp-1")  # False
    """

    # Valid state transitions for workflow states
    WORKFLOW_TRANSITIONS: Dict[WorkflowState, Set[WorkflowState]] = {
        WorkflowState.CREATED: {WorkflowState.LOADING_PLUGINS, WorkflowState.FAILED},
        WorkflowState.LOADING_PLUGINS: {
            WorkflowState.GENERATING_COMMANDS,
            WorkflowState.FAILED,
        },
        WorkflowState.GENERATING_COMMANDS: {
            WorkflowState.BUILDING_DOCKER,
            WorkflowState.FAILED,
        },
        WorkflowState.BUILDING_DOCKER: {WorkflowState.DEPLOYING, WorkflowState.FAILED},
        WorkflowState.DEPLOYING: {WorkflowState.RUNNING, WorkflowState.FAILED},
        WorkflowState.RUNNING: {WorkflowState.COLLECTING_OUTPUTS, WorkflowState.FAILED},
        WorkflowState.COLLECTING_OUTPUTS: {
            WorkflowState.ANALYZING_RESULTS,
            WorkflowState.FAILED,
        },
        WorkflowState.ANALYZING_RESULTS: {
            WorkflowState.REPORTING_RESULTS,
            WorkflowState.FAILED,
        },
        WorkflowState.REPORTING_RESULTS: {
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
        },
        WorkflowState.COMPLETED: set(),  # Terminal state
        WorkflowState.FAILED: set(),  # Terminal state
    }

    def __init__(self):
        """Initialize the workflow state tracker."""
        super().__init__()
        self._lock = RLock()
        self.logger.setLevel(logging.CRITICAL)  # TODO
        self._workflow_states: Dict[str, WorkflowState] = {}
        self._state_history: List[dict] = []
        self._max_history = 1000

    def set_workflow_state(self, experiment_id: str, state: WorkflowState) -> bool:
        """
        Set the workflow state for an experiment.

        Args:
            experiment_id: Unique identifier for the experiment
            state: New workflow state

        Returns:
            bool: True if state was set successfully, False otherwise
        """
        if not experiment_id:
            raise ValueError("Experiment ID cannot be empty")

        with self._lock:
            current_state = self._workflow_states.get(experiment_id)

            # If no current state, allow setting to CREATED only
            if current_state is None:
                if state == WorkflowState.CREATED:
                    self._workflow_states[experiment_id] = state
                    self._record_transition(
                        experiment_id, None, state, "experiment_created"
                    )
                    self.logger.info(
                        f"Workflow '{experiment_id}' created with state: {state.value}"
                    )
                    return True
                else:
                    self.logger.error(
                        f"Cannot create workflow '{experiment_id}' in state: {state.value}. Must start with CREATED state."
                    )
                    return False

            # Validate transition
            if self._validate_transition(current_state, state):
                old_state = current_state
                self._workflow_states[experiment_id] = state
                self._record_transition(
                    experiment_id, old_state, state, "workflow_transition"
                )
                self.logger.info(
                    f"Workflow '{experiment_id}' transitioned from {old_state.value} to {state.value}"
                )
                return True
            else:
                allowed = list(self.WORKFLOW_TRANSITIONS.get(current_state, set()))
                self.logger.error(
                    f"Invalid workflow transition for '{experiment_id}': {current_state.value} -> {state.value}. "
                    f"Allowed transitions from {current_state.value}: {[s.value for s in allowed]}"
                )
                return False

    def get_workflow_state(self, experiment_id: str) -> Optional[WorkflowState]:
        """
        Get the current workflow state for an experiment.

        Args:
            experiment_id: Unique identifier for the experiment

        Returns:
            Optional[WorkflowState]: Current state or None if not found
        """
        with self._lock:
            return self._workflow_states.get(experiment_id)

    def force_fail_workflow(
        self, experiment_id: str, reason: str = "Forced failure"
    ) -> bool:
        """
        Force a workflow to FAILED state regardless of current state.
        Used for error recovery.

        Args:
            experiment_id: Unique identifier for the experiment
            reason: Reason for forcing failure

        Returns:
            bool: True if successfully set to FAILED
        """
        with self._lock:
            current_state = self._workflow_states.get(experiment_id)
            if current_state is None:
                self.logger.error(
                    f"Cannot force fail non-existent workflow '{experiment_id}'"
                )
                return False

            if current_state == WorkflowState.FAILED:
                return True  # Already failed

            old_state = current_state
            self._workflow_states[experiment_id] = WorkflowState.FAILED
            self._record_transition(
                experiment_id, old_state, WorkflowState.FAILED, f"force_fail: {reason}"
            )
            self.logger.warning(
                f"Forced workflow '{experiment_id}' from {current_state.value} to FAILED: {reason}"
            )
            return True

    def clear_workflow_state(self, experiment_id: str) -> None:
        """
        Clear the state for a specific workflow.

        Args:
            experiment_id: Unique identifier for the experiment to clear
        """
        with self._lock:
            if experiment_id in self._workflow_states:
                old_state = self._workflow_states[experiment_id]
                del self._workflow_states[experiment_id]
                self._record_transition(
                    experiment_id, old_state, None, "workflow_cleared"
                )
                self.logger.info(f"Cleared workflow state for '{experiment_id}'")

    def is_workflow_in_terminal_state(self, experiment_id: str) -> bool:
        """
        Check if a workflow is in a terminal state (COMPLETED or FAILED).

        Args:
            experiment_id: Unique identifier for the experiment

        Returns:
            bool: True if in terminal state, False otherwise
        """
        with self._lock:
            state = self._workflow_states.get(experiment_id)
            if state is None:
                return False
            return state in {WorkflowState.COMPLETED, WorkflowState.FAILED}

    def get_all_workflow_states(self) -> Dict[str, str]:
        """
        Get all current workflow states.

        Returns:
            Dict[str, str]: Dictionary mapping experiment IDs to their current states
        """
        with self._lock:
            return {
                exp_id: state.value for exp_id, state in self._workflow_states.items()
            }

    def get_allowed_transitions(self, current_state_str: str) -> List[str]:
        """
        Get list of allowed state transitions from current state.

        Args:
            current_state_str: Current state as string

        Returns:
            List[str]: List of allowed state names
        """
        try:
            current = WorkflowState(current_state_str)
            allowed = self.WORKFLOW_TRANSITIONS.get(current, set())
            return [s.value for s in allowed]
        except ValueError:
            return []

    def get_state_history(self, experiment_id: str = None) -> List[dict]:
        """
        Get state transition history for debugging.

        Args:
            experiment_id: Optional experiment ID to filter by

        Returns:
            List of state transition records
        """
        with self._lock:
            if experiment_id:
                return [
                    record
                    for record in self._state_history
                    if record["experiment_id"] == experiment_id
                ]
            return self._state_history.copy()

    def _validate_transition(
        self, current_state: WorkflowState, new_state: WorkflowState
    ) -> bool:
        """Validate if a workflow state transition is allowed."""
        # Allow transition to same state (no-op)
        if current_state == new_state:
            return True

        # Check if transition is in allowed transitions
        allowed_transitions = self.WORKFLOW_TRANSITIONS.get(current_state, set())
        return new_state in allowed_transitions

    def _record_transition(
        self,
        experiment_id: str,
        old_state: Union[WorkflowState, None],
        new_state: Union[WorkflowState, None],
        trigger: str,
    ):
        """Record state transition in history for debugging."""
        transition = {
            "timestamp": datetime.now().isoformat(),
            "experiment_id": experiment_id,
            "old_state": old_state.value if old_state else None,
            "new_state": new_state.value if new_state else None,
            "trigger": trigger,
        }

        self._state_history.append(transition)

        # Keep history size manageable
        if len(self._state_history) > self._max_history:
            self._state_history = self._state_history[-self._max_history :]
