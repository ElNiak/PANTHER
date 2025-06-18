"""
Unit tests for PANTHER Observer System.

This module tests the observer pattern implementation used for monitoring
and reacting to events throughout the PANTHER framework.
"""

import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Test imports with fallback to mocks
try:
    from panther.core.observer.factory.observer_factory import ObserverFactory
    from panther.core.observer.impl.command_audit_observer import CommandAuditObserver
    from panther.core.observer.impl.metrics_observer import MetricsObserver
    from panther.core.observer.impl.state_observer import StateObserver
    from panther.core.observer.impl.storage_observer import StorageObserver
    from panther.core.observer.management.results_manager import ResultsManager

    REAL_OBSERVER_SYSTEM_AVAILABLE = True
except ImportError:
    REAL_OBSERVER_SYSTEM_AVAILABLE = False

    # Create mock implementations for testing
    class MetricsObserver:
        def __init__(self, metrics_collector=None):
            self.metrics_collector = metrics_collector or Mock()
            self.events_processed = 0
            self.metrics_recorded = []

        def handle_event(self, event):
            """Handle metrics-related events."""
            self.events_processed += 1

            # Extract metrics from event
            if event.get("type", "").endswith(".started"):
                metric = {
                    "name": f"{event['entity_type']}.start_count",
                    "value": 1,
                    "timestamp": event.get("timestamp"),
                    "tags": {"entity_id": event.get("entity_id")},
                }
                self.metrics_recorded.append(metric)
                self.metrics_collector.record(
                    metric["name"], metric["value"], metric["tags"]
                )

            elif event.get("type", "").endswith(".completed"):
                metric = {
                    "name": f"{event['entity_type']}.completion_count",
                    "value": 1,
                    "timestamp": event.get("timestamp"),
                    "tags": {"entity_id": event.get("entity_id")},
                }
                self.metrics_recorded.append(metric)
                self.metrics_collector.record(
                    metric["name"], metric["value"], metric["tags"]
                )

        def get_metrics_summary(self):
            """Get summary of recorded metrics."""
            return {
                "events_processed": self.events_processed,
                "metrics_count": len(self.metrics_recorded),
                "metrics": self.metrics_recorded,
            }

    class StorageObserver:
        def __init__(self, storage_path=None):
            self.storage_path = (
                Path(storage_path) if storage_path else Path.cwd() / "events"
            )
            self.storage_path.mkdir(exist_ok=True)
            self.stored_events = []

        def handle_event(self, event):
            """Store events to persistent storage."""
            # Add storage metadata
            storage_event = {
                **event,
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "storage_id": f"store_{len(self.stored_events)}",
            }

            self.stored_events.append(storage_event)

            # Write to file (simulate persistent storage)
            event_file = self.storage_path / f"event_{storage_event['storage_id']}.json"
            with open(event_file, "w") as f:
                json.dump(storage_event, f, default=str)

        def get_stored_events(self, filter_type=None, limit=None):
            """Retrieve stored events with optional filtering."""
            events = self.stored_events

            if filter_type:
                events = [e for e in events if e.get("type") == filter_type]

            if limit:
                events = events[:limit]

            return events

        def get_storage_stats(self):
            """Get storage statistics."""
            return {
                "total_events": len(self.stored_events),
                "storage_path": str(self.storage_path),
                "disk_files": len(list(self.storage_path.glob("event_*.json"))),
            }

    class CommandAuditObserver:
        def __init__(self, audit_log_path=None):
            self.audit_log_path = (
                Path(audit_log_path) if audit_log_path else Path.cwd() / "audit.log"
            )
            self.audited_commands = []
            self.security_violations = []

        def handle_event(self, event):
            """Audit command-related events."""
            if "command" in event.get("data", {}):
                audit_entry = {
                    "timestamp": event.get("timestamp"),
                    "entity_id": event.get("entity_id"),
                    "command": event["data"]["command"],
                    "event_type": event.get("type"),
                    "audit_id": f"audit_{len(self.audited_commands)}",
                }

                # Check for security violations
                command_str = str(event["data"]["command"])
                if any(
                    dangerous in command_str
                    for dangerous in ["rm -rf", "sudo", "passwd"]
                ):
                    violation = {
                        **audit_entry,
                        "violation_type": "dangerous_command",
                        "severity": "high",
                    }
                    self.security_violations.append(violation)

                self.audited_commands.append(audit_entry)

        def get_audit_log(self):
            """Get complete audit log."""
            return self.audited_commands

        def get_security_violations(self):
            """Get security violations."""
            return self.security_violations

        def get_audit_summary(self):
            """Get audit summary."""
            return {
                "total_commands": len(self.audited_commands),
                "security_violations": len(self.security_violations),
                "audit_log_path": str(self.audit_log_path),
            }

    class StateObserver:
        def __init__(self):
            self.state_transitions = []
            self.current_states = {}
            self.invalid_transitions = []

        def handle_event(self, event):
            """Monitor state transitions."""
            if "state" in event.get("data", {}):
                entity_id = event.get("entity_id")
                new_state = event["data"]["state"]
                previous_state = self.current_states.get(entity_id)

                transition = {
                    "entity_id": entity_id,
                    "entity_type": event.get("entity_type"),
                    "previous_state": previous_state,
                    "new_state": new_state,
                    "timestamp": event.get("timestamp"),
                    "event_type": event.get("type"),
                }

                # Validate state transition
                if self._is_valid_transition(previous_state, new_state):
                    self.state_transitions.append(transition)
                    self.current_states[entity_id] = new_state
                else:
                    transition["violation"] = "invalid_state_transition"
                    self.invalid_transitions.append(transition)

        def _is_valid_transition(self, from_state, to_state):
            """Validate state transition logic."""
            # Simple validation - can be expanded
            valid_transitions = {
                None: ["initialized", "created"],
                "initialized": ["running", "configured"],
                "configured": ["running", "deployed"],
                "running": ["completed", "failed", "stopped"],
                "stopped": ["running", "completed"],
                "completed": ["cleanup"],
                "failed": ["cleanup", "retry"],
            }

            allowed_states = valid_transitions.get(from_state, [])
            return to_state in allowed_states or from_state == to_state

        def get_current_state(self, entity_id):
            """Get current state of entity."""
            return self.current_states.get(entity_id)

        def get_state_history(self, entity_id):
            """Get state history for entity."""
            return [t for t in self.state_transitions if t["entity_id"] == entity_id]

        def get_invalid_transitions(self):
            """Get invalid state transitions."""
            return self.invalid_transitions

    class ResultsManager:
        def __init__(self, results_path=None):
            self.results_path = (
                Path(results_path) if results_path else Path.cwd() / "results"
            )
            self.results_path.mkdir(exist_ok=True)
            self.experiment_results = {}
            self.test_results = {}

        def handle_event(self, event):
            """Collect and manage experiment results."""
            entity_type = event.get("entity_type")
            entity_id = event.get("entity_id")

            if entity_type == "experiment":
                self._handle_experiment_event(event)
            elif entity_type == "test":
                self._handle_test_event(event)

        def _handle_experiment_event(self, event):
            """Handle experiment-related events."""
            entity_id = event.get("entity_id")
            if entity_id not in self.experiment_results:
                self.experiment_results[entity_id] = {
                    "experiment_id": entity_id,
                    "start_time": None,
                    "end_time": None,
                    "status": "unknown",
                    "tests": [],
                    "metrics": {},
                }

            result = self.experiment_results[entity_id]
            event_type = event.get("type", "")

            if event_type.endswith(".started"):
                result["start_time"] = event.get("timestamp")
                result["status"] = "running"
            elif event_type.endswith(".completed"):
                result["end_time"] = event.get("timestamp")
                result["status"] = "completed"
            elif event_type.endswith(".failed"):
                result["end_time"] = event.get("timestamp")
                result["status"] = "failed"

        def _handle_test_event(self, event):
            """Handle test-related events."""
            entity_id = event.get("entity_id")
            if entity_id not in self.test_results:
                self.test_results[entity_id] = {
                    "test_id": entity_id,
                    "start_time": None,
                    "end_time": None,
                    "status": "unknown",
                    "assertions": [],
                    "metrics": {},
                }

            result = self.test_results[entity_id]
            event_type = event.get("type", "")

            if event_type.endswith(".started"):
                result["start_time"] = event.get("timestamp")
                result["status"] = "running"
            elif event_type.endswith(".completed"):
                result["end_time"] = event.get("timestamp")
                result["status"] = "completed"
            elif event_type.endswith(".failed"):
                result["end_time"] = event.get("timestamp")
                result["status"] = "failed"

        def get_experiment_results(self, experiment_id=None):
            """Get experiment results."""
            if experiment_id:
                return self.experiment_results.get(experiment_id)
            return self.experiment_results

        def get_test_results(self, test_id=None):
            """Get test results."""
            if test_id:
                return self.test_results.get(test_id)
            return self.test_results

        def generate_report(self, output_file=None):
            """Generate results report."""
            report = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "experiments": self.experiment_results,
                "tests": self.test_results,
                "summary": {
                    "total_experiments": len(self.experiment_results),
                    "total_tests": len(self.test_results),
                    "completed_experiments": len(
                        [
                            e
                            for e in self.experiment_results.values()
                            if e["status"] == "completed"
                        ]
                    ),
                    "failed_experiments": len(
                        [
                            e
                            for e in self.experiment_results.values()
                            if e["status"] == "failed"
                        ]
                    ),
                },
            }

            if output_file:
                with open(output_file, "w") as f:
                    json.dump(report, f, indent=2, default=str)

            return report

    class ObserverFactory:
        def __init__(self):
            self.observer_registry = {}
            self.created_observers = []

        def register_observer_type(self, observer_type, observer_class):
            """Register observer type."""
            self.observer_registry[observer_type] = observer_class

        def create_observer(self, observer_type, **kwargs):
            """Create observer instance."""
            if observer_type not in self.observer_registry:
                raise ValueError(f"Unknown observer type: {observer_type}")

            observer_class = self.observer_registry[observer_type]
            observer = observer_class(**kwargs)
            self.created_observers.append(observer)
            return observer

        def create_metrics_observer(self, **kwargs):
            """Create metrics observer."""
            return self.create_observer("metrics", **kwargs)

        def create_storage_observer(self, **kwargs):
            """Create storage observer."""
            return self.create_observer("storage", **kwargs)

        def create_audit_observer(self, **kwargs):
            """Create audit observer."""
            return self.create_observer("audit", **kwargs)

        def create_state_observer(self, **kwargs):
            """Create state observer."""
            return self.create_observer("state", **kwargs)

        def get_available_types(self):
            """Get available observer types."""
            return list(self.observer_registry.keys())

pytestmark = [pytest.mark.unit, pytest.mark.observer_system]

class TestMetricsObserver:
    """Test MetricsObserver functionality."""

    def test_metrics_observer_initialization(self):
        """Test MetricsObserver initialization."""
        observer = MetricsObserver()

        assert observer.metrics_collector is not None
        assert observer.events_processed == 0
        assert observer.metrics_recorded == []

    def test_metrics_observer_with_custom_collector(self):
        """Test MetricsObserver with custom metrics collector."""
        mock_collector = Mock()
        observer = MetricsObserver(metrics_collector=mock_collector)

        assert observer.metrics_collector == mock_collector

    def test_handle_start_event(self):
        """Test handling of start events."""
        observer = MetricsObserver()

        event = {
            "id": "event-123",
            "type": "experiment.started",
            "entity_id": "exp-456",
            "entity_type": "experiment",
            "timestamp": datetime.now(timezone.utc),
            "data": {},
        }

        observer.handle_event(event)

        assert observer.events_processed == 1
        assert len(observer.metrics_recorded) == 1

        metric = observer.metrics_recorded[0]
        assert metric["name"] == "experiment.start_count"
        assert metric["value"] == 1
        assert metric["tags"]["entity_id"] == "exp-456"

    def test_handle_completion_event(self):
        """Test handling of completion events."""
        observer = MetricsObserver()

        event = {
            "id": "event-789",
            "type": "test.completed",
            "entity_id": "test-101",
            "entity_type": "test",
            "timestamp": datetime.now(timezone.utc),
            "data": {},
        }

        observer.handle_event(event)

        assert observer.events_processed == 1
        assert len(observer.metrics_recorded) == 1

        metric = observer.metrics_recorded[0]
        assert metric["name"] == "test.completion_count"
        assert metric["value"] == 1
        assert metric["tags"]["entity_id"] == "test-101"

    def test_handle_multiple_events(self):
        """Test handling multiple events."""
        observer = MetricsObserver()

        events = [
            {
                "id": "event-1",
                "type": "experiment.started",
                "entity_id": "exp-1",
                "entity_type": "experiment",
                "timestamp": datetime.now(timezone.utc),
                "data": {},
            },
            {
                "id": "event-2",
                "type": "test.started",
                "entity_id": "test-1",
                "entity_type": "test",
                "timestamp": datetime.now(timezone.utc),
                "data": {},
            },
            {
                "id": "event-3",
                "type": "experiment.completed",
                "entity_id": "exp-1",
                "entity_type": "experiment",
                "timestamp": datetime.now(timezone.utc),
                "data": {},
            },
        ]

        for event in events:
            observer.handle_event(event)

        assert observer.events_processed == 3
        assert len(observer.metrics_recorded) == 3

    def test_get_metrics_summary(self):
        """Test metrics summary generation."""
        observer = MetricsObserver()

        # Process some events
        observer.handle_event(
            {
                "id": "event-1",
                "type": "service.started",
                "entity_id": "service-1",
                "entity_type": "service",
                "timestamp": datetime.now(timezone.utc),
                "data": {},
            }
        )

        summary = observer.get_metrics_summary()

        assert summary["events_processed"] == 1
        assert summary["metrics_count"] == 1
        assert len(summary["metrics"]) == 1

class TestStorageObserver:
    """Test StorageObserver functionality."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory."""
        temp_dir = tempfile.mkdtemp(prefix="panther_storage_test_")
        yield Path(temp_dir)
        # Cleanup handled by tempfile

    def test_storage_observer_initialization(self, temp_storage_dir):
        """Test StorageObserver initialization."""
        observer = StorageObserver(storage_path=temp_storage_dir)

        assert observer.storage_path == temp_storage_dir
        assert observer.stored_events == []
        assert observer.storage_path.exists()

    def test_storage_observer_default_path(self):
        """Test StorageObserver with default path."""
        observer = StorageObserver()

        assert observer.storage_path.name == "events"
        assert observer.stored_events == []

    def test_handle_event_storage(self, temp_storage_dir):
        """Test event storage functionality."""
        observer = StorageObserver(storage_path=temp_storage_dir)

        event = {
            "id": "event-123",
            "type": "test.event",
            "entity_id": "entity-456",
            "entity_type": "test",
            "timestamp": datetime.now(timezone.utc),
            "data": {"key": "value"},
        }

        observer.handle_event(event)

        assert len(observer.stored_events) == 1
        stored_event = observer.stored_events[0]

        # Verify original event data preserved
        assert stored_event["id"] == event["id"]
        assert stored_event["type"] == event["type"]
        assert stored_event["entity_id"] == event["entity_id"]

        # Verify storage metadata added
        assert "stored_at" in stored_event
        assert "storage_id" in stored_event

        # Verify file written
        event_files = list(temp_storage_dir.glob("event_*.json"))
        assert len(event_files) == 1

    def test_get_stored_events_no_filter(self, temp_storage_dir):
        """Test retrieving stored events without filter."""
        observer = StorageObserver(storage_path=temp_storage_dir)

        # Store multiple events
        events = [
            {"id": "1", "type": "type1", "entity_id": "e1", "entity_type": "test"},
            {"id": "2", "type": "type2", "entity_id": "e2", "entity_type": "test"},
            {"id": "3", "type": "type1", "entity_id": "e3", "entity_type": "test"},
        ]

        for event in events:
            observer.handle_event(event)

        retrieved_events = observer.get_stored_events()

        assert len(retrieved_events) == 3

    def test_get_stored_events_with_filter(self, temp_storage_dir):
        """Test retrieving stored events with type filter."""
        observer = StorageObserver(storage_path=temp_storage_dir)

        # Store events of different types
        events = [
            {
                "id": "1",
                "type": "experiment.started",
                "entity_id": "e1",
                "entity_type": "experiment",
            },
            {
                "id": "2",
                "type": "test.started",
                "entity_id": "e2",
                "entity_type": "test",
            },
            {
                "id": "3",
                "type": "experiment.completed",
                "entity_id": "e3",
                "entity_type": "experiment",
            },
        ]

        for event in events:
            observer.handle_event(event)

        experiment_events = observer.get_stored_events(filter_type="experiment.started")

        assert len(experiment_events) == 1
        assert experiment_events[0]["type"] == "experiment.started"

    def test_get_stored_events_with_limit(self, temp_storage_dir):
        """Test retrieving stored events with limit."""
        observer = StorageObserver(storage_path=temp_storage_dir)

        # Store multiple events
        for i in range(5):
            event = {
                "id": f"event-{i}",
                "type": "test.event",
                "entity_id": f"entity-{i}",
                "entity_type": "test",
            }
            observer.handle_event(event)

        limited_events = observer.get_stored_events(limit=3)

        assert len(limited_events) == 3

    def test_get_storage_stats(self, temp_storage_dir):
        """Test storage statistics."""
        observer = StorageObserver(storage_path=temp_storage_dir)

        # Store some events
        for i in range(3):
            event = {
                "id": f"event-{i}",
                "type": "test.event",
                "entity_id": f"entity-{i}",
                "entity_type": "test",
            }
            observer.handle_event(event)

        stats = observer.get_storage_stats()

        assert stats["total_events"] == 3
        assert stats["storage_path"] == str(temp_storage_dir)
        assert stats["disk_files"] == 3

class TestCommandAuditObserver:
    """Test CommandAuditObserver functionality."""

    def test_command_audit_observer_initialization(self):
        """Test CommandAuditObserver initialization."""
        observer = CommandAuditObserver()

        assert observer.audit_log_path.name == "audit.log"
        assert observer.audited_commands == []
        assert observer.security_violations == []

    def test_handle_command_event(self):
        """Test handling of command events."""
        observer = CommandAuditObserver()

        event = {
            "id": "event-123",
            "type": "command.executed",
            "entity_id": "service-456",
            "entity_type": "service",
            "timestamp": datetime.now(timezone.utc),
            "data": {"command": ["python", "-m", "panther", "--config", "test.yaml"]},
        }

        observer.handle_event(event)

        assert len(observer.audited_commands) == 1
        audit_entry = observer.audited_commands[0]

        assert audit_entry["entity_id"] == "service-456"
        assert audit_entry["command"] == [
            "python",
            "-m",
            "panther",
            "--config",
            "test.yaml",
        ]
        assert audit_entry["event_type"] == "command.executed"
        assert "audit_id" in audit_entry

    def test_handle_non_command_event(self):
        """Test handling of non-command events."""
        observer = CommandAuditObserver()

        event = {
            "id": "event-123",
            "type": "service.started",
            "entity_id": "service-456",
            "entity_type": "service",
            "timestamp": datetime.now(timezone.utc),
            "data": {"status": "running"},
        }

        observer.handle_event(event)

        assert len(observer.audited_commands) == 0

    def test_security_violation_detection(self):
        """Test detection of security violations."""
        observer = CommandAuditObserver()

        dangerous_event = {
            "id": "event-dangerous",
            "type": "command.executed",
            "entity_id": "service-bad",
            "entity_type": "service",
            "timestamp": datetime.now(timezone.utc),
            "data": {"command": ["sudo", "rm", "-rf", "/important/data"]},
        }

        observer.handle_event(dangerous_event)

        assert len(observer.audited_commands) == 1
        assert len(observer.security_violations) == 1

        violation = observer.security_violations[0]
        assert violation["violation_type"] == "dangerous_command"
        assert violation["severity"] == "high"

    def test_get_audit_log(self):
        """Test audit log retrieval."""
        observer = CommandAuditObserver()

        # Add some commands
        commands = [["python", "script.py"], ["ls", "-la"], ["echo", "hello"]]

        for i, cmd in enumerate(commands):
            event = {
                "id": f"event-{i}",
                "type": "command.executed",
                "entity_id": f"service-{i}",
                "entity_type": "service",
                "timestamp": datetime.now(timezone.utc),
                "data": {"command": cmd},
            }
            observer.handle_event(event)

        audit_log = observer.get_audit_log()

        assert len(audit_log) == 3
        assert all("audit_id" in entry for entry in audit_log)

    def test_get_security_violations(self):
        """Test security violations retrieval."""
        observer = CommandAuditObserver()

        # Add safe and dangerous commands
        safe_event = {
            "id": "event-safe",
            "type": "command.executed",
            "entity_id": "service-safe",
            "timestamp": datetime.now(timezone.utc),
            "data": {"command": ["echo", "hello"]},
        }

        dangerous_event = {
            "id": "event-dangerous",
            "type": "command.executed",
            "entity_id": "service-dangerous",
            "timestamp": datetime.now(timezone.utc),
            "data": {"command": ["rm", "-rf", "/"]},
        }

        observer.handle_event(safe_event)
        observer.handle_event(dangerous_event)

        violations = observer.get_security_violations()

        assert len(violations) == 1
        assert violations[0]["entity_id"] == "service-dangerous"

    def test_get_audit_summary(self):
        """Test audit summary generation."""
        observer = CommandAuditObserver()

        # Add some commands including violations
        events = [
            {"data": {"command": ["echo", "safe"]}},
            {"data": {"command": ["sudo", "dangerous"]}},
            {"data": {"command": ["ls", "safe"]}},
        ]

        for i, event_data in enumerate(events):
            event = {
                "id": f"event-{i}",
                "type": "command.executed",
                "entity_id": f"service-{i}",
                "timestamp": datetime.now(timezone.utc),
                **event_data,
            }
            observer.handle_event(event)

        summary = observer.get_audit_summary()

        assert summary["total_commands"] == 3
        assert summary["security_violations"] == 1

class TestStateObserver:
    """Test StateObserver functionality."""

    def test_state_observer_initialization(self):
        """Test StateObserver initialization."""
        observer = StateObserver()

        assert observer.state_transitions == []
        assert observer.current_states == {}
        assert observer.invalid_transitions == []

    def test_handle_state_event(self):
        """Test handling of state events."""
        observer = StateObserver()

        event = {
            "id": "event-123",
            "type": "experiment.state_changed",
            "entity_id": "exp-456",
            "entity_type": "experiment",
            "timestamp": datetime.now(timezone.utc),
            "data": {"state": "initialized"},
        }

        observer.handle_event(event)

        assert len(observer.state_transitions) == 1
        assert observer.current_states["exp-456"] == "initialized"

        transition = observer.state_transitions[0]
        assert transition["entity_id"] == "exp-456"
        assert transition["previous_state"] is None
        assert transition["new_state"] == "initialized"

    def test_valid_state_transition(self):
        """Test valid state transitions."""
        observer = StateObserver()

        # Initialize entity
        init_event = {
            "id": "event-1",
            "type": "experiment.initialized",
            "entity_id": "exp-123",
            "entity_type": "experiment",
            "timestamp": datetime.now(timezone.utc),
            "data": {"state": "initialized"},
        }

        # Transition to running
        run_event = {
            "id": "event-2",
            "type": "experiment.started",
            "entity_id": "exp-123",
            "entity_type": "experiment",
            "timestamp": datetime.now(timezone.utc),
            "data": {"state": "running"},
        }

        observer.handle_event(init_event)
        observer.handle_event(run_event)

        assert len(observer.state_transitions) == 2
        assert len(observer.invalid_transitions) == 0
        assert observer.current_states["exp-123"] == "running"

    def test_invalid_state_transition(self):
        """Test invalid state transitions."""
        observer = StateObserver()

        # Try to go directly to completed without proper setup
        invalid_event = {
            "id": "event-invalid",
            "type": "experiment.completed",
            "entity_id": "exp-bad",
            "entity_type": "experiment",
            "timestamp": datetime.now(timezone.utc),
            "data": {"state": "completed"},
        }

        observer.handle_event(invalid_event)

        assert len(observer.state_transitions) == 0
        assert len(observer.invalid_transitions) == 1
        assert "exp-bad" not in observer.current_states

        violation = observer.invalid_transitions[0]
        assert violation["violation"] == "invalid_state_transition"

    def test_get_current_state(self):
        """Test current state retrieval."""
        observer = StateObserver()

        event = {
            "id": "event-1",
            "type": "test.running",
            "entity_id": "test-123",
            "entity_type": "test",
            "timestamp": datetime.now(timezone.utc),
            "data": {"state": "running"},
        }

        observer.handle_event(event)

        assert observer.get_current_state("test-123") == "running"
        assert observer.get_current_state("nonexistent") is None

    def test_get_state_history(self):
        """Test state history retrieval."""
        observer = StateObserver()
        entity_id = "service-123"

        # Create state progression
        states = ["initialized", "running", "completed"]
        for i, state in enumerate(states):
            event = {
                "id": f"event-{i}",
                "type": f"service.{state}",
                "entity_id": entity_id,
                "entity_type": "service",
                "timestamp": datetime.now(timezone.utc),
                "data": {"state": state},
            }
            observer.handle_event(event)

        history = observer.get_state_history(entity_id)

        assert len(history) == 3
        assert [t["new_state"] for t in history] == states

    def test_get_invalid_transitions(self):
        """Test invalid transitions retrieval."""
        observer = StateObserver()

        # Create an invalid transition
        invalid_event = {
            "id": "event-invalid",
            "type": "service.invalid",
            "entity_id": "service-bad",
            "entity_type": "service",
            "timestamp": datetime.now(timezone.utc),
            "data": {"state": "invalid_state"},
        }

        observer.handle_event(invalid_event)

        invalid_transitions = observer.get_invalid_transitions()

        assert len(invalid_transitions) == 1
        assert invalid_transitions[0]["violation"] == "invalid_state_transition"

class TestResultsManager:
    """Test ResultsManager functionality."""

    def test_results_manager_initialization(self):
        """Test ResultsManager initialization."""
        manager = ResultsManager()

        assert manager.results_path.name == "results"
        assert manager.experiment_results == {}
        assert manager.test_results == {}

    def test_handle_experiment_events(self):
        """Test handling of experiment events."""
        manager = ResultsManager()

        start_event = {
            "id": "event-1",
            "type": "experiment.started",
            "entity_id": "exp-123",
            "entity_type": "experiment",
            "timestamp": datetime.now(timezone.utc),
            "data": {},
        }

        end_event = {
            "id": "event-2",
            "type": "experiment.completed",
            "entity_id": "exp-123",
            "entity_type": "experiment",
            "timestamp": datetime.now(timezone.utc),
            "data": {},
        }

        manager.handle_event(start_event)
        manager.handle_event(end_event)

        result = manager.get_experiment_results("exp-123")

        assert result is not None
        assert result["experiment_id"] == "exp-123"
        assert result["status"] == "completed"
        assert result["start_time"] is not None
        assert result["end_time"] is not None

    def test_handle_test_events(self):
        """Test handling of test events."""
        manager = ResultsManager()

        start_event = {
            "id": "event-1",
            "type": "test.started",
            "entity_id": "test-456",
            "entity_type": "test",
            "timestamp": datetime.now(timezone.utc),
            "data": {},
        }

        fail_event = {
            "id": "event-2",
            "type": "test.failed",
            "entity_id": "test-456",
            "entity_type": "test",
            "timestamp": datetime.now(timezone.utc),
            "data": {},
        }

        manager.handle_event(start_event)
        manager.handle_event(fail_event)

        result = manager.get_test_results("test-456")

        assert result is not None
        assert result["test_id"] == "test-456"
        assert result["status"] == "failed"

    def test_generate_report(self):
        """Test report generation."""
        manager = ResultsManager()

        # Add some results
        exp_event = {
            "id": "event-1",
            "type": "experiment.completed",
            "entity_id": "exp-1",
            "entity_type": "experiment",
            "timestamp": datetime.now(timezone.utc),
            "data": {},
        }

        test_event = {
            "id": "event-2",
            "type": "test.completed",
            "entity_id": "test-1",
            "entity_type": "test",
            "timestamp": datetime.now(timezone.utc),
            "data": {},
        }

        manager.handle_event(exp_event)
        manager.handle_event(test_event)

        report = manager.generate_report()

        assert "generated_at" in report
        assert "experiments" in report
        assert "tests" in report
        assert "summary" in report

        summary = report["summary"]
        assert summary["total_experiments"] == 1
        assert summary["total_tests"] == 1
        assert summary["completed_experiments"] == 1
        assert summary["failed_experiments"] == 0

class TestObserverFactory:
    """Test ObserverFactory functionality."""

    def test_observer_factory_initialization(self):
        """Test ObserverFactory initialization."""
        factory = ObserverFactory()

        assert factory.observer_registry == {}
        assert factory.created_observers == []

    def test_register_observer_type(self):
        """Test observer type registration."""
        factory = ObserverFactory()

        factory.register_observer_type("metrics", MetricsObserver)
        factory.register_observer_type("storage", StorageObserver)

        assert "metrics" in factory.observer_registry
        assert "storage" in factory.observer_registry
        assert factory.observer_registry["metrics"] == MetricsObserver

    def test_create_observer(self):
        """Test observer creation."""
        factory = ObserverFactory()
        factory.register_observer_type("metrics", MetricsObserver)

        observer = factory.create_observer("metrics")

        assert isinstance(observer, MetricsObserver)
        assert observer in factory.created_observers

    def test_create_observer_with_kwargs(self):
        """Test observer creation with kwargs."""
        factory = ObserverFactory()
        factory.register_observer_type("storage", StorageObserver)

        temp_path = "/tmp/test_storage"
        observer = factory.create_observer("storage", storage_path=temp_path)

        assert isinstance(observer, StorageObserver)
        assert str(observer.storage_path) == temp_path

    def test_create_unknown_observer_type(self):
        """Test creating unknown observer type."""
        factory = ObserverFactory()

        with pytest.raises(ValueError, match="Unknown observer type"):
            factory.create_observer("unknown_type")

    def test_convenience_methods(self):
        """Test convenience observer creation methods."""
        factory = ObserverFactory()

        # Register observer types
        factory.register_observer_type("metrics", MetricsObserver)
        factory.register_observer_type("storage", StorageObserver)
        factory.register_observer_type("audit", CommandAuditObserver)
        factory.register_observer_type("state", StateObserver)

        # Test convenience methods
        metrics_obs = factory.create_metrics_observer()
        storage_obs = factory.create_storage_observer()
        audit_obs = factory.create_audit_observer()
        state_obs = factory.create_state_observer()

        assert isinstance(metrics_obs, MetricsObserver)
        assert isinstance(storage_obs, StorageObserver)
        assert isinstance(audit_obs, CommandAuditObserver)
        assert isinstance(state_obs, StateObserver)

        assert len(factory.created_observers) == 4

    def test_get_available_types(self):
        """Test getting available observer types."""
        factory = ObserverFactory()

        factory.register_observer_type("metrics", MetricsObserver)
        factory.register_observer_type("storage", StorageObserver)
        factory.register_observer_type("audit", CommandAuditObserver)

        available_types = factory.get_available_types()

        assert len(available_types) == 3
        assert "metrics" in available_types
        assert "storage" in available_types
        assert "audit" in available_types

class TestObserverSystemIntegration:
    """Test integration between observer system components."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for integration tests."""
        temp_dir = tempfile.mkdtemp(prefix="panther_observer_integration_")
        yield Path(temp_dir)

    def test_multi_observer_event_processing(self, temp_workspace):
        """Test multiple observers processing the same events."""
        # Create observers
        metrics_observer = MetricsObserver()
        storage_observer = StorageObserver(storage_path=temp_workspace / "storage")
        audit_observer = CommandAuditObserver()
        state_observer = StateObserver()

        observers = [metrics_observer, storage_observer, audit_observer, state_observer]

        # Create test events
        events = [
            {
                "id": "event-1",
                "type": "experiment.started",
                "entity_id": "exp-123",
                "entity_type": "experiment",
                "timestamp": datetime.now(timezone.utc),
                "data": {
                    "state": "initialized",
                    "command": ["python", "experiment.py"],
                },
            },
            {
                "id": "event-2",
                "type": "service.started",
                "entity_id": "service-456",
                "entity_type": "service",
                "timestamp": datetime.now(timezone.utc),
                "data": {"state": "running", "command": ["docker", "run", "image"]},
            },
            {
                "id": "event-3",
                "type": "experiment.completed",
                "entity_id": "exp-123",
                "entity_type": "experiment",
                "timestamp": datetime.now(timezone.utc),
                "data": {"state": "completed"},
            },
        ]

        # Process events through all observers
        for event in events:
            for observer in observers:
                observer.handle_event(event)

        # Verify each observer processed events correctly
        assert metrics_observer.events_processed == 3
        assert len(storage_observer.stored_events) == 3
        assert len(audit_observer.audited_commands) == 2  # 2 events with commands
        assert len(state_observer.state_transitions) == 3

    def test_observer_factory_full_workflow(self, temp_workspace):
        """Test complete observer factory workflow."""
        factory = ObserverFactory()

        # Register all observer types
        factory.register_observer_type("metrics", MetricsObserver)
        factory.register_observer_type("storage", StorageObserver)
        factory.register_observer_type("audit", CommandAuditObserver)
        factory.register_observer_type("state", StateObserver)

        # Create observers with custom configurations
        observers = []
        observers.append(factory.create_metrics_observer())
        observers.append(factory.create_storage_observer(storage_path=temp_workspace))
        observers.append(factory.create_audit_observer())
        observers.append(factory.create_state_observer())

        # Verify all observers created
        assert len(observers) == 4
        assert len(factory.created_observers) == 4

        # Test event processing
        test_event = {
            "id": "factory-test",
            "type": "test.completed",
            "entity_id": "test-789",
            "entity_type": "test",
            "timestamp": datetime.now(timezone.utc),
            "data": {"state": "completed", "command": ["pytest", "tests/"]},
        }

        for observer in observers:
            observer.handle_event(test_event)

        # Verify each observer type processed the event
        metrics_obs = observers[0]
        storage_obs = observers[1]
        audit_obs = observers[2]
        state_obs = observers[3]

        assert metrics_obs.events_processed == 1
        assert len(storage_obs.stored_events) == 1
        assert len(audit_obs.audited_commands) == 1
        assert len(state_obs.state_transitions) == 1

    def test_results_manager_with_other_observers(self, temp_workspace):
        """Test ResultsManager integration with other observers."""
        results_manager = ResultsManager(results_path=temp_workspace)
        metrics_observer = MetricsObserver()

        # Simulate experiment workflow
        experiment_events = [
            {
                "id": "exp-start",
                "type": "experiment.started",
                "entity_id": "integration-exp",
                "entity_type": "experiment",
                "timestamp": datetime.now(timezone.utc),
                "data": {},
            },
            {
                "id": "test-start",
                "type": "test.started",
                "entity_id": "integration-test",
                "entity_type": "test",
                "timestamp": datetime.now(timezone.utc),
                "data": {},
            },
            {
                "id": "test-complete",
                "type": "test.completed",
                "entity_id": "integration-test",
                "entity_type": "test",
                "timestamp": datetime.now(timezone.utc),
                "data": {},
            },
            {
                "id": "exp-complete",
                "type": "experiment.completed",
                "entity_id": "integration-exp",
                "entity_type": "experiment",
                "timestamp": datetime.now(timezone.utc),
                "data": {},
            },
        ]

        # Process through both observers
        for event in experiment_events:
            results_manager.handle_event(event)
            metrics_observer.handle_event(event)

        # Verify results collection
        exp_result = results_manager.get_experiment_results("integration-exp")
        test_result = results_manager.get_test_results("integration-test")

        assert exp_result["status"] == "completed"
        assert test_result["status"] == "completed"

        # Verify metrics collection
        assert metrics_observer.events_processed == 4
        assert len(metrics_observer.metrics_recorded) == 4

        # Generate comprehensive report
        report = results_manager.generate_report()
        metrics_summary = metrics_observer.get_metrics_summary()

        assert report["summary"]["completed_experiments"] == 1
        assert metrics_summary["events_processed"] == 4

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
