# panther/core/events/event_summarizer.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class EventImportance(Enum):
    """Event importance levels for filtering."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class EventSummary:
    """Summary of an event with importance and details."""

    importance: EventImportance
    summary: str
    details: Dict[str, Any]
    should_batch: bool = False


class EventSummarizer:
    """Summarize event data to reduce log verbosity."""

    IMPORTANT_EVENT_TYPES = {
        # Experiment events
        "experiment.started": EventImportance.HIGH,
        "experiment.completed": EventImportance.HIGH,
        "experiment.failed": EventImportance.CRITICAL,
        "experiment.phase_changed": EventImportance.MEDIUM,
        # Test events
        "test.started": EventImportance.HIGH,
        "test.completed": EventImportance.HIGH,
        "test.failed": EventImportance.CRITICAL,
        "test.skipped": EventImportance.MEDIUM,
        # Step events - set to LOW importance so they're logged at DEBUG level
        "step.progress": EventImportance.LOW,
        "step.execution_started": EventImportance.LOW,
        "step.execution_completed": EventImportance.MEDIUM,
        "step.execution_failed": EventImportance.HIGH,
        # Service events
        "service.started": EventImportance.MEDIUM,
        "service.stopped": EventImportance.MEDIUM,
        "service.crashed": EventImportance.CRITICAL,
        "service.error": EventImportance.HIGH,
        "service.ready": EventImportance.MEDIUM,
        "service.preparation_started": EventImportance.LOW,
        # Command events
        "command.generated": EventImportance.LOW,
        "command.executed": EventImportance.LOW,
        "command.failed": EventImportance.HIGH,
        # State events
        "state.changed": EventImportance.LOW,
        "state.transitioning": EventImportance.LOW,
        # Environment events
        "environment.setup_started": EventImportance.MEDIUM,
        "environment.ready": EventImportance.MEDIUM,
        "environment.teardown_completed": EventImportance.MEDIUM,
        "environment.error": EventImportance.HIGH,
        # Metrics events
        "metrics.collected": EventImportance.LOW,
        "metrics.published": EventImportance.LOW,
        # Plugin events
        "plugin.loaded": EventImportance.LOW,
        "plugin.error": EventImportance.HIGH,
    }

    # Events that should be batched to reduce noise
    BATCHABLE_EVENTS = {
        "command.generated",
        "state.transitioning",
        "metrics.collected",
        "plugin.loaded",
        "step.progress",  # Add step progress to batchable events to reduce noise
    }

    @classmethod
    def summarize_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> EventSummary:
        """Create a concise summary of an event."""
        importance = cls.IMPORTANT_EVENT_TYPES.get(event_type, EventImportance.MEDIUM)
        should_batch = event_type in cls.BATCHABLE_EVENTS

        # Extract key information based on event type
        if "experiment" in event_type:
            summary, details = cls._summarize_experiment_event(event_type, event_data)
        elif "test" in event_type:
            summary, details = cls._summarize_test_event(event_type, event_data)
        elif "service" in event_type:
            summary, details = cls._summarize_service_event(event_type, event_data)
        elif "step" in event_type:
            summary, details = cls._summarize_step_event(event_type, event_data)
        elif "command" in event_type:
            summary, details = cls._summarize_command_event(event_type, event_data)
        elif "state" in event_type:
            summary, details = cls._summarize_state_event(event_type, event_data)
        elif "environment" in event_type:
            summary, details = cls._summarize_environment_event(event_type, event_data)
        elif "metrics" in event_type:
            summary, details = cls._summarize_metrics_event(event_type, event_data)
        elif "plugin" in event_type:
            summary, details = cls._summarize_plugin_event(event_type, event_data)
        else:
            summary, details = cls._summarize_generic_event(event_type, event_data)

        return EventSummary(
            importance=importance,
            summary=summary,
            details=details,
            should_batch=should_batch,
        )

    @classmethod
    def should_log_event(cls, event_type: str, threshold: EventImportance) -> bool:
        """Check if an event should be logged based on importance threshold."""
        importance = cls.IMPORTANT_EVENT_TYPES.get(event_type, EventImportance.MEDIUM)
        return importance.value >= threshold.value

    @classmethod
    def _summarize_step_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize step events."""
        step_name = event_data.get("step_name", "unknown")

        if event_type == "step.progress":
            progress = event_data.get("progress_percentage", 0)
            message = event_data.get("progress_message", "")
            summary = f"{step_name} progress: {progress:.1f}%"
            if message:
                summary += f" - {message}"

            details = {
                "step_name": step_name,
                "progress": f"{progress:.1f}%",
                "test_case": event_data.get("test_case_id"),
            }
        elif event_type == "step.execution_started":
            summary = f"Started step: {step_name}"
            details = {"step_name": step_name}
        elif event_type == "step.execution_completed":
            duration = event_data.get("duration")
            summary = f"Completed step: {step_name}"
            if duration:
                summary += f" in {duration:.2f}s"
            details = {"step_name": step_name, "duration": duration}
        elif event_type == "step.execution_failed":
            error = event_data.get("error_message", "Unknown error")
            summary = f"Step failed: {step_name} - {error}"
            details = {"step_name": step_name, "error": error}
        else:
            summary = f"Step {event_type}: {step_name}"
            details = {"step_name": step_name}

        return summary, details

    @classmethod
    def _summarize_experiment_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize experiment events."""
        experiment_id = event_data.get("experiment_id", "unknown")

        if event_type == "experiment.started":
            summary = f"Experiment started: {experiment_id}"
            details = {"experiment_id": experiment_id}
        elif event_type == "experiment.completed":
            duration = event_data.get("duration")
            summary = f"Experiment completed: {experiment_id}"
            if duration:
                summary += f" in {duration:.2f}s"
            details = {"experiment_id": experiment_id, "duration": duration}
        elif event_type == "experiment.failed":
            reason = event_data.get("failure_reason", "Unknown")
            summary = f"Experiment failed: {experiment_id} - {reason}"
            details = {"experiment_id": experiment_id, "failure_reason": reason}
        else:
            summary = f"Experiment {event_type}: {experiment_id}"
            details = {"experiment_id": experiment_id}

        return summary, details

    @classmethod
    def _summarize_test_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize test events."""
        test_name = event_data.get("test_name", event_data.get("test_id", "unknown"))

        if event_type == "test.started":
            summary = f"Test started: {test_name}"
            details = {"test_name": test_name}
        elif event_type == "test.completed":
            passed = event_data.get("passed", False)
            summary = f"Test {'passed' if passed else 'failed'}: {test_name}"
            details = {"test_name": test_name, "passed": passed}
        elif event_type == "test.failed":
            reason = event_data.get("failure_reason", "Unknown")
            summary = f"Test failed: {test_name} - {reason}"
            details = {"test_name": test_name, "failure_reason": reason}
        else:
            summary = f"Test {event_type}: {test_name}"
            details = {"test_name": test_name}

        return summary, details

    @classmethod
    def _summarize_service_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize service events."""
        service_name = event_data.get(
            "service_name", event_data.get("service_id", "unknown")
        )

        if event_type == "service.started":
            summary = f"Service started: {service_name}"
            details = {"service_name": service_name}
        elif event_type == "service.stopped":
            summary = f"Service stopped: {service_name}"
            details = {"service_name": service_name}
        elif event_type == "service.error":
            error = event_data.get("error_message", "Unknown error")
            summary = f"Service error: {service_name} - {error}"
            details = {"service_name": service_name, "error": error}
        else:
            summary = f"Service {event_type}: {service_name}"
            details = {"service_name": service_name}

        return summary, details

    @classmethod
    def _summarize_command_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize command events."""
        command = event_data.get("command", "unknown")
        # Truncate long commands
        if len(command) > 50:
            command = command[:47] + "..."

        if event_type == "command.executed":
            return_code = event_data.get("return_code")
            summary = f"Command executed: {command}"
            if return_code is not None:
                summary += f" (exit {return_code})"
            details = {"command": command, "return_code": return_code}
        else:
            summary = f"Command {event_type}: {command}"
            details = {"command": command}

        return summary, details

    @classmethod
    def _summarize_state_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize state events."""
        from_state = event_data.get("from_state", "unknown")
        to_state = event_data.get("to_state", "unknown")

        if event_type == "state.changed":
            summary = f"State: {from_state} → {to_state}"
            details = {"from_state": from_state, "to_state": to_state}
        else:
            summary = f"State {event_type}: {from_state}"
            details = {"from_state": from_state}

        return summary, details

    @classmethod
    def _summarize_environment_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize environment events."""
        env_name = event_data.get("environment_name", "unknown")

        if event_type == "environment.setup_started":
            summary = f"Environment setup: {env_name}"
            details = {"environment_name": env_name}
        elif event_type == "environment.ready":
            summary = f"Environment ready: {env_name}"
            details = {"environment_name": env_name}
        else:
            summary = f"Environment {event_type}: {env_name}"
            details = {"environment_name": env_name}

        return summary, details

    @classmethod
    def _summarize_metrics_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize metrics events."""
        metric_count = len(event_data.get("metrics", {}))
        summary = f"Metrics {event_type}: {metric_count} metrics"
        details = {"count": metric_count}
        return summary, details

    @classmethod
    def _summarize_plugin_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize plugin events."""
        plugin_name = event_data.get("plugin_name", "unknown")
        summary = f"Plugin {event_type}: {plugin_name}"
        details = {"plugin_name": plugin_name}
        return summary, details

    @classmethod
    def _summarize_generic_event(
        cls, event_type: str, event_data: Dict[str, Any]
    ) -> tuple:
        """Summarize generic events."""
        # Extract any name-like field for context
        name_fields = ["name", "id", "entity_id", "entity_name"]
        entity_name = None
        for field in name_fields:
            if field in event_data:
                entity_name = event_data[field]
                break

        if entity_name:
            summary = f"{event_type}: {entity_name}"
            details = {"entity": entity_name}
        else:
            summary = event_type
            details = {}

        return summary, details
