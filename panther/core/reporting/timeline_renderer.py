"""Timeline renderer for correlated experiment log entries.

Reads structured JSONL log files via LogQueryEngine and renders them as
chronologically sorted, service-grouped timelines. Supports both
machine-readable JSON output and human-readable swimlane text.

Typical usage::

    from panther.core.reporting.timeline_renderer import TimelineRenderer

    renderer = TimelineRenderer(Path("outputs/2024-01-01/exp1"))
    # Machine-readable
    entries = renderer.render_json(limit=50)
    # Human-readable swimlane
    print(renderer.render_human(limit=50))
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from panther.core.reporting.log_query_engine import LogFilter, LogQueryEngine


class TimelineRenderer:
    """Renders chronological timelines from structured JSONL log files.

    Reads log entries via LogQueryEngine, sorts them by timestamp, and
    presents them either as JSON dicts or as formatted swimlane text
    grouped by service_id.

    Args:
        directory: Root directory containing ``structured.jsonl`` files.
    """

    def __init__(self, directory: Path) -> None:
        """Initialize the timeline renderer.

        Args:
            directory: Root directory to search for ``structured.jsonl`` files.
        """
        self._directory = Path(directory)
        self._engine = LogQueryEngine(self._directory)

    def render_json(
        self,
        *,
        test: Optional[str] = None,
        service: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Return filtered and chronologically sorted log entries as dicts.

        Args:
            test: Filter by test_id.
            service: Filter by service_id.
            after: Include entries at or after this time.
            before: Include entries strictly before this time.
            limit: Maximum number of entries to return. 0 means unlimited.

        Returns:
            List of log record dicts sorted by timestamp.
        """
        log_filter = self._build_filter(
            test=test, service=service, after=after, before=before
        )
        # Collect all matching records (no limit yet — we sort first)
        records = list(self._engine.query(log_filter))
        records = self._sort_by_timestamp(records)
        if limit > 0:
            records = records[:limit]
        return records

    def render_human(
        self,
        *,
        test: Optional[str] = None,
        service: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        limit: int = 50,
    ) -> str:
        """Return a human-readable swimlane-formatted timeline.

        Output format::

            [12:00:01.500] picoquic(server)  INFO   Handshake started
            [12:00:01.502] aioquic(client)   INFO   Sending Initial packet

        Args:
            test: Filter by test_id.
            service: Filter by service_id.
            after: Include entries at or after this time.
            before: Include entries strictly before this time.
            limit: Maximum number of entries to return. 0 means unlimited.

        Returns:
            Formatted multi-line string with swimlane columns.
        """
        records = self.render_json(
            test=test, service=service, after=after, before=before, limit=limit
        )
        if not records:
            return "(no matching log entries)"

        # Compute column widths for alignment
        service_labels = [self._format_service_label(r) for r in records]
        max_service_len = max(len(s) for s in service_labels)
        max_level_len = max(len(r.get("level", "?")) for r in records)

        lines = []
        for record, svc_label in zip(records, service_labels):
            ts_str = self._format_timestamp(record.get("ts", ""))
            level = record.get("level", "?")
            message = record.get("message", "")
            line = (
                f"[{ts_str}] "
                f"{svc_label:<{max_service_len}}  "
                f"{level:<{max_level_len}}  "
                f"{message}"
            )
            lines.append(line)

        return "\n".join(lines)

    # -- Private helpers -----------------------------------------------------

    @staticmethod
    def _build_filter(
        *,
        test: Optional[str] = None,
        service: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
    ) -> LogFilter:
        """Build a LogFilter from the provided keyword arguments.

        Args:
            test: Test ID to filter by.
            service: Service ID to filter by.
            after: Lower time bound.
            before: Upper time bound.

        Returns:
            Configured LogFilter instance.
        """
        return LogFilter(
            tests={test} if test else None,
            services={service} if service else None,
            after=after,
            before=before,
        )

    @staticmethod
    def _sort_by_timestamp(records: List[Dict]) -> List[Dict]:
        """Sort records chronologically by the ``ts`` field.

        Records without a ``ts`` field or with unparseable timestamps are
        placed at the end of the list.

        Args:
            records: List of log record dicts.

        Returns:
            New list sorted by timestamp ascending.
        """

        def _sort_key(record: Dict):
            ts_str = record.get("ts")
            if ts_str is None:
                return (1, "")
            try:
                return (0, datetime.fromisoformat(ts_str).isoformat())
            except (ValueError, TypeError):
                return (1, "")

        return sorted(records, key=_sort_key)

    @staticmethod
    def _format_service_label(record: Dict) -> str:
        """Format the service swimlane label from a record.

        Produces labels like ``picoquic(server)`` when both service_id
        and a role/phase are available, or just the service_id otherwise.

        Args:
            record: A log record dict.

        Returns:
            Formatted service label string, or ``"-"`` if no service info.
        """
        service_id = record.get("service_id")
        if not service_id:
            return "-"
        # Include phase as context if available
        phase = record.get("phase")
        if phase:
            return f"{service_id}({phase})"
        return service_id

    @staticmethod
    def _format_timestamp(ts_str: str) -> str:
        """Extract a compact time representation from an ISO timestamp.

        Produces ``HH:MM:SS.mmm`` format for readability.

        Args:
            ts_str: ISO-format timestamp string.

        Returns:
            Compact time string, or the raw value if parsing fails.
        """
        if not ts_str:
            return "??:??:??.???"
        try:
            dt = datetime.fromisoformat(ts_str)
            return dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
        except (ValueError, TypeError):
            return ts_str[:12]
