"""Command-line entry point for timeline clustering."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .build import build_timeline
from .corpus import TimelineError, find_tip, read_commits
from .store import write_timeline


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it.
    """
    print(message, file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a_rfc.timeline",
        description=(
            "Cluster a commit corpus into a total-ordered timeline of PR "
            "clusters and epoch clusters of direct pushes."
        ),
    )
    parser.add_argument("corpus", type=Path, help="Directory holding the corpus.")
    parser.add_argument(
        "--out", type=Path, required=True, help="Directory for the timeline."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help=(
            "Clone the corpus was extracted from; its HEAD must equal the "
            "corpus tip, or the run is refused."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Cluster a corpus into a timeline directory.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, 1 if the corpus could not be read or clustered, or if
        ``--repo`` names a clone whose HEAD is not the corpus tip.
    """
    args = _parser().parse_args(argv)

    try:
        commits = read_commits(args.corpus)
        tip = find_tip(commits)
    except (TimelineError, OSError) as error:
        _report(f"error: {error}")
        return 1

    if args.repo is not None:
        head = subprocess.run(
            ["git", "-C", str(args.repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        if head.returncode != 0:
            _report(
                f"error: {args.repo} is not a git repository: {head.stderr.strip()}"
            )
            return 1
        if head.stdout.strip() != tip:
            _report(
                f"error: {args.repo} HEAD {head.stdout.strip()} is not the "
                f"corpus tip {tip}; the corpus and the clone have diverged"
            )
            return 1

    try:
        clusters = build_timeline(commits)
    except TimelineError as error:
        _report(f"error: {error}")
        return 1

    write_timeline(clusters, tip, args.corpus, args.out)

    pr_count = sum(1 for cluster in clusters if cluster.kind == "pr")
    _report(
        f"note: {len(clusters)} clusters ({pr_count} pr, "
        f"{len(clusters) - pr_count} epoch) over {len(commits)} commits"
    )
    return 0
