"""Build Command.

Provides CLI commands for building, installing, testing, and cleaning
the PANTHER package. Replaces the standalone panther_builder.py build commands.
"""

import os
import shutil
import sys
from pathlib import Path

import click

from panther.cli.core.base import (
    error_message,
    featured_example,
    find_project_root,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    rmtree_onerror,
    run_command,
    success_message,
    warning_message,
)


def _clean_build_artifacts(project_root: Path) -> int:
    """Clean build artifacts."""
    info_message("Cleaning build artifacts...")
    dirs_to_clean = ["build", "dist", "docs", "site", "htmlcov"]
    for dir_name in dirs_to_clean:
        dir_path = project_root / dir_name
        if dir_path.exists():
            click.echo(f"Removing {dir_path}")
            shutil.rmtree(dir_path, onerror=rmtree_onerror)

    for egg_info in project_root.glob("*.egg-info"):
        click.echo(f"Removing {egg_info}")
        shutil.rmtree(egg_info, onerror=rmtree_onerror)

    for pycache in project_root.rglob("__pycache__"):
        if ".git" in pycache.parts:
            continue
        shutil.rmtree(pycache, onerror=rmtree_onerror)

    for pyc_file in project_root.rglob("*.pyc"):
        if ".git" in pyc_file.parts:
            continue
        pyc_file.unlink()

    success_message("Clean completed.")
    return 0


def _run_steps(*steps) -> int:
    """Run build steps sequentially, stopping on first failure."""
    for step in steps:
        result = step()
        if result != 0:
            return result
    return 0


def _install_dependencies(project_root: Path) -> int:
    """Install build dependencies."""
    info_message("Installing build dependencies...")
    return _run_steps(
        lambda: run_command(
            [sys.executable, "-m", "pip", "install", "build", "wheel", "setuptools"],
            cwd=project_root,
        ),
        lambda: run_command(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            cwd=project_root,
        ),
        lambda: run_command(
            [sys.executable, "-m", "pip", "install", "."], cwd=project_root
        ),
    )


def _uninstall_package(project_root: Path) -> int:
    """Uninstall existing package."""
    info_message("Uninstalling existing panther-net...")
    return run_command(
        [sys.executable, "-m", "pip", "uninstall", "--yes", "panther-net"],
        cwd=project_root,
    )


def _build_wheel(project_root: Path) -> int:
    """Build the wheel package."""
    info_message("Building wheel...")
    return run_command(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation"],
        cwd=project_root,
    )


def _install_wheel(project_root: Path) -> int:
    """Install the built wheel."""
    info_message("Installing wheel...")
    dist_dir = project_root / "dist"
    wheel_files = list(dist_dir.glob("panther?net-*.whl"))
    if not wheel_files:
        error_message("No wheel file found in dist/")
        return 1
    return run_command(
        [sys.executable, "-m", "pip", "install", str(wheel_files[0])],
        cwd=project_root,
    )


def _install_editable(project_root: Path) -> int:
    """Install in editable/development mode."""
    info_message("Installing in editable mode...")
    return run_command(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--editable",
            ".",
        ],
        cwd=project_root,
    )


def _install_ivy_submodule(project_root: Path) -> int:
    """Install the panther_ivy submodule in editable mode (if present)."""
    ivy_path = (
        project_root / "panther" / "plugins" / "services" / "testers" / "panther_ivy"
    )
    if (
        not (ivy_path / "setup.py").exists()
        and not (ivy_path / "pyproject.toml").exists()
    ):
        warning_message(
            "Skipping panther_ivy: submodule not initialized"
            " (run 'git submodule update --init')"
        )
        return 0
    info_message("Installing panther_ivy submodule...")
    old_val = os.environ.get("CMAKE_POLICY_VERSION_MINIMUM")
    os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
    try:
        return run_command(
            [sys.executable, "-m", "pip", "install", "--editable", str(ivy_path)],
            cwd=project_root,
        )
    finally:
        if old_val is None:
            os.environ.pop("CMAKE_POLICY_VERSION_MINIMUM", None)
        else:
            os.environ["CMAKE_POLICY_VERSION_MINIMUM"] = old_val


def _install_ai_rfc_submodule(project_root: Path) -> int:
    """Install the ai_rfc submodule in editable mode (if present)."""
    ai_rfc_path = (
        project_root / "panther" / "plugins" / "services" / "testers" / "ai_rfc"
    )
    if not (ai_rfc_path / "pyproject.toml").exists():
        warning_message(
            "Skipping ai_rfc: submodule not initialized"
            " (run 'git submodule update --init')"
        )
        return 0
    info_message("Installing ai_rfc submodule...")
    return run_command(
        [sys.executable, "-m", "pip", "install", "--editable", f"{ai_rfc_path}[mcp]"],
        cwd=project_root,
    )


def _run_tests(project_root: Path) -> int:
    """Run the test suite."""
    info_message("Running tests...")
    result = run_command(
        [sys.executable, "-m", "pip", "install", ".[tests]"], cwd=project_root
    )
    if result != 0:
        return result
    return run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--cov=panther",
            "--cov-report=xml",
            "--cov-report=html",
        ],
        cwd=project_root,
    )


@featured_example("panther build dev")
@click.group()
def build():
    """Build, install, and test the PANTHER package.

    Provides commands for building wheel packages, installing in development
    mode, running tests, and cleaning build artifacts.
    """
    pass


@build.command()
@handle_errors
@pass_context_and_setup_logging
def package(ctx):
    """Build and install the PANTHER wheel package.

    Cleans artifacts, installs dependencies, builds a wheel, and installs it.
    """
    root = find_project_root()
    result = _run_steps(
        lambda: _clean_build_artifacts(root),
        lambda: _install_dependencies(root),
        lambda: _uninstall_package(root),
        lambda: _build_wheel(root),
        lambda: _install_wheel(root),
    )
    if result == 0:
        success_message("Package built and installed successfully.")
    sys.exit(result)


@build.command()
@handle_errors
@pass_context_and_setup_logging
def dev(ctx):
    r"""Install PANTHER in development (editable) mode.

    Cleans artifacts, installs dependencies, performs an editable install,
    and installs the panther_ivy and ai_rfc submodules if present.

    \b
    Example:
      panther build dev
    """
    root = find_project_root()
    result = _run_steps(
        lambda: _clean_build_artifacts(root),
        lambda: _install_dependencies(root),
        lambda: _uninstall_package(root),
        lambda: _install_editable(root),
        lambda: _install_ivy_submodule(root),
        lambda: _install_ai_rfc_submodule(root),
    )
    if result == 0:
        success_message("Development install completed successfully.")
    sys.exit(result)


@build.command()
@handle_errors
@pass_context_and_setup_logging
def test(ctx):
    """Build, install, and run the test suite.

    Builds a wheel package, installs it, then runs pytest with coverage.
    """
    root = find_project_root()
    result = _run_steps(
        lambda: _clean_build_artifacts(root),
        lambda: _install_dependencies(root),
        lambda: _uninstall_package(root),
        lambda: _build_wheel(root),
        lambda: _install_wheel(root),
        lambda: _run_tests(root),
    )
    if result == 0:
        success_message("Tests completed successfully.")
    sys.exit(result)


@build.command()
@handle_errors
@pass_context_and_setup_logging
def install(ctx):
    """Install dependencies and set up editable install.

    Installs build dependencies, performs editable install, and installs
    the panther_ivy and ai_rfc submodules if present.
    """
    root = find_project_root()
    result = _run_steps(
        lambda: _install_dependencies(root),
        lambda: _install_editable(root),
        lambda: _install_ivy_submodule(root),
        lambda: _install_ai_rfc_submodule(root),
    )
    if result == 0:
        success_message("Install completed successfully.")
    sys.exit(result)


@build.command()
@handle_errors
@pass_context_and_setup_logging
def clean(ctx):
    """Clean all build artifacts.

    Removes build/, dist/, docs/, site/, htmlcov/, egg-info, __pycache__,
    and .pyc files.
    """
    root = find_project_root()
    result = _clean_build_artifacts(root)
    sys.exit(result)
