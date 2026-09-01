"""Measure how much of a timeline a reconstruction has actually specified.

The citation gate checks that a draft is internally consistent: that every
revision cites only claims its checkpoint holds. It cannot say whether the
reconstruction is *finished*, because nothing in the workspace records how much
of the timeline was ever visited. This module answers that: which clusters
produced no claim, and which claims no prose cites.
"""

from __future__ import annotations

import json
from pathlib import Path

from .checkpoint import CHECKPOINT_FILE


class CompletenessError(ValueError):
    """Raised when the gate's inputs cannot be interpreted as written."""


def load_clusters(timeline_dir: Path) -> tuple[dict, ...]:
    """Read a timeline's clusters, ordered by ordinal.

    Args:
        timeline_dir: Directory written by the timeline stage.

    Returns:
        Every cluster row, ascending by ``ordinal``.

    Raises:
        CompletenessError: If ``clusters.jsonl`` is absent or malformed.
    """
    path = timeline_dir / "clusters.jsonl"
    try:
        lines = path.read_text().splitlines()
    except OSError as error:
        raise CompletenessError(f"could not read {path}: {error}") from error
    try:
        rows = [json.loads(line) for line in lines if line.strip()]
    except json.JSONDecodeError as error:
        raise CompletenessError(f"{path} is not valid JSON Lines: {error}") from error
    return tuple(sorted(rows, key=lambda row: row["ordinal"]))


def checkpoint_records(checkpoints_dir: Path) -> tuple[tuple[str, dict], ...]:
    """Read every checkpoint record, ordered by the ordinal each one names.

    Sorting on the recorded ordinal rather than the directory name is what makes
    claim attribution correct: directory names are cluster ids, and ids do not
    sort into processing order.

    Args:
        checkpoints_dir: The checkpoints root.

    Returns:
        Pairs of directory name and record, ascending by ``ordinal``. Empty when
        the root does not exist.

    Raises:
        CompletenessError: If a record is present but unreadable.
    """
    if not checkpoints_dir.is_dir():
        return ()
    records: list[tuple[str, dict]] = []
    for directory in sorted(checkpoints_dir.iterdir()):
        record_path = directory / CHECKPOINT_FILE
        if not record_path.exists():
            continue
        try:
            records.append((directory.name, json.loads(record_path.read_text())))
        except (OSError, json.JSONDecodeError) as error:
            raise CompletenessError(f"could not read {record_path}: {error}") from error
    return tuple(sorted(records, key=lambda pair: pair[1]["ordinal"]))
