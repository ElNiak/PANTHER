"""Unit tests for TimelineRenderer."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from panther.core.reporting.timeline_renderer import TimelineRenderer

# -- Helpers -----------------------------------------------------------------


def _write_jsonl(path: Path, records: list[dict]) -> Path:
    """Write a list of dicts as a structured.jsonl file.

    Args:
        path: Directory to write into.
        records: List of JSON-serializable dicts.

    Returns:
        Path to the created structured.jsonl file.
    """
    jsonl_path = path / "structured.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, default=str) + "\n")
    return jsonl_path


def _make_record(
    level="INFO",
    message="test message",
    source="logging",
    service_id=None,
    test_id=None,
    phase=None,
    ts="2025-01-15T10:00:00+00:00",
    **extra,
) -> dict:
    """Build a structured log record dict with sensible defaults."""
    rec = {
        "ts": ts,
        "level": level,
        "source": source,
        "message": message,
    }
    if service_id is not None:
        rec["service_id"] = service_id
    if test_id is not None:
        rec["test_id"] = test_id
    if phase is not None:
        rec["phase"] = phase
    rec.update(extra)
    return rec


# Records in non-chronological order to test sorting
SAMPLE_RECORDS = [
    _make_record(
        level="ERROR",
        message="Certificate validation failed",
        service_id="picoquic",
        phase="server",
        ts="2025-01-15T12:00:01.550000+00:00",
    ),
    _make_record(
        level="INFO",
        message="Handshake started",
        service_id="picoquic",
        phase="server",
        ts="2025-01-15T12:00:01.500000+00:00",
    ),
    _make_record(
        level="INFO",
        message="Sending Initial packet",
        service_id="aioquic",
        phase="client",
        ts="2025-01-15T12:00:01.502000+00:00",
    ),
    _make_record(
        level="WARNING",
        message="Retry received",
        service_id="aioquic",
        phase="client",
        test_id="t1",
        ts="2025-01-15T12:00:02.000000+00:00",
    ),
    _make_record(
        level="INFO",
        message="Connection established",
        service_id="picoquic",
        phase="server",
        test_id="t1",
        ts="2025-01-15T12:00:03.000000+00:00",
    ),
]


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture()
def sample_dir(tmp_path):
    """Create a tmp directory with a structured.jsonl containing SAMPLE_RECORDS."""
    _write_jsonl(tmp_path, SAMPLE_RECORDS)
    return tmp_path


@pytest.fixture()
def renderer(sample_dir):
    """Return a TimelineRenderer pointed at the sample directory."""
    return TimelineRenderer(sample_dir)


# -- Tests: render_json ------------------------------------------------------


@pytest.mark.unit
class TestTimelineRendererJson:
    """Tests for render_json output."""

    def test_returns_all_records_sorted(self, renderer):
        """All records are returned in chronological order."""
        entries = renderer.render_json(limit=0)
        assert len(entries) == len(SAMPLE_RECORDS)
        timestamps = [e["ts"] for e in entries]
        assert timestamps == sorted(timestamps)

    def test_first_entry_is_earliest(self, renderer):
        """The first entry has the earliest timestamp."""
        entries = renderer.render_json(limit=0)
        assert entries[0]["message"] == "Handshake started"

    def test_last_entry_is_latest(self, renderer):
        """The last entry has the latest timestamp."""
        entries = renderer.render_json(limit=0)
        assert entries[-1]["message"] == "Connection established"

    def test_limit_caps_results(self, renderer):
        """Limit parameter restricts number of returned entries."""
        entries = renderer.render_json(limit=2)
        assert len(entries) == 2

    def test_limit_zero_returns_all(self, renderer):
        """Limit=0 means unlimited."""
        entries = renderer.render_json(limit=0)
        assert len(entries) == len(SAMPLE_RECORDS)

    def test_default_limit_50(self, renderer):
        """Default limit is 50 (more than our sample, so all returned)."""
        entries = renderer.render_json()
        assert len(entries) == len(SAMPLE_RECORDS)

    def test_entries_are_dicts(self, renderer):
        """Each entry is a dict with expected fields."""
        for entry in renderer.render_json():
            assert isinstance(entry, dict)
            assert "ts" in entry
            assert "level" in entry
            assert "message" in entry


# -- Tests: render_json filtering -------------------------------------------


@pytest.mark.unit
class TestTimelineRendererJsonFiltering:
    """Tests for filtering in render_json."""

    def test_filter_by_service(self, renderer):
        """Filter by service_id returns only that service's entries."""
        entries = renderer.render_json(service="picoquic", limit=0)
        assert len(entries) == 3
        assert all(e["service_id"] == "picoquic" for e in entries)

    def test_filter_by_test(self, renderer):
        """Filter by test_id returns only that test's entries."""
        entries = renderer.render_json(test="t1", limit=0)
        assert len(entries) == 2
        assert all(e["test_id"] == "t1" for e in entries)

    def test_filter_by_time_after(self, renderer):
        """Filter by after time excludes earlier entries."""
        after = datetime(2025, 1, 15, 12, 0, 1, 510000, tzinfo=timezone.utc)
        entries = renderer.render_json(after=after, limit=0)
        # Should include: ERROR (1.55), WARNING (2.0), Connection (3.0)
        assert len(entries) == 3

    def test_filter_by_time_before(self, renderer):
        """Filter by before time excludes later entries."""
        before = datetime(2025, 1, 15, 12, 0, 1, 510000, tzinfo=timezone.utc)
        entries = renderer.render_json(before=before, limit=0)
        # Should include: Handshake (1.5), Sending Initial (1.502)
        assert len(entries) == 2

    def test_combined_filters(self, renderer):
        """Multiple filters apply with AND semantics."""
        entries = renderer.render_json(service="aioquic", test="t1", limit=0)
        assert len(entries) == 1
        assert entries[0]["message"] == "Retry received"


# -- Tests: render_human ----------------------------------------------------


@pytest.mark.unit
class TestTimelineRendererHuman:
    """Tests for render_human output."""

    def test_returns_string(self, renderer):
        """Output is a non-empty string."""
        result = renderer.render_human()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_timestamps(self, renderer):
        """Output contains formatted timestamps."""
        result = renderer.render_human()
        assert "12:00:01.500" in result

    def test_contains_service_labels(self, renderer):
        """Output contains service_id labels."""
        result = renderer.render_human()
        assert "picoquic" in result
        assert "aioquic" in result

    def test_contains_levels(self, renderer):
        """Output contains log level names."""
        result = renderer.render_human()
        assert "ERROR" in result
        assert "INFO" in result

    def test_contains_messages(self, renderer):
        """Output contains the log messages."""
        result = renderer.render_human()
        assert "Handshake started" in result
        assert "Sending Initial packet" in result

    def test_entries_are_chronological(self, renderer):
        """Lines appear in chronological order."""
        result = renderer.render_human()
        lines = result.strip().split("\n")
        handshake_idx = next(i for i, l in enumerate(lines) if "Handshake started" in l)
        sending_idx = next(i for i, l in enumerate(lines) if "Sending Initial" in l)
        error_idx = next(
            i for i, l in enumerate(lines) if "Certificate validation" in l
        )
        assert handshake_idx < sending_idx < error_idx

    def test_empty_results_message(self, tmp_path):
        """Empty results produce a meaningful message."""
        renderer = TimelineRenderer(tmp_path)
        result = renderer.render_human()
        assert result == "(no matching log entries)"

    def test_service_label_includes_phase(self, renderer):
        """Service labels include phase info when available."""
        result = renderer.render_human()
        assert "picoquic(server)" in result
        assert "aioquic(client)" in result

    def test_records_without_service_show_dash(self, tmp_path):
        """Records without service_id show '-' as the label."""
        _write_jsonl(tmp_path, [_make_record(message="global event")])
        r = TimelineRenderer(tmp_path)
        result = r.render_human()
        assert "-" in result


# -- Tests: Edge cases -------------------------------------------------------


@pytest.mark.unit
class TestTimelineRendererEdgeCases:
    """Edge cases for timeline rendering."""

    def test_empty_directory(self, tmp_path):
        """Empty directory yields no entries."""
        r = TimelineRenderer(tmp_path)
        assert r.render_json(limit=0) == []

    def test_nonexistent_directory(self, tmp_path):
        """Nonexistent directory yields no entries."""
        r = TimelineRenderer(tmp_path / "does_not_exist")
        assert r.render_json(limit=0) == []

    def test_records_without_timestamp_sorted_last(self, tmp_path):
        """Records missing ts are placed at the end."""
        records = [
            {"level": "INFO", "message": "no ts"},
            _make_record(message="has ts", ts="2025-01-15T10:00:00+00:00"),
        ]
        _write_jsonl(tmp_path, records)
        r = TimelineRenderer(tmp_path)
        entries = r.render_json(limit=0)
        assert entries[0]["message"] == "has ts"
        assert entries[1]["message"] == "no ts"

    def test_malformed_ts_sorted_last(self, tmp_path):
        """Records with bad ts are placed at the end."""
        records = [
            {"level": "INFO", "message": "bad ts", "ts": "not-a-date"},
            _make_record(message="good ts", ts="2025-01-15T10:00:00+00:00"),
        ]
        _write_jsonl(tmp_path, records)
        r = TimelineRenderer(tmp_path)
        entries = r.render_json(limit=0)
        assert entries[0]["message"] == "good ts"
        assert entries[1]["message"] == "bad ts"
