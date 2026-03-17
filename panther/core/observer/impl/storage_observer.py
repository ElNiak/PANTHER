"""Storage Observer Module."""

from typing import Any, Dict, List, Optional

"""
Storage Observer Module

This module provides a storage observer that leverages the ResultsManager
for comprehensive data persistence and retrieval capabilities.
"""

import json
import shutil
import time
from datetime import datetime
from pathlib import Path

from panther.core.events.base.event_base import BaseEvent
from panther.core.events.experiment.events import ExperimentFinishedEarlyEvent
from panther.core.events.metrics.events import MetricCollectedEvent, MetricsSummaryEvent
from panther.core.events.test.events import (
    EnhancedResultEvent,
    TestCompletedEvent,
    TestFailedEvent,
    TestResultEvent,
)
from panther.core.exceptions.fast_fail import ResourceExhaustionException
from panther.core.observer.base.typed_observer_interface import ITypedObserver
from panther.core.observer.management.results_manager import ResultsManager


class StorageObserver(ITypedObserver):
    """Storage observer that provides comprehensive data persistence using ResultsManager.

    Implements singleton pattern per storage path to prevent duplicate event logging.

    This observer handles:
    - Event storage and retrieval
    - Test result aggregation
    - Metrics persistence
    - Data export and import
    - Historical data management

    Note:
        As of Batch 2, all events are also written to ``structured.jsonl``
        by :class:`EventStreamRecorder`. The separate per-category JSONL files
        (events.jsonl, error_events.jsonl, performance_metrics.jsonl) written
        by this observer are retained for backward-compatible query/export but
        may be removed in a future refactoring once query methods are migrated
        to read from ``structured.jsonl`` with filtering.
    """

    # Class-level registry to maintain one instance per storage path
    _instances = {}
    _instance_lock = None

    def __new__(cls, storage_path: Optional[str] = None, **kwargs):
        """Implement singleton pattern per storage path.

        Returns existing instance if one exists for the same storage path,
        otherwise creates new instance.
        """
        # Initialize lock if not exists
        if cls._instance_lock is None:
            import threading

            cls._instance_lock = threading.Lock()

        # Normalize storage path for consistent keys
        if storage_path is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            storage_path = f"outputs/{timestamp}/storage"

        storage_key = str(Path(storage_path).resolve())

        with cls._instance_lock:
            # Return existing instance if it exists
            if storage_key in cls._instances:
                existing_instance = cls._instances[storage_key]
                # Update logger info to show reuse
                if hasattr(existing_instance, "logger"):
                    existing_instance.logger.debug(
                        f"Reusing existing StorageObserver instance for path: {storage_path}"
                    )
                return existing_instance

            # Create new instance
            instance = super().__new__(cls)
            cls._instances[storage_key] = instance
            return instance

    def __init__(
        self,
        storage_path: Optional[str] = None,
        enable_compression: bool = True,
        max_storage_size: Optional[int] = None,
        auto_backup: bool = True,
        backup_interval: int = 3600,  # 1 hour
        retention_days: int = 30,
        event_type_filters: Optional[List[str]] = None,
        batch_size: int = 100,
        log_level: str = "INFO",
    ):
        """Initialize the storage observer.

        Args:
            storage_path: Base path for storage (defaults to outputs/<timestamp>)
            enable_compression: Whether to compress stored data
            max_storage_size: Maximum storage size in bytes
            auto_backup: Whether to automatically backup data
            backup_interval: Backup interval in seconds
            retention_days: Number of days to retain data
            event_type_filters: List of event types to store (None for all)
            batch_size: Number of events to batch before writing
            log_level: Logging level for the observer
        """
        # Skip initialization if this instance is already initialized
        if hasattr(self, "_initialized") and self._initialized:
            return

        # Initialize storage path
        if storage_path is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            storage_path = f"outputs/{timestamp}/storage"

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.log_level = log_level

        super().__init__()

        # Create unique logger name based on storage path to prevent cross-contamination
        storage_key = str(self.storage_path.resolve())
        unique_logger_name = f"StorageObserver_{hash(storage_key) & 0x7FFFFFFF}"

        self.logger = self._setup_logging(
            logger_name=unique_logger_name,
            log_level=self.log_level,
            enable_colors=True,
            output_file=self.storage_path / "storage_observer.log",
            structured_output=False,
        )

        # Initialize ResultsManager for core storage functionality
        self.results_manager = ResultsManager(output_dir=str(self.storage_path))

        # Configuration
        self.retention_days = retention_days
        self.event_type_filters = set(event_type_filters or [])
        self.batch_size = batch_size

        # Storage tracking
        self.pending_events: List[Dict[str, Any]] = []
        self.storage_stats = {
            "events_stored": 0,
            "events_filtered": 0,
            "storage_size": 0,
            "last_backup": None,
            "last_cleanup": None,
        }

        # Resource monitoring
        self.disk_check_interval = 30  # seconds
        self.last_disk_check = time.time()
        self.disk_warning_threshold = 1.0  # GB
        self.disk_critical_threshold = 0.5  # GB
        self.resource_monitoring_enabled = True

        # Event categorization
        self.event_categories = {
            "test_results": [],
            "system_events": [],
            "performance_metrics": [],
            "error_events": [],
            "user_actions": [],
            "network_events": [],
        }

        self.logger.info(
            f"StorageObserver initialized with storage path: {self.storage_path}"
        )

        # Mark instance as initialized to prevent re-initialization
        self._initialized = True

    def on_event(self, event: BaseEvent) -> bool:
        """Handle generic events and route to typed handlers.

        This method handles special cases like the experiment finished early check,
        then delegates to the parent class for typed event routing.
        """
        # Check disk space periodically when handling events
        try:
            self._check_disk_space()
        except ResourceExhaustionException:
            # Let the exception propagate - fast-fail will handle it
            raise

        # Special handling for experiment finished early check action
        if isinstance(event, ExperimentFinishedEarlyEvent):
            event_data = getattr(event, "data", {})
            if event_data.get("action") == "check":
                self.logger.debug(
                    "Check request for ExperimentFinishedEarlyEvent - "
                    "returning False as StorageObserver doesn't track this state"
                )
                return False

        # Call parent to handle typed event routing
        return super().on_event(event)

    # Typed event handlers

    def on_test_execution_started(self, event: BaseEvent) -> bool:
        """Handle test started event."""
        self._store_test_event(event, "test.started")
        return True

    def on_test_completed(self, event: TestCompletedEvent) -> bool:
        """Handle test completed event."""
        # Create a TestResultEvent for ResultsManager
        test_result_event = TestResultEvent(
            name="test.completed",
            test_name=event.test_name,
            result="passed",
            data={
                "test_id": event.test_id,
                "duration": getattr(event, "duration", None),
            },
            metadata={"original_event_id": str(getattr(event, "event_id", event.id))},
        )
        self.results_manager.on_event(test_result_event)
        self._store_test_event(event, "test.completed")
        # Flush after each test to ensure data is persisted
        try:
            self._flush_pending_events()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to flush events after test completed: %s", e)
        return True

    def on_test_failed(self, event: TestFailedEvent) -> bool:
        """Handle test failed event."""
        # Create a TestResultEvent for ResultsManager
        test_result_event = TestResultEvent(
            name="test.failed",
            test_name=getattr(
                event, "test_name", getattr(event, "entity_id", "unknown")
            ),
            result="failed",
            data={
                "test_id": getattr(
                    event, "test_id", getattr(event, "entity_id", "unknown")
                ),
                "failure_reason": getattr(event, "failure_reason", None)
                or getattr(event, "data", {}).get("error_message", "Unknown"),
            },
            metadata={"original_event_id": str(getattr(event, "event_id", event.id))},
        )
        self.results_manager.on_event(test_result_event)
        self._store_error_event(event, "test.failed")
        # Flush after each test failure to ensure error data is persisted
        try:
            self._flush_pending_events()
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to flush events after test failed: %s", e)
        return True

    def on_experiment_execution_started(self, event: BaseEvent) -> bool:
        """Handle experiment started event."""
        self._store_system_event(event, "experiment.started")
        return True

    def on_experiment_completed(self, event: BaseEvent) -> bool:
        """Handle experiment completed event."""
        self._store_system_event(event, "experiment.completed")
        # Flush all pending data when experiment completes
        self.flush_all()
        return True

    def on_experiment_failed(self, event: BaseEvent) -> bool:
        """Handle experiment failed event."""
        self._store_error_event(event, "experiment.failed")
        # Flush all pending data when experiment fails
        self.flush_all()
        return True

    def on_service_error(self, event: BaseEvent) -> bool:
        """Handle service error event."""
        self._store_error_event(event, "service.error")
        return True

    def on_environment_error(self, event: BaseEvent) -> bool:
        """Handle environment error event."""
        self._store_error_event(event, "environment.error")
        return True

    def on_metrics_summary(self, event: MetricsSummaryEvent) -> bool:
        """Handle metrics summary event."""
        self._store_performance_event(event, "metrics.summary")
        return True

    def on_metric_collected(self, event: MetricCollectedEvent) -> bool:
        """Handle custom metric collected event."""
        self._store_performance_event(event, "metric.collected")
        return True

    def on_unknown_event(self, event: BaseEvent) -> bool:
        """Handle unknown events."""
        event_type = self._get_event_type_safely(event)

        # Apply event type filters if configured
        if self.event_type_filters and not self._should_store_event(event_type):
            self.storage_stats["events_filtered"] += 1
            return True

        # Store as generic event
        self._categorize_and_store_event(event, event_type)

        # Handle batched storage
        if len(self.pending_events) >= self.batch_size:
            self._flush_pending_events()

        self.storage_stats["events_stored"] += 1
        return True

    def _should_store_event(self, event_type: str) -> bool:
        """Check if an event type should be stored."""
        if not self.event_type_filters:
            return True

        return any(
            event_type.startswith(filter_type)
            for filter_type in self.event_type_filters
        )

    def _categorize_and_store_event(self, event: BaseEvent, event_type: str):
        """Categorize an event and store it in the appropriate category."""
        # Convert event to storage format
        event_data = self._convert_event_to_dict(event, event_type)

        # Add to pending events
        self.pending_events.append(event_data)

        # Categorize for specialized handling
        category = self._determine_event_category(event_type)
        self.event_categories[category].append(event_data)

        # Handle special event types
        if event_type.startswith("test."):
            self._handle_test_event(event, event_type)
        elif event_type.startswith("performance."):
            self._handle_performance_event(event, event_type)
        elif "error" in event_type.lower() or "fail" in event_type.lower():
            self._handle_error_event(event, event_type)

    def _convert_event_to_dict(
        self, event: BaseEvent, event_type: str
    ) -> Dict[str, Any]:
        """Convert an event to a dictionary for storage."""
        return {
            "id": str(getattr(event, "id", "")),
            "type": event_type,
            "timestamp": getattr(event, "timestamp", datetime.now()).isoformat(),
            "data": getattr(event, "data", getattr(event, "entity_metadata", {})),
            "metadata": {
                "class": event.__class__.__name__,
                "storage_timestamp": datetime.now().isoformat(),
            },
        }

    def _determine_event_category(self, event_type: str) -> str:
        """Determine the storage category for an event type."""
        if event_type.startswith("test."):
            return "test_results"
        elif event_type.startswith("performance."):
            return "performance_metrics"
        elif "error" in event_type.lower() or "fail" in event_type.lower():
            return "error_events"
        elif event_type.startswith("user."):
            return "user_actions"
        elif event_type.startswith("network."):
            return "network_events"
        else:
            return "system_events"

    def _store_test_event(self, event: BaseEvent, event_type: str):
        """Store test-related event."""
        event_data = {
            "event_id": str(getattr(event, "event_id", event.id)),
            "event_type": event_type,
            "timestamp": event.timestamp.isoformat(),
            "test_id": getattr(event, "test_id", getattr(event, "entity_id", None)),
            "test_name": getattr(event, "test_name", None),
            "data": getattr(event, "data", getattr(event, "entity_metadata", {})),
        }
        self.pending_events.append(event_data)
        self.event_categories["test_results"].append(event_data)

    def _store_system_event(self, event: BaseEvent, event_type: str):
        """Store system-related event."""
        event_data = {
            "event_id": str(getattr(event, "event_id", event.id)),
            "event_type": event_type,
            "timestamp": event.timestamp.isoformat(),
            "data": getattr(event, "data", getattr(event, "entity_metadata", {})),
        }
        self.pending_events.append(event_data)
        self.event_categories["system_events"].append(event_data)

    def _store_error_event(self, event: BaseEvent, event_type: str):
        """Store error-related event."""
        # Extract error message from event data or direct attribute
        error_message = ""
        if hasattr(event, "data") and isinstance(event.data, dict):
            error_message = event.data.get("error_message", "")
        if not error_message:
            error_message = getattr(event, "error_message", "")

        event_data = {
            "event_id": str(getattr(event, "event_id", event.id)),
            "event_type": event_type,
            "timestamp": event.timestamp.isoformat(),
            "severity": self._determine_error_severity(event_type, {}),
            "error_message": error_message,
            "data": getattr(event, "data", getattr(event, "entity_metadata", {})),
        }

        # Write to error log immediately
        error_file = self.storage_path / "error_events.jsonl"
        self._append_to_file(error_file, event_data)

        self.pending_events.append(event_data)
        self.event_categories["error_events"].append(event_data)

    def _store_performance_event(self, event: BaseEvent, event_type: str):
        """Store performance-related event."""
        event_data = {
            "event_id": str(getattr(event, "event_id", event.id)),
            "event_type": event_type,
            "timestamp": event.timestamp.isoformat(),
            "metrics": getattr(event, "metrics", {}),
            "data": getattr(event, "data", getattr(event, "entity_metadata", {})),
        }

        # Write to performance log
        perf_file = self.storage_path / "performance_metrics.jsonl"
        self._append_to_file(perf_file, event_data)

        self.pending_events.append(event_data)
        self.event_categories["performance_metrics"].append(event_data)

    def _handle_test_event(self, event: BaseEvent, event_type: str):
        """Handle test-specific events using ResultsManager."""
        event_data = getattr(event, "data", {})

        # Create a TestResultEvent for the ResultsManager
        if "test_name" in event_data and "result" in event_data:
            test_result_event = TestResultEvent(
                name=event_type,
                test_name=event_data["test_name"],
                result=event_data["result"],
                data=event_data,
                metadata={"original_event_id": str(getattr(event, "id", ""))},
            )

            # Store using ResultsManager
            self.results_manager.on_event(test_result_event)

    def _handle_performance_event(self, event: BaseEvent, event_type: str):
        """Handle performance metrics events."""
        event_data = getattr(event, "data", {})

        # Store performance metrics in specialized format
        perf_data = {
            "event_id": str(getattr(event, "id", "")),
            "metric_type": event_type,
            "timestamp": getattr(event, "timestamp", datetime.now()).isoformat(),
            "values": event_data,
        }

        perf_file = self.storage_path / "performance_metrics.jsonl"
        self._append_to_file(perf_file, perf_data)

    def _handle_error_event(self, event: BaseEvent, event_type: str):
        """Handle error events with special attention."""
        event_data = getattr(event, "data", {})

        # Store error events in dedicated error log
        error_data = {
            "event_id": str(getattr(event, "id", "")),
            "error_type": event_type,
            "timestamp": getattr(event, "timestamp", datetime.now()).isoformat(),
            "severity": self._determine_error_severity(event_type, event_data),
            "details": event_data,
        }

        error_file = self.storage_path / "error_events.jsonl"
        self._append_to_file(error_file, error_data)

    def _determine_error_severity(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> str:
        """Determine the severity level of an error event."""
        if "critical" in event_type.lower():
            return "critical"
        elif "error" in event_type.lower():
            return "error"
        elif "warning" in event_type.lower():
            return "warning"
        elif "fail" in event_type.lower():
            return "error"
        else:
            return "info"

    def _flush_pending_events(self):
        """Flush pending events to storage."""
        if not self.pending_events:
            return

        # Store events in main event log
        events_file = self.storage_path / "events.jsonl"

        failed = []
        for event_data in self.pending_events:
            if not self._append_to_file(events_file, event_data):
                failed.append(event_data)

        # Keep only events that failed to write
        self.pending_events = failed

        # Update storage size
        self._update_storage_size()

    def _append_to_file(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """Append data to a JSONL file. Returns True on success."""
        try:
            with open(file_path, "a") as f:
                f.write(json.dumps(data, default=str) + "\n")
            return True
        except Exception as e:
            self.logger.error("Failed to write to %s: %s", file_path, e)
            return False

    def _update_storage_size(self):
        """Update storage size statistics."""
        try:
            total_size = sum(
                f.stat().st_size for f in self.storage_path.rglob("*") if f.is_file()
            )
            self.storage_stats["storage_size"] = total_size
        except Exception as e:
            self.logger.error("Failed to calculate storage size: %s", e)

    def is_interested(self, event_type: str) -> bool:
        """Check if the observer is interested in an event type."""
        if not event_type:
            return True
        return self._should_store_event(event_type)

    def get_priority(self) -> int:
        """Get the priority for this observer."""
        return 50  # Medium priority - storage should happen after processing

    def flush_all(self):
        """Flush all pending data to storage."""
        self._flush_pending_events()

        # Flush category-specific data
        for category, events in self.event_categories.items():
            if events:
                category_file = self.storage_path / f"{category}.jsonl"
                for event_data in events:
                    self._append_to_file(category_file, event_data)
                events.clear()

        # Trigger ResultsManager export
        self.results_manager.export_results()

        self.logger.info("All storage data flushed")

    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics and information."""
        self._update_storage_size()

        return {
            **self.storage_stats,
            "storage_path": str(self.storage_path),
            "pending_events": len(self.pending_events),
            "category_counts": {k: len(v) for k, v in self.event_categories.items()},
            "results_manager_stats": self.results_manager.get_statistics(),
        }

    def cleanup_old_data(self):
        """Clean up old data based on retention policy."""
        try:
            cutoff_date = datetime.now().timestamp() - (self.retention_days * 24 * 3600)

            for file_path in self.storage_path.rglob("*"):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_date:
                    file_path.unlink()
                    self.logger.info("Deleted old file: %s", file_path)

            self.storage_stats["last_cleanup"] = datetime.now().isoformat()

        except Exception as e:
            self.logger.error("Failed to cleanup old data: %s", e)

    def backup_data(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of all stored data."""
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.storage_path}_backup_{timestamp}"

            # Flush all pending data first
            self.flush_all()

            # Create backup using ResultsManager's export functionality
            backup_success = self.results_manager.export_results(
                export_format="backup", custom_path=backup_path
            )

            if backup_success:
                self.storage_stats["last_backup"] = datetime.now().isoformat()
                self.logger.info("Data backup created at: %s", backup_path)

            return backup_success

        except Exception as e:
            self.logger.error("Failed to create backup: %s", e)
            return False

    def query_events(
        self,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Query stored events with filters.

        Args:
            event_type: Filter by event type (supports prefix matching)
            start_time: Filter events after this time
            end_time: Filter events before this time
            limit: Maximum number of events to return

        Returns:
            List of matching events
        """
        try:
            events = []
            events_file = self.storage_path / "events.jsonl"

            if not events_file.exists():
                return events

            with open(events_file) as f:
                for line in f:
                    try:
                        event_data = json.loads(line.strip())

                        # Apply filters
                        if event_type and not event_data.get("type", "").startswith(
                            event_type
                        ):
                            continue

                        if start_time or end_time:
                            event_time = datetime.fromisoformat(
                                event_data.get("timestamp", "")
                            )
                            if start_time and event_time < start_time:
                                continue
                            if end_time and event_time > end_time:
                                continue

                        events.append(event_data)

                        # Apply limit
                        if limit and len(events) >= limit:
                            break

                    except (json.JSONDecodeError, ValueError) as e:
                        self.logger.warning("Failed to parse event line: %s", e)
                        continue

            return events

        except Exception as e:
            self.logger.error("Failed to query events: %s", e)
            return []

    def export_data(
        self,
        export_path: str,
        export_format: str = "json",
        include_categories: Optional[List[str]] = None,
    ) -> bool:
        """Export stored data in various formats.

        Args:
            export_path: Path to export the data
            export_format: Export format ('json', 'csv', 'xml')
            include_categories: Categories to include in export

        Returns:
            bool: True if export successful, False otherwise
        """
        try:
            # Flush pending data first
            self.flush_all()

            if export_format.lower() == "json":
                return self._export_json(export_path, include_categories)
            elif export_format.lower() == "csv":
                return self._export_csv(export_path, include_categories)
            elif export_format.lower() == "xml":
                return self._export_xml(export_path, include_categories)
            else:
                raise ValueError(f"Unsupported export format: {export_format}")

        except Exception as e:
            self.logger.error("Failed to export data: %s", e)
            return False

    def _export_json(
        self, export_path: str, include_categories: Optional[List[str]]
    ) -> bool:
        """Export data in JSON format."""
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "storage_path": str(self.storage_path),
                "statistics": self.get_storage_statistics(),
            },
            "events": {},
        }

        # Include all categories if none specified
        categories = include_categories or list(self.event_categories.keys())

        for category in categories:
            category_file = self.storage_path / f"{category}.jsonl"
            if category_file.exists():
                category_events = []
                with open(category_file) as f:
                    for line in f:
                        try:
                            category_events.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
                export_data["events"][category] = category_events

        with open(export_path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

        return True

    def _export_csv(
        self, export_path: str, include_categories: Optional[List[str]]
    ) -> bool:
        """Export data in CSV format."""
        import csv

        with open(export_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["category", "event_id", "event_type", "timestamp", "data"])

            categories = include_categories or list(self.event_categories.keys())

            for category in categories:
                category_file = self.storage_path / f"{category}.jsonl"
                if category_file.exists():
                    with open(category_file) as f:
                        for line in f:
                            try:
                                event_data = json.loads(line.strip())
                                writer.writerow(
                                    [
                                        category,
                                        event_data.get("id", ""),
                                        event_data.get("type", ""),
                                        event_data.get("timestamp", ""),
                                        json.dumps(event_data.get("data", {})),
                                    ]
                                )
                            except json.JSONDecodeError:
                                continue

        return True

    def _export_xml(
        self, export_path: str, include_categories: Optional[List[str]]
    ) -> bool:
        """Export data in XML format."""
        try:
            import xml.etree.ElementTree as ET

            root = ET.Element("storage_export")

            # Add metadata
            metadata = ET.SubElement(root, "metadata")
            ET.SubElement(metadata, "export_timestamp").text = (
                datetime.now().isoformat()
            )
            ET.SubElement(metadata, "storage_path").text = str(self.storage_path)

            # Add events
            events_elem = ET.SubElement(root, "events")
            categories = include_categories or list(self.event_categories.keys())

            for category in categories:
                category_elem = ET.SubElement(events_elem, "category", name=category)
                category_file = self.storage_path / f"{category}.jsonl"

                if category_file.exists():
                    with open(category_file) as f:
                        for line in f:
                            try:
                                event_data = json.loads(line.strip())
                                event_elem = ET.SubElement(category_elem, "event")

                                for key, value in event_data.items():
                                    if key != "data":
                                        ET.SubElement(event_elem, key).text = str(value)
                                    else:
                                        data_elem = ET.SubElement(event_elem, "data")
                                        data_elem.text = json.dumps(value)

                            except json.JSONDecodeError:
                                continue

            tree = ET.ElementTree(root)
            tree.write(export_path, encoding="utf-8", xml_declaration=True)
            return True

        except ImportError:
            self.logger.error("XML export requires xml.etree.ElementTree")
            return False
        except Exception as e:
            self.logger.error("XML export failed: %s", e)
            return False

    def _check_disk_space(self):
        """Periodic disk space check with fast-fail on critical thresholds."""
        if not self.resource_monitoring_enabled:
            return

        current_time = time.time()
        if current_time - self.last_disk_check < self.disk_check_interval:
            return

        stat = shutil.disk_usage(str(self.storage_path))
        available_gb = stat.free / (1024**3)

        self.logger.debug("Disk space check: %.2fGB available", available_gb)

        if available_gb < self.disk_critical_threshold:
            raise ResourceExhaustionException(
                f"Critical: Only {available_gb:.2f}GB disk space remaining",
                "disk_space",
                available_gb,
                self.disk_critical_threshold,
            )
        elif available_gb < self.disk_warning_threshold:
            self.logger.warning(
                f"Low disk space warning: {available_gb:.2f}GB remaining"
            )

        self.last_disk_check = current_time

    @classmethod
    def clear_instances(cls):
        """Clear all singleton instances. Useful for testing and cleanup."""
        if cls._instance_lock:
            with cls._instance_lock:
                cls._instances.clear()
        else:
            cls._instances.clear()

    @classmethod
    def get_instance_count(cls):
        """Get the number of active instances. Useful for monitoring."""
        return len(cls._instances)
