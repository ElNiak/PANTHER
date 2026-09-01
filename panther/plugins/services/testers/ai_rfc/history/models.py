"""Frozen records for a repository's commit history.

Data only. Extraction lives in :mod:`git_log`, emission in :mod:`store`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileChange:
    """One path touched by one commit.

    Args:
        sha: The commit that touched this path.
        path: The path *after* the change. For a rename or copy this is the
            destination, never the source — see trap 2 in the module README.
        status: Bare git status letter (``A``, ``C``, ``D``, ``M``, ``R``,
            ``T``) with any similarity score stripped.
        previous_path: The source path for a rename or copy; ``None``
            otherwise.
    """

    sha: str
    path: str
    status: str
    previous_path: str | None = None


@dataclass(frozen=True)
class Commit:
    """One commit's metadata, and how much of its file list was recorded.

    ``file_count`` is always the true number of paths the commit touched, even
    when the per-commit cap dropped rows; ``files_recorded`` is how many rows
    were written. They differ exactly when ``files_truncated`` is true.
    """

    sha: str
    parents: tuple[str, ...]
    author_name: str
    author_email: str
    authored_at: str
    committed_at: str
    subject: str
    body: str
    file_count: int = 0
    files_recorded: int = 0
    files_truncated: bool = False

    @property
    def is_merge(self) -> bool:
        """Whether this commit has more than one parent."""
        return len(self.parents) > 1


@dataclass(frozen=True)
class ExtractionReport:
    """What an extraction produced, including what it deliberately dropped."""

    commit_count: int
    file_row_count: int
    truncated: tuple[str, ...]

    @property
    def truncated_count(self) -> int:
        """How many commits had file rows dropped by the cap."""
        return len(self.truncated)
