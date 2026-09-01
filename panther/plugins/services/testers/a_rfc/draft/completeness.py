"""Measure how much of a timeline a reconstruction has actually specified.

The citation gate checks that a draft is internally consistent: that every
revision cites only claims its checkpoint holds. It cannot say whether the
reconstruction is *finished*, because nothing in the workspace records how much
of the timeline was ever visited. This module answers that: which clusters
produced no claim, and which claims no prose cites.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..schema import SchemaError, load
from .checkpoint import CHECKPOINT_FILE, MANIFEST_FILE
from .gate import GateError, cited_ids, load_revisions


class CompletenessError(ValueError):
    """Raised when the gate's inputs cannot be interpreted as written."""


@dataclass(frozen=True)
class ClusterCompleteness:
    """What one timeline cluster contributed to the reconstruction."""

    cluster_id: str
    ordinal: int
    checkpointed: bool
    new_claim_ids: tuple[str, ...]
    manifest_changed: bool


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


def _claim_ids(checkpoint_dir: Path) -> frozenset[str]:
    """The claim ids held by a checkpoint's frozen manifest copy."""
    try:
        manifest = load(checkpoint_dir / MANIFEST_FILE)
    except (SchemaError, OSError) as error:
        raise CompletenessError(
            f"could not read {checkpoint_dir / MANIFEST_FILE}: {error}"
        ) from error
    return frozenset(claim.id for claim in manifest.claims)


def attribute_claims(
    timeline_dir: Path, checkpoints_dir: Path
) -> tuple[ClusterCompleteness, ...]:
    """Attribute each claim to the cluster whose checkpoint first held it.

    Each checkpoint is differenced against its predecessor in *processing*
    order, not against its timeline neighbour: on a sparse run the ordinal-1
    neighbour is usually unprocessed, and differencing against it would credit
    every claim to every checkpoint.

    Args:
        timeline_dir: Directory written by the timeline stage.
        checkpoints_dir: The checkpoints root.

    Returns:
        One row per timeline cluster, ascending by ordinal.

    Raises:
        CompletenessError: If any input is absent or malformed.
    """
    by_cluster: dict[str, ClusterCompleteness] = {}
    seen: frozenset[str] = frozenset()
    previous_digest: str | None = None
    for name, record in checkpoint_records(checkpoints_dir):
        held = _claim_ids(checkpoints_dir / name)
        digest = record["manifest_sha256"]
        by_cluster[record["cluster_id"]] = ClusterCompleteness(
            cluster_id=record["cluster_id"],
            ordinal=record["ordinal"],
            checkpointed=True,
            new_claim_ids=tuple(sorted(held - seen)),
            manifest_changed=digest != previous_digest,
        )
        seen = seen | held
        previous_digest = digest

    return tuple(
        by_cluster.get(
            row["id"],
            ClusterCompleteness(
                cluster_id=row["id"],
                ordinal=row["ordinal"],
                checkpointed=False,
                new_claim_ids=(),
                manifest_changed=False,
            ),
        )
        for row in load_clusters(timeline_dir)
    )


def citation_gaps(
    draft_repo: Path, revisions_path: Path, claim_ids: frozenset[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Find claims the prose does not cite.

    Args:
        draft_repo: The nested prose-draft git repository.
        revisions_path: Path to ``revisions.yaml``.
        claim_ids: Every claim id the reconstruction currently holds.

    Returns:
        Two tuples: ids uncited at the highest-numbered revision tag, and ids
        cited at no tag at all. The second is a subset of the first.

    Raises:
        CompletenessError: If the revision map or the draft repo is unreadable.
    """
    try:
        entries = load_revisions(revisions_path)
    except (GateError, OSError) as error:
        raise CompletenessError(f"could not read {revisions_path}: {error}") from error
    if not entries:
        return tuple(sorted(claim_ids)), tuple(sorted(claim_ids))

    ever: set[str] = set()
    head: set[str] = set()
    highest = max(entry.number for entry in entries)
    for entry in entries:
        cited, problem = cited_ids(draft_repo, entry.tag)
        if problem is not None:
            raise CompletenessError(problem)
        ever |= cited
        if entry.number == highest:
            head = cited
    return tuple(sorted(claim_ids - head)), tuple(sorted(claim_ids - ever))
