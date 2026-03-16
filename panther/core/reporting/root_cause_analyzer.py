"""Root cause analysis engine for PANTHER experiment failures.

Reads error and failure entries from ``structured.jsonl`` via
``LogQueryEngine``, matches them against the declarative
``FailurePattern`` library, and produces ranked root-cause
explanations with log excerpts and actionable suggestions.

Typical usage::

    from pathlib import Path
    from panther.core.reporting.root_cause_analyzer import RootCauseAnalyzer

    analyzer = RootCauseAnalyzer(Path("outputs/2024-01-01/exp1"))
    for cause in analyzer.analyze():
        print(f"#{cause.rank} [{cause.category}] {cause.pattern_name}")
        print(f"  Suggestion: {cause.suggestion}")
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .failure_patterns import BUILTIN_PATTERNS, FailurePattern
from .log_query_engine import LogFilter, LogQueryEngine

logger = logging.getLogger(__name__)


@dataclass
class RootCause:
    """A single ranked root-cause finding.

    Attributes:
        rank: 1-based position (1 = most likely root cause).
        category: Error category label (from ``ErrorCategory`` values).
        pattern_name: Name of the matched ``FailurePattern``, or
            ``"unmatched"`` when no pattern matched.
        event: The structured log record that triggered this finding.
        suggestion: Actionable fix text from the matched pattern.
        log_excerpt: First few ERROR-level lines from the related service
            for additional context.
        confidence: Score in [0.0, 1.0] reflecting match quality.
    """

    rank: int
    category: str
    pattern_name: str
    event: Dict[str, Any]
    suggestion: str
    log_excerpt: List[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-compatible dictionary.

        Returns:
            Dict containing all fields with the event trimmed to key
            fields (ts, level, message, service_id, test_id).
        """
        trimmed_event = {
            k: self.event.get(k)
            for k in ("ts", "level", "message", "service_id", "test_id", "event_type")
            if self.event.get(k) is not None
        }
        return {
            "rank": self.rank,
            "category": self.category,
            "pattern_name": self.pattern_name,
            "event": trimmed_event,
            "suggestion": self.suggestion,
            "log_excerpt": self.log_excerpt,
            "confidence": round(self.confidence, 3),
        }


class RootCauseAnalyzer:
    """Analyze experiment failures and produce ranked root causes.

    The analyzer works in four steps:

    1. **Collect** error/failure records from ``structured.jsonl`` via
       ``LogQueryEngine`` (records with ``level_num >= 40`` or event-source
       records whose message contains error-related keywords).
    2. **Group** records chronologically by ``test_id``.
    3. **Match** each group's earliest error against the ``FailurePattern``
       catalog, scoring by pattern confidence and temporal order.
    4. **Enrich** each finding with the first few ERROR lines from the
       matched service for additional context.

    Args:
        experiment_dir: Path to the experiment output directory.
        patterns: Optional custom pattern list.  Defaults to
            ``BUILTIN_PATTERNS``.
        max_excerpt_lines: Maximum number of ERROR lines to include in
            each root-cause excerpt.
    """

    def __init__(
        self,
        experiment_dir: Path,
        patterns: Optional[List[FailurePattern]] = None,
        max_excerpt_lines: int = 5,
    ):
        """Initialize the root cause analyzer.

        Args:
            experiment_dir: Path to the experiment output directory.
            patterns: Custom pattern list (defaults to BUILTIN_PATTERNS).
            max_excerpt_lines: Maximum ERROR lines per excerpt.
        """
        self._dir = Path(experiment_dir)
        self._engine = LogQueryEngine(self._dir)
        self._patterns = patterns if patterns is not None else list(BUILTIN_PATTERNS)
        self._max_excerpt = max_excerpt_lines

    # -- public API ----------------------------------------------------------

    def analyze(self) -> List[RootCause]:
        """Run root-cause analysis and return ranked findings.

        Returns:
            List of ``RootCause`` objects ordered by rank (most likely
            root cause first).  Returns an empty list when no errors
            are found.
        """
        error_records = self._collect_error_records()
        if not error_records:
            return []

        grouped = self._group_by_test(error_records)
        raw_causes = self._match_patterns(grouped)

        # Sort by confidence descending, then by timestamp ascending
        raw_causes.sort(
            key=lambda rc: (-rc.confidence, rc.event.get("ts", "")),
        )

        # Assign ranks
        for idx, cause in enumerate(raw_causes, start=1):
            cause.rank = idx

        return raw_causes

    def analyze_as_dicts(self) -> List[Dict[str, Any]]:
        """Run analysis and return serializable dicts.

        Convenience wrapper around :meth:`analyze` for JSON output.

        Returns:
            List of dicts suitable for ``json.dump``.
        """
        return [rc.to_dict() for rc in self.analyze()]

    # -- private helpers -----------------------------------------------------

    def _collect_error_records(self) -> List[Dict]:
        """Gather error-relevant records from structured logs.

        Includes records with ``level_num >= 40`` (ERROR and above)
        and event-source records whose message contains error-related
        keywords.

        Returns:
            Chronologically sorted list of matching records.
        """
        # Collect ERROR/CRITICAL records
        error_filter = LogFilter(levels={"ERROR", "CRITICAL"})
        error_records = list(self._engine.query(error_filter))

        # Also collect event-source records with error-related types
        event_filter = LogFilter(sources={"event"})
        for record in self._engine.query(event_filter):
            message = record.get("message", "")
            event_type = record.get("event_type", "")
            # Include events that look error-related
            if any(
                kw in (message + " " + event_type).lower()
                for kw in ("error", "fail", "crash", "timeout", "killed")
            ):
                # Avoid duplicates
                if record not in error_records:
                    error_records.append(record)

        # Sort chronologically
        error_records.sort(key=lambda r: r.get("ts", ""))
        return error_records

    def _group_by_test(self, records: List[Dict]) -> Dict[str, List[Dict]]:
        """Group records by test_id.

        Records without a ``test_id`` are placed in a ``"_global"``
        group.

        Args:
            records: Chronologically sorted error records.

        Returns:
            Mapping from test_id to list of records.
        """
        groups: Dict[str, List[Dict]] = {}
        for record in records:
            test_id = record.get("test_id", "_global")
            groups.setdefault(test_id, []).append(record)
        return groups

    def _match_patterns(self, grouped: Dict[str, List[Dict]]) -> List[RootCause]:
        """Match each test group against the failure pattern catalog.

        For each group the analyzer considers the earliest error record
        first (temporal priority), then tries every pattern for the best
        confidence score.

        Args:
            grouped: Mapping from test_id to error records.

        Returns:
            Unranked list of ``RootCause`` findings.
        """
        causes: List[RootCause] = []

        for test_id, records in grouped.items():
            if not records:
                continue

            # Take the earliest record as the primary candidate
            primary = records[0]

            best_pattern: Optional[FailurePattern] = None
            best_confidence = 0.0

            for pattern in self._patterns:
                confidence = pattern.matches(primary)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_pattern = pattern

            # If the primary record didn't match well, scan the rest
            if best_confidence < 0.4 and len(records) > 1:
                for record in records[1:]:
                    for pattern in self._patterns:
                        confidence = pattern.matches(record)
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_pattern = pattern
                            primary = record

            # Build the root cause
            if best_pattern is not None and best_confidence > 0.0:
                excerpt = self._get_excerpt(primary.get("service_id"), test_id)
                causes.append(
                    RootCause(
                        rank=0,  # assigned later
                        category=best_pattern.category,
                        pattern_name=best_pattern.name,
                        event=primary,
                        suggestion=best_pattern.suggestion,
                        log_excerpt=excerpt,
                        confidence=best_confidence,
                    )
                )
            else:
                # Unmatched error -- still worth reporting
                excerpt = self._get_excerpt(primary.get("service_id"), test_id)
                causes.append(
                    RootCause(
                        rank=0,
                        category=self._infer_category(primary),
                        pattern_name="unmatched",
                        event=primary,
                        suggestion=(
                            "No known failure pattern matched. Check the "
                            "error message and log excerpt for clues."
                        ),
                        log_excerpt=excerpt,
                        confidence=0.1,
                    )
                )

        return causes

    def _get_excerpt(self, service_id: Optional[str], test_id: str) -> List[str]:
        """Retrieve the first N ERROR lines for a service/test combination.

        Args:
            service_id: Service to filter by (may be None).
            test_id: Test to filter by.

        Returns:
            List of message strings (up to ``max_excerpt_lines``).
        """
        filt = LogFilter(levels={"ERROR", "CRITICAL"})
        if service_id:
            filt = LogFilter(levels={"ERROR", "CRITICAL"}, services={service_id})
        if test_id != "_global":
            filt = LogFilter(
                levels=filt.levels,
                services=filt.services,
                tests={test_id},
            )

        lines: List[str] = []
        for record in self._engine.query(filt, limit=self._max_excerpt):
            msg = record.get("message", "")
            if msg:
                lines.append(msg)
        return lines

    @staticmethod
    def _infer_category(record: Dict) -> str:
        """Best-effort category inference from record fields.

        Args:
            record: The log record to inspect.

        Returns:
            A category string, defaulting to ``"unknown"``.
        """
        message = (
            record.get("message", "") + " " + record.get("event_type", "")
        ).lower()

        category_hints = [
            ("docker", "docker_build"),
            ("container", "docker_runtime"),
            ("network", "network_setup"),
            ("timeout", "timeout"),
            ("memory", "resource"),
            ("certificate", "security"),
            ("tls", "security"),
            ("ssl", "security"),
            ("compile", "command_execution"),
            ("service", "service_start"),
            ("plugin", "plugin_load"),
            ("config", "configuration"),
        ]

        for hint, category in category_hints:
            if hint in message:
                return category

        return "unknown"
