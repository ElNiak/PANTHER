#!/usr/bin/env python3
"""Script to prepare the documentation directory by creating symlinks to markdown files."""

import os
import shutil
from pathlib import Path

def create_symlink_or_copy(source, target):
    """Create a symlink or copy a file if symlinks are not supported."""
    if os.path.exists(target):
        # Remove existing file or symlink
        if os.path.islink(target) or os.path.isfile(target):
            os.remove(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
    
    target_dir = os.path.dirname(target)
    os.makedirs(target_dir, exist_ok=True)
    
    try:
        # Try to create symlink (preferred)
        os.symlink(source, target)
        print(f"Created symlink: {target} -> {source}")
    except (OSError, NotImplementedError):
        # Fall back to copying if symlinks are not supported
        if os.path.isdir(source):
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        print(f"Copied: {source} to {target}")

def main():
    # Define paths
    repo_dir = Path.cwd()
    docs_dir = repo_dir / "docs"
    
    # Create docs directory if it doesn't exist
    docs_dir.mkdir(exist_ok=True)
    
    # Create symlinks for markdown files in the root directory
    root_md_files = list(repo_dir.glob("*.md"))
    for md_file in root_md_files:
        target = docs_dir / md_file.name
        create_symlink_or_copy(md_file, target)
    
    # Create symlinks for README.md files in the panther directory and subdirectories
    # Exclude panther_ivy subdirectories except the main README
    panther_readme_files = []
    for readme in repo_dir.glob("panther/**/README.md"):
        # Skip files in certain panther_ivy subdirectories
        if not any(subdir in str(readme) for subdir in 
                   ["/panther_ivy/submodules/", "/panther_ivy/test/", 
                    "/panther_ivy/ivy/", "/panther_ivy/protocol-testing/"]):
            panther_readme_files.append(readme)
    
    # Specifically include the panther_ivy README.md
    panther_ivy_readme = repo_dir / "panther" / "plugins" / "services" / "testers" / "panther_ivy" / "README.md"
    if panther_ivy_readme.is_file():
        if panther_ivy_readme not in panther_readme_files:
            panther_readme_files.append(panther_ivy_readme)
            print(f"Including panther_ivy README.md: {panther_ivy_readme}")
    
    for readme in panther_readme_files:
        relative_path = str(readme).replace(str(repo_dir) + "/", "")
        target = docs_dir / relative_path
        create_symlink_or_copy(readme, target)
    
    # Create symlinks for other markdown files in the panther directory
    # Exclude panther_ivy subdirectories
    panther_md_files = []
    for md_file in repo_dir.glob("panther/**/*.md"):
        if md_file.name.lower() != "readme.md" and not any(subdir in str(md_file) for subdir in 
                ["/panther_ivy/submodules/", "/panther_ivy/test/", 
                 "/panther_ivy/ivy/", "/panther_ivy/protocol-testing/"]):
            panther_md_files.append(md_file)
            
    for md_file in panther_md_files:
        relative_path = str(md_file).replace(str(repo_dir) + "/", "")
        target = docs_dir / relative_path
        create_symlink_or_copy(md_file, target)
    
    # Create an index.md file if it doesn't exist
    index_path = docs_dir / "index.md"
    if not index_path.exists():
        with open(index_path, "w") as f:
            f.write("# PANTHER Documentation\n\n")
            f.write("Welcome to the PANTHER (Protocol formal Analysis and formal Network Threat Evaluation Resources) documentation.\n\n")
            f.write("## Quick Links\n\n")
            f.write("- [Installation](INSTALL.md)\n")
            f.write("- [Quick Start](quick_start.md)\n")
            f.write("- [Plugin System](plugin_development.md)\n")
            f.write("- [Contributing](CONTRIBUTING.md)\n")
            f.write("- [API Reference](panther/)\n")
    
    print(f"Documentation prepared in {docs_dir}")

if __name__ == "__main__":
    main()
