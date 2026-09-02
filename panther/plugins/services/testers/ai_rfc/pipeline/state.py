"""Read a workspace's state off its own artifacts.

Nothing records what has been run. The substrate already writes the digest of
every stage's inputs into that stage's output — ``timeline.json`` carries the
corpus digests, a ``view.json`` carries the timeline's, a ``checkpoint.json``
carries the manifest's — so "is this still current?" is a question the
artifacts already answer.

A run ledger would answer it faster and would start lying the first time
somebody ran a sub-CLI by hand, which the authoring loop actively tells them to
do. The state here is derived on every call for that reason. ``status`` emits
``pipeline-status.json`` for a driver to read, but nothing reads it back as
authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..forge.store import FIDELITY_CEILINGS, FULL_FIDELITY
from ..schema import SchemaError, load
from .stages import STAGES, Performer, Stage
from .workspace import Workspace, digest


class State(Enum):
    """What a stage's artifacts say about it."""

    #: Produced, and consistent with the inputs currently on disk.
    DONE = "done"
    #: Produced for some of the units it covers, but not all of them. Unlike
    #: ``STALE``, what exists is correct and stays: the stage is resumed rather
    #: than re-run. A stage that grades doneness by asking whether it produced
    #: *anything* cannot report this, and so reports a reconstruction of two
    #: clusters in sixty-nine as finished.
    PARTIAL = "partial"
    #: Produced, but an input has moved since. Re-run it.
    STALE = "stale"
    #: Not produced yet, and everything it needs is ready.
    PENDING = "pending"
    #: Not produced, and something upstream is not ready either.
    BLOCKED = "blocked"
    #: Pure, cheap and idempotent, so doneness is not tracked: the runner just
    #: performs it. Its output carries no digest of its input, and adding one
    #: would cost more than re-deriving the answer.
    RECOMPUTED = "re-derivable"


@dataclass(frozen=True)
class StageState:
    """One stage's state, and why."""

    stage: Stage
    state: State
    reason: str = ""


@dataclass(frozen=True)
class NextStage:
    """The first thing that needs doing, and who does it."""

    stage: Stage
    state: State
    reason: str

    @property
    def is_agent(self) -> bool:
        """Whether this stage needs a model rather than the runner."""
        return self.stage.performer is Performer.AGENT


def _read_json(path: Path) -> dict | None:
    """Parse an artifact, or return ``None`` when it is unusable.

    A malformed artifact is a stage that needs re-running, not an error to
    raise at the caller: probing a half-written workspace is exactly when this
    happens, and it is the situation the report exists to describe.

    Args:
        path: The artifact to read.

    Returns:
        The parsed object, or ``None`` if it is not readable JSON.
    """
    try:
        parsed = json.loads(path.read_text())
    except (ValueError, OSError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _pin(ws: Workspace) -> tuple[State, str]:
    """The clone's state.

    An uncommitted change is reported but does not block. Nothing downstream
    reads the working tree: history extracts from ``git log``, views reads git
    objects, and anchors resolve through ``git show <commit>:<path>``. Blocking
    on dirt would hide a corpus, timeline and views that are all perfectly
    current — which is what it did before this was noticed against a real
    workspace.
    """
    if not (ws.clone / ".git").exists():
        return State.PENDING, f"{ws.clone} is not a git repository"
    if ws.clone_is_dirty():
        return State.DONE, (
            "note: the clone has uncommitted changes. Nothing downstream reads "
            "the working tree, but they are invisible to every anchor."
        )
    return State.DONE, ""


def _history(ws: Workspace, pin: State) -> tuple[State, str]:
    if pin is not State.DONE:
        return State.BLOCKED, "the clone is not pinned"
    if not (ws.commits.exists() and ws.files.exists()):
        return State.PENDING, f"no corpus in {ws.corpus}"
    return State.DONE, ""


def _forge(ws: Workspace) -> tuple[State, str]:
    snapshot = ws.latest_forge_snapshot()
    if snapshot is None:
        return State.PENDING, (
            "no forge snapshot; the timeline will be built from git alone, "
            "which on a squash-heavy repository sees far fewer pull requests"
        )
    meta = _read_json(snapshot / "meta.json")
    if meta is None:
        return State.STALE, f"{snapshot.name}/meta.json is unreadable"
    denied = meta.get("denied_subfetches", 0)
    ceiling = meta.get("fidelity_ceiling")
    if ceiling in FIDELITY_CEILINGS and ceiling != FULL_FIDELITY:
        # Reported whether or not the route refused anything: adoption refuses
        # nothing, so it is `complete` while still carrying no discussion, and
        # grading on completeness alone would report it as a full fetch.
        refused = f" {denied} richer endpoint(s) were refused, and" if denied else ""
        return State.DONE, (
            f"note: {snapshot.name} reaches {ceiling}, the ceiling of the "
            f"route that wrote it.{refused} re-running that route cannot "
            f"improve it. Clustering reads nothing that is missing."
        )
    if not meta.get("complete", False):
        return State.STALE, (
            f"{snapshot.name} is incomplete: {denied} sub-fetch(es) were "
            f"denied. Set GITHUB_TOKEN or GITLAB_TOKEN and fetch again."
        )
    return State.DONE, ""


def _timeline(ws: Workspace, history: State) -> tuple[State, str]:
    if history is not State.DONE:
        return State.BLOCKED, "there is no corpus to cluster"
    if not ws.timeline_json.exists():
        return State.PENDING, f"no timeline in {ws.timeline}"
    recorded = _read_json(ws.timeline_json)
    if recorded is None:
        return State.STALE, f"{ws.timeline_json.name} is unreadable"
    for key, path in (("commits_sha256", ws.commits), ("files_sha256", ws.files)):
        if recorded.get(key) != digest(path):
            return State.STALE, f"{path.name} changed since the timeline was built"
    return State.DONE, ""


def _cluster_ids(ws: Workspace) -> list[str]:
    """Every cluster id the timeline names, in order.

    Callers reach this only once the timeline itself has been found current, so
    a row that will not parse is a corrupt artifact rather than a state to
    report, and is left to surface as the error it is.
    """
    return [
        json.loads(line)["id"] for line in ws.clusters_jsonl.read_text().splitlines()
    ]


def _views(ws: Workspace, timeline: State) -> tuple[State, str]:
    if timeline is not State.DONE:
        return State.BLOCKED, "the timeline is not current"
    ids = _cluster_ids(ws)
    missing = [cid for cid in ids if not (ws.clusters / cid / "view.json").exists()]
    if len(missing) == len(ids):
        return State.PENDING, f"no views in {ws.clusters}"
    if missing:
        return State.STALE, f"{len(missing)} of {len(ids)} cluster(s) have no view"
    current = digest(ws.timeline_json)
    for cid in ids:
        view = _read_json(ws.clusters / cid / "view.json")
        if view is None:
            return State.STALE, f"{cid}/view.json is unreadable"
        if view.get("source", {}).get("timeline_sha256") != current:
            return State.STALE, f"{cid} was emitted from an older timeline"
    return State.DONE, ""


def _mining(ws: Workspace, views: State) -> tuple[State, str]:
    if views is not State.DONE:
        return State.BLOCKED, "there is no cluster evidence to mine"
    if not ws.manifest.exists():
        return State.PENDING, f"no manifest at {ws.manifest}"
    try:
        manifest = load(ws.manifest)
    except (SchemaError, OSError) as error:
        return State.STALE, f"the manifest does not load: {error}"
    if not manifest.claims:
        return State.PENDING, "the manifest holds no claims yet"
    return State.DONE, ""


def _checkpoint(ws: Workspace, mining: State) -> tuple[State, str]:
    if mining is not State.DONE:
        return State.BLOCKED, "there is no manifest to freeze"
    # Counted per cluster id, not per directory. A checkpoint directory is
    # named for its cluster, written once and never pruned, so a re-clustering
    # that changes ids leaves orphans behind — and a bare directory count then
    # reads "2 of 2" for a timeline whose second cluster was never frozen at
    # all, which is the false "done" this whole state exists to prevent.
    #
    # A directory alone is also not a checkpoint: ``write_checkpoint`` creates
    # it before writing the record, so a kill between the two leaves one that
    # holds nothing. Requiring the record matches what ``draft/completeness``
    # and the harness's own metrics already count, so the three agree.
    ids = _cluster_ids(ws)
    total = len(ids)
    frozen = sum(
        1 for cid in ids if (ws.checkpoints / cid / "checkpoint.json").is_file()
    )
    if not frozen:
        return State.PENDING, f"no cluster checkpointed of {total}"
    if frozen < total:
        return State.PARTIAL, f"{frozen} of {total} cluster(s) checkpointed"
    return State.DONE, f"{frozen} of {total} cluster(s) checkpointed"


def _prose(ws: Workspace, mining: State) -> tuple[State, str]:
    if mining is not State.DONE:
        return State.BLOCKED, "there are no claims to cite"
    if not (ws.draft / ".git").exists():
        return State.PENDING, f"{ws.draft} is not a draft repository"
    if not ws.revisions.exists():
        return State.PENDING, "no revision has been recorded"
    return State.DONE, ""


def state(ws: Workspace) -> tuple[StageState, ...]:
    """Read every stage's state off the workspace.

    Args:
        ws: The workspace to read.

    Returns:
        One :class:`StageState` per stage, in pipeline order.

    Raises:
        OSError: If an artifact exists but cannot be read.
    """
    pin = _pin(ws)
    history = _history(ws, pin[0])
    timeline = _timeline(ws, history[0])
    views = _views(ws, timeline[0])
    mining = _mining(ws, views[0])
    rederivable = (
        (State.RECOMPUTED, "")
        if mining[0] is State.DONE
        else (State.BLOCKED, "there is no manifest to check")
    )
    by_name: dict[str, tuple[State, str]] = {
        "pin": pin,
        "history": history,
        "forge": _forge(ws),
        "timeline": timeline,
        "views": views,
        "mining": mining,
        "check": rederivable,
        "prose": _prose(ws, mining[0]),
        "checkpoint": _checkpoint(ws, mining[0]),
        "gate": rederivable,
    }
    return tuple(StageState(stage, *by_name[stage.name]) for stage in STAGES)


def next_stage(ws: Workspace) -> NextStage | None:
    """The first stage that still needs doing.

    This is the function a driver outside the package calls: it says what to do
    next and whether the runner or a model does it, without the caller needing
    to know the stage table.

    ``forge`` never blocks. Its enrichment is optional — a git-only timeline is
    a narrower reconstruction, not a broken one — so a workspace with no
    snapshot is reported by :func:`state` and stepped over here.

    Args:
        ws: The workspace to read.

    Returns:
        The next action, or ``None`` when nothing is outstanding.

    Raises:
        OSError: If an artifact exists but cannot be read.
    """
    for entry in state(ws):
        if entry.stage.name == "forge":
            continue
        if entry.state in (State.DONE, State.RECOMPUTED):
            continue
        return NextStage(entry.stage, entry.state, entry.reason)
    return None
