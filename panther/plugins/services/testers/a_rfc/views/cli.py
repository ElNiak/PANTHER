"""Command-line entry point for per-cluster view emission."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from panther import __version__

from .emit import ViewsError, emit_views, verify_views


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it.
    """
    print(message, file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a_rfc.views",
        description=(
            "Emit one evidence folder per timeline cluster: metadata, the "
            "member file set, and a deterministic span diff."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"a_rfc.views {__version__}"
    )
    parser.add_argument("timeline", type=Path, help="Timeline directory.")
    parser.add_argument(
        "--corpus",
        type=Path,
        required=True,
        help="Corpus the timeline was built from.",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="Pinned clone; its HEAD must still be the corpus tip.",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="Directory for the views."
    )
    parser.add_argument(
        "--only",
        default=None,
        help=(
            "Restrict to a single cluster id. Scopes --verify as well as "
            "emission, so a clean verify then covers only that cluster."
        ),
    )
    parser.add_argument(
        "--forge",
        type=Path,
        default=None,
        help=(
            "A forge snapshot directory; PR clusters carrying a pr_number "
            "get their pull record, reviews and comments copied into "
            "evidence/pr.json."
        ),
    )
    parser.add_argument(
        "--patches",
        choices=("span", "members"),
        default="span",
        help=(
            "span emits only the cluster span diff; members also emits one "
            "first-parent patch per member commit."
        ),
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Re-emit every view into scratch space and compare digests with "
            "what --out already holds; drift exits 3."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Emit or verify per-cluster views.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, 1 if the inputs could not be read or are stale, and 3
        when ``--verify`` found a view whose bytes no longer reproduce. 2 is
        left to ``argparse`` for a malformed invocation.
    """
    args = _parser().parse_args(argv)

    try:
        if args.verify:
            drifted = verify_views(
                args.timeline,
                args.corpus,
                args.repo,
                args.out,
                only=args.only,
                forge_snapshot=args.forge,
                patches=args.patches,
            )
            if drifted:
                for cluster_id in drifted:
                    _report(f"drift: {cluster_id} no longer reproduces")
                return 3
            scope = args.only if args.only else "every"
            _report(f"note: {scope} view reproduces byte-for-byte")
            return 0
        emitted = emit_views(
            args.timeline,
            args.corpus,
            args.repo,
            args.out,
            only=args.only,
            forge_snapshot=args.forge,
            patches=args.patches,
        )
    except (ViewsError, OSError) as error:
        _report(f"error: {error}")
        return 1

    _report(f"note: {len(emitted)} cluster view(s) written to {args.out}")
    return 0
