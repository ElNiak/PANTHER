"""Command-line entry point for runtime-anchor proposals."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import yaml

from panther import __version__

from ..schema import SchemaError, load
from .commit import PinError
from .jacoco import CoverageError
from .jacoco import read as read_jacoco
from .propose import PROPOSAL_CRITERION, propose

#: Coverage formats this command can read. The internal model is
#: tool-agnostic; adding a format is adding a reader here.
READERS = {"jacoco": read_jacoco}


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it.
    """
    print(message, file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a_rfc.runtime",
        description=(
            "Propose runtime anchors for the claims whose cited code lines a "
            "test run actually reached. Writes proposals; never edits the "
            "manifest."
        ),
        epilog=(
            "note:\n"
            "  A runtime anchor is primary evidence, so merging one beside an\n"
            "  existing code anchor takes a claim to confirmed. The criterion\n"
            "  is line-executed: the line ran. Nothing in a coverage report\n"
            "  says an assertion examined what it did.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"a_rfc.runtime {__version__}"
    )
    parser.add_argument("manifest", type=Path, help="The manifest to corroborate.")
    parser.add_argument(
        "--coverage", type=Path, required=True, help="The coverage report to read."
    )
    parser.add_argument(
        "--format",
        choices=sorted(READERS),
        default="jacoco",
        help="Coverage format (default: %(default)s).",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="The clone the run came from; must be at --commit and clean.",
    )
    parser.add_argument(
        "--commit",
        required=True,
        help="The commit the anchors are pinned to.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Directory for runtime-anchors.yaml and runtime-anchors.json.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Propose runtime anchors from one coverage run.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, including when a run corroborates nothing — a report
        that reached none of the cited lines is a finding about the test suite,
        not a failure of this command. 1 if an input could not be read or the
        checkout could not be bound. 2 is left to argparse.
    """
    args = _parser().parse_args(argv)

    try:
        manifest = load(args.manifest)
        report = READERS[args.format](args.coverage)
        proposals, skipped = propose(manifest, report, args.repo, args.commit)
    except (SchemaError, CoverageError, PinError, OSError) as error:
        _report(f"error: {error}")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    fragment = {"requirements": {}}
    for proposal in proposals:
        entry = fragment["requirements"].setdefault(proposal.claim_id, {"anchors": []})
        entry["anchors"].append(
            {
                "evidence_class": "runtime",
                "locator": proposal.locator,
                "commit": proposal.commit,
                "line": proposal.line,
                "line_sha256": proposal.line_sha256,
            }
        )
    (args.out / "runtime-anchors.yaml").write_text(
        yaml.safe_dump(fragment, sort_keys=True, default_flow_style=False)
    )
    (args.out / "runtime-anchors.json").write_text(
        json.dumps(
            {
                "tool": report.tool,
                "tool_version": report.tool_version,
                "report_sha256": report.report_sha256,
                "criterion": PROPOSAL_CRITERION,
                "commit": args.commit,
                "proposed": [asdict(proposal) for proposal in proposals],
                "skipped": [asdict(entry) for entry in skipped],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    _report(
        f"note: {len(proposals)} runtime anchor(s) proposed, "
        f"{len(skipped)} code anchor(s) not corroborated"
    )
    if not proposals and skipped:
        _report(
            "note: the run reached none of the cited lines. That is a fact "
            "about the test suite, not about the claims."
        )
    return 0
