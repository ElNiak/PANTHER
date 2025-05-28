#!/usr/bin/env python3
"""
Documentation Pre-Commit Hook

This script runs documentation checks as a pre-commit hook.
It verifies links, adds cross-references, and updates the MkDocs navigation.
"""

import os
import sys
import subprocess
from pathlib import Path

# Repository root is two directories up from this script
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent.parent
DOCS_GEN_DIR = REPO_ROOT / "docs-gen"

def run_command(command, description=None):
    """Run a command and handle any errors."""
    if description:
        print(f"Running {description}...")
    
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    
    if result.returncode != 0:
        print(f"❌ Error: {description or command} failed!")
        print(result.stderr)
        return False
    
    if description:
        print(f"✅ {description} completed successfully")
    
    return True

def main():
    """Main function to run documentation checks."""
    print("🔍 Running documentation pre-commit checks...")
    
    # Change to repository root
    os.chdir(REPO_ROOT)
    
    # Check if any Markdown files are staged
    result = subprocess.run(
        "git diff --cached --name-only --diff-filter=d | grep -E '\\.md$'",
        shell=True, text=True, capture_output=True
    )
    
    if result.returncode != 0 and not result.stdout.strip():
        print("No Markdown files changed, skipping documentation checks")
        return 0
    
    # Verify links
    verify_links_cmd = f"python {DOCS_GEN_DIR}/verify_links.py --autofix"
    if not run_command(verify_links_cmd, "link verification"):
        return 1
    
    # Add cross-references
    add_refs_cmd = f"python {DOCS_GEN_DIR}/add_cross_references.py"
    if not run_command(add_refs_cmd, "cross-reference addition"):
        return 1
    
    # Update MkDocs navigation
    update_nav_cmd = f"python {DOCS_GEN_DIR}/update_mkdocs_nav.py"
    if not run_command(update_nav_cmd, "MkDocs navigation update"):
        return 1
    
    # Stage any modified files
    modified_files = [
        "mkdocs.yml",
        *[str(f) for f in Path(".").rglob("*.md") if f.is_file()]
    ]
    
    for file in modified_files:
        # Check if the file exists and was modified by our scripts
        result = subprocess.run(
            f"git diff --name-only {file}",
            shell=True, text=True, capture_output=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"Staging modified file: {file}")
            subprocess.run(f"git add {file}", shell=True)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
