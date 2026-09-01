"""Read commit history out of a local repository.

The only module here that shells out to git. Two passes: metadata, which is
effectively free, and file changes, which is not — see the module README for
the measurements behind that split.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from .models import Commit, ExtractionReport, FileChange

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
            f"re-clone without --depth, run git fetch --unshallow, or — with "
            f"no network — clone a bundle (git clone repo.bundle) or copy the "
            f"whole repository directory"
        )


def extract_commits(repo: Path) -> list[Commit]:
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


def read_file_changes(
    repo: Path, cap: int = DEFAULT_FILE_CAP
) -> tuple[dict[str, list[FileChange]], dict[str, int]]:
    """Read the paths each commit touched, recording at most ``cap`` per commit.

    Merge commits produce no diff against their first parent and are excluded,
    so they map to an empty list.

    The token stream is NUL-separated and interleaves commit markers with file
    entries. A status beginning ``R`` or ``C`` is followed by *two* paths — the
    source then the destination — and every other status by one. Reading only
    the first path would silently record the rename's source as the file that
    changed; on the repository this was measured against, 8% of all rows are
    rename rows.

    Args:
        repo: Path to an existing, complete clone.
        cap: Maximum rows recorded per commit.

    Returns:
        A pair of (changes keyed by sha, true path count keyed by sha). The
        count is what the commit actually touched and exceeds the number of
        recorded rows exactly when the cap bit.

    Raises:
        ShallowRepositoryError: If the clone is shallow.
        GitError: If a file entry is truncated or appears before any commit.
    """
    assert_complete(repo)
    raw = _git(
        repo,
        "log",
        "-z",
        "--no-merges",
        f"--format={_MARK}%H",
        "--name-status",
        "HEAD",
    )

    tokens = raw.split("\0")
    changes: dict[str, list[FileChange]] = {}
    totals: dict[str, int] = {}
    sha: str | None = None
    index = 0

    while index < len(tokens):
        token = tokens[index].lstrip("\n")
        index += 1
        if not token:
            continue

        if token.startswith(_MARK):
            sha = token[1:]
            changes.setdefault(sha, [])
            totals.setdefault(sha, 0)
            continue

        if sha is None:
            raise GitError(f"file entry before any commit marker: {token!r}")

        wants_two = token.startswith(_RENAME_STATUSES)
        needed = 2 if wants_two else 1
        if index + needed > len(tokens):
            raise GitError(f"truncated file entry for {sha}: status {token!r}")

        if wants_two:
            previous_path = tokens[index]
            path = tokens[index + 1]
        else:
            previous_path = None
            path = tokens[index]
        index += needed

        totals[sha] += 1
        if len(changes[sha]) < cap:
            changes[sha].append(
                FileChange(
                    sha=sha,
                    path=path,
                    status=token[0],
                    previous_path=previous_path,
                )
            )

    return changes, totals


def extract(
    repo: Path, cap: int = DEFAULT_FILE_CAP
) -> tuple[list[Commit], list[FileChange], ExtractionReport]:
    """Read a repository into commits, file rows, and a report of both.

    Args:
        repo: Path to an existing, complete clone.
        cap: Maximum file rows recorded per commit.

    Returns:
        A triple of (commits sorted by ``(authored_at, sha)``, file rows sorted
        by ``(sha, path)``, and a report naming every truncated commit).

    Raises:
        ShallowRepositoryError: If the clone is shallow.
    """
    commits = extract_commits(repo)
    changes, totals = read_file_changes(repo, cap=cap)

    enriched: list[Commit] = []
    truncated: list[str] = []
    rows: list[FileChange] = []

    for commit in commits:
        recorded = changes.get(commit.sha, [])
        total = totals.get(commit.sha, 0)
        was_truncated = total > len(recorded)
        if was_truncated:
            truncated.append(commit.sha)
        rows.extend(recorded)
        enriched.append(
            Commit(
                sha=commit.sha,
                parents=commit.parents,
                author_name=commit.author_name,
                author_email=commit.author_email,
                authored_at=commit.authored_at,
                committed_at=commit.committed_at,
                subject=commit.subject,
                body=commit.body,
                file_count=total,
                files_recorded=len(recorded),
                files_truncated=was_truncated,
            )
        )

    rows.sort(key=lambda row: (row.sha, row.path))
    report = ExtractionReport(
        commit_count=len(enriched),
        file_row_count=len(rows),
        truncated=tuple(sorted(truncated)),
    )
    return enriched, rows, report
