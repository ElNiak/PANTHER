"""Event-Aware Logger Observer Module.

This module provides an enhanced logger observer that uses event types and context
for intelligent logging with color coding, filtering, and adaptive formatting.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    import click

    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False

from panther.core.events.base.event_base import BaseEvent
from panther.core.events.experiment.events import ExperimentFinishedEarlyEvent
from panther.core.events.service.events import (
    DockerBuildCompletedEvent,
    DockerBuildFailedEvent,
    DockerBuildStartedEvent,
)
from panther.core.events.test.events import TestFailedEvent
from panther.core.observer.base.typed_observer_interface import (
    ITypedObserver,
    _handler_name_for,
)
from panther.core.observer.impl.event_colors import (
    get_severity_indicator,
    is_terminal_capable,
)

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


class LoggerObserver(ITypedObserver):
    """Enhanced logger observer with event-aware capabilities.

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
        excluded_event_types: Optional[List[str]] = None,
        include_event_id: bool = True,
        include_timestamp: bool = True,
        enable_colors: Optional[bool] = None,
        output_file: Optional[str] = None,
        max_data_length: int = 500,
        event_filters: Optional[Dict[str, Callable]] = None,
        correlation_tracking: bool = True,
        structured_output: bool = False,
        priority_boost: Optional[Dict[str, int]] = None,
        global_config: Any = None,
        debug_mode: bool = False,
        track_event_history: bool = False,
        max_history_size: int = 1000,
    ):
        """Initialize the event-aware logger observer with optional debug capabilities."""
        super().__init__()
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
        self.debug_mode = debug_mode
        self.track_event_history = track_event_history or debug_mode
        self.max_history_size = max_history_size

        # Store global config for log formatting settings
        self.config = global_config

        # Auto-detect color capability if not specified
        self.enable_colors = (
            enable_colors if enable_colors is not None else is_terminal_capable()
        )

        # Set up logging using the interface method
        # Use DEBUG level if debug mode is enabled
        if self.debug_mode and self.log_level > logging.DEBUG:
            self.log_level = logging.DEBUG

        self.logger = self._setup_logging(
            logger_name="DebugObserver",
            log_level=self.log_level,
            enable_colors=self.enable_colors,
            output_file=output_file,
            structured_output=self.structured_output,
        )

        # Event correlation tracking
        self.event_correlations: Dict[str, List[str]] = {}
        self.event_context: Dict[str, Dict[str, Any]] = {}

        # Statistics tracking
        self.event_counts: Dict[str, int] = {}
        self.error_events: List[Dict[str, Any]] = []

        # Recursion protection
        self._processing_event = False
        self._recursion_depth = 0
        self._max_recursion_depth = 5

        # Name-based handler names for typed dispatch (factory events only).
        # Type-based handlers (DockerBuild*, TestFailed) are dispatched via
        # _type_handlers and don't need to be listed here.
        self._logger_typed_handlers = {
            "on_experiment_failed",
            "on_service_error",
            "on_environment_error",
        }

        # Debug mode event history tracking
        if self.track_event_history:
            self.event_history: List[Dict[str, Any]] = []

    def on_event(self, event: BaseEvent) -> bool:
        """Handle an event with enhanced logging capabilities."""
        # Recursion protection
        if self._recursion_depth >= self._max_recursion_depth:
            # Silently drop the event to prevent infinite recursion
            return False

        self._recursion_depth += 1
        try:
            return self._process_event(event)
        finally:
            self._recursion_depth -= 1

    def _process_event(self, event: BaseEvent) -> bool:
        """Process the event with recursion protection."""
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
            isinstance(event, ExperimentFinishedEarlyEvent)
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

        # Track event history in debug mode
        if self.track_event_history:
            self._track_event_in_history(event, event_type)

        # Dedup check (LoggerObserver.on_event bypasses ITypedObserver.on_event)
        if hasattr(event, "id") and event.id:
            if event.id in self.processed_events_uuids:
                return True
            self.processed_events_uuids.add(event.id)

        # Dispatch to typed handler if one exists on this class.
        # Typed handlers provide specialized formatting (emoji, ERROR level).
        typed_handler = self._type_handlers.get(type(event))
        if typed_handler is not None:
            try:
                typed_handler(event)
            except Exception as exc:
                self.logger.error("Typed handler error: %s", exc)
            return True

        # Try name-based dispatch for non-subclass events
        handler_name = _handler_name_for(event.entity_type, event.name)
        if handler_name in self._logger_typed_handlers:
            try:
                getattr(self, handler_name)(event)
            except Exception as exc:
                self.logger.error("Named handler '%s' error: %s", handler_name, exc)
            return True

        # Generic path: format and log via EventSummarizer
        self._log_event(event)
        return True

    def _should_exclude_event(self, event_type: str) -> bool:
        """Check if an event should be excluded from logging."""
        return any(
            event_type.startswith(excluded) for excluded in self.excluded_event_types
        )

    def _apply_custom_filters(self, event_type: str, event: BaseEvent) -> bool:
        """Apply custom filters for the event type."""
        if event_type in self.event_filters:
            return self.event_filters[event_type](event)
        return True

    def _update_statistics(self, event_type: str, event: BaseEvent):
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

    def _track_event_correlation(self, event: BaseEvent):
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

    def _is_progress_active(self) -> bool:
        """Check if a Click progress bar is currently active."""
        if not CLICK_AVAILABLE:
            return False

        try:
            # For Click progress bars, we check if progress configuration is enabled
            # This is a simpler check since Click progress bars don't maintain global state like tqdm
            # We can check if the global config indicates progress bars are enabled
            if hasattr(self, "config") and self.config:
                return getattr(self.config, "progress", {}).get(
                    "enable_progress_bar", False
                )

            # Default to False if we can't determine progress state
            return False
        except (AttributeError, TypeError, ImportError):
            return False

    def _should_use_progress_coordination(self, event: BaseEvent) -> bool:
        """Determine if we should use progress coordination for this event."""
        if not self._is_progress_active():
            return False

        # Use coordinated logging for all events when progress bars are active to prevent interleaving
        # This ensures coordinated output between progress bars and log messages
        return True

    def _log_event(self, event: BaseEvent):
        """Format and log the event with enhanced formatting using EventSummarizer."""
        from panther.core.events.event_summarizer import (
            EventImportance,
            EventSummarizer,
        )

        event_type = self._get_event_type_safely(event)
        event_id = str(getattr(event, "id", "")) if self.include_event_id else None
        timestamp = getattr(event, "timestamp", datetime.now()).strftime("%H:%M:%S.%f")[
            :-3
        ]

        # Get event data
        event_data = getattr(event, "data", {}) if hasattr(event, "data") else {}

        # Use EventSummarizer to process the event
        event_summary = EventSummarizer.summarize_event(event_type, event_data)

        # Check importance threshold (configurable)
        importance_threshold = getattr(
            self, "importance_threshold", EventImportance.MEDIUM
        )
        if not EventSummarizer.should_log_event(event_type, importance_threshold):
            return

        # Determine log level based on event importance
        log_level = self._get_log_level_from_importance(event_summary.importance)

        if self.structured_output:
            self._log_structured_event(event, event_type, event_summary)
        else:
            # Build a clean, standardized log message
            severity = get_severity_indicator(event_type)
            msg = f"{severity} [{event_type}] {event_summary.summary}"

            if event_id:
                msg += f" ({event_id})"

            # Add details for important events
            if (
                event_summary.importance.value >= EventImportance.HIGH.value
                and event_summary.details
            ):
                details_str = ", ".join(
                    f"{k}={v}"
                    for k, v in event_summary.details.items()
                    if v is not None
                )
                if details_str:
                    msg += f" | {details_str}"

            # Log at appropriate level
            self.logger.log(log_level, msg)

            # Log full event data at TRACE level
            if hasattr(self.logger, "trace") and self.logger.isEnabledFor(
                5
            ):  # TRACE = 5
                self.logger.trace(f"Full event data for {event_type}: {event_data}")

    def _get_log_level_from_importance(self, importance):
        """Convert EventImportance to logging level."""
        from panther.core.events.event_summarizer import EventImportance

        mapping = {
            EventImportance.LOW: logging.DEBUG,
            EventImportance.MEDIUM: logging.INFO,
            EventImportance.HIGH: logging.WARNING,
            EventImportance.CRITICAL: logging.ERROR,
        }
        return mapping.get(importance, logging.INFO)

    def _get_event_priority(self, event_type: str, event: BaseEvent) -> str:
        """Determine the priority of an event."""
        # Check for explicit priority in event data
        event_data = getattr(event, "data", {})
        if "priority" in event_data:
            return event_data["priority"]

        # Check priority boost configuration
        for boost_type, boost_level in self.priority_boost.items():
            if event_type.startswith(boost_type):
                return ["debug", "info", "low", "medium", "high", "critical"][
                    min(boost_level, 5)
                ]

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

    def _log_structured_event(self, event: BaseEvent, event_type: str, event_summary):
        """Log event in structured JSON format with smart summarization."""
        import json

        structured_data = {
            "event_type": event_type,
            "importance": event_summary.importance.name,
            "summary": event_summary.summary,
            "timestamp": getattr(event, "timestamp", datetime.now()).isoformat(),
            "event_id": str(getattr(event, "id", "")),
            "details": event_summary.details,
        }

        self.logger.info(json.dumps(structured_data, default=str))

    def _log_docker_build_event_with_click(
        self, event: BaseEvent, msg: str, log_level: int
    ):
        """Log Docker build events using coordinated logging to avoid progress bar interference."""
        if not CLICK_AVAILABLE:
            # Fallback to regular logging if click is not available
            self.logger.log(log_level, msg)
            return

        # Create user-friendly messages for Docker build events
        event_data = getattr(event, "data", {})

        if isinstance(event, DockerBuildStartedEvent):
            service_name = event_data.get("service_name", "Unknown")
            image_name = event_data.get("image_name", "Unknown")
            dockerfile_path = event_data.get("dockerfile_path", "Unknown")

            # Show a concise, informative message
            tqdm_msg = f"🐳 Building Docker image: {service_name} ({image_name})"
            if self.debug_mode:
                tqdm_msg += f" from {dockerfile_path}"

            self.logger.info(tqdm_msg)

        elif isinstance(event, DockerBuildCompletedEvent):
            service_name = event_data.get("service_name", "Unknown")
            image_name = event_data.get("image_name", "Unknown")
            success = event_data.get("success", False)
            build_duration = event_data.get("build_duration", 0)

            if success:
                tqdm_msg = f"✅ Docker build completed: {service_name} ({image_name})"
                if build_duration and build_duration > 0:
                    tqdm_msg += f" in {build_duration:.1f}s"
            else:
                error_message = event_data.get("error_message", "Unknown error")
                tqdm_msg = f"❌ Docker build failed: {service_name} ({image_name}) - {error_message}"

            self.logger.info(tqdm_msg)

        elif isinstance(event, DockerBuildFailedEvent):
            service_name = event_data.get("service_name", "Unknown")
            error_message = event_data.get("error_message", "Unknown error")
            build_duration = event_data.get("build_duration", 0)

            tqdm_msg = f"❌ Docker build failed: {service_name} - {error_message}"
            if build_duration and build_duration > 0:
                tqdm_msg += f" after {build_duration:.1f}s"

            self.logger.info(tqdm_msg)

        # Still log to the regular logger for file output and detailed analysis
        self.logger.log(log_level, msg)

    def _get_event_type_safely(self, event: BaseEvent) -> str:
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

    def get_statistics(self) -> Dict[str, Any]:
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

    def add_event_filter(
        self, event_type: str, filter_func: Callable[[BaseEvent], bool]
    ):
        """Add a custom filter for a specific event type."""
        self.event_filters[event_type] = filter_func

    def remove_event_filter(self, event_type: str):
        """Remove a custom filter for a specific event type."""
        self.event_filters.pop(event_type, None)

    def set_priority_boost(self, event_type_prefix: str, boost_level: int):
        """Set priority boost for events matching a type prefix."""
        self.priority_boost[event_type_prefix] = boost_level

    # Override specific typed event handlers for important events

    def on_experiment_failed(self, event: BaseEvent) -> bool:
        """Handle experiment failed event with special attention."""
        self.logger.error(
            "🔴 EXPERIMENT FAILED: %s - %s",
            event.entity_id,
            getattr(event, "data", {}).get("failure_reason", "Unknown reason"),
        )
        return True

    def on_test_failed(self, event: TestFailedEvent) -> bool:
        """Handle test failed event with details."""
        self.logger.error(
            "❌ TEST FAILED: %s - %s",
            getattr(event, "test_id", getattr(event, "entity_id", "unknown")),
            getattr(event, "failure_reason", None)
            or getattr(event, "data", {}).get("error_message", "Unknown reason"),
        )
        return True

    def on_service_error(self, event: BaseEvent) -> bool:
        """Handle service error event with emphasis."""
        self.logger.error(
            "⚠️  SERVICE ERROR: %s - %s",
            event.entity_id,
            getattr(event, "data", {}).get("error_message", "Unknown error"),
        )
        return True

    def on_environment_error(self, event: BaseEvent) -> bool:
        """Handle environment error event."""
        self.logger.error(
            "🔥 ENVIRONMENT ERROR: %s - %s",
            event.entity_id,
            getattr(event, "data", {}).get("error_message", "Unknown error"),
        )
        return True

    def on_docker_build_started(self, event: DockerBuildStartedEvent) -> bool:
        """Handle Docker build started event with special tqdm support."""
        # Process the event normally - tqdm.write will be used automatically if tqdm is active
        self._log_event(event)
        return True

    def on_docker_build_completed(self, event: DockerBuildCompletedEvent) -> bool:
        """Handle Docker build completed event with special tqdm support."""
        # Process the event normally - tqdm.write will be used automatically if tqdm is active
        self._log_event(event)
        return True

    def on_docker_build_failed(self, event: DockerBuildFailedEvent) -> bool:
        """Handle Docker build failed event with special tqdm support."""
        # Process the event normally - tqdm.write will be used automatically if tqdm is active
        self._log_event(event)
        return True

    def _track_event_in_history(self, event: BaseEvent, event_type: str):
        """Track event in history for debug mode."""
        if not hasattr(self, "event_history"):
            self.event_history = []

        event_entry = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "event_id": str(getattr(event, "event_id", "")),
            "event_data": getattr(event, "data", getattr(event, "entity_metadata", {})),
        }

        self.event_history.append(event_entry)

        # Maintain max history size
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)

    def get_event_history(
        self, event_type: Optional[str] = None, limit: Optional[int] = None
    ) -> List[dict]:
        """Get history of events, optionally filtered by type.

        This method provides the same functionality as DebugObserver.

        Args:
            event_type: Optional event type to filter by
            limit: Optional maximum number of events to return

        Returns:
            List of event entries
        """
        if not hasattr(self, "event_history"):
            return []

        if event_type:
            filtered = [e for e in self.event_history if e["event_type"] == event_type]
            return filtered[-limit:] if limit else filtered

        return self.event_history[-limit:] if limit else self.event_history

    def analyze_event_flow(self) -> List[dict]:
        """Analyze event flow for anomalies or bottlenecks.

        This method provides the same functionality as DebugObserver.

        Returns:
            List of analysis results
        """
        if not hasattr(self, "event_history") or len(self.event_history) < 2:
            return []

        analysis = []
        prev_event = self.event_history[0]

        for event in self.event_history[1:]:
            time_diff = (event["timestamp"] - prev_event["timestamp"]).total_seconds()

            # Identify slow transitions (more than 5 seconds)
            if time_diff > 5:
                analysis.append(
                    {
                        "type": "slow_transition",
                        "from_event": prev_event["event_type"],
                        "to_event": event["event_type"],
                        "duration_seconds": time_diff,
                    }
                )

            prev_event = event

        return analysis

    def export_logs(self, output_path: str, format: str = "json") -> bool:
        """Export collected event data to a file.

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
