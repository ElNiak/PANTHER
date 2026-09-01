"""Command-line entry point for checkpoints and the citation gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from panther import __version__

from ..schema import SchemaError
from .checkpoint import CheckpointError, write_checkpoint
from .completeness import CompletenessError
from .completeness import build as build_completeness
from .completeness import findings as completeness_findings
from .completeness import to_json as completeness_json
from .gate import GateError, run_gate


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it.
    """
    print(message, file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a_rfc.draft",
        description=(
            "Freeze manifest checkpoints against timeline clusters, and gate "
            "a prose draft's revision map against them."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"a_rfc.draft {__version__}"
    )
    verbs = parser.add_subparsers(dest="verb", required=True)

    checkpoint = verbs.add_parser(
        "checkpoint", help="Freeze a manifest against one timeline cluster."
    )
    checkpoint.add_argument("manifest", type=Path, help="Manifest to freeze.")
    checkpoint.add_argument(
        "--timeline", type=Path, required=True, help="Timeline directory."
    )
    checkpoint.add_argument(
        "--cluster", required=True, help="Cluster id the manifest state belongs to."
    )
    checkpoint.add_argument(
        "--out", type=Path, required=True, help="Checkpoints root directory."
    )

    gate = verbs.add_parser(
        "gate", help="Run the deterministic citation gate over a draft."
    )
    gate.add_argument("draftrepo", type=Path, help="The nested draft repository.")
    gate.add_argument(
        "--timeline", type=Path, required=True, help="Timeline directory."
    )
    gate.add_argument(
        "--checkpoints", type=Path, required=True, help="Checkpoints root."
    )
    gate.add_argument(
        "--questions", type=Path, required=True, help="Question register."
    )
    gate.add_argument("--revisions", type=Path, required=True, help="Revision map.")
    gate.add_argument(
        "--out", type=Path, required=True, help="Directory for gate-report.json."
    )
    gate.add_argument(
        "--strict",
        action="store_true",
        help="Exit 3 when any finding is reported.",
    )

    complete = verbs.add_parser(
        "completeness",
        help="Report which clusters produced no claim and which claims no "
        "prose cites.",
    )
    complete.add_argument(
        "workspace",
        type=Path,
        help="Workspace root holding timeline/, checkpoints/, draft/, "
        "manifest.yaml and revisions.yaml.",
    )
    complete.add_argument(
        "--out", type=Path, required=True, help="Directory for completeness.json."
    )
    complete.add_argument(
        "--strict",
        action="store_true",
        help="Exit 3 when any finding is reported.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the requested verb.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, 1 if an input could not be read or interpreted, and 3
        when ``gate --strict`` or ``completeness --strict`` reported findings.
    """
    args = _parser().parse_args(argv)

    if args.verb == "checkpoint":
        try:
            checkpoint_dir = write_checkpoint(
                args.manifest, args.timeline, args.cluster, args.out
            )
        except (CheckpointError, SchemaError, OSError) as error:
            _report(f"error: {error}")
            return 1
        _report(f"note: checkpoint written to {checkpoint_dir}")
        return 0

    if args.verb == "completeness":
        workspace = args.workspace
        try:
            report = build_completeness(
                workspace / "timeline",
                workspace / "checkpoints",
                workspace / "manifest.yaml",
                workspace / "revisions.yaml",
                workspace / "draft",
            )
        except (CompletenessError, OSError) as error:
            _report(f"error: {error}")
            return 1

        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "completeness.json").write_text(completeness_json(report))

        found = completeness_findings(report)
        for finding in found:
            _report(f"finding: {finding}")
        if not found:
            _report("note: reconstruction complete")
        if found and args.strict:
            return 3
        return 0

    try:
        findings = run_gate(
            args.draftrepo,
            args.timeline,
            args.checkpoints,
            args.questions,
            args.revisions,
        )
    except (GateError, OSError) as error:
        _report(f"error: {error}")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "gate-report.json").write_text(
        json.dumps({"findings": list(findings)}, sort_keys=True, indent=2) + "\n"
    )

    for finding in findings:
        _report(f"finding: {finding}")
    if findings and args.strict:
        return 3
    if not findings:
        _report("note: gate clean")
    return 0
