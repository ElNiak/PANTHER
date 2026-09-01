"""Aggregates computed from the corpus rather than from fresh git calls.

Keeping every aggregate downstream of one extraction means git plumbing lives
in exactly one module, and it makes each aggregate testable against a known
corpus instead of against a repository.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import Commit


@dataclass(frozen=True)
class HistoryShape:
    """Coarse shape of a repository's history."""

    commit_count: int
    merge_count: int
    first_authored: str
    last_authored: str
    commits_by_year: dict[str, int]


def history_shape(commits: list[Commit]) -> HistoryShape:
    """Summarise a corpus's history.

    Args:
        commits: Commits as returned by :func:`git_log.extract`.

    Returns:
        The aggregate shape.

    Raises:
        ValueError: If ``commits`` is empty. This is deliberate: an empty
            corpus is a failed fetch wearing a disguise, and returning a hollow
            record would let it pass as a real result.
    """
    if not commits:
        raise ValueError(
            "cannot summarise an empty history; an empty corpus is a failed "
            "extraction, not a repository with no commits"
        )

    authored = sorted(commit.authored_at for commit in commits)
    years = Counter(stamp[:4] for stamp in authored)

    return HistoryShape(
        commit_count=len(commits),
        merge_count=sum(1 for commit in commits if commit.is_merge),
        first_authored=authored[0],
        last_authored=authored[-1],
        commits_by_year=dict(sorted(years.items())),
    )
