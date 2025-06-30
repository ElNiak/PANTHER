"""
Metrics States

This module defines states for metrics collection and monitoring.
"""

from enum import Enum
from typing import Any, Dict, Optional

from panther.core.events.base.state_base import BaseState


class MetricsState(Enum):
    """Enumeration of metrics collection states."""

    COLLECTING = "collecting"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class MetricsCollectionState(BaseState):
    """
    State for metrics collection process.

    Tracks the current state of metrics collection for a given entity.
    """

    def __init__(
        self,
        entity_id: str,
        state: MetricsState = MetricsState.COLLECTING,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize metrics collection state.

        Args:
            entity_id: Identifier of the entity being monitored
            state: Current metrics collection state
            metadata: Additional state metadata
        """
        super().__init__(entity_id=entity_id, state=state.value, metadata=metadata)
        self.metrics_state = state

    def is_collecting(self) -> bool:
        """Check if metrics collection is active."""
        return self.metrics_state == MetricsState.COLLECTING

    def is_paused(self) -> bool:
        """Check if metrics collection is paused."""
        return self.metrics_state == MetricsState.PAUSED

    def is_stopped(self) -> bool:
        """Check if metrics collection is stopped."""
        return self.metrics_state == MetricsState.STOPPED

    def is_error(self) -> bool:
        """Check if metrics collection is in error state."""
        return self.metrics_state == MetricsState.ERROR

    def pause(self) -> None:
        """Pause metrics collection."""
        self.metrics_state = MetricsState.PAUSED
        self.state = self.metrics_state.value

    def resume(self) -> None:
        """Resume metrics collection."""
        self.metrics_state = MetricsState.COLLECTING
        self.state = self.metrics_state.value

    def stop(self) -> None:
        """Stop metrics collection."""
        self.metrics_state = MetricsState.STOPPED
        self.state = self.metrics_state.value

    def error(self) -> None:
        """Set metrics collection to error state."""
        self.metrics_state = MetricsState.ERROR
        self.state = self.metrics_state.value
