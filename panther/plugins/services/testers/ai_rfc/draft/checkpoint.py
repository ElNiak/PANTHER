"""Freeze a manifest against one timeline cluster.

A checkpoint is the manifest as it stood when cluster ``i`` was processed:
a normalized byte-stable copy plus a record tying it to the cluster, the
timeline it came from, and an adjudication summary. Checkpoints are written
once and never overwritten — a re-run against the same cluster is a new
decision, not an update.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..models import STATUS_RANK, Status
from ..promotion import adjudicate, violations
from ..schema import dump, load

CHECKPOINT_FILE = "checkpoint.json"
MANIFEST_FILE = "manifest.yaml"


class CheckpointError(RuntimeError):
    """Raised when a checkpoint cannot be written or no longer holds."""


def _digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _cluster_row(timeline_dir: Path, cluster_id: str) -> tuple[dict, str | None]:
    rows = [
        json.loads(line)
        for line in (timeline_dir / "clusters.jsonl").read_text().splitlines()
    ]
    by_id = {row["id"]: row for row in rows}
    if cluster_id not in by_id:
        raise CheckpointError(f"no cluster {cluster_id} in {timeline_dir}")
    row = by_id[cluster_id]
    previous = [r["id"] for r in rows if r["ordinal"] == row["ordinal"] - 1]
    return row, previous[0] if previous else None


def write_checkpoint(
    manifest_path: Path, timeline_dir: Path, cluster_id: str, out: Path
) -> Path:
    """Checkpoint ``manifest_path`` against one cluster of a timeline.

    Args:
        manifest_path: The manifest to freeze; loaded and re-dumped so the
            stored copy is normalized, byte-stable and citable.
        timeline_dir: Directory written by the timeline stage.
        cluster_id: The cluster this manifest state belongs to.
        out: Root directory; the checkpoint lands in ``out/<cluster_id>/``.

    Returns:
        The checkpoint directory.

    Raises:
        CheckpointError: If the cluster is unknown or the checkpoint exists.
        SchemaError: If the manifest cannot be loaded as written.
        OSError: If an input cannot be read.
    """
    manifest = load(manifest_path)
    row, prev_cluster_id = _cluster_row(timeline_dir, cluster_id)

    # Every input is read before anything is created. A failure after `mkdir`
    # leaves a directory the write-once guard below then refuses forever, and
    # `pipeline status` reads it as unfrozen and routes the operator straight
    # back into the stage that will refuse them.
    timeline_sha256 = _digest_bytes((timeline_dir / "timeline.json").read_bytes())
    normalized = dump(manifest).encode()

    checkpoint_dir = out / cluster_id
    if checkpoint_dir.exists():
        raise CheckpointError(
            f"{checkpoint_dir} already exists; a checkpoint is written once "
            f"and never overwritten"
        )
    checkpoint_dir.mkdir(parents=True)

    (checkpoint_dir / MANIFEST_FILE).write_bytes(normalized)

    supported_counts = {status.value: 0 for status in Status}
    promotable = 0
    for claim in manifest.claims:
        supported = adjudicate(claim)
        supported_counts[supported.value] += 1
        if STATUS_RANK[supported] > STATUS_RANK[claim.status]:
            promotable += 1

    record = {
        "adjudication": {
            "count_by_stored": manifest.count_by_status,
            "count_by_supported": supported_counts,
            "promotable_count": promotable,
            "violation_count": len(violations(manifest)),
        },
        "cluster_id": cluster_id,
        "manifest_sha256": _digest_bytes(normalized),
        "ordinal": row["ordinal"],
        "prev_cluster_id": prev_cluster_id,
        "timeline_sha256": timeline_sha256,
    }
    (checkpoint_dir / CHECKPOINT_FILE).write_text(
        json.dumps(record, sort_keys=True, indent=2) + "\n"
    )
    return checkpoint_dir


def verify_checkpoint(checkpoint_dir: Path) -> str | None:
    """Check that a checkpoint's stored manifest still matches its digest.

    Args:
        checkpoint_dir: A directory written by :func:`write_checkpoint`.

    Returns:
        None when the copy still matches; otherwise the reason it does not.

    Raises:
        OSError: If the checkpoint record cannot be read.
    """
    record = json.loads((checkpoint_dir / CHECKPOINT_FILE).read_text())
    stored = checkpoint_dir / MANIFEST_FILE
    if not stored.exists():
        return f"{stored} is missing"
    current = _digest_bytes(stored.read_bytes())
    if current != record["manifest_sha256"]:
        return (
            f"{checkpoint_dir.name}/manifest.yaml has been edited since the "
            f"checkpoint was written; a checkpoint is immutable"
        )
    return None
