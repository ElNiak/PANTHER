"""Command-line entry point for timeline clustering."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from panther import __version__

from .build import build_timeline
from .corpus import TimelineError, find_tip, read_commits
from .store import write_timeline


def _read_forge_snapshot(
    snapshot: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Read a forge snapshot's meta and pull records.

    Deliberately re-parses the files instead of importing ``forge/`` — the
    corpus-side subpackages hand data to each other on disk, never through
    imports, so each can move without dragging the others along.
    """
    meta = json.loads((snapshot / "meta.json").read_text())
    pulls = [
        json.loads(line) for line in (snapshot / "pulls.jsonl").read_text().splitlines()
    ]
    return meta, pulls


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
    parser.add_argument(
        "--version", action="version", version=f"a_rfc.timeline {__version__}"
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
    parser.add_argument(
        "--forge",
        type=Path,
        default=None,
        help=(
            "A forge snapshot directory; merged pulls enrich their merge "
            "clusters and squash-landed pulls are rescued into PR clusters. "
            "The snapshot must have been fetched at the corpus tip."
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

    forge_pulls = None
    forge_descriptor = None
    if args.forge is not None:
        try:
            forge_meta, forge_pulls = _read_forge_snapshot(args.forge)
        except (OSError, ValueError) as error:
            _report(f"error: could not read forge snapshot {args.forge}: {error}")
            return 1
        if forge_meta["clone_head"] != tip:
            _report(
                f"error: forge snapshot was fetched at "
                f"{forge_meta['clone_head']} but the corpus tip is "
                f"{tip}; refetch against the pinned clone"
            )
            return 1
        forge_descriptor = {
            "dir_name": f"{args.forge.parent.name}/{args.forge.name}",
            "meta_sha256": hashlib.sha256(
                (args.forge / "meta.json").read_bytes()
            ).hexdigest(),
        }

    try:
        clusters = build_timeline(commits, forge_pulls=forge_pulls)
    except TimelineError as error:
        _report(f"error: {error}")
        return 1

    write_timeline(
        clusters,
        tip,
        args.corpus,
        args.out,
        forge_snapshot=forge_descriptor,
        tip_verified=args.repo is not None,
    )

    if args.repo is None:
        _report(
            "note: --repo not given; the corpus tip went unverified against a "
            "clone — recorded as tip_verified false in timeline.json"
        )

    pr_count = sum(1 for cluster in clusters if cluster.kind == "pr")
    _report(
        f"note: {len(clusters)} clusters ({pr_count} pr, "
        f"{len(clusters) - pr_count} epoch) over {len(commits)} commits"
    )
    if forge_pulls is not None:
        by_sha = {commit.sha for commit in commits}
        merged = [pull for pull in forge_pulls if pull.get("merged_at")]
        unmatched = [
            pull["number"]
            for pull in merged
            if (pull.get("squash_commit_sha") or pull.get("merge_commit_sha"))
            not in by_sha
        ]
        rescued = sum(1 for cluster in clusters if cluster.provenance == "forge_squash")
        enriched = sum(
            1
            for cluster in clusters
            if cluster.provenance == "merge_commit" and cluster.pr_number is not None
        )
        _report(
            f"note: forge: {rescued} squash-rescued, {enriched} enriched, "
            f"{len(unmatched)} of {len(merged)} merged pull(s) unmatched"
        )
        if unmatched:
            _report(
                f"note: unmatched pull numbers: "
                f"{', '.join(str(number) for number in unmatched[:20])}"
                f"{' …' if len(unmatched) > 20 else ''}"
            )
    return 0
