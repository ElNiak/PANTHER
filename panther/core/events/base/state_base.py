"""Base state management infrastructure for entity lifecycle tracking.

Provides the state machine primitives used by all domain-specific state
managers in the event system:

- :class:`BaseState` -- Base ``Enum`` for entity-specific states.
- :class:`StateTransition` -- Records a single state change with metadata.
- :class:`StateManager` -- Abstract state machine that validates transitions
  against an allowed-transitions map, maintains full transition history, and
  provides time-in-state queries.

Example:
    Define a custom state machine::

        from enum import Enum
        from panther.core.events.base.state_base import BaseState, StateManager

        class MyState(BaseState):
            CREATED = "created"
            RUNNING = "running"
            COMPLETED = "completed"
            FAILED = "failed"

        class MyStateManager(StateManager):
            def _define_allowed_transitions(self):
                return {
                    MyState.CREATED: {MyState.RUNNING},
                    MyState.RUNNING: {MyState.COMPLETED, MyState.FAILED},
                    MyState.COMPLETED: set(),
                    MyState.FAILED: set(),
                }

        sm = MyStateManager("entity-1", MyState.CREATED)
        sm.setup_transitions()
        assert sm.transition_to(MyState.RUNNING)   # True
        assert not sm.transition_to(MyState.CREATED)  # False -- not allowed
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class BaseState(Enum):
    """Base state enumeration for entity lifecycle tracking.

    Entity-specific states (e.g. ``ServiceState``, ``TestState``) should
    inherit from this class to participate in the :class:`StateManager`
    transition validation system.
    """

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}.{self.name}>"


class StateTransition:
    """Represents a single state transition with metadata.

    Attributes:
        from_state: State transitioned from (``None`` for the initial state).
        to_state: State transitioned to.
        timestamp: When the transition occurred.
        trigger: What triggered the transition (e.g. ``"service_creation"``).
        metadata: Additional context about the transition.
    """

    def __init__(
        self,
        from_state: BaseState,
        to_state: BaseState,
        timestamp: Optional[datetime] = None,
        trigger: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.timestamp = timestamp or datetime.now()
        self.trigger = trigger
        self.metadata = metadata or {}

    def __str__(self) -> str:
        return f"{self.from_state} -> {self.to_state}"


class StateManager(ABC):
    """Abstract base state manager for entity lifecycle tracking.

    Manages allowed state transitions, maintains a full transition history,
    and provides time-in-state queries.  Subclasses must implement
    :meth:`_define_allowed_transitions` and call :meth:`setup_transitions`
    before using ``transition_to()``.

    Attributes:
        entity_id: Unique identifier for the managed entity.
        current_state: The entity's current state.
        state_history: Ordered list of all :class:`StateTransition` records.
        allowed_transitions: Map from each state to its set of valid
            next states (populated by :meth:`setup_transitions`).
        logger: Logger instance scoped to ``{ClassName}({entity_id})``.
    """

    def __init__(self, entity_id: str, initial_state: BaseState):
        """
        Initialize state manager.

        Args:
            entity_id: Unique identifier for the entity
            initial_state: Initial state of the entity
        """
        self.entity_id = entity_id
        self.current_state = initial_state
        self.state_history: List[StateTransition] = []
        self.allowed_transitions: Dict[BaseState, Set[BaseState]] = {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}({entity_id})")

        # Record initial state
        self.state_history.append(
            StateTransition(None, initial_state, trigger="initialization")
        )

    @abstractmethod
    def _define_allowed_transitions(self) -> Dict[BaseState, Set[BaseState]]:
        """
        Define allowed state transitions for this entity type.

        Returns:
            Dictionary mapping each state to its allowed next states
        """
        pass

    def setup_transitions(self) -> None:
        """Setup allowed transitions for this state manager."""
        self.allowed_transitions = self._define_allowed_transitions()

    def get_current_state(self) -> BaseState:
        """Get the current state."""
        return self.current_state

    def get_state_history(self) -> List[StateTransition]:
        """Get the complete state transition history."""
        return self.state_history.copy()

    def can_transition_to(self, target_state: BaseState) -> bool:
        """
        Check if transition to target state is allowed.

        Args:
            target_state: State to transition to

        Returns:
            True if transition is allowed, False otherwise
        """
        allowed_next_states = self.allowed_transitions.get(self.current_state, set())
        return target_state in allowed_next_states

    def transition_to(
        self,
        target_state: BaseState,
        trigger: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Transition to a new state.

        Args:
            target_state: State to transition to
            trigger: What triggered this transition
            metadata: Additional transition metadata

        Returns:
            True if transition was successful, False otherwise
        """
        if not self.can_transition_to(target_state):
            self.logger.warning(
                f"Invalid state transition from {self.current_state} to {target_state}"
            )
            return False

        # Record the transition
        transition = StateTransition(
            from_state=self.current_state,
            to_state=target_state,
            trigger=trigger,
            metadata=metadata,
        )

        self.state_history.append(transition)
        self.current_state = target_state

        self.logger.debug(f"State transition: {transition}")
        return True

    def is_in_state(self, state: BaseState) -> bool:
        """Check if currently in specified state."""
        return self.current_state == state

    def is_in_any_state(self, states: Set[BaseState]) -> bool:
        """Check if currently in any of the specified states."""
        return self.current_state in states

    def get_time_in_current_state(self) -> Optional[float]:
        """
        Get time spent in current state in seconds.

        Returns:
            Time in seconds, or None if no transitions recorded
        """
        if not self.state_history:
            return None

        last_transition = self.state_history[-1]
        return (datetime.now() - last_transition.timestamp).total_seconds()

    def get_last_transition(self) -> Optional[StateTransition]:
        """Get the most recent state transition."""
        return self.state_history[-1] if self.state_history else None

    def reset_to_initial_state(self, initial_state: BaseState) -> None:
        """Reset to initial state and clear history."""
        self.current_state = initial_state
        self.state_history = [StateTransition(None, initial_state, trigger="reset")]

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.entity_id}): {self.current_state}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.entity_id}): {self.current_state}>"
