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

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .. import cli as check_cli
from ..draft import cli as draft_cli
from ..entrypoints import CommandModule
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


@dataclass(frozen=True)
class _Request:
    """Everything any stage builder may need, so all of them share a signature.

    The uniform signature is what lets :data:`DISPATCH` be a table instead of a
    chain of ``elif``s, and a table is what lets one assertion prove it covers
    exactly the deterministic stages.
    """

    ws: Workspace
    strict: bool = False
    cluster: str | None = None
    forge_url: str | None = None
    host: str | None = None


_Builder = Callable[[_Request], "tuple[list[str], CommandModule]"]


def _history(req: _Request) -> tuple[list[str], CommandModule]:
    return [str(req.ws.clone), "--out", str(req.ws.corpus)], history_cli


def _forge(req: _Request) -> tuple[list[str], CommandModule]:
    if req.forge_url is None:
        raise PipelineError("forge needs --forge-url")
    from ..forge import cli as forge_cli

    argv = [
        "fetch",
        req.forge_url,
        "--repo",
        str(req.ws.clone),
        "--out",
        str(req.ws.forge),
    ]
    if req.host is not None:
        argv += ["--host", req.host]
    return argv, forge_cli


def _timeline(req: _Request) -> tuple[list[str], CommandModule]:
    ws = req.ws
    argv = [str(ws.corpus), "--out", str(ws.timeline), "--repo", str(ws.clone)]
    snapshot = ws.latest_forge_snapshot()
    if snapshot is not None:
        argv += ["--forge", str(snapshot)]
    return argv, timeline_cli


def _views(req: _Request) -> tuple[list[str], CommandModule]:
    ws = req.ws
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


def _check(req: _Request) -> tuple[list[str], CommandModule]:
    ws = req.ws
    argv = [str(ws.manifest), "--out", str(ws.out), "--repo", str(ws.clone)]
    if req.strict:
        argv.append("--strict")
    return argv, check_cli


def _checkpoint(req: _Request) -> tuple[list[str], CommandModule]:
    if req.cluster is None:
        raise PipelineError("checkpoint needs --cluster")
    ws = req.ws
    return [
        "checkpoint",
        str(ws.manifest),
        "--timeline",
        str(ws.timeline),
        "--cluster",
        req.cluster,
        "--out",
        str(ws.checkpoints),
    ], draft_cli


def _gate(req: _Request) -> tuple[list[str], CommandModule]:
    ws = req.ws
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
    if req.strict:
        argv.append("--strict")
    return argv, draft_cli


#: Stage name to the builder that turns a request into that stage's argv. A
#: table rather than a chain of ``elif``s, because the correspondence with
#: ``STAGES`` is then one assertion instead of seven branches nobody re-reads:
#: a stage renamed in ``stages.py`` but missed here used to fall through to a
#: refusal that called a deterministic stage handed-over, and no test noticed.
DISPATCH: dict[str, _Builder] = {
    "history": _history,
    "forge": _forge,
    "timeline": _timeline,
    "views": _views,
    "check": _check,
    "checkpoint": _checkpoint,
    "gate": _gate,
}


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
    builder = DISPATCH.get(stage.name)
    if builder is None:
        raise PipelineError(
            f"{stage.name} is a {stage.performer.value} stage; the pipeline reports "
            f"it and stops rather than performing it"
        )

    argv, module = builder(
        _Request(ws, strict=strict, cluster=cluster, forge_url=forge_url, host=host)
    )
    ws.root.mkdir(parents=True, exist_ok=True)
    return StageResult(stage, module.main(argv), tuple(argv))


def workspace_from(root: Path) -> Workspace:
    """Build a workspace handle for a root directory.

    Args:
        root: The workspace root.

    Returns:
        The handle every other function here takes.
    """
    return Workspace(root=root)
