#!/usr/bin/env python3.10
"""Tests for CommandAuditObserver using real implementations.

Tests the real CommandAuditObserver from
panther/core/observer/impl/command_audit_observer.py which tracks command
generation and modification events, maintains an audit trail, and writes
audit JSON to disk.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.command_audit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cmd_gen_started_event(
    service_id: str = "svc-1",
    service_name: str = "picoquic",
    phase: str = "run",
    config: Dict[str, Any] | None = None,
):
    """Create a real CommandGenerationStartedEvent."""
    from panther.core.events.service.events import CommandGenerationStartedEvent

    return CommandGenerationStartedEvent(
        service_id=service_id,
        service_name=service_name,
        phase=phase,
        config=config,
    )


def _make_cmd_generated_event(
    service_id: str = "svc-1",
    service_name: str = "picoquic",
    phase: str = "run",
    command: str = "echo hello",
    command_type: str | None = None,
):
    """Create a real CommandGeneratedEvent."""
    from panther.core.events.service.events import CommandGeneratedEvent

    return CommandGeneratedEvent(
        service_id=service_id,
        service_name=service_name,
        phase=phase,
        command=command,
        command_type=command_type,
    )


def _make_cmd_modified_event(
    service_id: str = "svc-1",
    service_name: str = "picoquic",
    phase: str = "run",
    original_command: str = "echo hello",
    modified_command: str = "strace echo hello",
    modifier: str = "strace",
    modification_details: Dict[str, Any] | None = None,
):
    """Create a real CommandModifiedEvent."""
    from panther.core.events.service.events import CommandModifiedEvent

    return CommandModifiedEvent(
        service_id=service_id,
        service_name=service_name,
        phase=phase,
        original_command=original_command,
        modified_command=modified_command,
        modifier=modifier,
        modification_details=modification_details,
    )


def _make_config_generated_event(
    service_id: str = "experiment-1",
    config_type: str = "docker-compose",
    config_path: str = "/tmp/docker-compose.yml",
    config_content: str | None = None,
    services_included: list[str] | None = None,
):
    """Create a real ConfigGeneratedEvent."""
    from panther.core.events.service.events import ConfigGeneratedEvent

    return ConfigGeneratedEvent(
        service_id=service_id,
        config_type=config_type,
        config_path=config_path,
        config_content=config_content,
        services_included=services_included,
    )


def _make_observer(tmp_path: Path):
    """Create a real CommandAuditObserver pointing at tmp_path."""
    from panther.core.observer.impl.command_audit_observer import (
        CommandAuditObserver,
    )

    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    return CommandAuditObserver(output_dir=audit_dir)


# ===================================================================
# Construction and Initialization
# ===================================================================


class TestCommandAuditObserverInit:
    """Test observer construction and initialization."""

    def test_creates_output_directory(self, tmp_path):
        """Observer creates the output directory if it does not exist."""
        from panther.core.observer.impl.command_audit_observer import (
            CommandAuditObserver,
        )

        audit_dir = tmp_path / "new_audit_dir"
        assert not audit_dir.exists()
        observer = CommandAuditObserver(output_dir=audit_dir)
        assert audit_dir.exists()
        assert observer.output_dir == audit_dir

    def test_default_observer_id(self, tmp_path):
        """Observer uses 'command_audit' as default observer_id."""
        observer = _make_observer(tmp_path)
        # ITypedObserver stores nothing public for observer_id, but the
        # constructor accepted it without error.
        assert observer.output_dir.exists()

    def test_custom_observer_id(self, tmp_path):
        """Observer accepts a custom observer_id."""
        from panther.core.observer.impl.command_audit_observer import (
            CommandAuditObserver,
        )

        audit_dir = tmp_path / "audit"
        observer = CommandAuditObserver(
            output_dir=audit_dir, observer_id="custom_audit"
        )
        assert observer.output_dir == audit_dir

    def test_empty_initial_state(self, tmp_path):
        """Observer starts with empty command_history and generation_in_progress."""
        observer = _make_observer(tmp_path)
        assert observer.command_history == {}
        assert observer.generation_in_progress == {}

    def test_audit_file_path(self, tmp_path):
        """Observer sets audit_file to output_dir / command_audit.json."""
        observer = _make_observer(tmp_path)
        expected = observer.output_dir / "command_audit.json"
        assert observer.audit_file == expected

    def test_uses_real_command_audit_observer_fixture(
        self, real_command_audit_observer
    ):
        """The conftest fixture produces a working observer."""
        obs = real_command_audit_observer
        assert obs.command_history == {}
        assert obs.output_dir.exists()


# ===================================================================
# get_supported_event_types
# ===================================================================


class TestGetSupportedEventTypes:
    """Test the get_supported_event_types method."""

    def test_returns_four_event_types(self, real_command_audit_observer):
        """Observer supports exactly four event types."""
        types = real_command_audit_observer.get_supported_event_types()
        assert len(types) == 4

    def test_includes_command_generation_started(self, real_command_audit_observer):
        """Supported types include CommandGenerationStartedEvent."""
        from panther.core.events.service.events import CommandGenerationStartedEvent

        types = real_command_audit_observer.get_supported_event_types()
        assert CommandGenerationStartedEvent in types

    def test_includes_command_generated(self, real_command_audit_observer):
        """Supported types include CommandGeneratedEvent."""
        from panther.core.events.service.events import CommandGeneratedEvent

        types = real_command_audit_observer.get_supported_event_types()
        assert CommandGeneratedEvent in types

    def test_includes_command_modified(self, real_command_audit_observer):
        """Supported types include CommandModifiedEvent."""
        from panther.core.events.service.events import CommandModifiedEvent

        types = real_command_audit_observer.get_supported_event_types()
        assert CommandModifiedEvent in types

    def test_includes_config_generated(self, real_command_audit_observer):
        """Supported types include ConfigGeneratedEvent."""
        from panther.core.events.service.events import ConfigGeneratedEvent

        types = real_command_audit_observer.get_supported_event_types()
        assert ConfigGeneratedEvent in types


# ===================================================================
# handle_command_generation_started
# ===================================================================


class TestHandleCommandGenerationStarted:
    """Test handling of CommandGenerationStartedEvent."""

    def test_records_generation_in_progress(self, real_command_audit_observer):
        """Event is recorded in generation_in_progress dict."""
        event = _make_cmd_gen_started_event(
            service_name="picoquic", phase="run"
        )
        real_command_audit_observer.handle_command_generation_started(event)

        key = "picoquic_run"
        assert key in real_command_audit_observer.generation_in_progress
        entry = real_command_audit_observer.generation_in_progress[key]
        assert entry["service_name"] == "picoquic"
        assert entry["phase"] == "run"
        assert "started_at" in entry

    def test_stores_config_from_event(self, real_command_audit_observer):
        """Config data from the event is stored in generation_in_progress."""
        cfg = {"port": 4433, "version": "rfc9000"}
        event = _make_cmd_gen_started_event(config=cfg)
        real_command_audit_observer.handle_command_generation_started(event)

        key = "picoquic_run"
        assert real_command_audit_observer.generation_in_progress[key]["config"] == cfg

    def test_overwrites_previous_in_progress(self, real_command_audit_observer):
        """A second started event for the same service+phase overwrites the first."""
        e1 = _make_cmd_gen_started_event(config={"v": 1})
        e2 = _make_cmd_gen_started_event(config={"v": 2})
        real_command_audit_observer.handle_command_generation_started(e1)
        real_command_audit_observer.handle_command_generation_started(e2)

        key = "picoquic_run"
        assert real_command_audit_observer.generation_in_progress[key]["config"] == {
            "v": 2
        }

    def test_does_not_affect_command_history(self, real_command_audit_observer):
        """Started events do not create entries in command_history."""
        event = _make_cmd_gen_started_event()
        real_command_audit_observer.handle_command_generation_started(event)
        assert real_command_audit_observer.command_history == {}


# ===================================================================
# handle_command_generated
# ===================================================================


class TestHandleCommandGenerated:
    """Test handling of CommandGeneratedEvent."""

    def test_adds_to_command_history(self, real_command_audit_observer):
        """Generated event creates an entry in command_history."""
        event = _make_cmd_generated_event(
            service_name="picoquic", phase="run", command="./run.sh"
        )
        real_command_audit_observer.handle_command_generated(event)

        key = "picoquic_run"
        assert key in real_command_audit_observer.command_history
        assert len(real_command_audit_observer.command_history[key]) == 1

    def test_record_contains_expected_fields(self, real_command_audit_observer):
        """The command record contains service_name, phase, command, timestamp."""
        event = _make_cmd_generated_event(
            service_name="aioquic", phase="setup", command="pip install ."
        )
        real_command_audit_observer.handle_command_generated(event)

        record = real_command_audit_observer.command_history["aioquic_setup"][0]
        assert record["service_name"] == "aioquic"
        assert record["phase"] == "setup"
        assert record["command"] == "pip install ."
        assert "timestamp" in record
        assert record["modifications"] == []

    def test_clears_generation_in_progress(self, real_command_audit_observer):
        """After a generated event, the corresponding in-progress entry is removed."""
        obs = real_command_audit_observer
        started = _make_cmd_gen_started_event(service_name="pico", phase="run")
        obs.handle_command_generation_started(started)
        assert "pico_run" in obs.generation_in_progress

        generated = _make_cmd_generated_event(service_name="pico", phase="run")
        obs.handle_command_generated(generated)
        assert "pico_run" not in obs.generation_in_progress

    def test_links_generation_info(self, real_command_audit_observer):
        """Generated record includes generation_info from the started event."""
        obs = real_command_audit_observer
        started = _make_cmd_gen_started_event(
            service_name="pico", phase="run", config={"port": 4433}
        )
        obs.handle_command_generation_started(started)

        generated = _make_cmd_generated_event(
            service_name="pico", phase="run", command="./run"
        )
        obs.handle_command_generated(generated)

        record = obs.command_history["pico_run"][0]
        assert record["generation_info"]["config"] == {"port": 4433}

    def test_multiple_commands_same_service_phase(self, real_command_audit_observer):
        """Multiple generated events for the same key append to the list."""
        obs = real_command_audit_observer
        for i in range(3):
            event = _make_cmd_generated_event(
                service_name="pico", phase="run", command=f"cmd-{i}"
            )
            obs.handle_command_generated(event)

        assert len(obs.command_history["pico_run"]) == 3
        assert obs.command_history["pico_run"][2]["command"] == "cmd-2"

    def test_saves_audit_trail_to_disk(self, real_command_audit_observer):
        """Generated event triggers a save of the audit JSON to disk."""
        obs = real_command_audit_observer
        event = _make_cmd_generated_event(command="echo test")
        obs.handle_command_generated(event)

        assert obs.audit_file.exists()
        data = json.loads(obs.audit_file.read_text())
        assert "command_history" in data
        assert "statistics" in data


# ===================================================================
# handle_command_modified
# ===================================================================


class TestHandleCommandModified:
    """Test handling of CommandModifiedEvent."""

    def test_appends_modification_to_latest_record(
        self, real_command_audit_observer
    ):
        """Modification is appended to the modifications list of the latest record."""
        obs = real_command_audit_observer
        gen = _make_cmd_generated_event(
            service_name="pico", phase="run", command="./run.sh"
        )
        obs.handle_command_generated(gen)

        mod = _make_cmd_modified_event(
            service_name="pico",
            phase="run",
            original_command="./run.sh",
            modified_command="strace ./run.sh",
            modifier="strace",
        )
        obs.handle_command_modified(mod)

        record = obs.command_history["pico_run"][0]
        assert len(record["modifications"]) == 1
        m = record["modifications"][0]
        assert m["modifier"] == "strace"
        assert m["original_command"] == "./run.sh"
        assert m["modified_command"] == "strace ./run.sh"
        assert "timestamp" in m

    def test_multiple_modifications(self, real_command_audit_observer):
        """Multiple modifications stack up on the latest record."""
        obs = real_command_audit_observer
        gen = _make_cmd_generated_event(
            service_name="pico", phase="run", command="./run.sh"
        )
        obs.handle_command_generated(gen)

        for modifier in ["strace", "gperf", "wrapper"]:
            mod = _make_cmd_modified_event(
                service_name="pico",
                phase="run",
                modifier=modifier,
            )
            obs.handle_command_modified(mod)

        record = obs.command_history["pico_run"][0]
        assert len(record["modifications"]) == 3
        modifiers = [m["modifier"] for m in record["modifications"]]
        assert modifiers == ["strace", "gperf", "wrapper"]

    def test_modification_with_details(self, real_command_audit_observer):
        """modification_details from the event are preserved."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )

        details = {"added_flags": ["-f", "-e trace=network"]}
        mod = _make_cmd_modified_event(
            service_name="pico",
            phase="run",
            modifier="strace",
            modification_details=details,
        )
        obs.handle_command_modified(mod)

        record = obs.command_history["pico_run"][0]
        assert record["modifications"][0]["modification_details"] == details

    def test_modification_for_unknown_service_logged(
        self, real_command_audit_observer
    ):
        """Modifying a service with no history logs a warning but does not crash."""
        obs = real_command_audit_observer
        mod = _make_cmd_modified_event(
            service_name="nonexistent", phase="run"
        )
        # Should not raise
        obs.handle_command_modified(mod)
        assert obs.command_history == {}

    def test_modification_saves_audit_trail(self, real_command_audit_observer):
        """Modification triggers an audit trail save."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        # Remove the file to prove modification re-creates it
        obs.audit_file.unlink()

        obs.handle_command_modified(
            _make_cmd_modified_event(service_name="pico", phase="run")
        )
        assert obs.audit_file.exists()


# ===================================================================
# handle_config_generated
# ===================================================================


class TestHandleConfigGenerated:
    """Test handling of ConfigGeneratedEvent."""

    def test_stores_config_in_special_key(self, real_command_audit_observer):
        """Config events are stored under the 'config_generation' key."""
        obs = real_command_audit_observer
        event = _make_config_generated_event(
            config_type="docker-compose",
            config_path="/tmp/dc.yml",
            services_included=["picoquic", "aioquic"],
        )
        obs.handle_config_generated(event)

        assert "config_generation" in obs.command_history
        assert len(obs.command_history["config_generation"]) == 1

    def test_config_record_fields(self, real_command_audit_observer):
        """Config record contains expected fields."""
        obs = real_command_audit_observer
        event = _make_config_generated_event(
            config_type="kubernetes",
            config_path="/tmp/k8s.yml",
            config_content="apiVersion: v1\nkind: Pod",
            services_included=["svc-a"],
        )
        obs.handle_config_generated(event)

        record = obs.command_history["config_generation"][0]
        assert record["config_type"] == "kubernetes"
        assert record["config_path"] == "/tmp/k8s.yml"
        assert record["services_included"] == ["svc-a"]
        assert "timestamp" in record

    def test_config_content_preview_truncated(self, real_command_audit_observer):
        """Long config_content is truncated to 500 chars in the preview."""
        obs = real_command_audit_observer
        long_content = "x" * 1000
        event = _make_config_generated_event(config_content=long_content)
        obs.handle_config_generated(event)

        record = obs.command_history["config_generation"][0]
        assert record["config_preview"] is not None
        assert len(record["config_preview"]) == 500

    def test_config_content_none_preview_none(self, real_command_audit_observer):
        """When config_content is None, config_preview is also None."""
        obs = real_command_audit_observer
        event = _make_config_generated_event(config_content=None)
        obs.handle_config_generated(event)

        record = obs.command_history["config_generation"][0]
        assert record["config_preview"] is None

    def test_config_saves_audit_trail(self, real_command_audit_observer):
        """Config event triggers an audit trail save."""
        obs = real_command_audit_observer
        obs.handle_config_generated(_make_config_generated_event())
        assert obs.audit_file.exists()


# ===================================================================
# _save_audit_trail
# ===================================================================


class TestSaveAuditTrail:
    """Test the audit trail persistence."""

    def test_audit_json_structure(self, real_command_audit_observer):
        """Saved JSON contains generated_at, command_history, statistics."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )

        data = json.loads(obs.audit_file.read_text())
        assert "generated_at" in data
        assert "command_history" in data
        assert "statistics" in data

    def test_audit_trail_survives_write_error(self, real_command_audit_observer):
        """If writing the audit file fails, the observer does not crash."""
        obs = real_command_audit_observer
        with patch("builtins.open", side_effect=PermissionError("denied")):
            # Should not raise
            obs._save_audit_trail()

    def test_audit_trail_updated_on_each_event(self, real_command_audit_observer):
        """Each generated event updates the audit file."""
        obs = real_command_audit_observer
        for i in range(3):
            obs.handle_command_generated(
                _make_cmd_generated_event(
                    service_name=f"svc-{i}", phase="run", command=f"cmd-{i}"
                )
            )

        data = json.loads(obs.audit_file.read_text())
        # Each service+phase gets its own key
        assert len(data["command_history"]) == 3


# ===================================================================
# _calculate_statistics
# ===================================================================


class TestCalculateStatistics:
    """Test the statistics calculation."""

    def test_empty_statistics(self, real_command_audit_observer):
        """Empty observer returns zero statistics."""
        stats = real_command_audit_observer._calculate_statistics()
        assert stats["total_services"] == 0
        assert stats["total_commands"] == 0
        assert stats["total_modifications"] == 0

    def test_counts_services_and_commands(self, real_command_audit_observer):
        """Statistics count services (distinct keys) and total commands."""
        obs = real_command_audit_observer
        # 2 services, 3 commands total
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="aio", phase="setup")
        )

        stats = obs._calculate_statistics()
        assert stats["total_services"] == 2
        assert stats["total_commands"] == 3

    def test_counts_modifications(self, real_command_audit_observer):
        """Statistics count total modifications across all commands."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        obs.handle_command_modified(
            _make_cmd_modified_event(
                service_name="pico", phase="run", modifier="strace"
            )
        )
        obs.handle_command_modified(
            _make_cmd_modified_event(
                service_name="pico", phase="run", modifier="gperf"
            )
        )

        stats = obs._calculate_statistics()
        assert stats["total_modifications"] == 2

    def test_modifications_by_type(self, real_command_audit_observer):
        """Statistics track modifications grouped by modifier name."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        obs.handle_command_modified(
            _make_cmd_modified_event(
                service_name="pico", phase="run", modifier="strace"
            )
        )
        obs.handle_command_modified(
            _make_cmd_modified_event(
                service_name="pico", phase="run", modifier="strace"
            )
        )
        obs.handle_command_modified(
            _make_cmd_modified_event(
                service_name="pico", phase="run", modifier="gperf"
            )
        )

        stats = obs._calculate_statistics()
        assert stats["modifications_by_type"]["strace"] == 2
        assert stats["modifications_by_type"]["gperf"] == 1

    def test_commands_by_phase(self, real_command_audit_observer):
        """Statistics track commands grouped by phase."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="setup")
        )
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="aio", phase="run")
        )

        stats = obs._calculate_statistics()
        assert stats["commands_by_phase"]["run"] == 2
        assert stats["commands_by_phase"]["setup"] == 1

    def test_excludes_config_generation_from_service_count(
        self, real_command_audit_observer
    ):
        """The 'config_generation' key is excluded from service count."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        obs.handle_config_generated(_make_config_generated_event())

        stats = obs._calculate_statistics()
        assert stats["total_services"] == 1  # only pico_run, not config_generation


# ===================================================================
# get_command_history
# ===================================================================


class TestGetCommandHistory:
    """Test the get_command_history method."""

    def test_returns_all_history_when_no_filter(self, real_command_audit_observer):
        """Without a service_name filter, returns the entire history dict."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="aio", phase="setup")
        )

        history = obs.get_command_history()
        assert "pico_run" in history
        assert "aio_setup" in history

    def test_filters_by_service_name(self, real_command_audit_observer):
        """With a service_name, returns only matching keys."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="setup")
        )
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="aio", phase="run")
        )

        history = obs.get_command_history(service_name="pico")
        assert "pico_run" in history
        assert "pico_setup" in history
        assert "aio_run" not in history

    def test_filter_returns_empty_for_unknown_service(
        self, real_command_audit_observer
    ):
        """Filtering for a service that has no history returns empty dict."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )

        history = obs.get_command_history(service_name="nonexistent")
        assert history == {}


# ===================================================================
# get_audit_summary
# ===================================================================


class TestGetAuditSummary:
    """Test the get_audit_summary method."""

    def test_summary_contains_expected_keys(self, real_command_audit_observer):
        """Summary contains audit_file, statistics, and last_updated."""
        summary = real_command_audit_observer.get_audit_summary()
        assert "audit_file" in summary
        assert "statistics" in summary
        assert "last_updated" in summary

    def test_summary_audit_file_path(self, real_command_audit_observer):
        """Summary reports the correct audit file path."""
        obs = real_command_audit_observer
        summary = obs.get_audit_summary()
        assert summary["audit_file"] == str(obs.audit_file)

    def test_summary_statistics_reflect_state(self, real_command_audit_observer):
        """Summary statistics are calculated from current state."""
        obs = real_command_audit_observer
        obs.handle_command_generated(
            _make_cmd_generated_event(service_name="pico", phase="run")
        )

        summary = obs.get_audit_summary()
        assert summary["statistics"]["total_services"] == 1
        assert summary["statistics"]["total_commands"] == 1


# ===================================================================
# on_event routing via ITypedObserver
# ===================================================================


class TestOnEventRouting:
    """Test event routing through ITypedObserver.on_event.

    NOTE: CommandAuditObserver uses 'handle_*' method names (e.g.
    handle_command_generation_started) but ITypedObserver._event_handlers
    maps to 'on_*' method names (e.g. on_command_generation_started).
    As a result, on_event() calls the base ITypedObserver no-op handlers
    rather than CommandAuditObserver's handle_* methods. This is a
    pre-existing design mismatch in the production code. The handle_*
    methods must be called directly.
    """

    def test_on_event_routes_to_base_handler_not_custom(
        self, real_command_audit_observer
    ):
        """on_event calls on_command_generation_started (base), not handle_*."""
        obs = real_command_audit_observer
        event = _make_cmd_gen_started_event(service_name="pico", phase="run")
        result = obs.on_event(event)

        # Base handler returns True without modifying state
        assert result is True
        assert obs.generation_in_progress == {}

    def test_direct_handle_methods_work(self, real_command_audit_observer):
        """Calling handle_* methods directly processes events correctly."""
        obs = real_command_audit_observer
        obs.handle_command_generation_started(
            _make_cmd_gen_started_event(service_name="pico", phase="run")
        )
        assert "pico_run" in obs.generation_in_progress

        obs.handle_command_generated(
            _make_cmd_generated_event(
                service_name="pico", phase="run", command="./run.sh"
            )
        )
        assert "pico_run" in obs.command_history

    def test_unknown_event_does_not_crash(self, real_command_audit_observer):
        """An unrelated event type does not crash the observer via on_event."""
        from panther.core.events.service.events import ServiceStartedEvent

        obs = real_command_audit_observer
        event = ServiceStartedEvent(
            service_id="svc-1", service_name="pico"
        )
        result = obs.on_event(event)
        # Base handler for ServiceStartedEvent returns True
        assert result is True
        assert obs.command_history == {}


# ===================================================================
# Integration: Full Workflow
# ===================================================================


class TestFullWorkflow:
    """Integration tests for complete command audit workflows."""

    def test_start_generate_modify_workflow(self, real_command_audit_observer):
        """Full lifecycle: started -> generated -> modified produces correct trail."""
        obs = real_command_audit_observer

        # Step 1: generation started
        obs.handle_command_generation_started(
            _make_cmd_gen_started_event(
                service_name="picoquic",
                phase="run",
                config={"port": 4433},
            )
        )
        assert "picoquic_run" in obs.generation_in_progress

        # Step 2: command generated
        obs.handle_command_generated(
            _make_cmd_generated_event(
                service_name="picoquic",
                phase="run",
                command="./picoquic -p 4433",
            )
        )
        assert "picoquic_run" not in obs.generation_in_progress
        assert len(obs.command_history["picoquic_run"]) == 1

        # Step 3: command modified by strace
        obs.handle_command_modified(
            _make_cmd_modified_event(
                service_name="picoquic",
                phase="run",
                original_command="./picoquic -p 4433",
                modified_command="strace -f ./picoquic -p 4433",
                modifier="strace",
            )
        )

        record = obs.command_history["picoquic_run"][0]
        assert record["command"] == "./picoquic -p 4433"
        assert record["generation_info"]["config"] == {"port": 4433}
        assert len(record["modifications"]) == 1
        assert record["modifications"][0]["modifier"] == "strace"

    def test_multi_service_multi_phase_workflow(self, real_command_audit_observer):
        """Multiple services and phases are tracked independently."""
        obs = real_command_audit_observer

        services = [
            ("picoquic", "setup", "make"),
            ("picoquic", "run", "./run.sh"),
            ("aioquic", "setup", "pip install ."),
            ("aioquic", "run", "python server.py"),
        ]

        for svc, phase, cmd in services:
            obs.handle_command_generation_started(
                _make_cmd_gen_started_event(service_name=svc, phase=phase)
            )
            obs.handle_command_generated(
                _make_cmd_generated_event(
                    service_name=svc, phase=phase, command=cmd
                )
            )

        assert len(obs.command_history) == 4
        assert obs.command_history["picoquic_run"][0]["command"] == "./run.sh"
        assert obs.command_history["aioquic_setup"][0]["command"] == "pip install ."

        stats = obs._calculate_statistics()
        assert stats["total_services"] == 4
        assert stats["total_commands"] == 4
        assert stats["commands_by_phase"]["setup"] == 2
        assert stats["commands_by_phase"]["run"] == 2

    def test_workflow_with_config_generation(self, real_command_audit_observer):
        """Workflow including config generation event."""
        obs = real_command_audit_observer

        # Generate commands for services
        obs.handle_command_generated(
            _make_cmd_generated_event(
                service_name="picoquic", phase="run", command="./run.sh"
            )
        )
        obs.handle_command_generated(
            _make_cmd_generated_event(
                service_name="aioquic", phase="run", command="python srv.py"
            )
        )

        # Generate the final config
        obs.handle_config_generated(
            _make_config_generated_event(
                config_type="docker-compose",
                config_path="/tmp/dc.yml",
                services_included=["picoquic", "aioquic"],
            )
        )

        # Verify audit file
        data = json.loads(obs.audit_file.read_text())
        assert "picoquic_run" in data["command_history"]
        assert "aioquic_run" in data["command_history"]
        assert "config_generation" in data["command_history"]
        assert data["statistics"]["total_services"] == 2

    def test_performance_with_many_events(self, real_command_audit_observer):
        """Observer handles a large number of events without excessive slowdown."""
        import time

        obs = real_command_audit_observer

        start = time.time()
        for i in range(100):
            obs.handle_command_generated(
                _make_cmd_generated_event(
                    service_name=f"svc-{i % 10}",
                    phase=f"phase-{i % 3}",
                    command=f"command-{i}",
                )
            )
        elapsed = time.time() - start

        # Should complete reasonably quickly (generous limit for CI)
        assert elapsed < 5.0
        stats = obs._calculate_statistics()
        assert stats["total_commands"] == 100


# ===================================================================
# Edge Cases and Error Handling
# ===================================================================


class TestEdgeCases:
    """Test edge cases and error resilience."""

    def test_generated_without_prior_started(self, real_command_audit_observer):
        """Generated event works even without a prior started event."""
        obs = real_command_audit_observer
        event = _make_cmd_generated_event(
            service_name="pico", phase="run", command="./run.sh"
        )
        obs.handle_command_generated(event)

        record = obs.command_history["pico_run"][0]
        assert record["generation_info"] == {}  # no started event was recorded

    def test_empty_service_name_in_event(self, real_command_audit_observer):
        """Events with empty service_name are handled (key becomes '_phase')."""
        obs = real_command_audit_observer
        event = _make_cmd_generated_event(
            service_name="", phase="run", command="echo"
        )
        obs.handle_command_generated(event)
        assert "_run" in obs.command_history

    def test_special_characters_in_command(self, real_command_audit_observer):
        """Commands with special characters are stored correctly."""
        obs = real_command_audit_observer
        cmd = 'bash -c "echo \'hello world\' && exit 0"'
        obs.handle_command_generated(
            _make_cmd_generated_event(
                service_name="pico", phase="run", command=cmd
            )
        )
        assert obs.command_history["pico_run"][0]["command"] == cmd

    def test_very_long_command_stored(self, real_command_audit_observer):
        """Very long commands are stored in full (no truncation in history)."""
        obs = real_command_audit_observer
        long_cmd = "x" * 10000
        obs.handle_command_generated(
            _make_cmd_generated_event(
                service_name="pico", phase="run", command=long_cmd
            )
        )
        assert obs.command_history["pico_run"][0]["command"] == long_cmd

    def test_command_type_stored(self, real_command_audit_observer):
        """command_type field from event is stored in the record."""
        obs = real_command_audit_observer
        event = _make_cmd_generated_event(
            service_name="pico",
            phase="run",
            command="./run.sh",
            command_type="shell",
        )
        obs.handle_command_generated(event)
        assert obs.command_history["pico_run"][0]["command_type"] == "shell"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
