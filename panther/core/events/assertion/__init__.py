"""
Assertion Module

This module provides assertion-related events, emitters, and states.
"""

from .emitter import AssertionEventEmitter
from .events import (
    AssertionErrorEvent,
    AssertionEvent,
    AssertionEventType,
    AssertionProgressEvent,
    AssertionResultEvent,
    AssertionsValidationCompletedEvent,
    AssertionsValidationStartedEvent,
    AssertionUnknownEvent,
)
from .states import AssertionState, AssertionValidationState

__all__ = [
    # Event types and base classes
    "AssertionEventType",
    "AssertionEvent",
    # Specific event classes
    "AssertionsValidationStartedEvent",
    "AssertionsValidationCompletedEvent",
    "AssertionProgressEvent",
    "AssertionResultEvent",
    "AssertionErrorEvent",
    "AssertionUnknownEvent",
    # Event emitter
    "AssertionEventEmitter",
    # States
    "AssertionState",
    "AssertionValidationState",
]
