"""
Storage Events Module

This module provides event classes specific to data storage and persistence operations.
"""

from panther.core.events.storage.events import (
    TestResultEvent,
    EnhancedResultEvent,
)

__all__ = [
    "TestResultEvent",
    "EnhancedResultEvent",
]
