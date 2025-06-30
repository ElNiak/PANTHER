from typing import TYPE_CHECKING, Any, Dict, List, Optional

"""
Experiment Event Emitter

This module provides typed event emission for experiment lifecycle events.
"""

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EntityEventEmitterBase
from panther.core.events.experiment.events import (
    ExperimentCompletedEvent,
    ExperimentExecutionCompletedEvent,
    ExperimentExecutionFailedEvent,
    ExperimentExecutionStartedEvent,
    ExperimentFailedEvent,
    ExperimentFinishedEarlyEvent,
    ExperimentInitializedEvent,
    ExperimentPluginLoadingCompletedEvent,
    ExperimentPluginLoadingFailedEvent,
    ExperimentPluginLoadingStartedEvent,
    ExperimentTestCasesInitializedEvent,
)


class ExperimentEventEmitter(EntityEventEmitterBase):
    """, TYPE_CHECKING, TYPE_CHECKINGType-safe event emitter for experiment events."""

    def __init__(self, event_manager: "EventManager", experiment_id: str):
        """
        Initialize experiment event emitter.

        Args:
            event_manager: Event manager to emit events through
            experiment_id: ID of the experiment this emitter handles
        """
        super().__init__(event_manager, experiment_id, "experiment")

    def emit_initialized(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Emit experiment initialized event."""
        self._create_and_emit_entity_event(ExperimentInitializedEvent, config=config)

    def emit_plugin_loading_started(self, plugin_count: Optional[int] = None) -> None:
        """Emit plugin loading started event."""
        self._create_and_emit_entity_event(
            ExperimentPluginLoadingStartedEvent, plugin_count=plugin_count
        )

    def emit_plugin_loading_completed(
        self, loaded_plugins: Optional[list] = None, plugin_count: Optional[int] = None
    ) -> None:
        """Emit plugin loading completed event."""
        self._create_and_emit_entity_event(
            ExperimentPluginLoadingCompletedEvent,
            loaded_plugins=loaded_plugins,
            plugin_count=plugin_count,
        )

    def emit_plugin_loading_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        failed_plugins: Optional[list] = None,
    ) -> None:
        """Emit plugin loading failed event."""
        self._create_and_emit_entity_event(
            ExperimentPluginLoadingFailedEvent,
            error_message=error_message,
            error_type=error_type,
            failed_plugins=failed_plugins,
        )

    def emit_test_cases_initialized(
        self, test_count: int, test_names: Optional[list] = None
    ) -> None:
        """Emit test cases initialized event."""
        self._create_and_emit_entity_event(
            ExperimentTestCasesInitializedEvent,
            test_count=test_count,
            test_names=test_names,
        )

    def emit_execution_started(self, test_count: Optional[int] = None) -> None:
        """Emit execution started event."""
        self._create_and_emit_entity_event(
            ExperimentExecutionStartedEvent, test_count=test_count
        )

    def emit_execution_completed(
        self,
        success_count: int,
        failure_count: int,
        total_count: int,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Emit execution completed event."""
        self._create_and_emit_entity_event(
            ExperimentExecutionCompletedEvent,
            success_count=success_count,
            failure_count=failure_count,
            total_count=total_count,
            duration_seconds=duration_seconds,
        )

    def emit_execution_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> None:
        """Emit execution failed event."""
        self._create_and_emit_entity_event(
            ExperimentExecutionFailedEvent,
            error_message=error_message,
            error_type=error_type,
            phase=phase,
        )

    def emit_finished_early(
        self, reason: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit finished early event."""
        self._create_and_emit_entity_event(
            ExperimentFinishedEarlyEvent, reason=reason, details=details
        )

    def emit_completed(self, summary: Optional[Dict[str, Any]] = None) -> None:
        """Emit experiment completed event."""
        self._create_and_emit_entity_event(ExperimentCompletedEvent, summary=summary)

    def emit_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit experiment failed event."""
        self._create_and_emit_entity_event(
            ExperimentFailedEvent,
            error_message=error_message,
            error_type=error_type,
            summary=summary,
        )
