"""Shared formatting utilities for the webapp."""

import json
from datetime import datetime
from typing import Any


def format_json(data: Any) -> str:
    """Format data as indented JSON string, falling back to str()."""
    try:
        return json.dumps(data, indent=2, default=str)
    except (TypeError, ValueError):
        return str(data)


def compute_duration(ts1: str, ts2: str) -> str:
    """Compute human-readable duration between two ISO timestamps.

    Returns strings like "<1s", "5s", "2.3m", "1.2h", or "" on parse failure.
    """
    try:
        fmt = "%Y-%m-%dT%H:%M:%S"
        t1 = datetime.strptime(ts1[:19], fmt)
        t2 = datetime.strptime(ts2[:19], fmt)
        delta = abs((t2 - t1).total_seconds())
        if delta < 1:
            return "<1s"
        if delta < 60:
            return f"{delta:.0f}s"
        if delta < 3600:
            return f"{delta / 60:.1f}m"
        return f"{delta / 3600:.1f}h"
    except (ValueError, TypeError):
        return ""
