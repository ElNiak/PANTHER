"""Verify that an anchor still points at what it claimed to.

An anchor without a pinned commit is refused rather than checked against the
working tree: a ``path:line`` reference into a moving tree silently points at
different code as the tree advances, and nothing about it looks wrong.
"""

from __future__ import annotations

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


def verify(anchor: Anchor, repo: Path) -> bool:
    """Check that an anchor's locator exists at its pinned commit.

    Args:
        anchor: The anchor to verify.
        repo: Path to a clone containing the anchor's commit.

    Returns:
        True if the locator exists at the pinned commit, False if it does not.

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
    return present.returncode == 0
