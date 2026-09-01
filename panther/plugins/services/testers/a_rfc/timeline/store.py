"""Write and read the timeline artifacts.

Three files land in the output directory, byte-stable across runs:
``clusters.jsonl`` (one cluster per line, without members), ``members.jsonl``
(one row per corpus commit, in cluster-ordinal then position order) and
``timeline.json`` (the run record, carrying SHA-256 digests of both corpus
JSONL files so every downstream consumer can refuse a moved corpus).
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from .build import Cluster
from .corpus import COMMITS_FILE

FILES_FILE = "files.jsonl"
CLUSTERS_FILE = "clusters.jsonl"
MEMBERS_FILE = "members.jsonl"
TIMELINE_FILE = "timeline.json"


def _digest(path: Path) -> str:
    """Return a hex digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_timeline(
    clusters: Sequence[Cluster],
    tip_sha: str,
    corpus: Path,
    out: Path,
    forge_snapshot: dict[str, str] | None = None,
    tip_verified: bool = False,
) -> None:
    """Write the timeline artifacts for ``clusters`` into ``out``.

    Args:
        clusters: The timeline, in ordinal order.
        tip_sha: The corpus tip the spine was walked from.
        corpus: The corpus directory the timeline was built from; both JSONL
            files are digested into ``timeline.json``.
        out: Destination directory, created if absent.
        forge_snapshot: ``{"dir_name", "meta_sha256"}`` of the snapshot that
            informed clustering, or ``None`` for a git-only timeline.
        tip_verified: Whether ``tip_sha`` was checked against a clone's HEAD.
            Recorded because a tip nobody verified is weaker provenance than a
            verified one, and the two are otherwise indistinguishable on disk.
    """
    out.mkdir(parents=True, exist_ok=True)

    cluster_lines = []
    member_lines = []
    for cluster in clusters:
        record = dataclasses.asdict(cluster)
        members = record.pop("members")
        cluster_lines.append(json.dumps(record, sort_keys=True))
        for member in members:
            member_lines.append(
                json.dumps({"cluster_id": cluster.id, **member}, sort_keys=True)
            )
    (out / CLUSTERS_FILE).write_text("\n".join(cluster_lines) + "\n")
    (out / MEMBERS_FILE).write_text("\n".join(member_lines) + "\n")

    payload = {
        "cluster_count": len(clusters),
        "commits_sha256": _digest(corpus / COMMITS_FILE),
        "epoch_count": sum(1 for cluster in clusters if cluster.kind == "epoch"),
        "files_sha256": _digest(corpus / FILES_FILE),
        "forge_snapshot": forge_snapshot,
        "member_count": sum(cluster.member_count for cluster in clusters),
        "pr_count": sum(1 for cluster in clusters if cluster.kind == "pr"),
        "tip_sha": tip_sha,
        "tip_verified": tip_verified,
    }
    (out / TIMELINE_FILE).write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    )


def read_timeline(directory: Path) -> dict[str, Any]:
    """Read ``timeline.json`` from a timeline directory."""
    return json.loads((directory / TIMELINE_FILE).read_text())


def read_clusters(directory: Path) -> tuple[dict[str, Any], ...]:
    """Read cluster records from a timeline directory, in ordinal order."""
    lines = (directory / CLUSTERS_FILE).read_text().splitlines()
    return tuple(json.loads(line) for line in lines)


def read_members(directory: Path) -> tuple[dict[str, Any], ...]:
    """Read member rows from a timeline directory, in emission order."""
    lines = (directory / MEMBERS_FILE).read_text().splitlines()
    return tuple(json.loads(line) for line in lines)
