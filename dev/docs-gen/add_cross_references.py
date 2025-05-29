#!/usr/bin/env python3
"""
Documentation Cross-Reference Generator

This script adds "See Also" sections to Markdown files to improve the
cross-connectivity of the documentation. It adds references between:
- Root documentation files and plugin documentation
- Plugin documentation and related API sections
- Related plugin families
"""

import os
import re
from pathlib import Path
import argparse

# Repository root is two directories up from this script
REPO_ROOT = Path(__file__).parent.parent.resolve()

# Core documentation files that should be cross-referenced
CORE_DOCS = {
    "README.md": "Project Overview",
    "QUICK_START.md": "Quick Start Guide",
    "CONTRIBUTING.md": "Contribution Guide",
    "WORKFLOW.md": "Development Workflow",
}

# Plugin directories to focus on
PLUGIN_TYPES = {
    "services": "Service Plugins",
    "protocols": "Protocol Plugins",
    "environments": "Environment Plugins",
}


def find_markdown_files() -> list[Path]:
    """Find all Markdown files in the project."""
    # Exclude node_modules, venv, and other directories that should be ignored
    ignore_patterns = [
        "**/node_modules/**",
        "**/.git/**",
        "**/.venv*/**",
        "**/venv*/**",
        "**/build/**",
        "**/dist/**",
        "**/__pycache__/**",
        "**/submodules/**",
        "**/.venv-10/**",
        "**/site-packages/**",
        "**/templates/**",
        ".venv-*/**",
        "**/licenses/**",
        "**/panther_ivy/submodules/**",
        "**/panther_ivy/test/**",
        "**/panther_ivy/ivy/**",
        "**/panther_ivy/doc/**",
        "**/panther_ivy/examples/**",
    ]

    # Start with an empty list of files
    markdown_files = []

    # Walk through the directory
    for path in REPO_ROOT.rglob("*.md"):
        # Check if path matches any ignore pattern
        if not any(path.match(pattern) for pattern in ignore_patterns):
            markdown_files.append(path)

    print(f"Found {len(markdown_files)} Markdown files")
    return markdown_files


def group_files_by_category(markdown_files: list[Path]) -> dict[str, list[Path]]:
    """Group Markdown files by category."""
    grouped = {
        "root": [],
        "services": [],
        "protocols": [],
        "environments": [],
        "other": [],
    }

    for file_path in markdown_files:
        rel_path = str(file_path.relative_to(REPO_ROOT))

        if "/" not in rel_path:
            # Root directory files
            grouped["root"].append(file_path)
        elif "plugins/services/" in rel_path:
            grouped["services"].append(file_path)
        elif "plugins/protocols/" in rel_path:
            grouped["protocols"].append(file_path)
        elif "plugins/environments/" in rel_path:
            grouped["environments"].append(file_path)
        else:
            grouped["other"].append(file_path)

    return grouped


def get_title_from_markdown(file_path: Path) -> str:
    """Extract title from the first heading in a Markdown file."""
    try:
        with open(file_path, encoding="utf-8") as file:
            for line in file:
                # Look for a level 1 heading (# Title)
                match = re.match(r"^#\s+(.+)$", line.strip())
                if match:
                    return match.group(1)

        # If no heading found, use the filename without extension
        return file_path.stem.replace("_", " ").title()
    except Exception:
        # Default to filename if file can't be read
        return file_path.stem.replace("_", " ").title()


def generate_relative_link(source: Path, target: Path) -> str:
    """Generate a relative link path from source file to target file."""
    try:
        # Get the relative path from source's directory to target
        rel_path = os.path.relpath(target, source.parent)
        return rel_path.replace("\\", "/")
    except Exception:
        # Fall back to absolute path if there's an issue
        return f"/{target.relative_to(REPO_ROOT)}"


def add_see_also_section(file_path: Path, references: list[tuple[str, Path]]) -> bool:
    """Add or update a 'See Also' section in a Markdown file."""
    if not references:
        return False

    try:
        with open(file_path, encoding="utf-8") as file:
            content = file.read()

        # Check if the file already has a See Also section
        see_also_pattern = re.compile(r"^##\s+See Also\s*$", re.MULTILINE)
        has_see_also = bool(see_also_pattern.search(content))

        # Generate reference links
        ref_links = []
        for title, target in references:
            link_path = generate_relative_link(file_path, target)
            ref_links.append(f"* [{title}]({link_path})")

        new_content = content

        if has_see_also:
            # Update existing See Also section
            new_section = "\n## See Also\n\n" + "\n".join(ref_links) + "\n"
            new_content = see_also_pattern.sub(new_section, content)
        else:
            # Add new See Also section at the end
            new_section = "\n\n## See Also\n\n" + "\n".join(ref_links) + "\n"
            new_content = content + new_section

        # Write updated content if changed
        if new_content != content:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(new_content)
            return True

        return False
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False


def cross_reference_root_docs(
    markdown_files: dict[str, list[Path]], dry_run: bool = False
) -> int:
    """Add cross-references from root docs to plugin docs and vice versa."""
    count = 0

    # Get primary plugin README files
    plugin_readmes = {}
    for plugin_type, title in PLUGIN_TYPES.items():
        for file_path in markdown_files[plugin_type]:
            rel_path = str(file_path.relative_to(REPO_ROOT))
            if (
                rel_path.endswith("README.md")
                and f"plugins/{plugin_type}/README.md" == rel_path
            ):
                plugin_readmes[plugin_type] = file_path

    # Cross-reference root docs to plugin docs
    for file_name, title in CORE_DOCS.items():
        file_path = REPO_ROOT / file_name
        if not file_path.exists():
            continue

        # Generate references to plugin READMEs
        refs = []
        for plugin_type, readme_path in plugin_readmes.items():
            plugin_title = PLUGIN_TYPES[plugin_type]
            refs.append((plugin_title, readme_path))

        if dry_run:
            print(
                f"Would add {len(refs)} references to {file_path.relative_to(REPO_ROOT)}"
            )
        else:
            if add_see_also_section(file_path, refs):
                print(f"✅ Added references to {file_path.relative_to(REPO_ROOT)}")
                count += 1

    # Cross-reference plugin READMEs to root docs
    for plugin_type, readme_path in plugin_readmes.items():
        refs = []

        # Add references to core docs
        for file_name, title in CORE_DOCS.items():
            file_path = REPO_ROOT / file_name
            if file_path.exists():
                refs.append((title, file_path))

        # Add references to related plugin types
        for other_type, other_readme in plugin_readmes.items():
            if other_type != plugin_type:
                refs.append((PLUGIN_TYPES[other_type], other_readme))

        if dry_run:
            print(
                f"Would add {len(refs)} references to {readme_path.relative_to(REPO_ROOT)}"
            )
        else:
            if add_see_also_section(readme_path, refs):
                print(f"✅ Added references to {readme_path.relative_to(REPO_ROOT)}")
                count += 1

    return count


def cross_reference_plugin_docs(
    markdown_files: dict[str, list[Path]], dry_run: bool = False
) -> int:
    """Add cross-references between plugin documentation files."""
    count = 0

    # Group plugin files by category and subcategory
    for plugin_type in PLUGIN_TYPES.keys():
        # Find the development guide for this plugin type
        dev_guide = None
        subcategory_readmes = {}

        for file_path in markdown_files[plugin_type]:
            rel_path = str(file_path.relative_to(REPO_ROOT))
            parts = rel_path.split("/")

            # Find development guide
            if len(parts) == 3 and parts[-1] == "development.md":
                dev_guide = file_path

            # Find subcategory READMEs
            elif len(parts) > 3 and parts[-1] == "README.md":
                subcategory = parts[3]
                subcategory_readmes[subcategory] = file_path

        # Skip if no development guide or not enough subcategories
        if not dev_guide or len(subcategory_readmes) < 1:
            continue

        # Add references from development guide to subcategory READMEs
        refs = [
            (f"{subcat.title()} {plugin_type[:-1].title()}", path)
            for subcat, path in subcategory_readmes.items()
        ]

        if dry_run:
            print(
                f"Would add {len(refs)} references to {dev_guide.relative_to(REPO_ROOT)}"
            )
        else:
            if add_see_also_section(dev_guide, refs):
                print(f"✅ Added references to {dev_guide.relative_to(REPO_ROOT)}")
                count += 1

        # Add references from subcategory READMEs to development guide
        for subcategory, readme_path in subcategory_readmes.items():
            refs = [(f"{plugin_type.title()} Development Guide", dev_guide)]

            if dry_run:
                print(f"Would add references to {readme_path.relative_to(REPO_ROOT)}")
            else:
                if add_see_also_section(readme_path, refs):
                    print(
                        f"✅ Added references to {readme_path.relative_to(REPO_ROOT)}"
                    )
                    count += 1

    return count


def main():
    """Main entry point of the script."""
    parser = argparse.ArgumentParser(
        description="PANTHER Documentation Cross-Referencer"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print actions without modifying files"
    )
    args = parser.parse_args()

    print("🔄 PANTHER Documentation Cross-Referencer")
    print("=" * 50)

    # Find all Markdown files
    markdown_files = find_markdown_files()

    # Group files by category
    grouped_files = group_files_by_category(markdown_files)

    # Perform cross-referencing
    count = 0
    count += cross_reference_root_docs(grouped_files, args.dry_run)
    count += cross_reference_plugin_docs(grouped_files, args.dry_run)

    # Print summary
    if args.dry_run:
        print(f"\nDry run complete. Would have updated {count} files.")
    else:
        print(f"\nCross-references added to {count} files.")

    print("\nRun the verify_links.py script to check for any broken links.")


if __name__ == "__main__":
    main()
