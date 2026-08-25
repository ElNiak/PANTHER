"""Emit one evidence folder per cluster: metadata, file set and span diff.

Corpus-side stage: reads the timeline artifacts and the corpus JSONL, runs
``git diff`` against the pinned clone, and writes nothing that cannot be
reproduced byte-for-byte from those inputs. Every input is digest-guarded —
a moved corpus or a moved clone HEAD is refused, never silently absorbed.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

#: git's well-known empty tree; the diff base for a cluster at the root.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

#: Flags chosen for byte-stability across git versions and user gitconfig:
#: ``--full-index`` kills abbreviation drift, explicit prefixes defeat
#: ``diff.mnemonicPrefix``, ``--no-renames`` removes similarity-threshold
#: drift (rename linkage already lives in ``files.jsonl``), and
#: ``--no-ext-diff``/``--no-textconv`` defeat local configuration.
_DIFF_ARGS = (
    "-c",
    "core.quotePath=true",
    "-c",
    "diff.algorithm=myers",
    "diff",
    "--no-color",
    "--no-ext-diff",
    "--no-textconv",
    "--no-renames",
    "--full-index",
    "--src-prefix=a/",
    "--dst-prefix=b/",
    "-U3",
)

SPAN_FILE = "span.diff"
VIEW_FILE = "view.json"


class ViewsError(RuntimeError):
    """Raised when views cannot be emitted from the inputs as written."""


def _digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _digest(path: Path) -> str:
    """Return a hex digest of a file's bytes."""
    return _digest_bytes(path.read_bytes())


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def _guard_inputs(timeline: dict[str, Any], corpus: Path, repo: Path) -> None:
    for name, key in (
        ("commits.jsonl", "commits_sha256"),
        ("files.jsonl", "files_sha256"),
    ):
        current = _digest(corpus / name)
        if current != timeline[key]:
            raise ViewsError(
                f"{name} has changed since the timeline was built; "
                f"rebuild the timeline rather than trusting these clusters"
            )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if head.returncode != 0:
        raise ViewsError(f"{repo} is not a git repository: {head.stderr.strip()}")
    if head.stdout.strip() != timeline["tip_sha"]:
        raise ViewsError(
            f"{repo} HEAD {head.stdout.strip()} is not the corpus tip "
            f"{timeline['tip_sha']}; the clone has moved on"
        )


def _span_diff(repo: Path, base: str, target: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *_DIFF_ARGS, base, target, "--"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise ViewsError(
            f"git diff {base}..{target} failed: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
    return result.stdout


def _file_set(
    member_shas: list[str], rows_by_sha: dict[str, list[tuple[str, str]]]
) -> list[dict[str, Any]]:
    statuses: dict[str, set[str]] = {}
    for sha in member_shas:
        for path, status in rows_by_sha.get(sha, ()):
            statuses.setdefault(path, set()).add(status)
    return [
        {"path": path, "statuses": sorted(found)}
        for path, found in sorted(statuses.items())
    ]


def emit_views(
    timeline_dir: Path,
    corpus: Path,
    repo: Path,
    out: Path,
    only: str | None = None,
) -> tuple[str, ...]:
    """Emit evidence folders for every cluster, or for one.

    Args:
        timeline_dir: Directory written by the timeline stage.
        corpus: The corpus the timeline was built from.
        repo: The pinned clone; its HEAD must still be the corpus tip.
        out: Destination directory; one subdirectory per cluster id.
        only: Emit a single cluster id instead of all of them.

    Returns:
        The emitted cluster ids, in ordinal order.

    Raises:
        ViewsError: If any input digest no longer matches, the clone HEAD has
            moved, ``only`` names an unknown cluster, or git refuses a diff.
        OSError: If an input cannot be read.
    """
    timeline = json.loads((timeline_dir / "timeline.json").read_text())
    _guard_inputs(timeline, corpus, repo)

    clusters = _jsonl(timeline_dir / "clusters.jsonl")
    members = _jsonl(timeline_dir / "members.jsonl")
    if only is not None:
        clusters = [cluster for cluster in clusters if cluster["id"] == only]
        if not clusters:
            raise ViewsError(f"no cluster {only} in {timeline_dir}")

    members_by_cluster: dict[str, list[str]] = {}
    for row in members:
        members_by_cluster.setdefault(row["cluster_id"], []).append(row["sha"])

    rows_by_sha: dict[str, list[tuple[str, str]]] = {}
    for row in _jsonl(corpus / "files.jsonl"):
        rows_by_sha.setdefault(row["sha"], []).append((row["path"], row["status"]))

    git_version = subprocess.run(
        ["git", "--version"], capture_output=True, text=True
    ).stdout.strip()
    source = {
        "commits_sha256": timeline["commits_sha256"],
        "files_sha256": timeline["files_sha256"],
        "timeline_sha256": _digest(timeline_dir / "timeline.json"),
    }

    emitted: list[str] = []
    for cluster in clusters:
        cluster_dir = out / cluster["id"]
        cluster_dir.mkdir(parents=True, exist_ok=True)
        base = cluster["spine_prev_sha"] or EMPTY_TREE
        # The span ends at the cluster's LAST member: a PR's anchor merge, or
        # an epoch's final spine commit. The anchor_sha is an epoch's FIRST
        # member (it names the cluster), so diffing to it would drop every
        # later commit of the epoch.
        span = _span_diff(repo, base, members_by_cluster[cluster["id"]][-1])
        (cluster_dir / SPAN_FILE).write_bytes(span)
        view = {
            **cluster,
            "file_set": _file_set(members_by_cluster[cluster["id"]], rows_by_sha),
            "git_version": git_version,
            "patches": [
                {"bytes": len(span), "name": SPAN_FILE, "sha256": _digest_bytes(span)}
            ],
            "source": source,
        }
        (cluster_dir / VIEW_FILE).write_text(
            json.dumps(view, sort_keys=True, indent=2) + "\n"
        )
        emitted.append(cluster["id"])
    return tuple(emitted)
