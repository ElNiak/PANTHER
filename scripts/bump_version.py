#!/usr/bin/env python3
"""Bump version in all locations, commit, and create a git tag.

Usage: python scripts/bump_version.py 1.2.3
"""
import re
import subprocess
import sys
from pathlib import Path

VERSION_FILES = [
    ("pyproject.toml", r'^version\s*=\s*"[^"]+"', 'version = "{version}"'),
    (
        "panther/__init__.py",
        r'^__version__\s*=\s*"[^"]+"',
        '__version__ = "{version}"',
    ),
]


def bump(new_version: str) -> None:
    for filepath, pattern, template in VERSION_FILES:
        path = Path(filepath)
        text = path.read_text()
        replacement = template.format(version=new_version)
        updated, count = re.subn(
            pattern, replacement, text, count=1, flags=re.MULTILINE
        )
        if count == 0:
            print(f"ERROR: no match in {filepath}")
            sys.exit(1)
        path.write_text(updated)
        print(f"Updated {filepath}")

    tag = f"v{new_version}"
    files = [f[0] for f in VERSION_FILES]
    subprocess.run(["git", "add"] + files, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"chore: bump version to {new_version}"], check=True
    )
    subprocess.run(["git", "tag", tag], check=True)
    print(f"\nCreated tag {tag}. Run:\n  git push && git push origin {tag}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} NEW_VERSION")
        sys.exit(1)
    bump(sys.argv[1])
