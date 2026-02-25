#!/usr/bin/env python3
"""Bump version in all locations, commit, and create a git tag.

Usage:
    python scripts/bump_version.py patch              # 1.2.3 -> 1.2.4
    python scripts/bump_version.py minor              # 1.2.3 -> 1.3.0
    python scripts/bump_version.py major              # 1.2.3 -> 2.0.0
    python scripts/bump_version.py 1.2.3              # explicit version
    python scripts/bump_version.py patch --dry-run    # preview changes
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# ── Per-repo config (only this section differs between repos) ────────────
# Each entry: (filepath, handler_type, handler_args...)
#   handler_type "regex": (filepath, "regex", pattern, template)
#   handler_type "json":  (filepath, "json", key)
VERSION_FILES = [
    ("pyproject.toml", "regex", r'^version\s*=\s*"[^"]+"', 'version = "{version}"'),
    (
        "panther/__init__.py",
        "regex",
        r'^__version__\s*=\s*"[^"]+"',
        '__version__ = "{version}"',
    ),
]
# ─────────────────────────────────────────────────────────────────────────

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_version(version: str) -> tuple[int, int, int]:
    m = SEMVER_RE.match(version)
    if not m:
        print(f"ERROR: invalid semver: {version!r}")
        sys.exit(1)
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def bump_component(version: str, component: str) -> str:
    major, minor, patch = parse_version(version)
    if component == "major":
        return f"{major + 1}.0.0"
    elif component == "minor":
        return f"{major}.{minor + 1}.0"
    elif component == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"unknown component: {component}")


def read_current_version() -> str:
    filepath, handler_type, *args = VERSION_FILES[0]
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: {filepath} not found")
        sys.exit(1)
    text = path.read_text()
    if handler_type == "regex":
        pattern = args[0]
        m = re.search(pattern, text, re.MULTILINE)
        if not m:
            print(f"ERROR: version pattern not found in {filepath}")
            sys.exit(1)
        version_match = re.search(r'"([^"]+)"', m.group(0))
        if not version_match:
            print(f"ERROR: could not extract version string from {filepath}")
            sys.exit(1)
        return version_match.group(1)
    elif handler_type == "json":
        key = args[0]
        data = json.loads(text)
        return data[key]
    raise ValueError(f"unknown handler: {handler_type}")


def resolve_version(arg: str) -> str:
    if arg in ("major", "minor", "patch"):
        current = read_current_version()
        new = bump_component(current, arg)
        print(f"Current version: {current}")
        print(f"Bump {arg}: {current} -> {new}")
        return new
    parse_version(arg)  # validate
    return arg


def update_file(
    filepath: str,
    handler_type: str,
    args: list,
    new_version: str,
    dry_run: bool,
) -> bool:
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: {filepath} not found")
        sys.exit(1)

    if handler_type == "regex":
        pattern, template = args[0], args[1]
        text = path.read_text()
        replacement = template.format(version=new_version)
        updated, count = re.subn(
            pattern, replacement, text, count=1, flags=re.MULTILINE
        )
        if count == 0:
            print(f"  WARNING: no match in {filepath}")
            return False
        if dry_run:
            print(f"  Would update {filepath}")
        else:
            path.write_text(updated)
            print(f"  Updated {filepath}")
        return True

    elif handler_type == "json":
        key = args[0]
        data = json.loads(path.read_text())
        old = data[key]
        if dry_run:
            print(f"  Would update {filepath}: {old} -> {new_version}")
        else:
            data[key] = new_version
            path.write_text(json.dumps(data, indent=2) + "\n")
            print(f"  Updated {filepath}: {old} -> {new_version}")
        return True

    raise ValueError(f"unknown handler: {handler_type}")


def bump(
    new_version: str, dry_run: bool, no_commit: bool, no_tag: bool
) -> None:
    print(f"\nBumping to {new_version}:")
    files_changed = []
    for entry in VERSION_FILES:
        filepath, handler_type = entry[0], entry[1]
        args = list(entry[2:])
        if update_file(filepath, handler_type, args, new_version, dry_run):
            files_changed.append(filepath)

    if dry_run:
        print("\nDry run complete. No files modified.")
        return

    if not files_changed:
        print("\nNo files were updated.")
        return

    if not no_commit:
        subprocess.run(["git", "add"] + files_changed, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"chore: bump version to {new_version}"],
            check=True,
        )

    tag = f"v{new_version}"
    if not no_tag and not no_commit:
        subprocess.run(["git", "tag", tag], check=True)
        print(f"\nCreated tag {tag}. Run:\n  git push && git push origin {tag}")
    elif not no_commit:
        print(f"\nCommitted. Tag skipped (--no-tag).")
    else:
        print(f"\nFiles updated. Commit and tag skipped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bump project version")
    parser.add_argument(
        "version",
        help="New version (X.Y.Z) or increment (major, minor, patch)",
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

    new_version = resolve_version(args.version)
    bump(new_version, args.dry_run, args.no_commit, args.no_tag)


if __name__ == "__main__":
    main()
