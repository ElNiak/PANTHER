"""Command-line entry point for the deterministic pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from panther import __version__

from .run import PipelineError, perform, workspace_from
from .stages import BY_NAME, STAGES, Performer
from .state import State, next_stage, state
from .substrate import check
from .workspace import Workspace


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it.
    """
    print(message, file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_rfc.pipeline",
        description=(
            "Run the deterministic stages of a reconstruction in order, "
            "stopping wherever a person or a model has to act."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"ai_rfc.pipeline {__version__}"
    )
    verbs = parser.add_subparsers(dest="verb", required=True)

    status = verbs.add_parser("status", help="Report every stage's state.")
    status.add_argument("workspace", type=Path, help="The workspace root.")
    status.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit pipeline-status.json to stdout instead of a table.",
    )

    substrate = verbs.add_parser(
        "substrate",
        help="Check that the pinned clone can carry a reconstruction.",
    )
    substrate.add_argument("workspace", type=Path, help="The workspace root.")

    run = verbs.add_parser("run", help="Perform the deterministic stages.")
    run.add_argument("workspace", type=Path, help="The workspace root.")
    run.add_argument(
        "--from",
        dest="start",
        choices=sorted(BY_NAME),
        default=None,
        help="First stage to run; default is wherever the workspace stands.",
    )
    run.add_argument(
        "--until",
        dest="until",
        choices=sorted(BY_NAME),
        default=None,
        help="Last stage to run; default is the next agent boundary.",
    )
    run.add_argument(
        "--forge-url", default=None, help="Repository URL, for the forge stage."
    )
    run.add_argument(
        "--host",
        choices=("github", "gitlab"),
        default=None,
        help="Forge kind; pass it for any self-hosted instance.",
    )
    run.add_argument(
        "--cluster", default=None, help="Cluster id, for the checkpoint stage."
    )
    run.add_argument(
        "--strict",
        action="store_true",
        help="Gate rather than lint in the stages that accept it.",
    )
    run.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit a machine-readable record of the run to stdout.",
    )
    return parser


def _status_payload(workspace: Path) -> dict:
    ws = workspace_from(workspace)
    action = next_stage(ws)
    return {
        "workspace": str(workspace),
        "stages": [
            {
                "ordinal": entry.stage.ordinal,
                "name": entry.stage.name,
                "kind": entry.stage.performer.value,
                "state": entry.state.value,
                "reason": entry.reason,
            }
            for entry in state(ws)
        ],
        # Recorded key. The Python name is `next_stage` — "action" was unbound
        # and it returns a Stage — but `pipeline-status.json` is what a driver
        # reads, so the key keeps the word it was published under.
        "next_action": (
            None
            if action is None
            else {
                "stage": action.stage.name,
                "kind": action.stage.performer.value,
                "state": action.state.value,
                "reason": action.reason,
                "instruction": action.stage.instruction,
            }
        ),
    }


def _print_status(payload: dict) -> None:
    for entry in payload["stages"]:
        line = f"{entry['ordinal']}  {entry['name']:<12} {entry['state']}"
        if entry["reason"]:
            line += f" — {entry['reason']}"
        print(line)
    action = payload["next_action"]
    print()
    if action is None:
        print("next: nothing outstanding")
        return
    print(f"next: {action['stage']} ({action['kind']}) — {action['reason']}")
    if action["instruction"]:
        print(f"      {action['instruction']}")


def _run(args: argparse.Namespace) -> int:
    ws = workspace_from(args.workspace)
    start = BY_NAME[args.start].ordinal if args.start else None
    until = BY_NAME[args.until].ordinal if args.until else None

    if start is None:
        action = next_stage(ws)
        if action is None:
            _report("note: nothing outstanding")
            return 0
        start = action.stage.ordinal

    performed: list[dict] = []
    halted_at: str | None = None
    code = 0
    for stage in STAGES:
        if stage.ordinal < start:
            continue
        if until is not None and stage.ordinal > until:
            break
        if stage.name == "forge" and args.forge_url is None:
            # Forge is the one networked stage and the only optional one: a
            # git-only timeline is a narrower reconstruction, not a broken one.
            # Skipping it without a URL matches how state steps over it, and
            # the two disagreeing is what this branch exists to prevent.
            if args.start == "forge":
                _report("error: forge was asked for but no --forge-url was given")
                return 1
            _report("note: skipping forge; no --forge-url given")
            continue
        if stage.performer is not Performer.DETERMINISTIC:
            # Reaching a boundary is the pipeline working, not failing: the
            # deterministic half is done and the next move is somebody else's.
            _report(
                f"boundary: stage {stage.ordinal} ({stage.name}) is "
                f"{stage.performer.value}; stopping here."
            )
            _report(f"next: {stage.instruction}")
            halted_at = stage.name
            break
        result = perform(
            stage,
            ws,
            strict=args.strict,
            cluster=args.cluster,
            forge_url=args.forge_url,
            host=args.host,
        )
        performed.append(
            {
                "stage": stage.name,
                "exit_code": result.exit_code,
                "argv": list(result.argv),
            }
        )
        if not result.ok:
            _report(f"error: {stage.name} exited {result.exit_code}")
            halted_at = stage.name
            code = result.exit_code
            break

    rederived = _perform_rederivable(args, ws, performed)
    if code == 0:
        code = rederived
    return _finish(args, performed, halted_at=halted_at, code=code)


def _perform_rederivable(
    args: argparse.Namespace, ws: Workspace, performed: list[dict]
) -> int:
    """Run the checks the stage walk cannot reach, and return the worst exit code.

    ``check`` and ``gate`` are the only re-derivable stages: neither records
    doneness and neither mutates the workspace beyond its own report, so both
    are safe to run whenever their inputs exist. The walk cannot reach them
    reliably — ``check`` sits at ordinal 6 but the agent boundary ``prose`` at 7
    ends the walk, and ``gate`` at 9 needs the draft ``prose`` produces — so
    they are performed by state instead.

    Args:
        args: The parsed arguments; ``strict`` decides whether findings exit 3.
        ws: The workspace to check.
        performed: The record the walk appended to; extended in place.

    Returns:
        The highest exit code any check returned, or 0.
    """
    states = {entry.stage.name: entry.state for entry in state(ws)}
    worst = 0
    for name in ("check", "gate"):
        if states.get(name) is not State.RECOMPUTED:
            continue
        if name == "gate" and states.get("prose") is not State.DONE:
            # `gate` reads the draft repository, the question register and the
            # revision log, none of which exist until `prose` has been written.
            continue
        result = perform(BY_NAME[name], ws, strict=args.strict, cluster=args.cluster)
        performed.append(
            {
                "stage": name,
                "exit_code": result.exit_code,
                "argv": list(result.argv),
            }
        )
        worst = max(worst, result.exit_code)
    return worst


def _finish(
    args: argparse.Namespace,
    performed: list[dict],
    *,
    halted_at: str | None,
    code: int = 0,
) -> int:
    if args.as_json:
        print(
            json.dumps(
                {
                    "workspace": str(args.workspace),
                    "performed": performed,
                    "halted_at": halted_at,
                },
                indent=2,
            )
        )
    return code


def main(argv: list[str] | None = None) -> int:
    """Report or advance a reconstruction workspace.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, including when the run stops at a stage a person or a
        model must perform — reaching a boundary is the pipeline working. 1 if
        the workspace could not be read or a stage was asked for that this
        command does not perform. Otherwise a stage's own exit code, so a
        strict gate's 3 reaches the caller unchanged. 2 is left to argparse.
    """
    args = _parser().parse_args(argv)
    try:
        if args.verb == "status":
            payload = _status_payload(args.workspace)
            if args.as_json:
                print(json.dumps(payload, indent=2))
            else:
                _print_status(payload)
            return 0
        if args.verb == "substrate":
            problems = check(Workspace(root=args.workspace).clone)
            for problem in problems:
                _report(f"error: {problem}")
            return 1 if problems else 0
        return _run(args)
    except (PipelineError, OSError) as error:
        _report(f"error: {error}")
        return 1
