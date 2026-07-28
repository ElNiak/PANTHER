"""Command-line entry point for corpus extraction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .git_log import DEFAULT_FILE_CAP, GitError, extract
from .index import build_index
from .store import write_corpus


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it.
    """
    print(message, file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a_rfc.history",
        description=(
            "Extract a repository's commit history into a deterministic JSONL "
            "corpus, with an optional SQLite index for querying."
        ),
    )
    parser.add_argument("repo", type=Path, help="Path to an existing clone.")
    parser.add_argument(
        "--out", type=Path, required=True, help="Directory for the corpus."
    )
    parser.add_argument(
        "--cap",
        type=int,
        default=DEFAULT_FILE_CAP,
        help=(
            "Maximum file rows recorded per commit. Commits above it are "
            "recorded with their true file count and flagged as truncated."
        ),
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Write the JSONL corpus without building the SQLite index.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Extract a repository into a corpus directory.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.

    Returns:
        0 on success, 1 if the repository could not be read — which includes a
        shallow clone, whose truncated history would otherwise pass silently.
    """
    args = _parser().parse_args(argv)

    try:
        commits, changes, report = extract(args.repo, cap=args.cap)
    except GitError as error:
        _report(f"error: {error}")
        return 1

    write_corpus(commits, changes, report, args.out)
    if not args.no_index:
        build_index(args.out)

    if report.truncated_count:
        _report(
            f"note: {report.truncated_count} commit(s) exceeded the "
            f"{args.cap}-file cap and were truncated; their true file counts "
            f"are recorded in {report.commit_count} commit records"
        )
    return 0
