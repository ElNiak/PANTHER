#!/usr/bin/env python3
"""
Fix MkDocs YAML Config

This script attempts to fix MkDocs YAML configuration files that have PyMdown Extensions
tags that cause parsing errors. It creates a new configuration file with the problematic
tags replaced with string placeholders.

Usage: python fix_mkdocs_yaml.py [--mkdocs-yaml path/to/mkdocs.yml]
"""

import os
import re
import sys
import argparse
from pathlib import Path
import shutil
import yaml


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Fix MkDocs YAML configuration")
    parser.add_argument(
        "--mkdocs-yaml", type=str, help="Path to the mkdocs.yml file to fix"
    )
    return parser.parse_args()


def fix_yaml_config(config_path):
    """
    Fix the MkDocs YAML configuration by replacing problematic Python tags
    with string placeholders.
    """
    # Create a backup of the original file
    backup_path = f"{config_path}.bak"
    print(f"Creating backup of original config at {backup_path}")
    shutil.copy2(config_path, backup_path)

    # Read the original file content
    with open(config_path, encoding="utf-8") as file:
        content = file.read()

    # Replace PyMdown Extensions tags with string placeholders
    print("Replacing PyMdown Extensions tags with placeholders...")

    # Look for common PyMdown Extensions tags
    content = re.sub(
        r"!!python/name:pymdownx\.emoji\.([^\s]+)", r'"pymdownx_emoji_\1"', content
    )
    content = re.sub(
        r"!!python/name:pymdownx\.superfences\.([^\s]+)",
        r'"pymdownx_superfences_\1"',
        content,
    )
    content = re.sub(r"!!python/name:pymdownx\.([^\s]+)", r'"pymdownx_\1"', content)
    content = re.sub(
        r"!!python/object/apply:pymdownx\.([^\s]+)", r'"pymdownx_object_\1"', content
    )

    # More generic Python tag replacements
    content = re.sub(r"!!python/name:([^\s]+)", r'"python_name_\1"', content)
    content = re.sub(r"!!python/object/apply:([^\s]+)", r'"python_apply_\1"', content)

    # Fix indentation and other common YAML issues
    # Look for YAML block mapping issues (misaligned blocks)
    content = re.sub(r"(\n\s+)(\w+):\s*\n\s+(\w+):", r"\1\2:\n\1  \3:", content)

    # Write the modified content to a temporary file
    temp_path = f"{config_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        file.write(content)

    # Try to parse the temporary file to check if we've fixed the issues
    try:
        with open(temp_path, encoding="utf-8") as file:
            yaml.safe_load(file)
        print("✅ Successfully fixed YAML configuration!")

        # Replace the original file with the fixed version
        shutil.move(temp_path, config_path)
        return True
    except yaml.YAMLError as e:
        print(f"❌ Failed to fix YAML configuration. Error: {e}")
        os.remove(temp_path)
        print(f"Original configuration restored from backup at {backup_path}")
        return False


def main():
    """Main entry point of the script."""
    args = parse_arguments()

    # Use provided path or default to repository root
    if args.mkdocs_yaml:
        config_path = Path(args.mkdocs_yaml)
    else:
        # Default: assume we're in the dev/docs-gen directory
        config_path = Path(__file__).parent.parent / "mkdocs.yml"

    if not config_path.exists():
        print(f"❌ Configuration file not found at {config_path}")
        return 1

    print(f"🔧 Fixing MkDocs YAML configuration at {config_path}")
    success = fix_yaml_config(config_path)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
