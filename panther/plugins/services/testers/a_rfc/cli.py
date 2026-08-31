"""Command-line entry point for manifest validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from panther import __version__

from .report import build, to_json, to_markdown, to_yaml
from .schema import SchemaError, load


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it — and a gate
    that exits non-zero without saying why is the exact failure this module
    exists to prevent.
    """
    print(message, file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a_rfc",
        description=(
            "Validate a reconstructed requirement manifest: check its schema, "
            "adjudicate every claim against the promotion rule, and optionally "
            "verify repository anchors against their pinned commits."
        ),
    )
    parser.add_argument("--version", action="version", version=f"a_rfc {__version__}")
    parser.add_argument("manifest", type=Path, help="Path to the YAML manifest.")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Directory for report.json, report.yaml and report.md.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Clone against which repository anchors are verified.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit 3 on any finding: a claim recorded above what its evidence "
            "supports, or an anchor that does not resolve at its pinned commit."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Validate a manifest and write its report.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, 1 if the manifest or repository could not be read, and 3
        if any finding was reported while ``--strict`` was given. A finding is
        either a promotion violation or an anchor that did not resolve at its
        pinned commit; an anchor citing code absent from the commit it names is
        weaker evidence than an overstated status, not stronger, so both gate.

        2 is left to ``argparse``, which raises it for a malformed invocation.
        Sharing one code between "you typed the command wrong" and "the
        manifest overstates its evidence" left a caller unable to tell them
        apart, and they call for opposite responses.
    """
    args = _parser().parse_args(argv)

    try:
        manifest = load(args.manifest)
    except (SchemaError, OSError) as error:
        _report(f"error: could not read manifest {args.manifest}: {error}")
        return 1

    if args.repo is not None and not (args.repo / ".git").exists():
        _report(f"error: {args.repo} is not a git repository")
        return 1

    report = build(manifest, repo=args.repo)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(to_json(report))
    (args.out / "report.yaml").write_text(to_yaml(report))
    (args.out / "report.md").write_text(to_markdown(report))

    if not report.anchors_checked and report.verifiable_anchor_count:
        _report(
            f"note: --repo not given; {report.verifiable_anchor_count} anchor(s) "
            f"requiring a repository went unverified — --strict cannot fail on "
            f"anchors"
        )
    for violation in report.violations:
        _report(f"violation: {violation.claim_id}: {violation.reason}")
    for item in report.unverified:
        _report(f"unverified: {item}")

    if (report.violations or report.unverified) and args.strict:
        return 3
    return 0
