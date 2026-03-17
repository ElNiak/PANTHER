#!/usr/bin/env python3
"""PANTHER Build Script - Bootstrap wrapper.

Bootstrap commands (available without installing PANTHER):
    python panther_builder.py package-dev    # Editable install with all deps
    python panther_builder.py clean          # Clean build artifacts

For full functionality after install, use the PANTHER CLI:
    panther build dev / package / test / clean
    panther docs build / serve / deploy
    panther admin archive-outputs
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


def main():
    """Main entry point for the bootstrap build script."""
    project_root = Path(__file__).parent

    parser = argparse.ArgumentParser(
        description="PANTHER Build Script (bootstrap)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="help",
        choices=["package-dev", "clean", "help"],
        help="Command to execute",
    )
    args = parser.parse_args()

    if args.command == "help":
        parser.print_help()
        return 0

    if args.command == "clean":
        return _clean(project_root)

    if args.command == "package-dev":
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
        result = _run([sys.executable, "-m", "pip", "install", ".[dev]"])
        if result != 0:
            return result
        result = _run([sys.executable, "-m", "pip", "uninstall", "--yes", "panther-net"])
        if result != 0:
            return result
        result = _run([sys.executable, "-m", "pip", "install", "--force-reinstall", "--editable", ".[dev]"])
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

        print("\nPANTHER installed. You can now use 'panther' CLI commands.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
