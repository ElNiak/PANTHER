"""Base classes for the PANTHER event system.

Provides the foundational abstractions that all domain-specific events,
emitters, and state managers inherit from:

- :class:`BaseEvent` -- Core event with content-based UUID deduplication
- :class:`EventType` -- Enum partitioning events by entity domain
- :class:`EventEmitterBase` / :class:`EntityEventEmitterBase` -- Abstract
  emitter hierarchy for domain-specific event emission
- :class:`BaseState` / :class:`StateManager` / :class:`StateTransition` --
  State machine infrastructure for entity lifecycle tracking
"""

from .event_base import BaseEvent, EventType
from .event_emitter_base import EntityEventEmitterBase, EventEmitterBase
from .state_base import BaseState, StateManager, StateTransition

__all__ = [
    "BaseEvent",
    "EventType",
    "BaseState",
    "StateManager",
    "StateTransition",
    "EventEmitterBase",
    "EntityEventEmitterBase",
]
