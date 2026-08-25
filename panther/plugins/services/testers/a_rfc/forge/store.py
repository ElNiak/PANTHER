"""Immutable forge snapshots on disk.

A snapshot is written once, after a complete fetch, and never overwritten:
downstream consumers name an explicit snapshot directory, so there is no
implicit "latest" to answer confidently from stale data. Records are sorted
and serialised with sorted keys, so permuting the fetcher's arrival order
cannot change a byte.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

TOOL_VERSION = "a_rfc.forge/1"

META_FILE = "meta.json"
PULLS_FILE = "pulls.jsonl"
REVIEWS_FILE = "reviews.jsonl"
COMMENTS_FILE = "comments.jsonl"

#: The only comment kinds a snapshot may carry; anything else raises rather
#: than being stored under a permissive label.
COMMENT_KINDS = frozenset({"review_comment", "issue_comment", "discussion_note"})


class ForgeError(RuntimeError):
    """Raised when forge data cannot be fetched or stored as intended."""


def _api_base(host: str, kind: str) -> str:
    if kind == "github":
        return "https://api.github.com"
    return f"https://{host}/api/v4"


def _write_jsonl(path: Path, records: Sequence[dict[str, Any]]) -> None:
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n" if lines else "")


def write_snapshot(
    out_root: Path,
    host: str,
    owner: str,
    repo: str,
    kind: str,
    clone_head: str,
    fetched_at: str,
    authenticated: bool,
    pulls: Sequence[dict[str, Any]],
    reviews: Sequence[dict[str, Any]],
    comments: Sequence[dict[str, Any]],
) -> Path:
    """Write one immutable snapshot of a repository's pull-request data.

    Args:
        out_root: The forge cache root; the snapshot lands under
            ``<host>__<owner>__<repo>/snapshot-<fetched_at>/``.
        host: Forge host name (``github.com``, ``gitlab.cylab.be``).
        owner: Repository owner or group path.
        repo: Repository name.
        kind: ``github`` or ``gitlab``.
        clone_head: HEAD of the clone the corpus was extracted from, so a
            snapshot fetched against a different state is refused downstream.
        fetched_at: Filesystem-safe UTC timestamp naming the snapshot.
        authenticated: Whether a token was used. The token itself is never
            recorded.
        pulls: Pull/merge-request records.
        reviews: Review records.
        comments: Comment records; each ``kind`` must be one of
            ``COMMENT_KINDS``.

    Returns:
        The snapshot directory.

    Raises:
        ForgeError: If the snapshot directory already exists, or a comment
            carries an unknown kind.
    """
    for comment in comments:
        if comment.get("kind") not in COMMENT_KINDS:
            raise ForgeError(
                f"comment {comment.get('id')!r} carries kind "
                f"{comment.get('kind')!r}; permitted kinds are "
                f"{', '.join(sorted(COMMENT_KINDS))}"
            )

    snapshot = out_root / f"{host}__{owner}__{repo}" / f"snapshot-{fetched_at}"
    if snapshot.exists():
        raise ForgeError(
            f"snapshot {snapshot} already exists; a snapshot is written once "
            f"— fetch again under a new timestamp instead of overwriting"
        )
    snapshot.mkdir(parents=True)

    _write_jsonl(snapshot / PULLS_FILE, sorted(pulls, key=lambda pull: pull["number"]))
    _write_jsonl(
        snapshot / REVIEWS_FILE,
        sorted(reviews, key=lambda review: (review["pr_number"], review["id"])),
    )
    _write_jsonl(
        snapshot / COMMENTS_FILE,
        sorted(
            comments,
            key=lambda comment: (
                comment["pr_number"],
                comment["created_at"],
                comment["id"],
            ),
        ),
    )
    meta = {
        "api_base": _api_base(host, kind),
        "authenticated": authenticated,
        "clone_head": clone_head,
        "complete": True,
        "fetched_at": fetched_at,
        "host": host,
        "kind": kind,
        "owner": owner,
        "repo": repo,
        "tool_version": TOOL_VERSION,
    }
    (snapshot / META_FILE).write_text(json.dumps(meta, sort_keys=True, indent=2) + "\n")
    return snapshot


def read_snapshot(snapshot_dir: Path) -> dict[str, Any]:
    """Read a snapshot back as ``{meta, pulls, reviews, comments}``.

    Args:
        snapshot_dir: A directory written by :func:`write_snapshot`.

    Returns:
        The parsed snapshot.

    Raises:
        OSError: If a snapshot file cannot be read.
    """

    def rows(name: str) -> list[dict[str, Any]]:
        text = (snapshot_dir / name).read_text()
        return [json.loads(line) for line in text.splitlines()]

    return {
        "meta": json.loads((snapshot_dir / META_FILE).read_text()),
        "pulls": rows(PULLS_FILE),
        "reviews": rows(REVIEWS_FILE),
        "comments": rows(COMMENTS_FILE),
    }
