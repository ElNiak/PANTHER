"""
Event-Aware Logger Observer Module

This module provides an enhanced logger observer that uses event types and context
for intelligent logging with color coding, filtering, and adaptive formatting.
"""

import logging
from datetime import datetime
from typing import Any
from collections.abc import Callable


from panther.core.observer.core.observer_interface import IObserver
from panther.core.observer.events import Event
from panther.core.observer.core.event_colors import get_severity_indicator, is_terminal_capable

# Map event types to colorlog colors for consistent coloring
EVENT_LOG_COLORS = {
    "system": "cyan",
    "test": "blue",
    "network": "magenta",
    "error": "bold_red",
    "fail": "bold_red",
    "warning": "bold_yellow",
    "pass": "bold_green",
    "success": "bold_green",
    "data": "cyan",
    "config": "blue",
    "security": "yellow",
    "performance": "yellow",
    "default": "white",
}


class LoggerObserver(IObserver):
    """
    Enhanced logger observer with event-aware capabilities.

    This observer provides:
    - Color-coded output based on event types (colorlog)
    - Adaptive log formatting based on event context
    - Intelligent filtering and prioritization
    - Multiple output formats (console, file, structured)
    - Event correlation and tracking
    """

    def __init__(
        self,
        log_level: str = "INFO",
        include_data: bool = True,
        excluded_event_types: list[str] | None = None,
        include_event_id: bool = True,
        include_timestamp: bool = True,
        enable_colors: bool | None = None,
        output_file: str | None = None,
        max_data_length: int = 500,
        event_filters: dict[str, Callable] | None = None,
        correlation_tracking: bool = True,
        structured_output: bool = False,
        priority_boost: dict[str, int] | None = None,
        global_config: Any = None,
    ):
        """Initialize the event-aware logger observer."""
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.include_data = include_data
        self.excluded_event_types = set(excluded_event_types or [])
        self.include_event_id = include_event_id
        self.include_timestamp = include_timestamp
        self.max_data_length = max_data_length
        self.event_filters = event_filters or {}
        self.correlation_tracking = correlation_tracking
        self.structured_output = structured_output
        self.priority_boost = priority_boost or {}

        # Store global config for log formatting settings
        self.config = global_config

        # Auto-detect color capability if not specified
        self.enable_colors = enable_colors if enable_colors is not None else is_terminal_capable()

        # Set up logging using the interface method
        self.logger = self._setup_logging(
            logger_name="EventLogger",
            log_level=self.log_level,
            enable_colors=self.enable_colors,
            output_file=output_file,
            structured_output=self.structured_output,
        )

        # Event correlation tracking
        self.event_correlations: dict[str, list[str]] = {}
        self.event_context: dict[str, dict[str, Any]] = {}

        # Statistics tracking
        self.event_counts: dict[str, int] = {}
        self.error_events: list[dict[str, Any]] = []

    def on_event(self, event: Event) -> bool:
        """Handle an event with enhanced logging capabilities."""
        # super().processed_events_uuids.append(str(event.id))
        event_type = self._get_event_type_safely(event)

        # Skip excluded event types
        if self._should_exclude_event(event_type):
            return True

        # Apply custom filters
        if not self._apply_custom_filters(event_type, event):
            return True

        # Special handling for experiment_finished_early check action
        # LoggerObserver should not confirm experiment finished early events
        if (
            event_type == "experiment_finished_early"
            and getattr(event, "data", {}).get("action") == "check"
        ):
            # Still log the event but don't confirm occurrence
            self._log_event(event)
            return False

        # Update statistics
        self._update_statistics(event_type, event)

        # Handle correlation tracking
        if self.correlation_tracking:
            self._track_event_correlation(event)

        # Format and log the event
        self._log_event(event)

        return True

    def _should_exclude_event(self, event_type: str) -> bool:
        """Check if an event should be excluded from logging."""
        return any(event_type.startswith(excluded) for excluded in self.excluded_event_types)

    def _apply_custom_filters(self, event_type: str, event: Event) -> bool:
        """Apply custom filters for the event type."""
        if event_type in self.event_filters:
            return self.event_filters[event_type](event)
        return True

    def _update_statistics(self, event_type: str, event: Event):
        """Update event statistics and tracking."""
        self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1

        # Track error events
        if "error" in event_type.lower() or "fail" in event_type.lower():
            self.error_events.append(
                {
                    "type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "data": getattr(event, "data", {}),
                    "id": getattr(event, "id", None),
                }
            )

    def _track_event_correlation(self, event: Event):
        """Track event correlations and context."""
        event_id = str(getattr(event, "id", "unknown"))
        event_type = self._get_event_type_safely(event)

        # Store event context
        self.event_context[event_id] = {
            "type": event_type,
            "timestamp": getattr(event, "timestamp", datetime.now()),
            "data": getattr(event, "data", {}),
        }

        # Track correlations based on data patterns
        event_data = getattr(event, "data", {})
        if "correlation_id" in event_data:
            corr_id = event_data["correlation_id"]
            if corr_id not in self.event_correlations:
                self.event_correlations[corr_id] = []
            self.event_correlations[corr_id].append(event_id)

    def _log_event(self, event: Event):
        """Format and log the event with enhanced formatting."""
        event_type = self._get_event_type_safely(event)
        event_id = str(getattr(event, "id", "")) if self.include_event_id else None
        timestamp = getattr(event, "timestamp", datetime.now()).strftime("%H:%M:%S.%f")[:-3]

        # Determine priority and log level
        priority = self._get_event_priority(event_type, event)
        log_level = self._get_log_level_for_event(event_type, priority)

        if self.structured_output:
            self._log_structured_event(event, event_type, priority)
        else:
            # Build a clean, standardized log message
            severity = get_severity_indicator(event_type)
            msg = f"{severity} {event_type}"

            if event_id:
                msg += f" ({event_id})"

            if hasattr(event, "data") and event.data and self.include_data:
                data_str = str(event.data)
                if len(data_str) > self.max_data_length:
                    data_str = f"{data_str[:self.max_data_length-3]}..."
                msg += f" - Data: {data_str}"

            # Send to logger - the ColoredFormatter will handle the colors
            self.logger.log(log_level, msg)

    def _get_event_priority(self, event_type: str, event: Event) -> str:
        """Determine the priority of an event."""
        # Check for explicit priority in event data
        event_data = getattr(event, "data", {})
        if "priority" in event_data:
            return event_data["priority"]

        # Check priority boost configuration
        for boost_type, boost_level in self.priority_boost.items():
            if event_type.startswith(boost_type):
                return ["debug", "info", "low", "medium", "high", "critical"][min(boost_level, 5)]

        # Default priority based on event type
        if "error" in event_type.lower() or "fail" in event_type.lower():
            return "high"
        elif "warning" in event_type.lower():
            return "medium"
        elif "critical" in event_type.lower():
            return "critical"
        elif "security" in event_type.lower():
            return "high"
        else:
            return "info"

    def _get_log_level_for_event(self, event_type: str, priority: str) -> int:
        """Map event priority to logging level."""
        priority_to_level = {
            "critical": logging.CRITICAL,
            "high": logging.ERROR,
            "medium": logging.WARNING,
            "low": logging.INFO,
            "info": logging.INFO,
            "debug": logging.DEBUG,
        }
        return priority_to_level.get(priority, logging.INFO)

    def _log_structured_event(self, event: Event, event_type: str, priority: str):
        """Log event in structured JSON format."""
        import json

        structured_data = {
            "event_type": event_type,
            "priority": priority,
            "timestamp": getattr(event, "timestamp", datetime.now()).isoformat(),
            "event_id": str(getattr(event, "id", "")),
            "data": getattr(event, "data", {}),
        }

        self.logger.info(json.dumps(structured_data, default=str))

    def _get_event_type_safely(self, event: Event) -> str:
        """Safely get the event type from an event object."""
        if hasattr(event, "get_type") and callable(getattr(event, "get_type")):
            return event.get_type()
        elif hasattr(event, "name"):
            return event.name
        else:
            return str(event.__class__.__name__)

    def is_interested(self, event_type: str) -> bool:
        """Check if the observer is interested in an event type."""
        if not event_type:
            return True
        return not self._should_exclude_event(event_type)

    def get_statistics(self) -> dict[str, Any]:
        """Get logging statistics and insights."""
        return {
            "event_counts": dict(self.event_counts),
            "total_events": sum(self.event_counts.values()),
            "error_events": len(self.error_events),
            "correlation_groups": len(self.event_correlations),
            "unique_event_types": len(self.event_counts),
        }

    def reset_statistics(self):
        """Reset all tracking statistics."""
        self.event_counts.clear()
        self.error_events.clear()
        self.event_correlations.clear()
        self.event_context.clear()

    def add_event_filter(self, event_type: str, filter_func: Callable[[Event], bool]):
        """Add a custom filter for a specific event type."""
        self.event_filters[event_type] = filter_func

    def remove_event_filter(self, event_type: str):
        """Remove a custom filter for a specific event type."""
        self.event_filters.pop(event_type, None)

    def set_priority_boost(self, event_type_prefix: str, boost_level: int):
        """Set priority boost for events matching a type prefix."""
        self.priority_boost[event_type_prefix] = boost_level

    def export_logs(self, output_path: str, format: str = "json") -> bool:
        """
        Export collected event data to a file.

        Args:
            output_path: Path to write the export file
            format: Export format ('json', 'csv')

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            if format.lower() == "json":
                self._export_json(output_path)
            elif format.lower() == "csv":
                self._export_csv(output_path)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to export logs: {e}")
            return False

    def _export_json(self, output_path: str):
        """Export logs in JSON format."""
        import json

        export_data = {
            "statistics": self.get_statistics(),
            "event_context": {
                k: {**v, "timestamp": v["timestamp"].isoformat()}
                for k, v in self.event_context.items()
            },
            "correlations": self.event_correlations,
            "export_timestamp": datetime.now().isoformat(),
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

    def _export_csv(self, output_path: str):
        """Export logs in CSV format."""
        import csv

        with open(output_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["event_id", "event_type", "timestamp", "data"])

            for event_id, context in self.event_context.items():
                writer.writerow(
                    [
                        event_id,
                        context["type"],
                        context["timestamp"].isoformat(),
                        str(context["data"]),
                    ]
                )
