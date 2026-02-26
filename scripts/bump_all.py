#!/usr/bin/env python3
"""Orchestrate version bumps across all PANTHER ecosystem repos.

Usage:
    python scripts/bump_all.py --repo panther patch           # bump one repo
    python scripts/bump_all.py --repo ivy-lsp --repo vscode-ivy patch  # bump several
    python scripts/bump_all.py --all patch                    # bump all repos
    python scripts/bump_all.py --all patch --dry-run          # preview all
"""
import argparse
import subprocess
import sys
from pathlib import Path

REPOS = {
    "panther": {
        "path": ".",
        "script": "scripts/bump_version.py",
    },
    "panther-ivy": {
        "path": "panther/plugins/services/testers/panther_ivy",
        "script": "scripts/bump_version.py",
    },
    "ivy-lsp": {
        "path": "panther/plugins/services/testers/panther_ivy/submodules/ivy_lsp",
        "script": "scripts/bump_version.py",
    },
    "vscode-ivy": {
        "path": "panther/plugins/services/testers/panther_ivy/submodules/vscode-ivy",
        "script": "scripts/bump_version.py",
    },
    "panther-serena": {
        "path": "panther/plugins/services/testers/panther_ivy/submodules/panther-serena",
        "script": "scripts/bump_version.py",
    },
    "panther-ivy-plugin": {
        "path": "panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin",
        "script": "scripts/bump_version.py",
    },
}


def bump_repo(
    name: str, info: dict, version_arg: str, extra_args: list[str]
) -> bool:
    repo_path = Path(info["path"])
    script_full = repo_path / info["script"]
    if not script_full.exists():
        print(f"  SKIP {name}: {script_full} not found")
        return False

    # Use script path relative to repo since cwd is set to repo_path
    cmd = [sys.executable, info["script"], version_arg] + extra_args
    print(f"\n{'=' * 60}")
    print(f"  Bumping: {name} ({repo_path})")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")
    result = subprocess.run(cmd, cwd=repo_path)
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bump versions across PANTHER repos"
    )
    parser.add_argument(
        "version",
        help="New version (X.Y.Z) or increment (major, minor, patch)",
    )
    parser.add_argument(
        "--repo",
        action="append",
        choices=list(REPOS.keys()),
        help="Repo(s) to bump (repeatable)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Bump all repos"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes only"
    )
    parser.add_argument(
        "--no-tag", action="store_true", help="Skip git tag creation"
    )
    parser.add_argument(
        "--no-commit", action="store_true", help="Skip git commit"
    )
    args = parser.parse_args()

    if not args.repo and not args.all:
        parser.error("specify --repo REPO or --all")

    targets = list(REPOS.keys()) if args.all else args.repo
    extra = []
    if args.dry_run:
        extra.append("--dry-run")
    if args.no_tag:
        extra.append("--no-tag")
    if args.no_commit:
        extra.append("--no-commit")

    results = {}
    for name in targets:
        ok = bump_repo(name, REPOS[name], args.version, extra)
        results[name] = "OK" if ok else "FAIL"

    print(f"\n{'=' * 60}")
    print("Summary:")
    for name, status in results.items():
        print(f"  {name:20s} {status}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
