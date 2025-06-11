"""
Experiment Event Emitter

This module provides typed event emission for experiment lifecycle events.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from panther.core.observer.event_manager import EventManager

from panther.core.events.experiment.events import (
    ExperimentInitializedEvent,
    ExperimentPluginLoadingStartedEvent,
    ExperimentPluginLoadingCompletedEvent,
    ExperimentPluginLoadingFailedEvent,
    ExperimentTestCasesInitializedEvent,
    ExperimentExecutionStartedEvent,
    ExperimentExecutionCompletedEvent,
    ExperimentExecutionFailedEvent,
    ExperimentFinishedEarlyEvent,
    ExperimentCompletedEvent,
    ExperimentFailedEvent,
)


class ExperimentEventEmitter:
    """Type-safe event emitter for experiment events."""

    def __init__(self, event_manager: "EventManager", experiment_id: str):
        """
        Initialize experiment event emitter.

        Args:
            event_manager: Event manager to emit events through
            experiment_id: ID of the experiment this emitter handles
        """
        self.event_manager = event_manager
        self.experiment_id = experiment_id

    def emit_initialized(self, config: dict[str, Any] | None = None) -> None:
        """Emit experiment initialized event."""
        event = ExperimentInitializedEvent(experiment_id=self.experiment_id, config=config)
        self.event_manager.notify(event)

    def emit_plugin_loading_started(self, plugin_count: int | None = None) -> None:
        """Emit plugin loading started event."""
        event = ExperimentPluginLoadingStartedEvent(
            experiment_id=self.experiment_id, plugin_count=plugin_count
        )
        self.event_manager.notify(event)

    def emit_plugin_loading_completed(
        self, loaded_plugins: list | None = None, plugin_count: int | None = None
    ) -> None:
        """Emit plugin loading completed event."""
        event = ExperimentPluginLoadingCompletedEvent(
            experiment_id=self.experiment_id,
            loaded_plugins=loaded_plugins,
            plugin_count=plugin_count,
        )
        self.event_manager.notify(event)

    def emit_plugin_loading_failed(
        self, error_message: str, error_type: str | None = None, failed_plugins: list | None = None
    ) -> None:
        """Emit plugin loading failed event."""
        event = ExperimentPluginLoadingFailedEvent(
            experiment_id=self.experiment_id,
            error_message=error_message,
            error_type=error_type,
            failed_plugins=failed_plugins,
        )
        self.event_manager.notify(event)

    def emit_test_cases_initialized(self, test_count: int, test_names: list | None = None) -> None:
        """Emit test cases initialized event."""
        event = ExperimentTestCasesInitializedEvent(
            experiment_id=self.experiment_id, test_count=test_count, test_names=test_names
        )
        self.event_manager.notify(event)

    def emit_execution_started(self, test_count: int | None = None) -> None:
        """Emit execution started event."""
        event = ExperimentExecutionStartedEvent(
            experiment_id=self.experiment_id, test_count=test_count
        )
        self.event_manager.notify(event)

    def emit_execution_completed(
        self,
        success_count: int,
        failure_count: int,
        total_count: int,
        duration_seconds: float | None = None,
    ) -> None:
        """Emit execution completed event."""
        event = ExperimentExecutionCompletedEvent(
            experiment_id=self.experiment_id,
            success_count=success_count,
            failure_count=failure_count,
            total_count=total_count,
            duration_seconds=duration_seconds,
        )
        self.event_manager.notify(event)

    def emit_execution_failed(
        self, error_message: str, error_type: str | None = None, phase: str | None = None
    ) -> None:
        """Emit execution failed event."""
        event = ExperimentExecutionFailedEvent(
            experiment_id=self.experiment_id,
            error_message=error_message,
            error_type=error_type,
            phase=phase,
        )
        self.event_manager.notify(event)

    def emit_finished_early(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Emit finished early event."""
        event = ExperimentFinishedEarlyEvent(
            experiment_id=self.experiment_id, reason=reason, details=details
        )
        self.event_manager.notify(event)

    def emit_completed(self, summary: dict[str, Any] | None = None) -> None:
        """Emit experiment completed event."""
        event = ExperimentCompletedEvent(experiment_id=self.experiment_id, summary=summary)
        self.event_manager.notify(event)

    def emit_failed(
        self,
        error_message: str,
        error_type: str | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        """Emit experiment failed event."""
        event = ExperimentFailedEvent(
            experiment_id=self.experiment_id,
            error_message=error_message,
            error_type=error_type,
            summary=summary,
        )
        self.event_manager.notify(event)
