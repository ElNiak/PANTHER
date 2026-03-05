"""State Management Module - Workflow State Machines for PANTHER.

Centralized state tracking with explicit transition validation ensuring
experiments and entities follow legal state progressions.

State Machines::

    WorkflowState (experiment-level):

        CREATED ──> LOADING_PLUGINS ──> BUILDING_DOCKER ──> RUNNING
            │                                                  │
            └──> FAILED                 COMPLETED <────────────┘

    EntityState (service/test-level):

        CREATED ──> INITIALIZED ──> PREPARING ──> RUNNING
            │                                       │
            └──> CANCELLED           COMPLETED <────┘
                                         │
                                       FAILED

Components:
    StateManager
        Thread-safe centralized state tracking dictionary with
        valid transition enforcement via ``WORKFLOW_TRANSITIONS``
        and ``ENTITY_TRANSITIONS`` maps.

    WorkflowState
        Enum of 10 experiment workflow states.

    EntityState
        Enum of generic entity states (services, tests, environments).

See Also:
    `panther.core.events` -- state change events emitted on transitions
    `panther.core.test_cases` -- test case state machine using EntityState
"""

from panther.core.state.state_manager import EntityState, StateManager, WorkflowState

__all__ = ["StateManager", "WorkflowState", "EntityState"]
