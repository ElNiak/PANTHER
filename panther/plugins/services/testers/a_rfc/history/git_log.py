"""Read commit history out of a local repository.

The only module here that shells out to git. Two passes: metadata, which is
effectively free, and file changes, which is not — see the module README for
the measurements behind that split.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .models import Commit, FileChange

#: Maximum file rows recorded for one commit. Of the 1276 commits this was
#: measured against, 23 exceed it — all vendoring or submodule imports. Without
#: a cap those few dominate a corpus of 1.52 million rows, one contributing
#: 247,455 on its own.
DEFAULT_FILE_CAP = 1000

_UNIT = "\x1f"
_MARK = "\x01"
_RENAME_STATUSES = ("R", "C")

_METADATA_FORMAT = (
    f"%H{_UNIT}%P{_UNIT}%an{_UNIT}%ae{_UNIT}%aI{_UNIT}%cI{_UNIT}%s{_UNIT}%b"
)
_METADATA_FIELDS = 8


class GitError(RuntimeError):
    """Raised when a git invocation fails or its output cannot be parsed."""


class ShallowRepositoryError(GitError):
    """Raised when a repository's history is incomplete."""


def _git(repo: Path, *args: str) -> str:
    """Run git inside ``repo`` and return its stdout.

    ``check=True`` is deliberately not used: it raises ``CalledProcessError``
    with no stderr attached, and callers need the message to tell one failure
    from another.

    Args:
        repo: Path to an existing clone.
        *args: Arguments passed through to git.

    Returns:
        Captured stdout, unmodified.

    Raises:
        GitError: If git exits non-zero, carrying stderr for diagnosis.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def assert_complete(repo: Path) -> None:
    """Refuse to read a repository whose history is truncated.

    Args:
        repo: Path to an existing clone.

    Raises:
        ShallowRepositoryError: If the clone is shallow. ``git log`` on a
            shallow clone returns fewer commits with no error at all, so every
            aggregate computed from it is quietly wrong.
    """
    if _git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        raise ShallowRepositoryError(
            f"{repo} is a shallow clone and its history is incomplete; "
            f"re-clone without --depth, or run git fetch --unshallow"
        )


def read_commits(repo: Path) -> list[Commit]:
    """Read every commit's metadata, in a deterministic order.

    Records are sorted by ``(authored_at, sha)``. Git's own ordering is
    reverse-chronological with no tiebreak between commits sharing a
    timestamp, so relying on it would make byte-stable output impossible.

    Args:
        repo: Path to an existing, complete clone.

    Returns:
        Every commit, sorted.

    Raises:
        ShallowRepositoryError: If the clone is shallow.
        GitError: If a record does not carry the expected field count.
    """
    assert_complete(repo)
    raw = _git(repo, "log", "-z", f"--format={_METADATA_FORMAT}", "HEAD")

    commits: list[Commit] = []
    for record in raw.split("\0"):
        record = record.lstrip("\n")
        if not record:
            continue
        # maxsplit is load-bearing: the body is the last field and may itself
        # contain the unit separator. NUL protects the record boundary, not the
        # fields — see trap 1a. Splitting without it turns one commit into a
        # nine-field record and this parse fails.
        fields = record.split(_UNIT, _METADATA_FIELDS - 1)
        if len(fields) != _METADATA_FIELDS:
            raise GitError(
                f"expected {_METADATA_FIELDS} fields in a commit record, got "
                f"{len(fields)}: {record[:80]!r}"
            )
        sha, parents, name, email, authored, committed, subject, body = fields
        commits.append(
            Commit(
                sha=sha,
                parents=tuple(p for p in parents.split() if p),
                author_name=name,
                author_email=email,
                authored_at=authored,
                committed_at=committed,
                subject=subject,
                body=body.strip(),
            )
        )

    commits.sort(key=lambda commit: (commit.authored_at, commit.sha))
    return commits
