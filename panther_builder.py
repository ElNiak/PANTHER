#!/usr/bin/env python3
"""PANTHER Build Script - Bootstrap wrapper.

This script provides a bootstrap entry point for building PANTHER when the
package is not yet installed. For full functionality, install PANTHER first
with ``pip install -e .`` and use the CLI commands:

    panther build dev          # Editable install with all deps
    panther build package      # Build and install wheel
    panther build test         # Build + run tests
    panther build clean        # Clean build artifacts
    panther docs build         # Build documentation
    panther docs serve         # Build + serve locally
    panther docs deploy        # Deploy to GitHub Pages
    panther admin archive-outputs  # Archive outputs directory

Bootstrap commands (available without installing PANTHER):
    python panther_builder.py package-dev    # Editable install with all deps
    python panther_builder.py clean          # Clean build artifacts
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def _rmtree_onerror(func, path, exc_info):
    """Handle permission errors during shutil.rmtree."""
    try:
        os.chmod(path, stat.S_IRWXU)
        func(path)
    except PermissionError:
        subprocess.run(["xattr", "-c", path], capture_output=True)
        os.chmod(path, stat.S_IRWXU)
        func(path)


def _run(cmd, cwd=None):
    """Run a command, print it, and return exit code."""
    print(f"Running: {' '.join(str(c) for c in cmd)}")
    try:
        return subprocess.run(cmd, cwd=cwd, check=True).returncode
    except subprocess.CalledProcessError as e:
        return e.returncode
    except FileNotFoundError:
        print(f"Error: Command not found: {cmd[0]}")
        return 1


def _clean(project_root):
    """Clean build artifacts."""
    print("Cleaning build artifacts...")
    for d in ["build", "dist", "docs", "site", "htmlcov"]:
        p = project_root / d
        if p.exists():
            shutil.rmtree(p, onerror=_rmtree_onerror)
    for egg in project_root.glob("*.egg-info"):
        shutil.rmtree(egg, onerror=_rmtree_onerror)
    for pc in project_root.rglob("__pycache__"):
        if ".git" not in pc.parts:
            shutil.rmtree(pc, onerror=_rmtree_onerror)
    print("Clean completed.")
    return 0


def _try_forward_to_cli(command):
    """Try to forward to installed CLI. Returns None if CLI not available."""
    cli_map = {
        "package": ["panther", "build", "package"],
        "package-dev": ["panther", "build", "dev"],
        "package-test": ["panther", "build", "test"],
        "install-local": ["panther", "build", "install"],
        "clean": ["panther", "build", "clean"],
        "docs": ["panther", "docs", "build"],
        "serve-docs": ["panther", "docs", "serve"],
        "deploy-docs": ["panther", "docs", "deploy"],
        "zip-outputs": ["panther", "admin", "archive-outputs"],
    }
    if command not in cli_map:
        return None
    try:
        return subprocess.run(cli_map[command]).returncode
    except FileNotFoundError:
        return None


def main():
    """Main entry point for the bootstrap build script."""
    project_root = Path(__file__).parent

    parser = argparse.ArgumentParser(
        description="PANTHER Build Script (bootstrap)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Note: Most commands are now available via the PANTHER CLI.
Install with 'pip install -e .' then use 'panther build', 'panther docs', etc.

Bootstrap commands:
    python panther_builder.py package-dev    # Editable install
    python panther_builder.py clean          # Clean artifacts
        """,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=[
            "package", "package-dev", "package-test",
            "clean", "install-local",
            "docs", "serve-docs", "deploy-docs",
            "zip-outputs", "help",
        ],
        help="Command to execute",
    )
    args = parser.parse_args()

    if args.command == "help":
        parser.print_help()
        return 0

    # For clean, handle directly (no install needed)
    if args.command == "clean":
        return _clean(project_root)

    # Try forwarding to installed CLI first
    result = _try_forward_to_cli(args.command)
    if result is not None:
        return result

    # CLI not available — handle bootstrap commands directly
    if args.command == "package-dev":
        print("PANTHER CLI not installed. Running bootstrap install...")
        # Check Python version
        if sys.version_info < (3, 10):
            print(f"Error: Python 3.10+ required. Current: {sys.version.split()[0]}")
            return 1

        result = _clean(project_root)
        if result != 0:
            return result

        # Install build deps + editable install
        result = _run([sys.executable, "-m", "pip", "install", "build", "wheel", "setuptools"])
        if result != 0:
            return result
        result = _run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        if result != 0:
            return result
        result = _run([sys.executable, "-m", "pip", "install", "."])
        if result != 0:
            return result
        result = _run([sys.executable, "-m", "pip", "uninstall", "--yes", "panther-net"])
        if result != 0:
            return result
        result = _run([sys.executable, "-m", "pip", "install", "--force-reinstall", "--editable", "."])
        if result != 0:
            return result

        # Install ivy submodule if present
        ivy_path = project_root / "panther" / "plugins" / "services" / "testers" / "panther_ivy"
        if (ivy_path / "setup.py").exists() or (ivy_path / "pyproject.toml").exists():
            print("Installing panther_ivy submodule...")
            old_val = os.environ.get("CMAKE_POLICY_VERSION_MINIMUM")
            os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
            try:
                _run([sys.executable, "-m", "pip", "install", "--editable", str(ivy_path)])
            finally:
                if old_val is None:
                    os.environ.pop("CMAKE_POLICY_VERSION_MINIMUM", None)
                else:
                    os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = old_val

        # Install ai_rfc submodule if present
        ai_rfc_path = project_root / "panther" / "plugins" / "services" / "testers" / "ai_rfc"
        if (ai_rfc_path / "pyproject.toml").exists():
            print("Installing ai_rfc submodule...")
            _run([sys.executable, "-m", "pip", "install", "--editable", f"{ai_rfc_path}[mcp]"])

        print("\nPANTHER installed. You can now use 'panther' CLI commands.")
        return 0

    # For other commands, CLI is required
    print(f"Error: '{args.command}' requires PANTHER to be installed.")
    print("Run 'python panther_builder.py package-dev' first, then use 'panther' CLI.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
