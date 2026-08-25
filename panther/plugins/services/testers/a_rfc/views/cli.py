"""Command-line entry point for per-cluster view emission."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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
        "--only", default=None, help="Emit a single cluster id instead of all."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Re-emit every view into scratch space and compare digests with "
            "what --out already holds; drift exits 2."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Emit or verify per-cluster views.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, 1 if the inputs could not be read or are stale, and 2
        when ``--verify`` found a view whose bytes no longer reproduce.
    """
    args = _parser().parse_args(argv)

    try:
        if args.verify:
            drifted = verify_views(args.timeline, args.corpus, args.repo, args.out)
            if drifted:
                for cluster_id in drifted:
                    _report(f"drift: {cluster_id} no longer reproduces")
                return 2
            _report("note: every view reproduces byte-for-byte")
            return 0
        emitted = emit_views(
            args.timeline, args.corpus, args.repo, args.out, only=args.only
        )
    except (ViewsError, OSError) as error:
        _report(f"error: {error}")
        return 1

    _report(f"note: {len(emitted)} cluster view(s) written to {args.out}")
    return 0
