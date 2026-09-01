"""Command-line entry point for forge fetching."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from panther import __version__

from .fetch import Transport, fetch_pull_data, parse_url
from .store import ForgeError, write_snapshot


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it.
    """
    print(message, file=sys.stderr)


def _add_target_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the arguments every verb needs to place a snapshot on disk.

    Both verbs pin the same clone and write into the same cache root; only
    where the records come from differs.
    """
    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="The pinned clone; its HEAD is recorded so downstream stages can "
        "refuse a snapshot fetched against a different state.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help=(
            "The forge cache root. Snapshots land in a timestamped subdirectory "
            "beneath it, so this is NOT the path downstream --forge arguments "
            "want; they want the individual snapshot directory holding "
            "meta.json."
        ),
    )
    parser.add_argument(
        "--host",
        choices=("github", "gitlab"),
        default=None,
        help=(
            "Forge kind. When omitted it is inferred from the host name, and "
            "the inference recognises only github.com as GitHub — pass this "
            "explicitly for a self-hosted instance of either kind."
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_rfc.forge",
        description=(
            "Collect a repository's pull/merge requests, reviews and comments "
            "into an immutable disk snapshot — from the forge API, or from "
            "records obtained without credentials."
        ),
        epilog=(
            "environment:\n"
            "  GITHUB_TOKEN, GITLAB_TOKEN\n"
            "                        Read for the matching forge kind. Without\n"
            "                        one the fetch is unauthenticated:\n"
            "                        discussion endpoints are refused, the\n"
            "                        snapshot records complete: false with a\n"
            "                        denied_subfetches count, and the command\n"
            "                        still exits 0. Read meta.json before\n"
            "                        treating a snapshot as whole.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"ai_rfc.forge {__version__}"
    )
    verbs = parser.add_subparsers(dest="verb", required=True)

    fetch = verbs.add_parser("fetch", help="Fetch pull data from the forge API.")
    fetch.add_argument("url", help="Repository URL on its forge.")
    _add_target_arguments(fetch)

    adopt = verbs.add_parser(
        "adopt",
        help="Write a snapshot from records obtained outside this tool.",
    )
    adopt.add_argument(
        "records",
        type=Path,
        help=(
            "A JSON file holding {pulls, reviews, comments} already shaped "
            "like a snapshot's rows — from a forge export, a glab/gh dump, or "
            "another operator's snapshot."
        ),
    )
    adopt.add_argument(
        "url",
        help="Repository URL the records describe. Nothing is fetched from it; "
        "it names the host, owner and repo the snapshot is filed under.",
    )
    _add_target_arguments(adopt)

    return parser


def main(argv: list[str] | None = None, transport: Transport | None = None) -> int:
    """Collect pull data by the chosen route and write one snapshot.

    Both verbs pin the same clone and write through the same writer; they
    differ only in where the records come from, which the snapshot records so
    a reader can tell how much the route could ever have delivered.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.
        transport: Transport override for tests; ``None`` uses urllib.

    Returns:
        0 on success, 1 if the clone, the forge or the records could not be
        read, or the snapshot already exists.
    """
    args = _parser().parse_args(argv)

    try:
        target = parse_url(args.url, args.host)
    except ForgeError as error:
        _report(f"error: {error}")
        return 1

    head = subprocess.run(
        ["git", "-C", str(args.repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    if head.returncode != 0:
        _report(f"error: {args.repo} is not a git repository: {head.stderr.strip()}")
        return 1

    if args.verb == "adopt":
        _report("error: adopt is not implemented yet")
        return 1

    token_env = "GITHUB_TOKEN" if target.kind == "github" else "GITLAB_TOKEN"
    token = os.environ.get(token_env) or None

    try:
        result = fetch_pull_data(target, transport=transport, token=token)
        snapshot = write_snapshot(
            args.out,
            host=target.host,
            owner=target.owner,
            repo=target.repo,
            kind=target.kind,
            clone_head=head.stdout.strip(),
            fetched_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ"),
            authenticated=token is not None,
            pulls=result.pulls,
            reviews=result.reviews,
            comments=result.comments,
            denied_subfetches=result.denied_subfetches,
            acquisition="api",
            fidelity_ceiling="pulls+discussion" if token else "pulls",
        )
    except (ForgeError, OSError) as error:
        _report(f"error: {error}")
        return 1

    _report(
        f"note: {len(result.pulls)} pull(s), {len(result.reviews)} review(s), "
        f"{len(result.comments)} comment(s) written to {snapshot} "
        f"(authenticated: {token is not None})"
    )
    if result.denied_subfetches:
        _report(
            f"note: {result.denied_subfetches} discussion endpoint(s) were "
            f"refused by the forge (set {token_env} for full discussion "
            f"data); the snapshot records the denial"
        )
    return 0
