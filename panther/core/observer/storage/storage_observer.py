"""
Storage Observer Module

This module provides a storage observer that leverages the ResultsManager
for comprehensive data persistence and retrieval capabilities.
"""

import json
from datetime import datetime
from typing import Any
from pathlib import Path

from panther.core.observer.core.observer_interface import IObserver
from panther.core.observer.core.core_events import Event
from panther.core.observer.storage.store_events import TestResultEvent
from panther.core.observer.storage.results_manager import ResultsManager


class StorageObserver(IObserver):
    """
    Storage observer that provides comprehensive data persistence using ResultsManager.

    This observer handles:
    - Event storage and retrieval
    - Test result aggregation
    - Metrics persistence
    - Data export and import
    - Historical data management
    """

    def __init__(
        self,
        storage_path: str | None = None,
        enable_compression: bool = True,
        max_storage_size: int | None = None,
        auto_backup: bool = True,
        backup_interval: int = 3600,  # 1 hour
        retention_days: int = 30,
        event_type_filters: list[str] | None = None,
        batch_size: int = 100,
        async_storage: bool = False,
        log_level: str = "INFO",
    ):
        """
        Initialize the storage observer.

        Args:
            storage_path: Base path for storage (defaults to outputs/<timestamp>)
            enable_compression: Whether to compress stored data
            max_storage_size: Maximum storage size in bytes
            auto_backup: Whether to automatically backup data
            backup_interval: Backup interval in seconds
            retention_days: Number of days to retain data
            event_type_filters: List of event types to store (None for all)
            batch_size: Number of events to batch before writing
            async_storage: Whether to use asynchronous storage
        """
        # Initialize storage path
        if storage_path is None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            storage_path = f"outputs/{timestamp}/storage"

        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.log_level = log_level

        self.logger = self._setup_logging(
            logger_name="StorageObserver",
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
        self.async_storage = async_storage

        # Storage tracking
        self.pending_events: list[dict[str, Any]] = []
        self.storage_stats = {
            "events_stored": 0,
            "events_filtered": 0,
            "storage_size": 0,
            "last_backup": None,
            "last_cleanup": None,
        }

        # Event categorization
        self.event_categories = {
            "test_results": [],
            "system_events": [],
            "performance_metrics": [],
            "error_events": [],
            "user_actions": [],
            "network_events": [],
        }

        self.logger.info(f"StorageObserver initialized with storage path: {self.storage_path}")

    def on_event(self, event: Event) -> bool:
        """
        Handle an event by storing it appropriately.

        Args:
            event: The event to store

        Returns:
            bool: True if storage was successful, False otherwise.
                 For "check" action events, returns True only if the event has actually occurred.
        """
        # super().processed_events_uuids.append(str(event.id))
        try:
            event_type = self._get_event_type_safely(event)
            event_data = getattr(event, "data", {})

            # Check if this is a query about whether an event has occurred
            if event_data.get("action") == "check":
                # For experiment.finished_early events, we should return False
                # as the storage observer doesn't track these state changes
                if event_type == "experiment.finished_early" or event_type.endswith(
                    ".finished_early"
                ):
                    self.logger.debug(
                        f"Check request for '{event_type}' event - returning False as StorageObserver doesn't track this state"
                    )
                    return False

                # For other event types, we could implement checks here
                # For now, return False for all check actions
                return False

            # Apply event type filters if configured
            if self.event_type_filters and not self._should_store_event(event_type):
                self.storage_stats["events_filtered"] += 1
                return True

            # Categorize and store the event
            self._categorize_and_store_event(event, event_type)

            # Handle batched storage
            if len(self.pending_events) >= self.batch_size:
                self._flush_pending_events()

            self.storage_stats["events_stored"] += 1
            return True

        except Exception as e:
            self.logger.error(f"Failed to store event: {e}")
            return False

    def _should_store_event(self, event_type: str) -> bool:
        """Check if an event type should be stored."""
        if not self.event_type_filters:
            return True

        return any(event_type.startswith(filter_type) for filter_type in self.event_type_filters)

    def _categorize_and_store_event(self, event: Event, event_type: str):
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

    def _convert_event_to_dict(self, event: Event, event_type: str) -> dict[str, Any]:
        """Convert an event to a dictionary for storage."""
        return {
            "id": str(getattr(event, "id", "")),
            "type": event_type,
            "timestamp": getattr(event, "timestamp", datetime.now()).isoformat(),
            "data": getattr(event, "data", {}),
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

    def _handle_test_event(self, event: Event, event_type: str):
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

    def _handle_performance_event(self, event: Event, event_type: str):
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

    def _handle_error_event(self, event: Event, event_type: str):
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

    def _determine_error_severity(self, event_type: str, event_data: dict[str, Any]) -> str:
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

        for event_data in self.pending_events:
            self._append_to_file(events_file, event_data)

        # Clear pending events
        self.pending_events.clear()

        # Update storage size
        self._update_storage_size()

    def _append_to_file(self, file_path: Path, data: dict[str, Any]):
        """Append data to a JSONL file."""
        try:
            with open(file_path, "a") as f:
                f.write(json.dumps(data, default=str) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write to {file_path}: {e}")

    def _update_storage_size(self):
        """Update storage size statistics."""
        try:
            total_size = sum(f.stat().st_size for f in self.storage_path.rglob("*") if f.is_file())
            self.storage_stats["storage_size"] = total_size
        except Exception as e:
            self.logger.error(f"Failed to calculate storage size: {e}")

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

    def get_storage_statistics(self) -> dict[str, Any]:
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
                    self.logger.info(f"Deleted old file: {file_path}")

            self.storage_stats["last_cleanup"] = datetime.now().isoformat()

        except Exception as e:
            self.logger.error(f"Failed to cleanup old data: {e}")

    def backup_data(self, backup_path: str | None = None) -> bool:
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
                self.logger.info(f"Data backup created at: {backup_path}")

            return backup_success

        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False

    def query_events(
        self,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query stored events with filters.

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
                        if event_type and not event_data.get("type", "").startswith(event_type):
                            continue

                        if start_time or end_time:
                            event_time = datetime.fromisoformat(event_data.get("timestamp", ""))
                            if start_time and event_time < start_time:
                                continue
                            if end_time and event_time > end_time:
                                continue

                        events.append(event_data)

                        # Apply limit
                        if limit and len(events) >= limit:
                            break

                    except (json.JSONDecodeError, ValueError) as e:
                        self.logger.warning(f"Failed to parse event line: {e}")
                        continue

            return events

        except Exception as e:
            self.logger.error(f"Failed to query events: {e}")
            return []

    def export_data(
        self,
        export_path: str,
        export_format: str = "json",
        include_categories: list[str] | None = None,
    ) -> bool:
        """
        Export stored data in various formats.

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
            self.logger.error(f"Failed to export data: {e}")
            return False

    def _export_json(self, export_path: str, include_categories: list[str] | None) -> bool:
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

    def _export_csv(self, export_path: str, include_categories: list[str] | None) -> bool:
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

    def _export_xml(self, export_path: str, include_categories: list[str] | None) -> bool:
        """Export data in XML format."""
        try:
            import xml.etree.ElementTree as ET

            root = ET.Element("storage_export")

            # Add metadata
            metadata = ET.SubElement(root, "metadata")
            ET.SubElement(metadata, "export_timestamp").text = datetime.now().isoformat()
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
            self.logger.error(f"XML export failed: {e}")
            return False
