"""Docs Command.

Provides CLI commands for building, serving, and deploying PANTHER documentation.
Replaces the standalone panther_builder.py docs commands.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from panther.cli.core.base import (
    error_message,
    featured_example,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
    warning_message,
)


def _find_project_root() -> Path:
    """Find the project root directory (where pyproject.toml lives)."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return current


def _run_command(cmd, cwd=None):
    """Run a command and return the exit code."""
    click.echo(f"Running: {' '.join(str(c) for c in cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=False)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode
    except FileNotFoundError:
        click.echo(f"Error: Command not found: {cmd[0]}", err=True)
        return 1


def _rmtree_onerror(func, path, exc_info):
    """Handle permission errors during shutil.rmtree."""
    import os
    import stat

    try:
        os.chmod(path, stat.S_IRWXU)
        func(path)
    except PermissionError:
        subprocess.run(["xattr", "-c", path], capture_output=True)
        os.chmod(path, stat.S_IRWXU)
        func(path)


def _build_documentation(project_root: Path) -> int:
    """Build full documentation pipeline."""
    from panther.tools.docs_gen.link_rewriting import (
        copy_md_rewriting_links,
        escape_autorefs,
    )

    # Static build_dict — maps root-level markdown to docs/ locations
    build_dict = {
        "INSTALL.md": "docs/INSTALL.md",
        "QUICK_START.md": "docs/QUICK_START.md",
        "workflow.md": "docs/workflow.md",
        "panther/plugins/plugins_inventory.md": "docs/plugins_inventory.md",
        "CONTRIBUTING.md": "docs/contributing.md",
        "CHANGELOG.md": "docs/changelog.md",
        "LICENSE.md": "docs/license.md",
    }

    # Backup/restore mkdocs.yml
    mkdocs_file = project_root / "mkdocs.yml"
    if mkdocs_file.exists():
        backup_file = project_root / "panther" / "tools" / "docs_gen" / "mkdocs.yml.bak"
        if backup_file.exists():
            info_message(f"Restoring backup of mkdocs.yml from {backup_file}")
            shutil.copy2(backup_file, mkdocs_file)
        info_message(f"Creating backup of mkdocs.yml -> {backup_file}")
        shutil.copy2(mkdocs_file, backup_file)
    else:
        warning_message("mkdocs.yml not found, no backup created")

    info_message("Building documentation...")

    # Clean docs-related artifacts
    for dir_name in ["docs", "site"]:
        dir_path = project_root / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path, onerror=_rmtree_onerror)

    # Install dependencies if not editable install
    _is_editable = (project_root / "panther_net.egg-info").exists() or any(
        Path(sys.prefix, "lib").rglob("__editable__.panther?net*")
    )
    if _is_editable:
        info_message("Editable install detected, skipping pip install .[doc,tests,web]")
    else:
        info_message("Installing documentation dependencies...")
        result = _run_command(
            [sys.executable, "-m", "pip", "install", ".[doc,tests,web]"],
            cwd=project_root,
        )
        if result != 0:
            warning_message("Could not install documentation dependencies")

    # Prepare docs directory
    docs_dir = project_root / "docs"
    if docs_dir.exists():
        shutil.rmtree(docs_dir)
    docs_dir.mkdir(exist_ok=True)

    # Generate plugin inventory
    info_message("Generating plugin inventory...")
    inventory_script = (
        project_root / "panther" / "tools" / "docs_gen" / "generate_plugin_inventory.py"
    )
    if inventory_script.exists():
        result = _run_command(
            [
                sys.executable,
                str(inventory_script),
                "--format",
                "markdown",
                "--output",
                "panther/plugins/plugins_inventory.md",
            ],
            cwd=project_root,
        )
        if result != 0:
            warning_message("Plugin inventory generation failed")

    # Copy flat docs with link rewriting
    info_message("Copying documentation files...")
    for source, destination in build_dict.items():
        source_path = project_root / source
        dest_path = project_root / destination
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.exists():
            click.echo(f"Copying {source} -> {destination}")
            copy_md_rewriting_links(
                source_path,
                dest_path,
                source_rel=source,
                build_dict=build_dict,
                project_root=project_root,
            )
        else:
            warning_message(f"Source file {source} not found")

    # Copy docs_src/ to docs/
    docs_src_dir = project_root / "docs_src"
    if docs_src_dir.exists():
        info_message("Copying docs_src/ to docs/...")
        for src_file in docs_src_dir.rglob("*"):
            if src_file.is_file():
                rel = src_file.relative_to(docs_src_dir)
                dest = docs_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)

    # Copy panther/ markdown hierarchy
    panther_docs_dir = project_root / "docs" / "panther"
    panther_src_dir = project_root / "panther"
    panther_docs_dir.mkdir(parents=True, exist_ok=True)
    _skip_dirs = {"submodules", "template"}
    for md_file in panther_src_dir.rglob("*.md"):
        if md_file.is_file():
            if any(part in _skip_dirs for part in md_file.parts):
                continue
            if md_file.name == "README.md" and (md_file.parent / "index.md").exists():
                continue
            relative_path = md_file.relative_to(panther_src_dir)
            dest_path = panther_docs_dir / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            copy_md_rewriting_links(md_file, dest_path)
            if "panther_ivy" in md_file.parts:
                text = dest_path.read_text(encoding="utf-8")
                dest_path.write_text(escape_autorefs(text), encoding="utf-8")

    # Convert .ivy files to .md
    ivy_setup = (
        project_root / "panther" / "plugins" / "services" / "testers" / "panther_ivy"
    )
    if ivy_setup.exists():
        info_message("Installing ivy for documentation conversion...")
        _run_command(
            [sys.executable, "-m", "pip", "install", "-e", str(ivy_setup)],
            cwd=project_root,
        )
        ivy_to_md_script = ivy_setup / "ivy" / "ivy_to_md.py"
        panther_ivy_docs = (
            project_root
            / "docs"
            / "panther"
            / "plugins"
            / "services"
            / "testers"
            / "panther_ivy"
        )
        if ivy_to_md_script.exists():
            info_message("Converting .ivy files to .md...")
            for ivy_file in ivy_setup.rglob("*.ivy"):
                if "submodules" in ivy_file.parts:
                    continue
                rel = ivy_file.relative_to(ivy_setup)
                dest_md = panther_ivy_docs / rel.with_suffix(".md")
                dest_md.parent.mkdir(parents=True, exist_ok=True)
                _run_command(
                    [
                        sys.executable,
                        "-c",
                        f"import sys; sys.argv = ['ivy_to_md', r'{ivy_file}']; "
                        "from ivy.ivy_to_md import main; main()",
                    ],
                    cwd=project_root,
                )
                generated_md = ivy_file.with_suffix(".md")
                if generated_md.exists():
                    copy_md_rewriting_links(generated_md, dest_md)
                    text = dest_md.read_text(encoding="utf-8")
                    dest_md.write_text(escape_autorefs(text), encoding="utf-8")

    # Generate coverage report
    htmlcov_dir = project_root / "htmlcov"
    placeholder = htmlcov_dir / "index.html"
    has_real_coverage = htmlcov_dir.exists() and not (
        placeholder.exists()
        and "Coverage report not available" in placeholder.read_text()
    )
    if not has_real_coverage:
        result = subprocess.run(
            [sys.executable, "-c", "import pytest; import pytest_cov"],
            capture_output=True,
        )
        if result.returncode == 0:
            info_message("Generating coverage report...")
            _run_command(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/",
                    "-m",
                    "unit",
                    "--cov=panther",
                    "--cov-report=html",
                    "-q",
                    "--no-header",
                ],
                cwd=project_root,
            )
        else:
            warning_message("Skipping coverage: pytest/pytest-cov not installed")
            htmlcov_dir.mkdir(exist_ok=True)
            if not placeholder.exists():
                placeholder.write_text(
                    "<html><body><p>Coverage report not available.</p></body></html>"
                )

    # Build with MkDocs
    info_message("Building documentation with MkDocs...")
    return _run_command(
        ["mkdocs", "build", "--verbose", "--config-file", "mkdocs.yml"],
        cwd=project_root,
    )


@featured_example("panther docs build")
@click.group()
def docs():
    """Build, serve, and deploy PANTHER documentation.

    Provides commands for building documentation with MkDocs, serving
    locally for preview, and deploying to GitHub Pages.
    """
    pass


@docs.command("build")
@handle_errors
@pass_context_and_setup_logging
def docs_build(ctx):
    r"""Build full documentation.

    Generates plugin inventory, copies markdown files with link rewriting,
    converts .ivy files, generates coverage report, and builds with MkDocs.

    \b
    Example:
      panther docs build
    """
    root = _find_project_root()
    result = _build_documentation(root)
    if result == 0:
        success_message("Documentation built successfully.")
    sys.exit(result)


@docs.command()
@handle_errors
@pass_context_and_setup_logging
def serve(ctx):
    r"""Build and serve documentation locally.

    Builds documentation first, then starts a local MkDocs development
    server for previewing.

    \b
    Example:
      panther docs serve
    """
    root = _find_project_root()
    result = _build_documentation(root)
    if result != 0:
        error_message("Documentation build failed.")
        sys.exit(result)

    info_message("Serving documentation locally...")
    mkdocs_result = _run_command(["mkdocs", "--version"], cwd=root)
    if mkdocs_result != 0:
        info_message("Installing MkDocs...")
        _run_command(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "mkdocs",
                "mkdocs-material",
                "mkdocstrings",
            ],
            cwd=root,
        )
    sys.exit(
        _run_command(
            ["mkdocs", "serve", "--verbose", "--config-file", "mkdocs.yml"], cwd=root
        )
    )


@docs.command()
@handle_errors
@pass_context_and_setup_logging
def deploy(ctx):
    r"""Build and deploy documentation to GitHub Pages.

    Builds documentation first, then deploys to GitHub Pages using
    mkdocs gh-deploy.

    \b
    Example:
      panther docs deploy
    """
    root = _find_project_root()
    result = _build_documentation(root)
    if result != 0:
        error_message("Documentation build failed.")
        sys.exit(result)

    info_message("Deploying documentation to GitHub Pages...")
    sys.exit(
        _run_command(
            [
                "mkdocs",
                "gh-deploy",
                "--force",
                "--clean",
                "--config-file",
                "mkdocs.yml",
            ],
            cwd=root,
        )
    )
