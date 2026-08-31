"""Perform the deterministic stages by calling the sub-CLIs in process.

Each stage is the same command a person would type, built here instead of
typed. The sub-packages are reached through ``cli.main(argv)`` and nothing
else: data still hands over on disk, exactly as it does when the commands are
run by hand, so chaining them changes how they are invoked and not what they
share.

An ``argparse`` failure inside a sub-CLI raises ``SystemExit(2)`` rather than
returning, and it is deliberately not caught. Every argv here is built by this
module, so a usage error means this module built one wrong — a defect that
should surface loudly rather than be translated into a stage failure that looks
like the workspace's fault.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import cli as adjudicate_cli
from ..draft import cli as draft_cli
from ..history import cli as history_cli
from ..timeline import cli as timeline_cli
from ..views import cli as views_cli
from .stages import Stage
from .workspace import Workspace


class PipelineError(RuntimeError):
    """Raised when a stage cannot be attempted as asked."""


@dataclass(frozen=True)
class StageResult:
    """What one stage did."""

    stage: Stage
    exit_code: int
    argv: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Whether the stage succeeded."""
        return self.exit_code == 0


def _history(ws: Workspace) -> tuple[list[str], object]:
    return [str(ws.clone), "--out", str(ws.corpus)], history_cli


def _timeline(ws: Workspace) -> tuple[list[str], object]:
    argv = [str(ws.corpus), "--out", str(ws.timeline), "--repo", str(ws.clone)]
    snapshot = ws.latest_forge_snapshot()
    if snapshot is not None:
        argv += ["--forge", str(snapshot)]
    return argv, timeline_cli


def _views(ws: Workspace) -> tuple[list[str], object]:
    argv = [
        str(ws.timeline),
        "--corpus",
        str(ws.corpus),
        "--repo",
        str(ws.clone),
        "--out",
        str(ws.clusters),
    ]
    snapshot = ws.latest_forge_snapshot()
    if snapshot is not None:
        argv += ["--forge", str(snapshot)]
    return argv, views_cli


def _adjudicate(ws: Workspace, strict: bool) -> tuple[list[str], object]:
    argv = [str(ws.manifest), "--out", str(ws.out), "--repo", str(ws.clone)]
    if strict:
        argv.append("--strict")
    return argv, adjudicate_cli


def _checkpoint(ws: Workspace, cluster: str) -> tuple[list[str], object]:
    return [
        "checkpoint",
        str(ws.manifest),
        "--timeline",
        str(ws.timeline),
        "--cluster",
        cluster,
        "--out",
        str(ws.checkpoints),
    ], draft_cli


def _gate(ws: Workspace, strict: bool) -> tuple[list[str], object]:
    argv = [
        "gate",
        str(ws.draft),
        "--timeline",
        str(ws.timeline),
        "--checkpoints",
        str(ws.checkpoints),
        "--questions",
        str(ws.questions),
        "--revisions",
        str(ws.revisions),
        "--out",
        str(ws.out),
    ]
    if strict:
        argv.append("--strict")
    return argv, draft_cli


def perform(
    stage: Stage,
    ws: Workspace,
    *,
    strict: bool = False,
    cluster: str | None = None,
    forge_url: str | None = None,
    host: str | None = None,
) -> StageResult:
    """Run one deterministic stage.

    Args:
        stage: The stage to run. Must be deterministic; ``pin``, ``mining`` and
            ``prose`` are performed by a human or a model, not here.
        ws: The workspace to act on.
        strict: Gate rather than lint, for the two stages that accept it.
        cluster: The cluster id ``checkpoint`` freezes against.
        forge_url: The repository URL ``forge`` fetches.
        host: The forge kind, when it cannot be inferred from the URL.

    Returns:
        What the stage's CLI returned.

    Raises:
        PipelineError: If the stage is not one this module performs, or a
            required argument for it is missing.
        SystemExit: If a built argv is malformed, which is a defect here.
    """
    if stage.name == "forge":
        if forge_url is None:
            raise PipelineError("forge needs --forge-url")
        from ..forge import cli as forge_cli

        argv = [forge_url, "--repo", str(ws.clone), "--out", str(ws.forge)]
        if host is not None:
            argv += ["--host", host]
        module: object = forge_cli
    elif stage.name == "history":
        argv, module = _history(ws)
    elif stage.name == "timeline":
        argv, module = _timeline(ws)
    elif stage.name == "views":
        argv, module = _views(ws)
    elif stage.name == "adjudicate":
        argv, module = _adjudicate(ws, strict)
    elif stage.name == "checkpoint":
        if cluster is None:
            raise PipelineError("checkpoint needs --cluster")
        argv, module = _checkpoint(ws, cluster)
    elif stage.name == "gate":
        argv, module = _gate(ws, strict)
    else:
        raise PipelineError(
            f"{stage.name} is a {stage.kind.value} stage; the pipeline reports "
            f"it and stops rather than performing it"
        )

    ws.root.mkdir(parents=True, exist_ok=True)
    return StageResult(stage, module.main(argv), tuple(argv))  # type: ignore[attr-defined]


def workspace_from(root: Path) -> Workspace:
    """Build a workspace handle for a root directory.

    Args:
        root: The workspace root.

    Returns:
        The handle every other function here takes.
    """
    return Workspace(root=root)
