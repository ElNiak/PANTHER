"""Verify that an anchor still points at what it claimed to.

An anchor without a pinned commit is refused rather than checked against the
working tree: a ``path:line`` reference into a moving tree silently points at
different code as the tree advances, and nothing about it looks wrong.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from .models import COMMIT_REQUIRED_FOR, Anchor


class AnchorError(ValueError):
    """Raised when an anchor cannot be verified as written."""


class UnknownCommitError(AnchorError):
    """Raised when the repository does not contain the anchor's commit."""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command inside ``repo`` without raising on failure.

    ``check=True`` is deliberately not used: it raises ``CalledProcessError``
    with no stderr attached, and this module must tell "no such path" from
    "no such commit".
    """
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )


def _git_bytes(repo: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    """Bytes-mode twin of :func:`_git`, for content that may not be text."""
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def verify_detailed(anchor: Anchor, repo: Path) -> str | None:
    """Verify an anchor and say why it failed, if it did.

    Beyond the locator existing at the pinned commit, a ``line`` is
    range-checked against the file as it was at that commit, and a
    ``line_sha256`` is compared against the digest of that line's bytes
    (newline stripped).

    Args:
        anchor: The anchor to verify.
        repo: Path to a clone containing the anchor's commit.

    Returns:
        None when the anchor verifies; otherwise a human-readable reason.

    Raises:
        AnchorError: If the anchor carries no commit, or names evidence that is
            not verifiable against a repository at all.
        UnknownCommitError: If the repository does not contain the commit, which
            is a different failure from the path being absent.
    """
    if anchor.evidence_class not in COMMIT_REQUIRED_FOR:
        raise AnchorError(
            f"{anchor.evidence_class.value} evidence is not verifiable against a "
            f"repository; only {', '.join(c.value for c in COMMIT_REQUIRED_FOR)} is"
        )

    if not anchor.commit:
        raise AnchorError(
            f"anchor {anchor.locator!r} carries no commit; an anchor without a "
            f"pinned commit cannot be verified and is refused"
        )

    known = _git(repo, "cat-file", "-e", f"{anchor.commit}^{{commit}}")
    if known.returncode != 0:
        raise UnknownCommitError(
            f"commit {anchor.commit} is not present in {repo}: "
            f"{known.stderr.strip()}"
        )

    present = _git(repo, "cat-file", "-e", f"{anchor.commit}:{anchor.locator}")
    if present.returncode != 0:
        return f"{anchor.locator} does not exist at {anchor.commit}"

    if anchor.line is None:
        return None

    shown = _git_bytes(repo, "show", f"{anchor.commit}:{anchor.locator}")
    if shown.returncode != 0:
        return (
            f"{anchor.locator} at {anchor.commit} could not be read: "
            f"{shown.stderr.decode(errors='replace').strip()}"
        )
    lines = shown.stdout.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    if not 1 <= anchor.line <= len(lines):
        return (
            f"line {anchor.line} is beyond the end of {anchor.locator} "
            f"({len(lines)} lines) at {anchor.commit}"
        )
    if anchor.line_sha256 is not None:
        actual = hashlib.sha256(lines[anchor.line - 1]).hexdigest()
        if actual != anchor.line_sha256:
            return (
                f"line {anchor.line} of {anchor.locator} at {anchor.commit} "
                f"no longer matches its recorded digest"
            )
    return None


def verify(anchor: Anchor, repo: Path) -> bool:
    """Check that an anchor still points at what it claimed to.

    Args:
        anchor: The anchor to verify.
        repo: Path to a clone containing the anchor's commit.

    Returns:
        True if the locator exists at the pinned commit and any recorded line
        and line digest still hold; False otherwise. For the reason behind a
        False, use :func:`verify_detailed`.

    Raises:
        AnchorError: If the anchor carries no commit, or names evidence that is
            not verifiable against a repository at all.
        UnknownCommitError: If the repository does not contain the commit, which
            is a different failure from the path being absent.
    """
    return verify_detailed(anchor, repo) is None
