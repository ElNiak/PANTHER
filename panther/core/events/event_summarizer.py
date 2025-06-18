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
        elif "command" in event_type:
            summary, details = cls._summarize_command_event(event_type, event_data)
        elif "environment" in event_type:
            summary, details = cls._summarize_environment_event(event_type, event_data)
        elif "state" in event_type:
            summary, details = cls._summarize_state_event(event_type, event_data)
        else:
            # Generic summary for unknown event types
            summary = cls._create_generic_summary(event_data)
            details = cls._extract_key_details(event_data)

        return EventSummary(importance, summary, details, should_batch)

    @classmethod
    def _summarize_experiment_event(
        cls, event_type: str, data: Dict[str, Any]
    ) -> tuple:
        """Summarize experiment-related events."""
        name = data.get("name", "Unknown")
        phase = data.get("phase", "Unknown")

        if event_type == "experiment.started":
            summary = f"Experiment '{name}' started"
            details = {
                "test_count": data.get("test_count", 0),
                "output_dir": data.get("output_dir", "N/A"),
            }
        elif event_type == "experiment.failed":
            summary = (
                f"Experiment '{name}' failed: {data.get('error', 'Unknown error')}"
            )
            details = {
                "phase": phase,
                "duration": data.get("duration", "N/A"),
                "error_type": data.get("error_type", "Unknown"),
            }
        else:
            summary = f"Experiment '{name}' - {phase}"
            details = {
                "test_count": data.get("test_count", 0),
                "duration": data.get("duration", "N/A"),
            }

        return summary, details

    @classmethod
    def _summarize_test_event(cls, event_type: str, data: Dict[str, Any]) -> tuple:
        """Summarize test-related events."""
        test_name = data.get("test_name", "Unknown")

        if event_type == "test.failed":
            summary = f"Test '{test_name}' failed: {data.get('reason', 'Unknown')}"
            details = {
                "duration": data.get("duration", "N/A"),
                "error": data.get("error", None),
                "assertion": data.get("assertion", None),
            }
        else:
            summary = f"Test '{test_name}' {event_type.split('.')[-1]}"
            details = {
                "duration": data.get("duration", "N/A"),
                "services": data.get("services", []),
            }

        return summary, details

    @classmethod
    def _summarize_service_event(cls, event_type: str, data: Dict[str, Any]) -> tuple:
        """Summarize service-related events."""
        service_name = data.get("service_name", "Unknown")
        implementation = data.get("implementation", "N/A")

        if event_type == "service.crashed":
            summary = f"Service '{service_name}' crashed"
            details = {
                "implementation": implementation,
                "exit_code": data.get("exit_code", "N/A"),
                "error": data.get("error", None),
            }
        elif event_type == "service.error":
            summary = (
                f"Service '{service_name}' error: {data.get('error_type', 'Unknown')}"
            )
            details = {
                "implementation": implementation,
                "error_message": data.get("error_message", "N/A"),
            }
        else:
            status = event_type.split(".")[-1]
            summary = f"Service '{service_name}' {status}"
            details = {
                "implementation": implementation,
            }

        return summary, details

    @classmethod
    def _summarize_command_event(cls, event_type: str, data: Dict[str, Any]) -> tuple:
        """Summarize command-related events."""
        phase = data.get("phase", "unknown")
        command = data.get("command", "")

        # Skip empty or no-op commands
        if not command or command in [
            "No commands",
            "No pre-run commands",
            "No post-run commands",
            "No compile commands",
            "No post-compile commands",
        ]:
            return None, None

        # Truncate long commands
        if len(command) > 80:
            command_summary = command[:77] + "..."
        else:
            command_summary = command

        summary = f"{phase.replace('_', ' ').title()}: {command_summary}"
        details = {
            "phase": phase,
            "length": len(command),
        }

        return summary, details

    @classmethod
    def _summarize_environment_event(
        cls, event_type: str, data: Dict[str, Any]
    ) -> tuple:
        """Summarize environment-related events."""
        env_type = data.get("environment_type", "Unknown")
        name = data.get("name", env_type)

        status = event_type.split(".")[-1].replace("_", " ")
        summary = f"Environment '{name}' {status}"

        details = {
            "type": env_type,
        }

        if "error" in data:
            details["error"] = data["error"]

        return summary, details

    @classmethod
    def _summarize_state_event(cls, event_type: str, data: Dict[str, Any]) -> tuple:
        """Summarize state-related events."""
        entity = data.get("entity", "Unknown")
        from_state = data.get("from_state", "Unknown")
        to_state = data.get("to_state", "Unknown")

        summary = f"{entity}: {from_state} → {to_state}"
        details = {}

        return summary, details

    @classmethod
    def _create_generic_summary(cls, data: Dict[str, Any]) -> str:
        """Create a generic summary for unknown event types."""
        if "message" in data:
            return str(data["message"])[:100]
        elif "name" in data:
            return f"{data['name']}"
        else:
            # Try to find the most relevant field
            for key in ["description", "summary", "title", "action"]:
                if key in data:
                    return str(data[key])[:100]

        # Fallback to string representation
        return str(data)[:100] + "..." if len(str(data)) > 100 else str(data)

    @classmethod
    def _extract_key_details(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key details from event data."""
        # Common important fields
        important_fields = {
            "duration",
            "error",
            "error_type",
            "error_message",
            "exit_code",
            "reason",
            "count",
            "size",
            "status",
        }

        details = {}
        for field in important_fields:
            if field in data:
                details[field] = data[field]

        return details

    @classmethod
    def should_log_event(
        cls, event_type: str, importance_threshold: EventImportance
    ) -> bool:
        """Determine if an event should be logged based on importance."""
        event_importance = cls.IMPORTANT_EVENT_TYPES.get(
            event_type, EventImportance.MEDIUM
        )
        return event_importance.value >= importance_threshold.value

    @classmethod
    def format_event_batch(cls, events: List[Dict[str, Any]], event_type: str) -> str:
        """Format a batch of similar events into a single log entry."""
        if not events:
            return ""

        count = len(events)
        if event_type == "command.generated":
            phases = [e.get("phase", "unknown") for e in events]
            phase_counts = {}
            for phase in phases:
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
            summary = f"Generated {count} commands: " + ", ".join(
                f"{cnt} {phase}" for phase, cnt in phase_counts.items()
            )
        elif event_type == "plugin.loaded":
            plugin_names = [e.get("plugin_name", "unknown") for e in events]
            summary = f"Loaded {count} plugins: {', '.join(plugin_names[:5])}"
            if count > 5:
                summary += f" and {count - 5} more"
        else:
            summary = f"Batched {count} {event_type} events"

        return summary
