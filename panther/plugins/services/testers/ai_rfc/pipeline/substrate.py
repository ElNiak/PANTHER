"""Whether a pinned clone can carry a reconstruction at all.

The three ways a clone fails are enforced one stage apart — shallow at
history, bare at pin, and neither until something reads the clone — so an
operator who assembled it by hand learns them one run at a time. This reports
all of them at once, and every remedy it names works with no network access,
because the operator who needs it is the one who could not clone normally.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: Named by every remedy below. ``git fetch --unshallow`` and a plain re-clone
#: both assume a reachable remote, which is exactly what the operator reading
#: this may not have.
_OFFLINE_REMEDY = (
    "obtain the full history without credentials: clone a bundle "
    "(git clone repo.bundle), copy the whole repository directory, or clone "
    "a mirror"
)


def _git(clone: Path, *args: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["git", "-C", str(clone), *args], capture_output=True, text=True
    )
    return completed.returncode, completed.stdout.strip()


def check(clone: Path) -> list[str]:
    """Every reason this clone cannot carry a reconstruction.

    Args:
        clone: Path to the pinned clone.

    Returns:
        One message per problem, each naming a remedy that needs no network;
        empty when the clone is usable.
    """
    if not clone.exists():
        return [f"{clone} does not exist; {_OFFLINE_REMEDY}"]
    if _git(clone, "rev-parse", "--git-dir")[0] != 0:
        return [f"{clone} is not a git repository; {_OFFLINE_REMEDY}"]

    problems: list[str] = []
    if _git(clone, "rev-parse", "--is-bare-repository")[1] == "true":
        problems.append(
            f"{clone} is bare, and the pin stage needs a working tree with a "
            f".git directory; clone it again without --bare"
        )
    if _git(clone, "rev-parse", "--is-shallow-repository")[1] == "true":
        problems.append(
            f"{clone} is shallow, and git log on a shallow clone returns fewer "
            f"commits with no error at all, so every aggregate computed from "
            f"it is quietly wrong; {_OFFLINE_REMEDY}"
        )
    return problems
