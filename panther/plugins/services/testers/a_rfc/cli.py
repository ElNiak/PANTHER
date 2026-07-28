"""Command-line entry point for manifest validation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .report import build, to_json, to_markdown, to_yaml
from .schema import SchemaError, load

logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a_rfc",
        description=(
            "Validate a reconstructed requirement manifest: check its schema, "
            "adjudicate every claim against the promotion rule, and optionally "
            "verify repository anchors against their pinned commits."
        ),
    )
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
        help="Exit 2 when any claim is recorded above what its evidence supports.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Validate a manifest and write its report.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, 1 if the manifest or repository could not be read, and 2
        if promotion violations were found while ``--strict`` was given.
    """
    args = _parser().parse_args(argv)

    if not logging.getLogger().handlers:
        logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    try:
        manifest = load(args.manifest)
    except (SchemaError, OSError) as error:
        logger.error("could not read manifest %s: %s", args.manifest, error)
        return 1

    if args.repo is not None and not (args.repo / ".git").exists():
        logger.error("%s is not a git repository", args.repo)
        return 1

    report = build(manifest, repo=args.repo)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(to_json(report))
    (args.out / "report.yaml").write_text(to_yaml(report))
    (args.out / "report.md").write_text(to_markdown(report))

    for violation in report.violations:
        logger.warning("%s: %s", violation.claim_id, violation.reason)

    if report.violations and args.strict:
        return 2
    return 0
