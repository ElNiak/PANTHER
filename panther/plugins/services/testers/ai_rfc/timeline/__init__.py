"""Cluster a commit corpus into an ordered PR/epoch timeline.

Corpus-side stage: reads the JSONL corpus written by ``history/`` and shares
no domain code with it or with the manifest core — the handoff in both
directions is a file on disk.
"""

from .build import PR_HINT, Cluster, Member, build_timeline
from .corpus import COMMITS_FILE, CorpusCommit, TimelineError, find_tip, read_commits

__all__ = [
    "COMMITS_FILE",
    "Cluster",
    "CorpusCommit",
    "Member",
    "PR_HINT",
    "TimelineError",
    "build_timeline",
    "find_tip",
    "read_commits",
]
