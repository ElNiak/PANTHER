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
import tempfile
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


def _read_forge_records(snapshot: Path) -> dict[str, Any]:
    """Read a forge snapshot's records.

    Deliberately re-parses the files instead of importing ``forge/`` — the
    corpus-side subpackages hand data to each other on disk, never through
    imports.
    """
    return {
        "pulls": {pull["number"]: pull for pull in _jsonl(snapshot / "pulls.jsonl")},
        "reviews": _jsonl(snapshot / "reviews.jsonl"),
        "comments": _jsonl(snapshot / "comments.jsonl"),
    }


def _git_version() -> str:
    """Return the local git version; patch bytes are only stable within one."""
    return subprocess.run(
        ["git", "--version"], capture_output=True, text=True
    ).stdout.strip()


def _write_patch(cluster_dir: Path, name: str, raw: bytes) -> dict[str, Any]:
    """Write one patch file and return the record naming it in ``view.json``."""
    (cluster_dir / name).write_bytes(raw)
    return {"bytes": len(raw), "name": name, "sha256": _digest_bytes(raw)}


def _write_span_patch(
    cluster_dir: Path, repo: Path, base: str, member_shas: list[str]
) -> dict[str, Any]:
    """Write the cluster's span diff and return its patch record."""
    # The span ends at the cluster's LAST member: a PR's anchor merge, or
    # an epoch's final spine commit. The anchor_sha is an epoch's FIRST
    # member (it names the cluster), so diffing to it would drop every
    # later commit of the epoch.
    span = _span_diff(repo, base, member_shas[-1])
    return _write_patch(cluster_dir, SPAN_FILE, span)


def _write_member_patches(
    cluster_dir: Path,
    repo: Path,
    member_shas: list[str],
    parents_by_sha: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    """Write one first-parent patch per member commit, in member order."""
    (cluster_dir / "members").mkdir(exist_ok=True)
    records: list[dict[str, Any]] = []
    for position, sha in enumerate(member_shas):
        parents = parents_by_sha.get(sha, ())
        member_base = parents[0] if parents else EMPTY_TREE
        patch = _span_diff(repo, member_base, sha)
        records.append(
            _write_patch(cluster_dir, f"members/{position:02d}-{sha[:12]}.patch", patch)
        )
    return records


def _write_evidence(
    cluster_dir: Path, forge: dict[str, Any], number: int
) -> dict[str, Any] | None:
    """Write a pull request's forge bundle into ``evidence/pr.json``.

    Returns the record for ``view.json``, or None when the snapshot holds no
    pull with that number — in which case nothing is written.
    """
    pull = forge["pulls"].get(number)
    if pull is None:
        return None
    bundle = {
        "pull": pull,
        "reviews": [
            review for review in forge["reviews"] if review["pr_number"] == number
        ],
        "comments": [
            comment for comment in forge["comments"] if comment["pr_number"] == number
        ],
    }
    raw = (json.dumps(bundle, sort_keys=True, indent=2) + "\n").encode()
    (cluster_dir / "evidence").mkdir(exist_ok=True)
    (cluster_dir / "evidence" / "pr.json").write_bytes(raw)
    return {
        "comment_count": len(bundle["comments"]),
        "pr_number": number,
        "review_count": len(bundle["reviews"]),
        "sha256": _digest_bytes(raw),
    }


def emit_views(
    timeline_dir: Path,
    corpus: Path,
    repo: Path,
    out: Path,
    only: str | None = None,
    forge_snapshot: Path | None = None,
    patches: str = "span",
) -> tuple[str, ...]:
    """Emit evidence folders for every cluster, or for one.

    Args:
        timeline_dir: Directory written by the timeline stage.
        corpus: The corpus the timeline was built from.
        repo: The pinned clone; its HEAD must still be the corpus tip.
        out: Destination directory; one subdirectory per cluster id.
        only: Emit a single cluster id instead of all of them.
        forge_snapshot: A forge snapshot; each PR cluster carrying a
            ``pr_number`` gets its pull record, reviews and comments copied
            into ``evidence/pr.json``.
        patches: ``span`` (the default) emits only the cluster span diff;
            ``members`` also emits one first-parent patch per member commit.

    Returns:
        The emitted cluster ids, in ordinal order.

    Raises:
        ViewsError: If any input digest no longer matches, the clone HEAD has
            moved, ``only`` names an unknown cluster, ``patches`` is not a
            recognised mode, or git refuses a diff.
        OSError: If an input cannot be read.
    """
    if patches not in ("span", "members"):
        raise ViewsError(f"unknown patches mode {patches!r}; use span or members")
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

    parents_by_sha: dict[str, tuple[str, ...]] = {}
    if patches == "members":
        for row in _jsonl(corpus / "commits.jsonl"):
            parents_by_sha[row["sha"]] = tuple(row["parents"])

    forge = _read_forge_records(forge_snapshot) if forge_snapshot else None

    git_version = _git_version()
    source = {
        "commits_sha256": timeline["commits_sha256"],
        "files_sha256": timeline["files_sha256"],
        "timeline_sha256": _digest(timeline_dir / "timeline.json"),
    }

    emitted: list[str] = []
    for cluster in clusters:
        cluster_dir = out / cluster["id"]
        cluster_dir.mkdir(parents=True, exist_ok=True)
        member_shas = members_by_cluster[cluster["id"]]
        base = cluster["spine_prev_sha"] or EMPTY_TREE

        patch_records = [_write_span_patch(cluster_dir, repo, base, member_shas)]
        if patches == "members":
            patch_records.extend(
                _write_member_patches(cluster_dir, repo, member_shas, parents_by_sha)
            )

        evidence = None
        if forge is not None and cluster.get("pr_number") is not None:
            evidence = _write_evidence(cluster_dir, forge, cluster["pr_number"])

        view = {
            **cluster,
            "evidence": evidence,
            "file_set": _file_set(member_shas, rows_by_sha),
            "git_version": git_version,
            "patches": patch_records,
            "source": source,
        }
        (cluster_dir / VIEW_FILE).write_text(
            json.dumps(view, sort_keys=True, indent=2) + "\n"
        )
        emitted.append(cluster["id"])
    return tuple(emitted)


def _patches_drifted(stored_dir: Path, fresh_view: dict[str, Any]) -> bool:
    """Report whether a stored cluster's patches match a fresh emission.

    Only the ``patches`` records and the patch files they name are compared;
    the rest of ``view.json`` is not. True when the stored view is missing,
    its patch records differ, or a named patch file is absent or has a
    different digest.
    """
    stored_view_path = stored_dir / VIEW_FILE
    if not stored_view_path.exists():
        return True
    stored_view = json.loads(stored_view_path.read_text())
    if stored_view.get("patches") != fresh_view["patches"]:
        return True
    for record in fresh_view["patches"]:
        stored_patch = stored_dir / record["name"]
        if not stored_patch.exists() or _digest(stored_patch) != record["sha256"]:
            return True
    return False


def verify_views(
    timeline_dir: Path,
    corpus: Path,
    repo: Path,
    out: Path,
    only: str | None = None,
    forge_snapshot: Path | None = None,
    patches: str = "span",
) -> tuple[str, ...]:
    """Re-emit views into scratch space and compare digests.

    Cross-git-version patch stability is empirical, not contractual, so drift
    is converted into a named failure instead of silent divergence.

    Args:
        timeline_dir: Directory written by the timeline stage.
        corpus: The corpus the timeline was built from.
        repo: The pinned clone.
        out: The previously emitted views to check.
        only: Check a single cluster id instead of all of them. Scoping the
            check narrows what is inspected, so a clean result means only that
            the named cluster reproduces.
        forge_snapshot: As :func:`emit_views`; pass what the original
            emission used.
        patches: As :func:`emit_views`; pass what the original emission used.

    Returns:
        The cluster ids whose stored artifacts no longer match a fresh
        emission; empty when everything checked still matches.

    Raises:
        ViewsError: As :func:`emit_views`.
        OSError: If an input cannot be read.
    """
    with tempfile.TemporaryDirectory() as scratch:
        fresh_root = Path(scratch)
        emitted = emit_views(
            timeline_dir,
            corpus,
            repo,
            fresh_root,
            only=only,
            forge_snapshot=forge_snapshot,
            patches=patches,
        )
        drifted = [
            cluster_id
            for cluster_id in emitted
            if _patches_drifted(
                out / cluster_id,
                json.loads((fresh_root / cluster_id / VIEW_FILE).read_text()),
            )
        ]
    return tuple(drifted)
