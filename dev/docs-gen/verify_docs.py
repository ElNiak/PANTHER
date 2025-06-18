from typing import List
#!/usr/bin/env python3
# filepath: /Users/elniak/Documents/Project/PANTHER/dev/docs-gen/verify_docs.py

"""
Documentation Verification Script

This script verifies that documentation contains proper source references
and does not have unresolved verification markers (TODO:VERIFY).
"""

import re
import sys
from pathlib import Path
import argparse

# Regular expressions for finding source references and verification markers
SRC_REFERENCE_PATTERN = re.compile(r"<!-- src:\s*([^>]+)\s*-->")
TODO_VERIFY_PATTERN = re.compile(r"<!-- TODO:VERIFY -->")

def check_file_exists(filepath):
    """Check if a referenced file exists in the repository."""
    # Handle line number references (file.py:10-15)
    file_path = filepath.split(":")[0].strip()
    repo_root = Path(__file__).parent.parent
    full_path = repo_root / file_path.lstrip("/")
    return full_path.exists()

def verify_docs(root_dir, report_mode=False, ignore_dirs=None):
    """
    Verify documentation files for proper source references and verification markers.

    Args:
        root_dir: Root directory to start searching for .md files
        report_mode: If True, only report issues without failing
        ignore_dirs: List of directories to ignore

    Returns:
        tuple: (is_valid, issues_found)
    """
    if ignore_dirs is None:
        ignore_dirs = []

    is_valid = True
    issues = []

    for path in Path(root_dir).rglob("*.md"):
        # Skip ignored directories
        if any(ignore_dir in str(path) for ignore_dir in ignore_dirs):
            continue

        with open(path, encoding="utf-8") as f:
            content = f.read()

        # Check for verification markers
        todo_verify_matches = TODO_VERIFY_PATTERN.findall(content)
        if todo_verify_matches:
            is_valid = False
            issues.append(
                f"{path}: Contains {len(todo_verify_matches)} unresolved verification markers (TODO:VERIFY)"
            )

        # Check source references
        src_references = SRC_REFERENCE_PATTERN.findall(content)
        for ref in src_references:
            if not check_file_exists(ref):
                is_valid = False
                issues.append(f"{path}: Invalid source reference: {ref}")

        # Check for references to other markdown files
        md_link_pattern = re.compile(r"\[.*?\]\(([^)]+\.md)\)")
        md_links = md_link_pattern.findall(content)
        for md_link in md_links:
            # Handle possible anchors in links (e.g., file.md#section)
            md_file = md_link.split("#")[0]
            md_path = (path.parent / md_file).resolve()
            if not md_path.exists():
                is_valid = False
                issues.append(f"{path}: Invalid markdown link: {md_link}")

    if issues:
        print("Documentation verification issues found:")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("Documentation verification successful. All files passed checks.")

    return is_valid, issues

def main():
    parser = argparse.ArgumentParser(
        description="Verify documentation source references and markers."
    )
    parser.add_argument(
        "--root", default="docs", help="Root directory to search for markdown files"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Report mode: only report issues without failing")
    parser.add_argument(
        "--ignore",
        nargs="*",
        default=["node_modules", ".git", "venv"],
        help="Directories to ignore",
    )

    args = parser.parse_args()

    is_valid, issues = verify_docs(args.root, args.report, args.ignore)

    if not is_valid and not args.report:
        sys.exit(1)

if __name__ == "__main__":
    main()
