"""Experiment Events.

This module defines events specific to experiment lifecycle management.
Uses factory classmethods on the base ExperimentEvent class instead of
individual subclasses for most event types.
"""

from enum import Enum
from typing import Any, Dict, Optional

from panther.core.events.base.event_base import BaseEvent, EventType


class ExperimentEventType(Enum):
    """Experiment-specific event types."""

    INITIALIZED = "initialized"
    PLUGIN_LOADING_STARTED = "plugin_loading_started"
    PLUGIN_LOADING_COMPLETED = "plugin_loading_completed"
    PLUGIN_LOADING_FAILED = "plugin_loading_failed"
    TEST_CASES_INITIALIZED = "test_cases_initialized"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    FINISHED_EARLY = "finished_early"
    SERVICE_FAILURE = "service_failure"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentEvent(BaseEvent):
    """Base class for all experiment events.

    Most experiment events are created via factory classmethods rather than
    individual subclasses. The event_type discriminant identifies the
    specific event kind.
    """

    def __init__(
        self,
        event_type: ExperimentEventType,
        experiment_id: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize experiment event."""
        super().__init__(
            name=event_type.value,
            entity_type=EventType.EXPERIMENT,
            entity_id=experiment_id,
            data=data,
        )
        self.event_type = event_type

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def initialized(
        cls, experiment_id: str, config: Optional[Dict[str, Any]] = None
    ) -> "ExperimentEvent":
        """Create initialized event."""
        return cls(
            ExperimentEventType.INITIALIZED,
            experiment_id,
            data={"config": config or {}},
        )

    @classmethod
    def plugin_loading_started(
        cls, experiment_id: str, plugin_count: Optional[int] = None
    ) -> "ExperimentEvent":
        """Create plugin loading started event."""
        return cls(
            ExperimentEventType.PLUGIN_LOADING_STARTED,
            experiment_id,
            data={"plugin_count": plugin_count},
        )

    @classmethod
    def plugin_loading_completed(
        cls,
        experiment_id: str,
        loaded_plugins: Optional[list] = None,
        plugin_count: Optional[int] = None,
    ) -> "ExperimentEvent":
        """Create plugin loading completed event."""
        return cls(
            ExperimentEventType.PLUGIN_LOADING_COMPLETED,
            experiment_id,
            data={
                "loaded_plugins": loaded_plugins or [],
                "plugin_count": plugin_count or len(loaded_plugins or []),
            },
        )

    @classmethod
    def plugin_loading_failed(
        cls,
        experiment_id: str,
        error_message: str,
        error_type: Optional[str] = None,
        failed_plugins: Optional[list] = None,
    ) -> "ExperimentEvent":
        """Create plugin loading failed event."""
        return cls(
            ExperimentEventType.PLUGIN_LOADING_FAILED,
            experiment_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "failed_plugins": failed_plugins or [],
            },
        )

    @classmethod
    def test_cases_initialized(
        cls,
        experiment_id: str,
        test_count: int,
        test_names: Optional[list] = None,
    ) -> "ExperimentEvent":
        """Create test cases initialized event."""
        return cls(
            ExperimentEventType.TEST_CASES_INITIALIZED,
            experiment_id,
            data={"test_count": test_count, "test_names": test_names or []},
        )

    @classmethod
    def execution_started(
        cls, experiment_id: str, test_count: Optional[int] = None
    ) -> "ExperimentEvent":
        """Create execution started event."""
        return cls(
            ExperimentEventType.EXECUTION_STARTED,
            experiment_id,
            data={"test_count": test_count},
        )

    @classmethod
    def execution_completed(
        cls,
        experiment_id: str,
        success_count: int,
        failure_count: int,
        total_count: int,
        duration_seconds: Optional[float] = None,
    ) -> "ExperimentEvent":
        """Create execution completed event."""
        return cls(
            ExperimentEventType.EXECUTION_COMPLETED,
            experiment_id,
            data={
                "success_count": success_count,
                "failure_count": failure_count,
                "total_count": total_count,
                "duration_seconds": duration_seconds,
            },
        )

    @classmethod
    def execution_failed(
        cls,
        experiment_id: str,
        error_message: str,
        error_type: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> "ExperimentEvent":
        """Create execution failed event."""
        return cls(
            ExperimentEventType.EXECUTION_FAILED,
            experiment_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "phase": phase,
            },
        )

    @classmethod
    def completed(
        cls, experiment_id: str, summary: Optional[Dict[str, Any]] = None
    ) -> "ExperimentEvent":
        """Create completed event."""
        return cls(
            ExperimentEventType.COMPLETED,
            experiment_id,
            data={"summary": summary or {}},
        )

    @classmethod
    def failed(
        cls,
        experiment_id: str,
        error_message: str,
        error_type: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> "ExperimentEvent":
        """Create failed event."""
        return cls(
            ExperimentEventType.FAILED,
            experiment_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "summary": summary or {},
            },
        )


# -- Subclasses kept for isinstance() compatibility ---------------------------


class ExperimentFinishedEarlyEvent(ExperimentEvent):
    """Event emitted when experiment finishes early due to interruption or error."""

    def __init__(
        self, experiment_id: str, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        """Initialize with experiment ID, reason, and optional details."""
        super().__init__(
            event_type=ExperimentEventType.FINISHED_EARLY,
            experiment_id=experiment_id,
            data={"reason": reason, "details": details or {}},
        )


class ExperimentServiceFailureEvent(ExperimentEvent):
    """Event emitted when a service failure should terminate the experiment."""

    def __init__(
        self,
        experiment_id: str,
        failed_service: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize with experiment ID, failed service, and reason."""
        super().__init__(
            event_type=ExperimentEventType.SERVICE_FAILURE,
            experiment_id=experiment_id,
            data={
                "failed_service": failed_service,
                "reason": reason,
                "details": details or {},
                "termination_source": "service_monitor",
            },
        )

    @property
    def failed_service(self) -> str:
        """Return the failed service name."""
        return self.data.get("failed_service", "")

    @property
    def reason(self) -> str:
        """Return the failure reason."""
        return self.data.get("reason", "")

    @property
    def termination_source(self) -> str:
        """Return the termination source."""
        return self.data.get("termination_source", "service_monitor")
