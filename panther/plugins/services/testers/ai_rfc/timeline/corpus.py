"""Read the slice of a commit corpus that clustering needs.

This module re-parses the corpus JSONL rather than importing ``history/``:
corpus-side stages share no domain code with their producer, and the handoff
between them is the file on disk. The duplication is deliberate and recorded
in the package README's consolidation table.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

COMMITS_FILE = "commits.jsonl"


class TimelineError(RuntimeError):
    """Raised when a corpus cannot be clustered as written."""


@dataclass(frozen=True)
class CorpusCommit:
    """The slice of a corpus commit record that clustering needs."""

    sha: str
    parents: tuple[str, ...]
    authored_at: str
    subject: str
    is_merge: bool
    files_truncated: bool


def read_commits(corpus: Path) -> tuple[CorpusCommit, ...]:
    """Read commit records from a corpus directory.

    Args:
        corpus: Directory containing ``commits.jsonl``.

    Returns:
        One record per commit, in file order.

    Raises:
        TimelineError: If the file is empty or a record is missing a field.
        OSError: If the file cannot be read.
    """
    path = corpus / COMMITS_FILE
    records: list[CorpusCommit] = []
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        raw = json.loads(line)
        try:
            records.append(
                CorpusCommit(
                    sha=raw["sha"],
                    parents=tuple(raw["parents"]),
                    authored_at=raw["authored_at"],
                    subject=raw["subject"],
                    is_merge=bool(raw["is_merge"]),
                    files_truncated=bool(raw["files_truncated"]),
                )
            )
        except KeyError as missing:
            raise TimelineError(
                f"{path}:{lineno}: record is missing field {missing}"
            ) from None
    if not records:
        raise TimelineError(f"{path} holds no commits")
    return tuple(records)


def find_tip(commits: Sequence[CorpusCommit]) -> str:
    """Return the corpus tip — the unique commit that is nobody's parent.

    Args:
        commits: Every commit record in the corpus.

    Returns:
        The tip commit's sha.

    Raises:
        TimelineError: If zero or several tips exist; a corpus extracted from
            ``git log HEAD`` has exactly one, so anything else means the
            corpus is not the kind of history this module understands.
    """
    parents = {parent for commit in commits for parent in commit.parents}
    tips = [commit.sha for commit in commits if commit.sha not in parents]
    if len(tips) != 1:
        raise TimelineError(
            f"expected exactly one tip commit, found {len(tips)}: "
            f"{', '.join(tips[:5]) or 'none'}"
        )
    return tips[0]
