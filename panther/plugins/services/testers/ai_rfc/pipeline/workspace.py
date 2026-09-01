"""The on-disk layout every stage reads and writes.

One place names the workspace's directories. The six substrate CLIs each take
their inputs and outputs as explicit paths and share no convention about where
those paths live, which is right for them — a stage should not assume a layout
it did not create. But something has to know the layout to chain them, and this
is that something: no path here is inferred from anything but the root.
"""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path


def digest(path: Path) -> str:
    """Return a hex digest of a file's bytes.

    The same construction the substrate uses to record its own inputs, so a
    digest computed here is comparable with one read out of ``timeline.json``
    or a ``view.json``.

    Args:
        path: The file to digest.

    Returns:
        The SHA-256 hex digest.

    Raises:
        OSError: If the file cannot be read.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class Workspace:
    """A reconstruction workspace, addressed by its root."""

    root: Path

    @property
    def clone(self) -> Path:
        """The pinned clone of the implementation under reconstruction."""
        return self.root / "clone"

    @property
    def corpus(self) -> Path:
        """The extracted commit corpus."""
        return self.root / "corpus"

    @property
    def commits(self) -> Path:
        """The corpus' commit rows."""
        return self.corpus / "commits.jsonl"

    @property
    def files(self) -> Path:
        """The corpus' per-file change rows."""
        return self.corpus / "files.jsonl"

    @property
    def forge(self) -> Path:
        """The forge cache root; snapshots live in dated subdirectories."""
        return self.root / "forge"

    @property
    def timeline(self) -> Path:
        """The clustered timeline."""
        return self.root / "timeline"

    @property
    def timeline_json(self) -> Path:
        """The timeline's summary, carrying the digests of its inputs."""
        return self.timeline / "timeline.json"

    @property
    def clusters_jsonl(self) -> Path:
        """One row per cluster, in timeline order."""
        return self.timeline / "clusters.jsonl"

    @property
    def clusters(self) -> Path:
        """One evidence folder per cluster."""
        return self.root / "clusters"

    @property
    def manifest(self) -> Path:
        """The claim manifest an agent mines."""
        return self.root / "manifest.yaml"

    @property
    def questions(self) -> Path:
        """The author-interview question register."""
        return self.root / "questions.yaml"

    @property
    def revisions(self) -> Path:
        """The draft's revision map."""
        return self.root / "revisions.yaml"

    @property
    def checkpoints(self) -> Path:
        """Frozen manifest states, one per processed cluster."""
        return self.root / "checkpoints"

    @property
    def draft(self) -> Path:
        """The Internet-Draft repository an agent writes prose into."""
        return self.root / "draft"

    @property
    def out(self) -> Path:
        """Reports and gate results."""
        return self.root / "out"

    def latest_forge_snapshot(self) -> Path | None:
        """The most recent forge snapshot, or ``None`` when none was fetched.

        Snapshots are named ``snapshot-<fetched_at>`` and never overwritten, so
        the newest is the last in sorted order. Enrichment is optional
        throughout, and its absence is a narrower reconstruction rather than a
        broken one.

        Returns:
            The snapshot directory holding ``meta.json``, or ``None``.
        """
        if not self.forge.is_dir():
            return None
        snapshots = [
            entry
            for repo in sorted(self.forge.iterdir())
            if repo.is_dir()
            for entry in sorted(repo.iterdir())
            if entry.is_dir() and (entry / "meta.json").exists()
        ]
        return snapshots[-1] if snapshots else None

    def clone_is_dirty(self) -> bool | None:
        """Whether the pinned clone has uncommitted changes.

        Returns:
            True or False, or ``None`` when the clone is not a git repository
            and the question does not apply.
        """
        if not (self.clone / ".git").exists():
            return None
        completed = subprocess.run(
            ["git", "-C", str(self.clone), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        return bool(completed.stdout.strip())
