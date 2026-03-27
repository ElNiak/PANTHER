"""Log query engine for structured JSONL files.

Provides streaming, generator-based filtering of structured.jsonl log files
produced by StructuredJsonFormatter and EventStreamRecorder. Records are
read one line at a time so that arbitrarily large files never need to be
loaded into memory entirely.

Typical usage::

    from panther.core.reporting.log_query_engine import LogQueryEngine, LogFilter

    engine = LogQueryEngine(Path("outputs/2024-01-01/exp1"))
    filt = LogFilter(levels={"ERROR", "CRITICAL"}, services={"picoquic"})
    for record in engine.query(filt, limit=50):
        print(record["message"])
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, Optional, Set


@dataclass
class LogFilter:
    """Composable filter specification for structured log records.

    All fields are optional. When multiple fields are set, they are
    combined with AND semantics: a record must match every non-None
    filter to be included.

    Attributes:
        levels: Filter by log level name (e.g. ``{"ERROR", "WARNING"}``).
        services: Filter by ``service_id`` field.
        tests: Filter by ``test_id`` field.
        phases: Filter by ``phase`` field.
        after: Include records with ``ts`` at or after this datetime.
        before: Include records with ``ts`` strictly before this datetime.
        correlation_id: Match records with this ``correlation_id``.
        message_pattern: Regex applied to the ``message`` field.
        sources: Filter by ``source`` (``"logging"`` or ``"event"``).
    """

    levels: Optional[Set[str]] = None
    services: Optional[Set[str]] = None
    tests: Optional[Set[str]] = None
    phases: Optional[Set[str]] = None
    after: Optional[datetime] = None
    before: Optional[datetime] = None
    correlation_id: Optional[str] = None
    message_pattern: Optional[re.Pattern] = None
    sources: Optional[Set[str]] = None


class LogQueryEngine:
    """Streaming query engine for structured JSONL log files.

    Scans all ``structured.jsonl`` files under a directory and yields
    matching records one at a time.  The engine never loads the full
    file contents into memory, making it suitable for large experiment
    outputs.

    Args:
        directory: Root directory to search for ``structured.jsonl`` files.
            The engine walks the directory tree recursively.
    """

    JSONL_FILENAME = "structured.jsonl"

    def __init__(self, directory: Path):
        """Initialize the query engine.

        Args:
            directory: Root directory to search for ``structured.jsonl`` files.
        """
        self._directory = Path(directory)

    # -- public API ----------------------------------------------------------

    def query(
        self, log_filter: Optional[LogFilter] = None, limit: int = 0
    ) -> Iterator[Dict]:
        """Yield log records matching the given filter.

        Args:
            log_filter: Filter criteria.  ``None`` means match everything.
            limit: Maximum number of records to yield.  0 means unlimited.

        Yields:
            Parsed JSON dictionaries, one per matching JSONL line.
        """
        if log_filter is None:
            log_filter = LogFilter()

        emitted = 0
        for record in self._iter_records():
            if self._matches(record, log_filter):
                yield record
                emitted += 1
                if limit and emitted >= limit:
                    return

    def count(self, log_filter: Optional[LogFilter] = None) -> Dict[str, int]:
        """Count matching records grouped by log level.

        Args:
            log_filter: Filter criteria.  ``None`` means count everything.

        Returns:
            Mapping from level name to count of matching records.
        """
        counts: Dict[str, int] = {}
        for record in self.query(log_filter):
            level = record.get("level", "UNKNOWN")
            counts[level] = counts.get(level, 0) + 1
        return counts

    # -- private helpers -----------------------------------------------------

    def _find_jsonl_files(self) -> Iterator[Path]:
        """Discover structured.jsonl files under the root directory.

        Yields:
            Paths to each ``structured.jsonl`` file found.
        """
        if not self._directory.is_dir():
            return
        # Check root directory first
        root_file = self._directory / self.JSONL_FILENAME
        if root_file.is_file():
            yield root_file
        # Then walk subdirectories
        for path in sorted(self._directory.rglob(self.JSONL_FILENAME)):
            if path != root_file and path.is_file():
                yield path

    def _iter_records(self) -> Iterator[Dict]:
        """Stream all JSONL records from discovered files.

        Malformed lines are silently skipped so that a single corrupt
        line does not abort the entire query.

        Yields:
            Parsed JSON dictionaries.
        """
        for jsonl_path in self._find_jsonl_files():
            yield from self._iter_file(jsonl_path)

    @staticmethod
    def _iter_file(path: Path) -> Iterator[Dict]:
        """Stream records from a single JSONL file.

        Args:
            path: Path to the JSONL file.

        Yields:
            Parsed JSON dictionaries, one per valid line.
        """
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            return

    @staticmethod
    def _matches(record: Dict, log_filter: LogFilter) -> bool:
        """Test whether a record passes all filter criteria.

        Args:
            record: Parsed JSONL record.
            log_filter: Filter to apply.

        Returns:
            True if the record matches every non-None filter field.
        """
        if log_filter.levels is not None:
            if record.get("level") not in log_filter.levels:
                return False

        if log_filter.services is not None:
            if record.get("service_id") not in log_filter.services:
                return False

        if log_filter.tests is not None:
            if record.get("test_id") not in log_filter.tests:
                return False

        if log_filter.phases is not None:
            if record.get("phase") not in log_filter.phases:
                return False

        if log_filter.sources is not None:
            if record.get("source") not in log_filter.sources:
                return False

        if log_filter.correlation_id is not None:
            if record.get("correlation_id") != log_filter.correlation_id:
                return False

        if log_filter.message_pattern is not None:
            message = record.get("message", "")
            if not log_filter.message_pattern.search(message):
                return False

        # Time-range filters
        if log_filter.after is not None or log_filter.before is not None:
            ts_str = record.get("ts")
            if ts_str is None:
                return False
            try:
                ts = datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                return False
            if log_filter.after is not None and ts < log_filter.after:
                return False
            if log_filter.before is not None and ts >= log_filter.before:
                return False

        return True
