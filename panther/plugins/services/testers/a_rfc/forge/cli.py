"""Command-line entry point for forge fetching."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .fetch import Transport, fetch_pull_data, parse_url
from .store import ForgeError, write_snapshot


def _report(message: str) -> None:
    """Write a diagnostic to stderr.

    Deliberately not the ``logging`` module. Every ``panther.*`` logger is
    configured with ``propagate=False`` and a handler admitting only ``ERROR``,
    so a logged warning here is discarded before anyone sees it.
    """
    print(message, file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a_rfc.forge",
        description=(
            "Fetch a repository's pull/merge requests, reviews and comments "
            "from its forge into an immutable disk snapshot."
        ),
    )
    parser.add_argument("url", help="Repository URL on its forge.")
    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="The pinned clone; its HEAD is recorded so downstream stages can "
        "refuse a snapshot fetched against a different state.",
    )
    parser.add_argument("--out", type=Path, required=True, help="The forge cache root.")
    parser.add_argument(
        "--host",
        choices=("github", "gitlab"),
        default=None,
        help="Forge kind; inferred from the host name when omitted.",
    )
    return parser


def main(argv: list[str] | None = None, transport: Transport | None = None) -> int:
    """Fetch pull data and write one snapshot.

    Args:
        argv: Argument vector; ``None`` reads ``sys.argv``.
        transport: Transport override for tests; ``None`` uses urllib.

    Returns:
        0 on success, 1 if the clone or the forge could not be read, or the
        snapshot already exists.
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
