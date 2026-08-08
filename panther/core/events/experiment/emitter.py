"""Experiment Event Emitter.

This module provides typed event emission for experiment lifecycle events.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EntityEventEmitterBase
from panther.core.events.experiment.events import (
    ExperimentEvent,
    ExperimentFinishedEarlyEvent,
)


class ExperimentEventEmitter(EntityEventEmitterBase):
    """Type-safe event emitter for experiment events."""

    def __init__(self, event_manager: "EventManager", experiment_id: str):
        """Initialize experiment event emitter.

        Args:
            event_manager: Event manager to emit events through
            experiment_id: ID of the experiment this emitter handles
        """
        super().__init__(event_manager, experiment_id, "experiment")

    def emit_initialized(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Emit experiment initialized event."""
        event = ExperimentEvent.initialized(self.entity_id, config=config)
        self.event_manager.notify(event)

    def emit_plugin_loading_started(self, plugin_count: Optional[int] = None) -> None:
        """Emit plugin loading started event."""
        event = ExperimentEvent.plugin_loading_started(
            self.entity_id, plugin_count=plugin_count
        )
        self.event_manager.notify(event)

    def emit_plugin_loading_completed(
        self, loaded_plugins: Optional[list] = None, plugin_count: Optional[int] = None
    ) -> None:
        """Emit plugin loading completed event."""
        event = ExperimentEvent.plugin_loading_completed(
            self.entity_id,
            loaded_plugins=loaded_plugins,
            plugin_count=plugin_count,
        )
        self.event_manager.notify(event)

    def emit_plugin_loading_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        failed_plugins: Optional[list] = None,
    ) -> None:
        """Emit plugin loading failed event."""
        event = ExperimentEvent.plugin_loading_failed(
            self.entity_id,
            error_message,
            error_type=error_type,
            failed_plugins=failed_plugins,
        )
        self.event_manager.notify(event)

    def emit_test_cases_initialized(
        self, test_count: int, test_names: Optional[list] = None
    ) -> None:
        """Emit test cases initialized event."""
        event = ExperimentEvent.test_cases_initialized(
            self.entity_id,
            test_count,
            test_names=test_names,
        )
        self.event_manager.notify(event)

    def emit_execution_started(self, test_count: Optional[int] = None) -> None:
        """Emit execution started event."""
        event = ExperimentEvent.execution_started(self.entity_id, test_count=test_count)
        self.event_manager.notify(event)

    def emit_execution_completed(
        self,
        success_count: int,
        failure_count: int,
        total_count: int,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Emit execution completed event."""
        event = ExperimentEvent.execution_completed(
            self.entity_id,
            success_count,
            failure_count,
            total_count,
            duration_seconds=duration_seconds,
        )
        self.event_manager.notify(event)

    def emit_execution_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> None:
        """Emit execution failed event."""
        event = ExperimentEvent.execution_failed(
            self.entity_id,
            error_message,
            error_type=error_type,
            phase=phase,
        )
        self.event_manager.notify(event)

    def emit_finished_early(
        self, reason: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit finished early event."""
        self._create_and_emit_entity_event(
            ExperimentFinishedEarlyEvent, reason=reason, details=details
        )

    def emit_completed(self, summary: Optional[Dict[str, Any]] = None) -> None:
        """Emit experiment completed event."""
        event = ExperimentEvent.completed(self.entity_id, summary=summary)
        self.event_manager.notify(event)

    def emit_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit experiment failed event."""
        event = ExperimentEvent.failed(
            self.entity_id,
            error_message,
            error_type=error_type,
            summary=summary,
        )
        self.event_manager.notify(event)
