"""
Experiment Events

This module defines events specific to experiment lifecycle management.
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
    """Base class for all experiment events."""

    def __init__(
        self,
        event_type: ExperimentEventType,
        experiment_id: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=event_type.value,
            entity_type=EventType.EXPERIMENT,
            entity_id=experiment_id,
            data=data,
        )
        self.event_type = event_type


class ExperimentInitializedEvent(ExperimentEvent):
    """Event emitted when an experiment is initialized."""

    def __init__(self, experiment_id: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            event_type=ExperimentEventType.INITIALIZED,
            experiment_id=experiment_id,
            data={"config": config or {}},
        )

    @property
    def config(self) -> Dict[str, Any]:
        return self.data.get("config", {})


class ExperimentPluginLoadingStartedEvent(ExperimentEvent):
    """Event emitted when plugin loading starts."""

    def __init__(self, experiment_id: str, plugin_count: Optional[int] = None):
        super().__init__(
            event_type=ExperimentEventType.PLUGIN_LOADING_STARTED,
            experiment_id=experiment_id,
            data={"plugin_count": plugin_count},
        )


class ExperimentPluginLoadingCompletedEvent(ExperimentEvent):
    """Event emitted when plugin loading completes."""

    def __init__(
        self,
        experiment_id: str,
        loaded_plugins: Optional[list] = None,
        plugin_count: Optional[int] = None,
    ):
        super().__init__(
            event_type=ExperimentEventType.PLUGIN_LOADING_COMPLETED,
            experiment_id=experiment_id,
            data={
                "loaded_plugins": loaded_plugins or [],
                "plugin_count": plugin_count or len(loaded_plugins or []),
            },
        )


class ExperimentPluginLoadingFailedEvent(ExperimentEvent):
    """Event emitted when plugin loading fails."""

    def __init__(
        self,
        experiment_id: str,
        error_message: str,
        error_type: Optional[str] = None,
        failed_plugins: Optional[list] = None,
    ):
        super().__init__(
            event_type=ExperimentEventType.PLUGIN_LOADING_FAILED,
            experiment_id=experiment_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "failed_plugins": failed_plugins or [],
            },
        )


class ExperimentTestCasesInitializedEvent(ExperimentEvent):
    """Event emitted when test cases are initialized."""

    def __init__(
        self, experiment_id: str, test_count: int, test_names: Optional[list] = None
    ):
        super().__init__(
            event_type=ExperimentEventType.TEST_CASES_INITIALIZED,
            experiment_id=experiment_id,
            data={"test_count": test_count, "test_names": test_names or []},
        )


class ExperimentExecutionStartedEvent(ExperimentEvent):
    """Event emitted when experiment execution starts."""

    def __init__(self, experiment_id: str, test_count: Optional[int] = None):
        super().__init__(
            event_type=ExperimentEventType.EXECUTION_STARTED,
            experiment_id=experiment_id,
            data={"test_count": test_count},
        )


class ExperimentExecutionCompletedEvent(ExperimentEvent):
    """Event emitted when experiment execution completes successfully."""

    def __init__(
        self,
        experiment_id: str,
        success_count: int,
        failure_count: int,
        total_count: int,
        duration_seconds: Optional[float] = None,
    ):
        super().__init__(
            event_type=ExperimentEventType.EXECUTION_COMPLETED,
            experiment_id=experiment_id,
            data={
                "success_count": success_count,
                "failure_count": failure_count,
                "total_count": total_count,
                "duration_seconds": duration_seconds,
            },
        )


class ExperimentExecutionFailedEvent(ExperimentEvent):
    """Event emitted when experiment execution fails."""

    def __init__(
        self,
        experiment_id: str,
        error_message: str,
        error_type: Optional[str] = None,
        phase: Optional[str] = None,
    ):
        super().__init__(
            event_type=ExperimentEventType.EXECUTION_FAILED,
            experiment_id=experiment_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "phase": phase,
            },
        )


class ExperimentFinishedEarlyEvent(ExperimentEvent):
    """Event emitted when experiment finishes early due to interruption or error."""

    def __init__(
        self, experiment_id: str, reason: str, details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            event_type=ExperimentEventType.FINISHED_EARLY,
            experiment_id=experiment_id,
            data={"reason": reason, "details": details or {}},
        )


class ExperimentCompletedEvent(ExperimentEvent):
    """Event emitted when experiment completes successfully."""

    def __init__(self, experiment_id: str, summary: Optional[Dict[str, Any]] = None):
        super().__init__(
            event_type=ExperimentEventType.COMPLETED,
            experiment_id=experiment_id,
            data={"summary": summary or {}},
        )


class ExperimentFailedEvent(ExperimentEvent):
    """Event emitted when experiment fails."""

    def __init__(
        self,
        experiment_id: str,
        error_message: str,
        error_type: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            event_type=ExperimentEventType.FAILED,
            experiment_id=experiment_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "summary": summary or {},
            },
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
        return self.data.get("failed_service", "")

    @property
    def reason(self) -> str:
        return self.data.get("reason", "")

    @property
    def termination_source(self) -> str:
        return self.data.get("termination_source", "service_monitor")
