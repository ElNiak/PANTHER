from typing import List

#!/usr/bin/env python3
"""
Script to fix markdown links in panther/ directory to be relative to project root.

This script:
1. Finds all .md files in the panther/ directory
2. Converts absolute links (starting with /) to relative links
3. Ensures all references are relative to the project root
4. Preserves external URLs and anchor links
"""

import os
import re
import sys
from pathlib import Path


def get_relative_path_to_root(file_path: Path, project_root: Path) -> str:
    """Calculate the relative path from a file to the project root."""
    try:
        # Get the relative path from project root to the file
        rel_path = file_path.relative_to(project_root)
        # Count the directory levels
        levels = (
            len(rel_path.parents) - 1
        )  # -1 because parents includes the file itself
        # Return the appropriate number of '../' to get to root
        return "../" * levels
    except ValueError:
        # File is not under project root
        return ""


def is_relative_to(path: Path, parent: Path) -> bool:
    """Check if path is relative to parent (compatibility for Python < 3.9)."""
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def fix_markdown_link(
    link_url: str, path_to_root: str, current_file: Path, project_root: Path
) -> str:
    """
    Fix a markdown link URL to be relative to project root, starting with panther/...

    Args:
        link_url: The original link URL
        path_to_root: The relative path from current file to project root (e.g., '../../')
        current_file: The current file being processed
        project_root: The project root directory

    Returns:
        The fixed link URL
    """
    # Skip external URLs, anchors, and empty links
    if (
        not link_url
        or link_url.startswith("http://")
        or link_url.startswith("https://")
        or link_url.startswith("#")
        or link_url.startswith("mailto:")
    ):
        return link_url

    # Already starts with panther/ - keep as is
    if link_url.startswith("panther/"):
        return link_url

    # Handle absolute links starting with '/'
    if link_url.startswith("/"):
        # Remove leading slash
        target_path = link_url[1:]
        if target_path.startswith("panther/"):
            # Already starts with panther/, just remove the leading slash
            return target_path
        else:
            # Check if this should be converted to panther/ format
            target_file = project_root / target_path
            if target_file.exists() and target_path.startswith("panther/"):
                return target_path
            # For non-panther files, use path to root
            return path_to_root + target_path

    # Handle relative links that go up directories (../)
    if link_url.startswith("../"):
        # Resolve the relative path to see where it points
        current_dir = current_file.parent
        try:
            # Resolve the relative path
            target_path = (current_dir / link_url).resolve()
            # Check if target is within the project
            if is_relative_to(target_path, project_root):
                rel_to_project = target_path.relative_to(project_root)
                # If it's in panther/ directory, use panther/ format
                if str(rel_to_project).startswith("panther/"):
                    return str(rel_to_project)
                # Otherwise use path_to_root format
                return path_to_root + str(rel_to_project)
        except (OSError, ValueError):
            # If resolution fails, keep original
            pass
        return link_url

    # Handle simple relative links (no ../ or ./)
    if not link_url.startswith("./"):
        # Check if this file exists locally
        current_dir = current_file.parent
        local_target = current_dir / link_url

        if local_target.exists():
            # File exists locally, check if we should convert to panther/ format
            try:
                abs_target = local_target.resolve()
                if is_relative_to(abs_target, project_root):
                    rel_to_project = abs_target.relative_to(project_root)
                    if str(rel_to_project).startswith("panther/"):
                        return str(rel_to_project)
            except (OSError, ValueError):
                pass
        else:
            # File doesn't exist locally, try to find it in panther/
            if link_url.endswith(".md"):
                for root, dirs, files in os.walk(project_root / "panther"):
                    if link_url in files:
                        found_path = Path(root) / link_url
                        rel_to_project = found_path.relative_to(project_root)
                        return str(rel_to_project)

    # For other cases, leave as-is
    return link_url


def process_markdown_file(
    file_path: Path, project_root: Path, dry_run: bool = True
) -> List[tuple[str, str]]:
    """
    Process a markdown file to fix links.

    Returns:
        List of (original_link, fixed_link) tuples for changes made
    """
    path_to_root = get_relative_path_to_root(file_path, project_root)

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Warning: Could not read {file_path} as UTF-8, skipping")
        return []

    # Pattern to match markdown links: [text](url)
    link_pattern = r"\[([^\]]*)\]\(([^)]+)\)"

    changes = []

    def replace_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        fixed_url = fix_markdown_link(link_url, path_to_root, file_path, project_root)

        if fixed_url != link_url:
            changes.append((link_url, fixed_url))

        return f"[{link_text}]({fixed_url})"

    new_content = re.sub(link_pattern, replace_link, content)

    # Only write if there are changes and not in dry-run mode
    if new_content != content and not dry_run:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

    return changes


def find_markdown_files(panther_dir: Path) -> List[Path]:
    """Find all markdown files in the panther directory."""
    md_files = []
    for root, dirs, files in os.walk(panther_dir):
        for file in files:
            if file.endswith(".md"):
                md_files.append(Path(root) / file)
    return sorted(md_files)


def main():
    # Determine project root (assumes script is in project root)
    script_dir = Path(__file__).parent.absolute()
    project_root = script_dir
    panther_dir = project_root / "panther"

    if not panther_dir.exists():
        print(f"Error: panther directory not found at {panther_dir}")
        sys.exit(1)

    # Parse command line arguments
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    else:
        print("🔄 LIVE MODE - Files will be modified")

    print(f"📁 Project root: {project_root}")
    print(f"📁 Panther directory: {panther_dir}")
    print()

    # Find all markdown files
    md_files = find_markdown_files(panther_dir)
    print(f"Found {len(md_files)} markdown files in panther/")

    if not md_files:
        print("No markdown files found. Exiting.")
        return

    total_changes = 0
    files_with_changes = 0

    # Process each file
    for file_path in md_files:
        rel_path = file_path.relative_to(project_root)
        changes = process_markdown_file(file_path, project_root, dry_run)

        if changes:
            files_with_changes += 1
            total_changes += len(changes)

            print(f"📝 {rel_path}")
            if verbose:
                for original, fixed in changes:
                    print(f"    {original} → {fixed}")
            else:
                print(f"    {len(changes)} link(s) to fix")
        elif verbose:
            print(f"✅ {rel_path} (no changes needed)")

    print()
    print("📊 Summary:")
    print(f"   Files processed: {len(md_files)}")
    print(f"   Files with changes: {files_with_changes}")
    print(f"   Total link changes: {total_changes}")

    if dry_run and total_changes > 0:
        print()
        print("🚀 To apply changes, run: python fix_markdown_links.py")
        print("💡 Add --verbose to see detailed changes")
    elif total_changes > 0:
        print()
        print("✅ All links have been fixed!")
    else:
        print()
        print("✅ All links are already correct!")


if __name__ == "__main__":
    main()
