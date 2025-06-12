"""
State Manager

This module provides centralized state management for PANTHER experiments,
ensuring valid state transitions and workflow tracking.
"""

import logging
from enum import Enum
from threading import RLock

# TODO link the workflow state to the event state ?


class WorkflowState(Enum):
    """
    Represents the various states in the PANTHER experiment workflow.
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


class EntityState(Enum):
    """
    Generic entity states used across different entity types.
    """

    CREATED = "created"
    INITIALIZED = "initialized"
    PREPARING = "preparing"
    PREPARED = "prepared"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StateManager:
    """
    Manages state transitions and workflow tracking for PANTHER experiments.

    This class ensures that state transitions are valid and provides centralized
    state tracking for all entities in the system.
    """

    # Valid state transitions for workflow states
    WORKFLOW_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
        WorkflowState.CREATED: {WorkflowState.LOADING_PLUGINS, WorkflowState.FAILED},
        WorkflowState.LOADING_PLUGINS: {WorkflowState.GENERATING_COMMANDS, WorkflowState.FAILED},
        WorkflowState.GENERATING_COMMANDS: {WorkflowState.BUILDING_DOCKER, WorkflowState.FAILED},
        WorkflowState.BUILDING_DOCKER: {WorkflowState.DEPLOYING, WorkflowState.FAILED},
        WorkflowState.DEPLOYING: {WorkflowState.RUNNING, WorkflowState.FAILED},
        WorkflowState.RUNNING: {WorkflowState.COLLECTING_OUTPUTS, WorkflowState.FAILED},
        WorkflowState.COLLECTING_OUTPUTS: {WorkflowState.ANALYZING_RESULTS, WorkflowState.FAILED},
        WorkflowState.ANALYZING_RESULTS: {WorkflowState.REPORTING_RESULTS, WorkflowState.FAILED},
        WorkflowState.REPORTING_RESULTS: {WorkflowState.COMPLETED, WorkflowState.FAILED},
        WorkflowState.COMPLETED: set(),  # Terminal state
        WorkflowState.FAILED: set(),  # Terminal state
    }

    # Valid state transitions for entity states
    ENTITY_TRANSITIONS: dict[EntityState, set[EntityState]] = {
        EntityState.CREATED: {EntityState.INITIALIZED, EntityState.FAILED},
        EntityState.INITIALIZED: {EntityState.PREPARING, EntityState.FAILED},
        EntityState.PREPARING: {EntityState.PREPARED, EntityState.FAILED},
        EntityState.PREPARED: {EntityState.STARTING, EntityState.FAILED},
        EntityState.STARTING: {EntityState.RUNNING, EntityState.FAILED},
        EntityState.RUNNING: {EntityState.STOPPING, EntityState.COMPLETED, EntityState.FAILED},
        EntityState.STOPPING: {EntityState.STOPPED, EntityState.FAILED},
        EntityState.STOPPED: {EntityState.COMPLETED, EntityState.FAILED},
        EntityState.COMPLETED: set(),  # Terminal state
        EntityState.FAILED: set(),  # Terminal state
        EntityState.CANCELLED: set(),  # Terminal state
    }

    def __init__(self):
        """Initialize the state manager."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._lock = RLock()
        self._workflow_states: dict[str, WorkflowState] = {}
        self._entity_states: dict[str, dict[str, EntityState]] = {}

    def set_workflow_state(self, name: str, state: WorkflowState) -> bool:
        """
        Set the workflow state for a named workflow.

        Args:
            name: Name of the workflow (e.g., experiment name)
            state: New workflow state

        Returns:
            bool: True if state was set successfully, False otherwise
        """
        with self._lock:
            current_state = self._workflow_states.get(name)

            # If no current state, allow setting to CREATED only
            if current_state is None:
                if state == WorkflowState.CREATED:
                    self._workflow_states[name] = state
                    self.logger.info(f"Workflow '{name}' created with state: {state.value}")
                    return True
                else:
                    self.logger.error(f"Cannot create workflow '{name}' in state: {state.value}")
                    return False

            # Validate transition
            if self.validate_workflow_transition(current_state, state):
                self._workflow_states[name] = state
                self.logger.info(
                    f"Workflow '{name}' transitioned from {current_state.value} to {state.value}"
                )
                return True
            else:
                self.logger.error(
                    f"Invalid workflow transition for '{name}': {current_state.value} -> {state.value}"
                )
                return False

    def get_workflow_state(self, name: str) -> WorkflowState | None:
        """
        Get the current workflow state.

        Args:
            name: Name of the workflow

        Returns:
            Optional[WorkflowState]: Current state or None if not found
        """
        with self._lock:
            return self._workflow_states.get(name)

    def set_entity_state(self, entity_type: str, entity_id: str, state: EntityState) -> bool:
        """
        Set the state for a specific entity.

        Args:
            entity_type: Type of entity (e.g., "experiment", "test", "service")
            entity_id: Unique identifier for the entity
            state: New entity state

        Returns:
            bool: True if state was set successfully, False otherwise
        """
        with self._lock:
            if entity_type not in self._entity_states:
                self._entity_states[entity_type] = {}

            current_state = self._entity_states[entity_type].get(entity_id)

            # If no current state, allow setting to CREATED only
            if current_state is None:
                if state == EntityState.CREATED:
                    self._entity_states[entity_type][entity_id] = state
                    self.logger.info(
                        f"Entity '{entity_type}:{entity_id}' created with state: {state.value}"
                    )
                    return True
                else:
                    self.logger.error(
                        f"Cannot create entity '{entity_type}:{entity_id}' in state: {state.value}"
                    )
                    return False

            # Validate transition
            if self.validate_entity_transition(current_state, state):
                self._entity_states[entity_type][entity_id] = state
                self.logger.info(
                    f"Entity '{entity_type}:{entity_id}' transitioned from {current_state.value} to {state.value}"
                )
                return True
            else:
                self.logger.error(
                    f"Invalid entity transition for '{entity_type}:{entity_id}': {current_state.value} -> {state.value}"
                )
                return False

    def get_entity_state(self, entity_type: str, entity_id: str) -> EntityState | None:
        """
        Get the current state for a specific entity.

        Args:
            entity_type: Type of entity
            entity_id: Unique identifier for the entity

        Returns:
            Optional[EntityState]: Current state or None if not found
        """
        with self._lock:
            return self._entity_states.get(entity_type, {}).get(entity_id)

    def validate_workflow_transition(
        self, current_state: WorkflowState, new_state: WorkflowState
    ) -> bool:
        """
        Validate if a workflow state transition is allowed.

        Args:
            current_state: Current workflow state
            new_state: Proposed new workflow state

        Returns:
            bool: True if transition is valid, False otherwise
        """
        # Allow transition to same state (no-op)
        if current_state == new_state:
            return True

        # Check if transition is in allowed transitions
        allowed_transitions = self.WORKFLOW_TRANSITIONS.get(current_state, set())
        return new_state in allowed_transitions

    def validate_entity_transition(
        self, current_state: EntityState, new_state: EntityState
    ) -> bool:
        """
        Validate if an entity state transition is allowed.

        Args:
            current_state: Current entity state
            new_state: Proposed new entity state

        Returns:
            bool: True if transition is valid, False otherwise
        """
        # Allow transition to same state (no-op)
        if current_state == new_state:
            return True

        # Check if transition is in allowed transitions
        allowed_transitions = self.ENTITY_TRANSITIONS.get(current_state, set())
        return new_state in allowed_transitions

    def validate_transition(self, entity_type: str, current_state: str, new_state: str) -> bool:
        """
        Generic transition validation method.

        Args:
            entity_type: Type of entity or "workflow"
            current_state: Current state as string
            new_state: New state as string

        Returns:
            bool: True if transition is valid, False otherwise
        """
        if entity_type == "workflow":
            try:
                current = WorkflowState(current_state)
                new = WorkflowState(new_state)
                return self.validate_workflow_transition(current, new)
            except ValueError:
                self.logger.error(f"Invalid workflow states: {current_state} or {new_state}")
                return False
        else:
            try:
                current = EntityState(current_state)
                new = EntityState(new_state)
                return self.validate_entity_transition(current, new)
            except ValueError:
                self.logger.error(f"Invalid entity states: {current_state} or {new_state}")
                return False

    def get_all_workflow_states(self) -> dict[str, str]:
        """
        Get all current workflow states.

        Returns:
            Dict[str, str]: Dictionary mapping workflow names to their current states
        """
        with self._lock:
            return {name: state.value for name, state in self._workflow_states.items()}

    def get_all_entity_states(self, entity_type: str | None = None) -> dict[str, dict[str, str]]:
        """
        Get all current entity states, optionally filtered by type.

        Args:
            entity_type: Optional entity type to filter by

        Returns:
            Dict[str, Dict[str, str]]: Nested dictionary of entity states
        """
        with self._lock:
            if entity_type:
                entities = self._entity_states.get(entity_type, {})
                return {entity_id: state.value for entity_id, state in entities.items()}
            else:
                result = {}
                for etype, entities in self._entity_states.items():
                    result[etype] = {
                        entity_id: state.value for entity_id, state in entities.items()
                    }
                return result

    def clear_workflow_state(self, name: str) -> None:
        """
        Clear the state for a specific workflow.

        Args:
            name: Name of the workflow to clear
        """
        with self._lock:
            if name in self._workflow_states:
                del self._workflow_states[name]
                self.logger.info(f"Cleared workflow state for '{name}'")

    def clear_entity_state(self, entity_type: str, entity_id: str) -> None:
        """
        Clear the state for a specific entity.

        Args:
            entity_type: Type of entity
            entity_id: Unique identifier for the entity
        """
        with self._lock:
            if entity_type in self._entity_states and entity_id in self._entity_states[entity_type]:
                del self._entity_states[entity_type][entity_id]
                self.logger.info(f"Cleared entity state for '{entity_type}:{entity_id}'")

    def clear_all_states(self) -> None:
        """Clear all tracked states."""
        with self._lock:
            self._workflow_states.clear()
            self._entity_states.clear()
            self.logger.info("Cleared all states")
