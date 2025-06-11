"""
Assertion Module

This module provides assertion-related events, emitters, and states.
"""

from .events import (
    AssertionEventType,
    AssertionEvent,
    AssertionsValidationStartedEvent,
    AssertionsValidationCompletedEvent,
    AssertionProgressEvent,
    AssertionResultEvent,
    AssertionErrorEvent,
    AssertionUnknownEvent,
)
from .emitter import AssertionEventEmitter
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
