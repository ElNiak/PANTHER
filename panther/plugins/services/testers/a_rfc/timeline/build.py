"""Cluster the corpus spine into PR and epoch clusters.

The total order is the first-parent walk from the corpus tip — topological,
never chronological, because ``authored_at`` is non-monotonic under rebase
and a date-ordered timeline would silently reorder history.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from .corpus import CorpusCommit, TimelineError, find_tip

#: A trailing ``(#N)`` in a subject is recorded as a hint and nothing more:
#: GitHub renders issue references identically, so clustering on it would
#: silently misattribute commits. Only a forge sha-match may restructure.
PR_HINT = re.compile(r"\(#(\d+)\)\s*$")


@dataclass(frozen=True)
class Member:
    """One commit's place inside a cluster."""

    sha: str
    position: int
    role: str


@dataclass(frozen=True)
class Cluster:
    """One ordered slot on the timeline: a PR or an epoch of direct pushes."""

    id: str
    ordinal: int
    kind: str
    provenance: str
    anchor_sha: str
    title: str
    member_count: int
    nested_merge_count: int
    files_complete: bool
    spine_prev_sha: str | None
    subject_pr_hint: int | None
    members: tuple[Member, ...]


def _spine(commits: Sequence[CorpusCommit]) -> list[str]:
    by_sha = {commit.sha: commit for commit in commits}
    walk: list[str] = []
    sha: str | None = find_tip(commits)
    while sha is not None:
        walk.append(sha)
        parents = by_sha[sha].parents
        if parents and parents[0] not in by_sha:
            raise TimelineError(
                f"first parent {parents[0]} of {sha} is absent from the corpus"
            )
        sha = parents[0] if parents else None
    walk.reverse()
    return walk


def _branch_members(
    merge: CorpusCommit,
    by_sha: dict[str, CorpusCommit],
    on_spine: frozenset[str],
    assigned: set[str],
) -> list[str]:
    queue = list(merge.parents[1:])
    found: list[str] = []
    seen: set[str] = set()
    while queue:
        sha = queue.pop()
        if sha in seen or sha in on_spine or sha in assigned:
            continue
        if sha not in by_sha:
            raise TimelineError(
                f"parent {sha} reached from merge {merge.sha} is absent "
                f"from the corpus"
            )
        seen.add(sha)
        found.append(sha)
        queue.extend(by_sha[sha].parents)
    return sorted(found, key=lambda member: (by_sha[member].authored_at, member))


def _cluster(
    ordinal: int,
    kind: str,
    member_shas: list[str],
    by_sha: dict[str, CorpusCommit],
    spine_prev: str | None,
) -> Cluster:
    anchor = member_shas[0] if kind == "epoch" else member_shas[-1]
    anchor_commit = by_sha[anchor]
    hint = PR_HINT.search(anchor_commit.subject) if kind == "pr" else None
    return Cluster(
        id=f"c{ordinal:04d}-{kind}-{anchor[:12]}",
        ordinal=ordinal,
        kind=kind,
        provenance="merge_commit" if kind == "pr" else "epoch",
        anchor_sha=anchor,
        title=anchor_commit.subject,
        member_count=len(member_shas),
        nested_merge_count=sum(
            1 for sha in member_shas if sha != anchor and by_sha[sha].is_merge
        ),
        files_complete=not any(by_sha[sha].files_truncated for sha in member_shas),
        spine_prev_sha=spine_prev,
        subject_pr_hint=int(hint.group(1)) if hint else None,
        members=tuple(
            Member(
                sha=sha,
                position=position,
                role=(
                    "spine"
                    if kind == "epoch"
                    else ("anchor" if sha == anchor else "branch")
                ),
            )
            for position, sha in enumerate(member_shas)
        ),
    )


def build_timeline(commits: Sequence[CorpusCommit]) -> tuple[Cluster, ...]:
    """Cluster a corpus into its total-ordered PR/epoch timeline.

    Args:
        commits: Every commit record in the corpus.

    Returns:
        Clusters in first-parent spine order, root to tip. Their members
        partition the corpus: every commit appears exactly once.

    Raises:
        TimelineError: If the corpus has no unique tip, a parent is missing,
            or the partition invariant breaks.
    """
    by_sha = {commit.sha: commit for commit in commits}
    spine = _spine(commits)
    on_spine = frozenset(spine)
    assigned: set[str] = set()
    clusters: list[Cluster] = []
    epoch_run: list[str] = []

    def flush(spine_prev: str | None) -> None:
        if epoch_run:
            clusters.append(
                _cluster(
                    len(clusters) + 1, "epoch", list(epoch_run), by_sha, spine_prev
                )
            )
            epoch_run.clear()

    for index, sha in enumerate(spine):
        if len(by_sha[sha].parents) > 1:
            first_epoch_index = index - len(epoch_run)
            flush(spine[first_epoch_index - 1] if first_epoch_index else None)
            branch = _branch_members(by_sha[sha], by_sha, on_spine, assigned)
            clusters.append(
                _cluster(
                    len(clusters) + 1,
                    "pr",
                    branch + [sha],
                    by_sha,
                    spine[index - 1] if index else None,
                )
            )
            assigned.update(branch)
            assigned.add(sha)
        else:
            epoch_run.append(sha)
            assigned.add(sha)
    first_epoch_index = len(spine) - len(epoch_run)
    flush(spine[first_epoch_index - 1] if first_epoch_index else None)

    seen = [member.sha for cluster in clusters for member in cluster.members]
    if sorted(seen) != sorted(by_sha) or len(seen) != len(set(seen)):
        raise TimelineError(
            f"cluster members do not partition the corpus: "
            f"{len(seen)} member rows over {len(by_sha)} commits"
        )
    return tuple(clusters)
