"""Unit tests for LogQueryEngine and LogFilter."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from panther.core.reporting.log_query_engine import LogFilter, LogQueryEngine

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
    correlation_id=None,
    ts="2025-01-15T10:00:00+00:00",
    **extra,
) -> dict:
    """Build a structured log record dict with sensible defaults."""
    rec = {
        "ts": ts,
        "level": level,
        "level_num": {
            "DEBUG": 10,
            "INFO": 20,
            "EVENT": 25,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
        }.get(level, 20),
        "source": source,
        "message": message,
    }
    if service_id is not None:
        rec["service_id"] = service_id
    if test_id is not None:
        rec["test_id"] = test_id
    if phase is not None:
        rec["phase"] = phase
    if correlation_id is not None:
        rec["correlation_id"] = correlation_id
    rec.update(extra)
    return rec


SAMPLE_RECORDS = [
    _make_record(
        level="INFO",
        message="Starting experiment",
        phase="init",
        ts="2025-01-15T10:00:00+00:00",
    ),
    _make_record(
        level="DEBUG",
        message="Loading config",
        phase="init",
        ts="2025-01-15T10:00:01+00:00",
    ),
    _make_record(
        level="INFO",
        message="Deploying containers",
        phase="deploy",
        service_id="picoquic",
        ts="2025-01-15T10:01:00+00:00",
    ),
    _make_record(
        level="WARNING",
        message="Slow container start",
        phase="deploy",
        service_id="picoquic",
        ts="2025-01-15T10:01:30+00:00",
    ),
    _make_record(
        level="ERROR",
        message="Connection refused",
        phase="test",
        service_id="aioquic",
        test_id="t1",
        ts="2025-01-15T10:02:00+00:00",
    ),
    _make_record(
        level="CRITICAL",
        message="Out of memory",
        phase="test",
        service_id="aioquic",
        test_id="t1",
        ts="2025-01-15T10:02:05+00:00",
    ),
    _make_record(
        level="EVENT",
        message="test.started",
        source="event",
        test_id="t1",
        phase="test",
        ts="2025-01-15T10:01:55+00:00",
    ),
    _make_record(
        level="INFO",
        message="Test completed",
        phase="teardown",
        test_id="t1",
        correlation_id="corr-42",
        ts="2025-01-15T10:03:00+00:00",
    ),
]


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture()
def sample_dir(tmp_path):
    """Create a tmp directory with a structured.jsonl containing SAMPLE_RECORDS."""
    _write_jsonl(tmp_path, SAMPLE_RECORDS)
    return tmp_path


@pytest.fixture()
def engine(sample_dir):
    """Return a LogQueryEngine pointed at the sample directory."""
    return LogQueryEngine(sample_dir)


# -- Tests: Basic query ------------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineBasicQuery:
    """Basic query / iteration tests."""

    def test_query_all_returns_every_record(self, engine):
        """Querying with no filter yields all records."""
        results = list(engine.query())
        assert len(results) == len(SAMPLE_RECORDS)

    def test_query_returns_dicts(self, engine):
        """Each yielded item is a dict."""
        for record in engine.query():
            assert isinstance(record, dict)
            assert "message" in record

    def test_limit_caps_results(self, engine):
        """Limit parameter truncates the output."""
        results = list(engine.query(limit=3))
        assert len(results) == 3

    def test_limit_zero_means_unlimited(self, engine):
        """Limit=0 (default) returns all records."""
        results = list(engine.query(limit=0))
        assert len(results) == len(SAMPLE_RECORDS)


# -- Tests: Level filter -----------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineLevelFilter:
    """Filtering by log level."""

    def test_single_level(self, engine):
        """Filter by a single level."""
        filt = LogFilter(levels={"ERROR"})
        results = list(engine.query(filt))
        assert all(r["level"] == "ERROR" for r in results)
        assert len(results) == 1

    def test_multiple_levels(self, engine):
        """Filter by multiple levels."""
        filt = LogFilter(levels={"ERROR", "CRITICAL"})
        results = list(engine.query(filt))
        assert len(results) == 2
        assert {r["level"] for r in results} == {"ERROR", "CRITICAL"}

    def test_level_no_match(self, engine):
        """Nonexistent level returns no results."""
        filt = LogFilter(levels={"TRACE"})
        results = list(engine.query(filt))
        assert len(results) == 0


# -- Tests: Service filter ---------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineServiceFilter:
    """Filtering by service_id."""

    def test_service_filter(self, engine):
        """Matching a known service_id."""
        filt = LogFilter(services={"picoquic"})
        results = list(engine.query(filt))
        assert len(results) == 2
        assert all(r["service_id"] == "picoquic" for r in results)

    def test_service_filter_no_match(self, engine):
        """Unknown service_id returns no records."""
        filt = LogFilter(services={"nonexistent"})
        results = list(engine.query(filt))
        assert len(results) == 0


# -- Tests: Test filter ------------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineTestFilter:
    """Filtering by test_id."""

    def test_test_filter(self, engine):
        """Filter by test_id."""
        filt = LogFilter(tests={"t1"})
        results = list(engine.query(filt))
        assert len(results) == 4  # ERROR, CRITICAL, EVENT, INFO with corr-42
        assert all(r.get("test_id") == "t1" for r in results)


# -- Tests: Phase filter -----------------------------------------------------


@pytest.mark.unit
class TestLogQueryEnginePhaseFilter:
    """Filtering by phase."""

    def test_phase_filter(self, engine):
        """Filter by phase name."""
        filt = LogFilter(phases={"init"})
        results = list(engine.query(filt))
        assert len(results) == 2
        assert all(r["phase"] == "init" for r in results)


# -- Tests: Source filter ----------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineSourceFilter:
    """Filtering by source."""

    def test_source_logging(self, engine):
        """Filter for logging-sourced records."""
        filt = LogFilter(sources={"logging"})
        results = list(engine.query(filt))
        assert all(r["source"] == "logging" for r in results)

    def test_source_event(self, engine):
        """Filter for event-sourced records."""
        filt = LogFilter(sources={"event"})
        results = list(engine.query(filt))
        assert len(results) == 1
        assert results[0]["source"] == "event"


# -- Tests: Correlation ID --------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineCorrelationFilter:
    """Filtering by correlation_id."""

    def test_correlation_id_match(self, engine):
        """Filter by a known correlation_id."""
        filt = LogFilter(correlation_id="corr-42")
        results = list(engine.query(filt))
        assert len(results) == 1
        assert results[0]["correlation_id"] == "corr-42"

    def test_correlation_id_no_match(self, engine):
        """Unknown correlation_id returns no records."""
        filt = LogFilter(correlation_id="nonexistent")
        results = list(engine.query(filt))
        assert len(results) == 0


# -- Tests: Message pattern --------------------------------------------------


@pytest.mark.unit
class TestLogQueryEnginePatternFilter:
    """Filtering by message regex."""

    def test_pattern_match(self, engine):
        """Regex matches the message field."""
        filt = LogFilter(message_pattern=re.compile(r"(?i)connection"))
        results = list(engine.query(filt))
        assert len(results) == 1
        assert "Connection" in results[0]["message"]

    def test_pattern_no_match(self, engine):
        """Regex that matches nothing returns empty."""
        filt = LogFilter(message_pattern=re.compile(r"xyzzy_no_match"))
        results = list(engine.query(filt))
        assert len(results) == 0


# -- Tests: Time-range filter ------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineTimeFilter:
    """Filtering by time range."""

    def test_after_filter(self, engine):
        """Records at or after the given time are included."""
        filt = LogFilter(after=datetime(2025, 1, 15, 10, 2, 0, tzinfo=timezone.utc))
        results = list(engine.query(filt))
        # Should include: ERROR (10:02:00), CRITICAL (10:02:05), INFO (10:03:00)
        assert len(results) == 3

    def test_before_filter(self, engine):
        """Records strictly before the given time are included."""
        filt = LogFilter(before=datetime(2025, 1, 15, 10, 1, 0, tzinfo=timezone.utc))
        results = list(engine.query(filt))
        # Should include: INFO (10:00:00), DEBUG (10:00:01)
        assert len(results) == 2

    def test_after_and_before(self, engine):
        """Combined after+before creates a time window."""
        filt = LogFilter(
            after=datetime(2025, 1, 15, 10, 1, 0, tzinfo=timezone.utc),
            before=datetime(2025, 1, 15, 10, 2, 0, tzinfo=timezone.utc),
        )
        results = list(engine.query(filt))
        # Should include: INFO (10:01:00), WARNING (10:01:30), EVENT (10:01:55)
        assert len(results) == 3


# -- Tests: Combined filters ------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineCombinedFilters:
    """Multiple filters combined with AND semantics."""

    def test_level_and_service(self, engine):
        """Level + service narrows results."""
        filt = LogFilter(levels={"ERROR", "CRITICAL"}, services={"aioquic"})
        results = list(engine.query(filt))
        assert len(results) == 2
        assert all(r["service_id"] == "aioquic" for r in results)
        assert {r["level"] for r in results} == {"ERROR", "CRITICAL"}

    def test_level_and_phase(self, engine):
        """Level + phase filter."""
        filt = LogFilter(levels={"INFO"}, phases={"init"})
        results = list(engine.query(filt))
        assert len(results) == 1
        assert results[0]["message"] == "Starting experiment"

    def test_service_and_time(self, engine):
        """Service + time window."""
        filt = LogFilter(
            services={"picoquic"},
            after=datetime(2025, 1, 15, 10, 1, 0, tzinfo=timezone.utc),
            before=datetime(2025, 1, 15, 10, 1, 31, tzinfo=timezone.utc),
        )
        results = list(engine.query(filt))
        assert len(results) == 2  # INFO deploy + WARNING deploy


# -- Tests: Count method -----------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineCount:
    """The count() aggregation method."""

    def test_count_all(self, engine):
        """Count all records grouped by level."""
        counts = engine.count()
        assert counts["INFO"] == 3
        assert counts["DEBUG"] == 1
        assert counts["WARNING"] == 1
        assert counts["ERROR"] == 1
        assert counts["CRITICAL"] == 1
        assert counts["EVENT"] == 1

    def test_count_with_filter(self, engine):
        """Count with a filter applied."""
        filt = LogFilter(services={"aioquic"})
        counts = engine.count(filt)
        assert counts == {"ERROR": 1, "CRITICAL": 1}


# -- Tests: File discovery ---------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineFileDiscovery:
    """JSONL file discovery across directory trees."""

    def test_empty_directory(self, tmp_path):
        """Empty directory yields no records."""
        engine = LogQueryEngine(tmp_path)
        results = list(engine.query())
        assert len(results) == 0

    def test_nonexistent_directory(self, tmp_path):
        """Nonexistent directory yields no records."""
        engine = LogQueryEngine(tmp_path / "does_not_exist")
        results = list(engine.query())
        assert len(results) == 0

    def test_nested_jsonl_files(self, tmp_path):
        """Files in subdirectories are discovered."""
        sub1 = tmp_path / "sub1"
        sub2 = tmp_path / "sub2"
        sub1.mkdir()
        sub2.mkdir()
        _write_jsonl(sub1, [_make_record(message="from sub1")])
        _write_jsonl(sub2, [_make_record(message="from sub2")])

        engine = LogQueryEngine(tmp_path)
        results = list(engine.query())
        messages = {r["message"] for r in results}
        assert "from sub1" in messages
        assert "from sub2" in messages

    def test_root_and_nested(self, tmp_path):
        """Both root-level and nested files are read."""
        _write_jsonl(tmp_path, [_make_record(message="root")])
        sub = tmp_path / "sub"
        sub.mkdir()
        _write_jsonl(sub, [_make_record(message="nested")])

        engine = LogQueryEngine(tmp_path)
        results = list(engine.query())
        messages = {r["message"] for r in results}
        assert "root" in messages
        assert "nested" in messages


# -- Tests: Malformed input --------------------------------------------------


@pytest.mark.unit
class TestLogQueryEngineMalformedInput:
    """Graceful handling of bad data."""

    def test_malformed_json_lines_skipped(self, tmp_path):
        """Lines that are not valid JSON are silently skipped."""
        jsonl_path = tmp_path / "structured.jsonl"
        with open(jsonl_path, "w") as fh:
            fh.write('{"level": "INFO", "message": "good"}\n')
            fh.write("this is not json\n")
            fh.write('{"level": "ERROR", "message": "also good"}\n')

        engine = LogQueryEngine(tmp_path)
        results = list(engine.query())
        assert len(results) == 2

    def test_empty_lines_skipped(self, tmp_path):
        """Empty and whitespace-only lines are skipped."""
        jsonl_path = tmp_path / "structured.jsonl"
        with open(jsonl_path, "w") as fh:
            fh.write('{"level": "INFO", "message": "one"}\n')
            fh.write("\n")
            fh.write("   \n")
            fh.write('{"level": "INFO", "message": "two"}\n')

        engine = LogQueryEngine(tmp_path)
        results = list(engine.query())
        assert len(results) == 2

    def test_missing_ts_with_time_filter(self, tmp_path):
        """Records without ts field are excluded when time filters are active."""
        _write_jsonl(tmp_path, [{"level": "INFO", "message": "no timestamp"}])
        engine = LogQueryEngine(tmp_path)
        filt = LogFilter(after=datetime(2025, 1, 1, tzinfo=timezone.utc))
        results = list(engine.query(filt))
        assert len(results) == 0

    def test_bad_ts_with_time_filter(self, tmp_path):
        """Records with unparseable ts are excluded when time filters are active."""
        _write_jsonl(
            tmp_path, [{"level": "INFO", "message": "bad ts", "ts": "not-a-date"}]
        )
        engine = LogQueryEngine(tmp_path)
        filt = LogFilter(after=datetime(2025, 1, 1, tzinfo=timezone.utc))
        results = list(engine.query(filt))
        assert len(results) == 0


# -- Tests: LogFilter dataclass ----------------------------------------------


@pytest.mark.unit
class TestLogFilter:
    """LogFilter dataclass behavior."""

    def test_default_all_none(self):
        """Default LogFilter has all fields None."""
        filt = LogFilter()
        assert filt.levels is None
        assert filt.services is None
        assert filt.tests is None
        assert filt.phases is None
        assert filt.after is None
        assert filt.before is None
        assert filt.correlation_id is None
        assert filt.message_pattern is None
        assert filt.sources is None

    def test_custom_fields(self):
        """LogFilter accepts custom values."""
        pattern = re.compile(r"error")
        filt = LogFilter(
            levels={"ERROR"},
            services={"svc-1"},
            tests={"t-1"},
            phases={"init"},
            after=datetime(2025, 1, 1, tzinfo=timezone.utc),
            before=datetime(2025, 12, 31, tzinfo=timezone.utc),
            correlation_id="corr-1",
            message_pattern=pattern,
            sources={"logging"},
        )
        assert filt.levels == {"ERROR"}
        assert filt.correlation_id == "corr-1"
        assert filt.message_pattern is pattern
