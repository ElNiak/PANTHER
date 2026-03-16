"""Unit tests for FailurePattern, RootCauseAnalyzer, and RootCause."""

import json
import re
from pathlib import Path

import pytest

from panther.core.reporting.failure_patterns import (
    BUILTIN_PATTERNS,
    FailurePattern,
    get_pattern_by_name,
)
from panther.core.reporting.root_cause_analyzer import RootCause, RootCauseAnalyzer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_jsonl(path: Path, records: list) -> Path:
    """Write records as structured.jsonl.

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
    level_num=20,
    message="test message",
    source="logging",
    service_id=None,
    test_id=None,
    event_type=None,
    ts="2025-01-15T10:00:00+00:00",
    **extra,
) -> dict:
    """Build a structured log record with sensible defaults."""
    rec = {
        "ts": ts,
        "level": level,
        "level_num": level_num,
        "source": source,
        "message": message,
    }
    if service_id is not None:
        rec["service_id"] = service_id
    if test_id is not None:
        rec["test_id"] = test_id
    if event_type is not None:
        rec["event_type"] = event_type
    rec.update(extra)
    return rec


# ---------------------------------------------------------------------------
# FailurePattern tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailurePattern:
    """Tests for the FailurePattern dataclass."""

    def test_matches_message_positive(self):
        """Pattern matches when message contains a listed regex."""
        pattern = FailurePattern(
            name="test",
            description="test",
            event_types=(),
            message_patterns=(r"docker\s+build\s+fail",),
            category="docker_build",
            suggestion="fix it",
            severity="critical",
        )
        assert pattern.matches_message("Error: docker build failed") is True

    def test_matches_message_negative(self):
        """Pattern does not match unrelated messages."""
        pattern = FailurePattern(
            name="test",
            description="test",
            event_types=(),
            message_patterns=(r"docker\s+build\s+fail",),
            category="docker_build",
            suggestion="fix it",
            severity="critical",
        )
        assert pattern.matches_message("Everything is fine") is False

    def test_matches_message_empty(self):
        """Empty message never matches."""
        pattern = FailurePattern(
            name="test",
            description="test",
            event_types=(),
            message_patterns=(r"anything",),
            category="docker_build",
            suggestion="fix it",
            severity="critical",
        )
        assert pattern.matches_message("") is False

    def test_matches_event_type(self):
        """Event type matching works."""
        pattern = FailurePattern(
            name="test",
            description="test",
            event_types=("service.error", "environment.error"),
            message_patterns=(),
            category="docker_build",
            suggestion="fix it",
            severity="critical",
        )
        assert pattern.matches_event_type("service.error") is True
        assert pattern.matches_event_type("service.started") is False

    def test_matches_record_both(self):
        """Record matching both event_type and message scores high."""
        pattern = FailurePattern(
            name="test",
            description="test",
            event_types=("service.error",),
            message_patterns=(r"docker.*fail",),
            category="docker_build",
            suggestion="fix it",
            severity="critical",
        )
        record = {
            "message": "docker build failed",
            "event_type": "service.error",
        }
        score = pattern.matches(record)
        assert score >= 0.8

    def test_matches_record_message_only(self):
        """Record matching only message scores moderately."""
        pattern = FailurePattern(
            name="test",
            description="test",
            event_types=("service.error",),
            message_patterns=(r"docker.*fail",),
            category="docker_build",
            suggestion="fix it",
            severity="critical",
        )
        record = {"message": "docker build failed", "event_type": ""}
        score = pattern.matches(record)
        assert 0.3 < score < 0.6

    def test_matches_record_no_match(self):
        """Record with no match returns 0.0."""
        pattern = FailurePattern(
            name="test",
            description="test",
            event_types=("service.error",),
            message_patterns=(r"docker.*fail",),
            category="docker_build",
            suggestion="fix it",
            severity="critical",
        )
        record = {"message": "all good", "event_type": "service.started"}
        assert pattern.matches(record) == 0.0

    def test_matches_record_category_bonus(self):
        """Category agreement adds a confidence bonus."""
        pattern = FailurePattern(
            name="test",
            description="test",
            event_types=("service.error",),
            message_patterns=(r"docker.*fail",),
            category="docker_build",
            suggestion="fix it",
            severity="critical",
        )
        record_with_cat = {
            "message": "docker build failed",
            "event_type": "service.error",
            "category": "docker_build",
        }
        record_without_cat = {
            "message": "docker build failed",
            "event_type": "service.error",
        }
        assert pattern.matches(record_with_cat) > pattern.matches(record_without_cat)


@pytest.mark.unit
class TestFailurePatternCatalog:
    """Tests for the built-in pattern catalog."""

    def test_builtin_patterns_not_empty(self):
        """The catalog contains at least the 8 declared patterns."""
        assert len(BUILTIN_PATTERNS) >= 8

    def test_all_patterns_have_required_fields(self):
        """Every pattern has non-empty name, description, suggestion, severity."""
        for p in BUILTIN_PATTERNS:
            assert p.name, f"Pattern missing name: {p}"
            assert p.description, f"Pattern missing description: {p.name}"
            assert p.suggestion, f"Pattern missing suggestion: {p.name}"
            assert p.severity in (
                "critical",
                "high",
                "medium",
                "low",
            ), f"Invalid severity for {p.name}: {p.severity}"

    def test_get_pattern_by_name_found(self):
        """get_pattern_by_name returns the correct pattern."""
        p = get_pattern_by_name("docker_build_failure")
        assert p is not None
        assert p.name == "docker_build_failure"

    def test_get_pattern_by_name_not_found(self):
        """get_pattern_by_name returns None for unknown names."""
        assert get_pattern_by_name("nonexistent_pattern") is None

    @pytest.mark.parametrize(
        "name,test_message",
        [
            ("docker_build_failure", "Error: docker build failed for image xyz"),
            ("certificate_error", "SSL certificate validation error"),
            ("ivy_compilation_timeout", "ivy compilation timed out after 300s"),
            ("port_conflict", "port 4433 already in use"),
            ("segfault", "Process received SIGSEGV"),
            ("oom_killed", "Container OOM killed"),
            ("timeout_cascade", "Connection timed out"),
            ("compilation_failure", "make: compilation error in src/main.c"),
        ],
    )
    def test_builtin_pattern_matches_expected_message(self, name, test_message):
        """Each built-in pattern matches its intended message."""
        pattern = get_pattern_by_name(name)
        assert pattern is not None, f"Pattern {name} not found"
        assert pattern.matches_message(
            test_message
        ), f"Pattern {name} did not match: {test_message}"


# ---------------------------------------------------------------------------
# RootCause tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRootCause:
    """Tests for the RootCause dataclass."""

    def test_to_dict_serializable(self):
        """to_dict produces a JSON-serializable dict."""
        cause = RootCause(
            rank=1,
            category="docker_build",
            pattern_name="docker_build_failure",
            event={"ts": "2025-01-15T10:00:00", "level": "ERROR", "message": "fail"},
            suggestion="fix it",
            log_excerpt=["line1", "line2"],
            confidence=0.85,
        )
        d = cause.to_dict()
        # Should be JSON-serializable
        serialized = json.dumps(d)
        assert '"rank": 1' in serialized
        assert d["confidence"] == 0.85
        assert d["pattern_name"] == "docker_build_failure"

    def test_to_dict_trims_event(self):
        """to_dict only keeps key fields from the event."""
        cause = RootCause(
            rank=1,
            category="test",
            pattern_name="test",
            event={
                "ts": "2025-01-15T10:00:00",
                "level": "ERROR",
                "message": "boom",
                "extra_field": "should_be_dropped",
                "service_id": "svc1",
            },
            suggestion="",
            confidence=0.5,
        )
        d = cause.to_dict()
        assert "extra_field" not in d["event"]
        assert d["event"]["service_id"] == "svc1"


# ---------------------------------------------------------------------------
# RootCauseAnalyzer tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRootCauseAnalyzerNoErrors:
    """Analyzer behavior when there are no errors."""

    def test_empty_directory(self, tmp_path):
        """Empty directory produces no root causes."""
        analyzer = RootCauseAnalyzer(tmp_path)
        assert analyzer.analyze() == []

    def test_only_info_records(self, tmp_path):
        """Directory with only INFO records produces no root causes."""
        _write_jsonl(
            tmp_path,
            [
                _make_record(level="INFO", message="Starting experiment"),
                _make_record(level="INFO", message="Test completed"),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path)
        assert analyzer.analyze() == []


@pytest.mark.unit
class TestRootCauseAnalyzerMatching:
    """Analyzer pattern matching and ranking."""

    def test_single_error_matches_pattern(self, tmp_path):
        """A single docker build error is matched to the correct pattern."""
        _write_jsonl(
            tmp_path,
            [
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="docker build failed for image panther-picoquic",
                    service_id="picoquic",
                    test_id="test1",
                    ts="2025-01-15T10:01:00+00:00",
                ),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path)
        causes = analyzer.analyze()

        assert len(causes) >= 1
        top = causes[0]
        assert top.pattern_name == "docker_build_failure"
        assert top.rank == 1
        assert top.confidence > 0.0

    def test_multiple_errors_ranked_by_confidence(self, tmp_path):
        """Multiple errors produce ranked findings with the best match first."""
        _write_jsonl(
            tmp_path,
            [
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="port 4433 already in use",
                    service_id="picoquic",
                    test_id="test1",
                    ts="2025-01-15T10:00:00+00:00",
                ),
                _make_record(
                    level="CRITICAL",
                    level_num=50,
                    message="Container OOM killed",
                    service_id="aioquic",
                    test_id="test2",
                    ts="2025-01-15T10:01:00+00:00",
                ),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path)
        causes = analyzer.analyze()

        assert len(causes) == 2
        # Both should have matched known patterns
        pattern_names = {c.pattern_name for c in causes}
        assert "port_conflict" in pattern_names
        assert "oom_killed" in pattern_names
        # Ranks should be 1 and 2
        assert {c.rank for c in causes} == {1, 2}

    def test_unmatched_error_still_reported(self, tmp_path):
        """Errors that match no pattern are reported as 'unmatched'."""
        _write_jsonl(
            tmp_path,
            [
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="Something completely unexpected happened",
                    test_id="test1",
                    ts="2025-01-15T10:00:00+00:00",
                ),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path)
        causes = analyzer.analyze()

        assert len(causes) == 1
        assert causes[0].pattern_name == "unmatched"
        assert causes[0].confidence < 0.2

    def test_event_source_errors_collected(self, tmp_path):
        """Event-source records with error keywords are included."""
        _write_jsonl(
            tmp_path,
            [
                _make_record(
                    level="EVENT",
                    level_num=25,
                    message="service.error",
                    source="event",
                    event_type="service.error",
                    service_id="picoquic",
                    test_id="test1",
                    ts="2025-01-15T10:00:00+00:00",
                ),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path)
        causes = analyzer.analyze()

        # The event should be collected (it has "error" in message)
        assert len(causes) >= 1

    def test_grouping_by_test_id(self, tmp_path):
        """Errors from different tests produce separate root causes."""
        _write_jsonl(
            tmp_path,
            [
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="docker build failed",
                    test_id="test1",
                    ts="2025-01-15T10:00:00+00:00",
                ),
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="SIGSEGV received",
                    test_id="test2",
                    ts="2025-01-15T10:01:00+00:00",
                ),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path)
        causes = analyzer.analyze()

        assert len(causes) == 2
        pattern_names = {c.pattern_name for c in causes}
        assert "docker_build_failure" in pattern_names
        assert "segfault" in pattern_names


@pytest.mark.unit
class TestRootCauseAnalyzerExcerpts:
    """Log excerpt extraction."""

    def test_excerpt_contains_error_lines(self, tmp_path):
        """Log excerpt includes ERROR-level messages from the same service."""
        _write_jsonl(
            tmp_path,
            [
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="docker build failed for image",
                    service_id="picoquic",
                    test_id="test1",
                    ts="2025-01-15T10:00:00+00:00",
                ),
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="COPY failed: file not found",
                    service_id="picoquic",
                    test_id="test1",
                    ts="2025-01-15T10:00:01+00:00",
                ),
                _make_record(
                    level="INFO",
                    level_num=20,
                    message="This should not appear in excerpt",
                    service_id="picoquic",
                    test_id="test1",
                    ts="2025-01-15T10:00:02+00:00",
                ),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path, max_excerpt_lines=5)
        causes = analyzer.analyze()

        assert len(causes) == 1
        # Excerpt should have the ERROR messages
        assert len(causes[0].log_excerpt) >= 1
        assert any(
            "COPY failed" in line or "docker build" in line
            for line in causes[0].log_excerpt
        )

    def test_excerpt_capped_at_max(self, tmp_path):
        """Excerpt is capped at max_excerpt_lines."""
        records = []
        for i in range(10):
            records.append(
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message=f"Error line {i}",
                    service_id="svc",
                    test_id="test1",
                    ts=f"2025-01-15T10:00:{i:02d}+00:00",
                )
            )
        _write_jsonl(tmp_path, records)

        analyzer = RootCauseAnalyzer(tmp_path, max_excerpt_lines=3)
        causes = analyzer.analyze()

        assert len(causes) == 1
        assert len(causes[0].log_excerpt) <= 3


@pytest.mark.unit
class TestRootCauseAnalyzerSerialization:
    """analyze_as_dicts convenience method."""

    def test_analyze_as_dicts(self, tmp_path):
        """analyze_as_dicts returns JSON-serializable dicts."""
        _write_jsonl(
            tmp_path,
            [
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="Connection timed out",
                    test_id="test1",
                    ts="2025-01-15T10:00:00+00:00",
                ),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path)
        dicts = analyzer.analyze_as_dicts()

        assert len(dicts) >= 1
        # Should be JSON-serializable
        serialized = json.dumps(dicts)
        assert "rank" in serialized

    def test_analyze_as_dicts_empty(self, tmp_path):
        """analyze_as_dicts returns empty list when no errors."""
        analyzer = RootCauseAnalyzer(tmp_path)
        assert analyzer.analyze_as_dicts() == []


@pytest.mark.unit
class TestRootCauseAnalyzerCustomPatterns:
    """Custom pattern injection."""

    def test_custom_pattern_used(self, tmp_path):
        """A custom pattern takes precedence when it matches."""
        custom = FailurePattern(
            name="custom_crash",
            description="Custom crash pattern",
            event_types=("service.error",),
            message_patterns=(r"custom_magic_word",),
            category="custom",
            suggestion="Do the custom thing",
            severity="high",
        )
        _write_jsonl(
            tmp_path,
            [
                _make_record(
                    level="ERROR",
                    level_num=40,
                    message="custom_magic_word occurred",
                    test_id="test1",
                    ts="2025-01-15T10:00:00+00:00",
                ),
            ],
        )
        analyzer = RootCauseAnalyzer(tmp_path, patterns=[custom])
        causes = analyzer.analyze()

        assert len(causes) == 1
        assert causes[0].pattern_name == "custom_crash"
        assert causes[0].suggestion == "Do the custom thing"
