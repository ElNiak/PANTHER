"""Structured JSONL formatter for PANTHER framework logging.

Emits one JSON object per log record (JSONL format). Each line includes
the current LogContext fields so that downstream tooling can
filter/aggregate by experiment, test, service, and execution phase
without parsing free-text messages.

The formatter is designed for file output only -- console output keeps
the existing human-readable colored format.
"""

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict

from .log_context import get_log_context


class StructuredJsonFormatter(logging.Formatter):
    """logging.Formatter that serializes each record as a single JSON line.

    Context fields (experiment_id, test_id, ...) are read from the
    current LogContext via get_log_context() on every call to format(),
    so they stay in sync without any per-call-site changes.

    Null-valued fields are omitted for compactness. The default=str
    fallback in json.dumps ensures that non-serializable objects
    (e.g. Path, datetime) do not cause crashes.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Serialize record to a compact JSON line.

        Args:
            record: The log record to format.

        Returns:
            A single JSON line string.
        """
        ctx = get_log_context()

        entry: Dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="microseconds"
            ),
            "level": record.levelname,
            "level_num": record.levelno,
            "source": "logging",
            "experiment_id": ctx.experiment_id,
            "test_id": ctx.test_id,
            "service_id": ctx.service_id,
            "phase": ctx.phase,
            "correlation_id": ctx.correlation_id,
            "feature": getattr(record, "_panther_feature", None),
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "lineno": record.lineno,
        }

        # Attach error information when present
        if record.exc_info and record.exc_info[0] is not None:
            exc_type, exc_value, exc_tb = record.exc_info
            entry["error"] = {
                "type": exc_type.__name__ if exc_type else None,
                "message": str(exc_value) if exc_value else None,
                "traceback": "".join(
                    traceback.format_exception(exc_type, exc_value, exc_tb)
                ),
            }

        # Strip null values for compactness
        entry = {k: v for k, v in entry.items() if v is not None}

        return json.dumps(entry, default=str)
