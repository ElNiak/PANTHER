"""Tie a coverage run to the commit its anchors will cite.

A ``runtime`` anchor is verified against a pinned commit, so a report has to be
bound to one before anything is proposed from it. The binding is refused rather
than assumed: a report produced from a different checkout, or from a tree with
uncommitted edits, describes code that no commit contains.

This module never runs a build. The report is ingested out of band, which keeps
the package's rule that only ``forge`` reaches the network and nothing here
executes the implementation under reconstruction.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


class PinError(RuntimeError):
    """Raised when a report cannot be bound to a commit."""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )


def require_clean_checkout(repo: Path, commit: str) -> str:
    """Refuse unless the repository is at ``commit`` with nothing uncommitted.

    Coverage describes the code that ran. If HEAD has moved, or the tree holds
    edits, the lines that ran are not the lines the commit contains — and an
    anchor citing the commit would be describing something else.

    Args:
        repo: The clone the coverage run was produced from.
        commit: The commit the report is to be bound to. Any revision git can
            peel to a commit is accepted, including a branch or a tag.

    Returns:
        The commit id ``commit`` resolved to. Callers record this rather than
        what they were given: ``main`` and ``v1`` name a commit today and a
        different one tomorrow, and an anchor pinned to a moving ref is not
        pinned at all.

    Raises:
        PinError: If the repository is not at that commit, or is dirty.
    """
    if not (repo / ".git").exists():
        raise PinError(f"{repo} is not a git repository")
    head = _git(repo, "rev-parse", "HEAD")
    if head.returncode != 0:
        raise PinError(f"cannot read HEAD of {repo}: {head.stderr.strip()}")
    # ``--verify <rev>^{commit}`` rather than a plain ``rev-parse``: the latter
    # exits 0 for any 40-hex string, echoing it back without looking for an
    # object, so a mistyped commit reached the HEAD comparison below and was
    # refused as a different checkout — true, but not the reason.
    resolved = _git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}")
    if resolved.returncode != 0:
        raise PinError(f"{commit} is not a commit in {repo}")
    if head.stdout.strip() != resolved.stdout.strip():
        raise PinError(
            f"{repo} is at {head.stdout.strip()[:12]}, not {commit[:12]}; the "
            f"coverage describes a different checkout"
        )
    status = _git(repo, "status", "--porcelain")
    if status.stdout.strip():
        raise PinError(
            f"{repo} has uncommitted changes; the lines that ran are not the "
            f"lines {commit[:12]} contains"
        )
    return resolved.stdout.strip()


def path_index(repo: Path, commit: str) -> dict[str, list[str]]:
    """Every path at ``commit``, grouped by the suffixes that could name it.

    Coverage reports a path relative to the tool's source roots, so
    ``be/cylab/mark/detection/OWAverage.java`` has to be resolved against the
    repository's own ``server/src/main/java/be/cylab/...``. The index is built
    once per run because the alternative is a ``git`` call per line.

    Args:
        repo: The clone.
        commit: The commit to list.

    Returns:
        A mapping from suffix to every repository path ending in it.

    Raises:
        PinError: If the tree cannot be listed.
    """
    listed = _git(repo, "ls-tree", "-r", "--name-only", commit)
    if listed.returncode != 0:
        raise PinError(f"cannot list {commit} in {repo}: {listed.stderr.strip()}")
    index: dict[str, list[str]] = {}
    for path in listed.stdout.splitlines():
        parts = path.split("/")
        for start in range(len(parts)):
            index.setdefault("/".join(parts[start:]), []).append(path)
    return index


def resolve(suffix: str, index: dict[str, list[str]]) -> str:
    """The one repository path a coverage suffix names.

    Ambiguity is refused rather than guessed. MARK's aggregate report merges
    seven modules, and a package path repeated across ``core/`` and ``server/``
    is a live possibility — picking either would attach a claim's evidence to
    the wrong file, silently.

    Args:
        suffix: The coverage tool's source path.
        index: The index from :func:`path_index`.

    Returns:
        The repository path.

    Raises:
        PinError: If no path or several paths end with the suffix.
    """
    matches = index.get(suffix, [])
    if not matches:
        raise PinError(f"no file in the commit ends with {suffix}")
    if len(matches) > 1:
        raise PinError(
            f"{suffix} is ambiguous: {', '.join(sorted(matches))}. Coverage "
            f"cannot say which was executed."
        )
    return matches[0]


def line_digest(repo: Path, commit: str, path: str, line: int) -> str:
    """The digest of one line as it stands at a commit.

    Read from the blob at the commit, using the same split and the same
    newline handling as ``anchors.verify_detailed`` — so an anchor carrying
    this digest verifies by construction rather than by coincidence.

    Args:
        repo: The clone.
        commit: The pinned commit.
        path: The repository path.
        line: The 1-based line number.

    Returns:
        The SHA-256 hex digest of the line's bytes, newline excluded.

    Raises:
        PinError: If the file cannot be read or the line is out of range.
    """
    import hashlib

    shown = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True
    )
    if shown.returncode != 0:
        raise PinError(
            f"{path} at {commit} could not be read: "
            f"{shown.stderr.decode(errors='replace').strip()}"
        )
    lines = shown.stdout.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    if not 1 <= line <= len(lines):
        raise PinError(
            f"line {line} is beyond the end of {path} ({len(lines)} lines) "
            f"at {commit}"
        )
    return hashlib.sha256(lines[line - 1]).hexdigest()
