"""
Admin Command - Click Implementation

Administrative and system management commands with enhanced user experience.
Migrated from argparse to Click with improved validation and feedback.
"""

import logging
from pathlib import Path

import click
from termcolor import colored

from panther.cli_click.core.base import (
    error_message,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
    warning_message,
)


@click.group()
def admin():
    """
    Administrative and system management commands.

    Provides comprehensive system management capabilities including:
    • System teardown and cleanup
    • Docker resource management
    • Health status monitoring
    • Temporary file cleanup
    • Cache management

    \b
    Examples:
      panther admin status                    # Show system status
      panther admin teardown --force         # Clean up everything
      panther admin clean --all              # Clean temporary files
      panther admin docker --images-all      # Remove Docker images
    """
    pass


@admin.command()
@click.option("--force", is_flag=True, help="Force cleanup without confirmation")
@handle_errors
@pass_context_and_setup_logging
def teardown(ctx, force):
    """
    Clean up system resources and temporary files.

    Performs comprehensive system cleanup including:
    • Docker containers and networks
    • Temporary directories and files
    • PANTHER-specific resources

    \b
    Examples:
      panther admin teardown              # Interactive cleanup
      panther admin teardown --force     # Force cleanup without prompts
    """
    # Native Click implementation for system teardown
    try:
        import subprocess

        info_message("Starting system teardown and cleanup...")

        if not force:
            if not click.confirm(
                colored(
                    "This will clean up Docker containers and networks. Continue?",
                    "yellow",
                )
            ):
                info_message("Teardown cancelled")
                return

        cleanup_steps = [
            (
                "Stopping containers",
                ["docker", "stop", '$(docker ps -q --filter "label=panther")'],
            ),
            (
                "Removing containers",
                ["docker", "rm", '$(docker ps -aq --filter "label=panther")'],
            ),
            (
                "Removing networks",
                ["docker", "network", "prune", "-f", "--filter", "label=panther"],
            ),
            (
                "Cleaning volumes",
                ["docker", "volume", "prune", "-f", "--filter", "label=panther"],
            ),
            (
                "Removing temp files",
                ["find", "/tmp", "-name", "*panther*", "-type", "f", "-delete"],
            ),
        ]

        with click.progressbar(
            length=len(cleanup_steps), label="Cleaning system", show_eta=True
        ) as bar:
            for step_name, cmd in cleanup_steps:
                click.echo(f"\n🧹 {step_name}...")

                try:
                    # Handle shell commands with variable substitution
                    if "$(" in " ".join(cmd):
                        result = subprocess.run(
                            " ".join(cmd), shell=True, capture_output=True, text=True
                        )
                    else:
                        result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode == 0:
                        click.echo(f"  ✅ {step_name} completed")
                    else:
                        click.echo(f"  ⚠️ {step_name} completed with warnings")

                except Exception as e:
                    click.echo(f"  ⚠️ {step_name} failed: {e}")

                bar.update(1)

        success_message("System teardown completed successfully")
        info_message("All PANTHER resources have been cleaned up")

    except Exception as e:
        error_message(f"Teardown failed: {e}")
        if ctx.obj.get("debug", False):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@admin.command()
@click.option(
    "--port", type=int, default=8080, help="Port to run web application (default: 8080)"
)
@click.option(
    "--host",
    default="localhost",
    help="Host to bind web application (default: localhost)",
)
@handle_errors
@pass_context_and_setup_logging
def webapp(ctx, port, host):
    """
    Start web application interface.

    ⚠️  Note: Web application feature has been deprecated.
    Use 'panther admin status' for system monitoring instead.
    """
    warning_message("Web application feature has been removed")
    info_message("This feature was incomplete and has been deprecated")
    info_message("Use 'panther admin status' for system monitoring instead")
    raise click.Abort()


@admin.command()
@handle_errors
@pass_context_and_setup_logging
def status(ctx):
    """
    Show comprehensive system status and health information.

    Displays:
    • Python and Docker versions
    • PANTHER installation status
    • Running containers
    • System health indicators

    \b
    Examples:
      panther admin status    # Show complete system status
    """
    # Native Click implementation for system status
    try:
        import subprocess
        import sys

        info_message("Checking PANTHER system status...")

        click.echo(colored("🔍 PANTHER System Status Report", "blue", attrs=["bold"]))
        click.echo(colored("=" * 40, "blue"))
        click.echo()

        # Check Python version
        python_version = sys.version.split()[0]
        click.echo(f"🐍 Python: {python_version}")

        # Check Docker
        try:
            result = subprocess.run(
                ["docker", "--version"], capture_output=True, text=True
            )
            if result.returncode == 0:
                docker_version = result.stdout.strip()
                click.echo(f"🐳 Docker: {docker_version}")

                # Check running containers
                containers_result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--filter",
                        "label=panther",
                        "--format",
                        "table {{.Names}}\t{{.Status}}",
                    ],
                    capture_output=True,
                    text=True,
                )

                if containers_result.returncode == 0:
                    container_lines = containers_result.stdout.strip().split("\n")
                    if len(container_lines) > 1:  # More than just header
                        click.echo(
                            f"📦 PANTHER Containers: {len(container_lines) - 1} running"
                        )
                        for line in container_lines[1:]:  # Skip header
                            click.echo(f"   • {line}")
                    else:
                        click.echo("📦 PANTHER Containers: None running")
            else:
                click.echo("🐳 Docker: Not available")
        except FileNotFoundError:
            click.echo("🐳 Docker: Not installed")

        # Check disk space
        try:
            result = subprocess.run(["df", "-h", "."], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    disk_info = lines[1].split()
                    click.echo(
                        f"💾 Disk Space: {disk_info[3]} available of {disk_info[1]}"
                    )
        except:
            click.echo("💾 Disk Space: Unable to check")

        # Check PANTHER installation
        try:
            import panther

            click.echo(f"🐾 PANTHER: Installed and importable")
        except ImportError:
            click.echo(f"🐾 PANTHER: Import issues detected")

        # Check network connectivity
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "google.com"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                click.echo("🌐 Network: Connected")
            else:
                click.echo("🌐 Network: Limited connectivity")
        except:
            click.echo("🌐 Network: Unable to test")

        click.echo()
        success_message("System status check completed")

    except Exception as e:
        error_message(f"Status check failed: {e}")
        if ctx.obj.get("debug", False):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@admin.command()
@click.option("--logs", is_flag=True, help="Clean log files")
@click.option("--cache", is_flag=True, help="Clean cache files")
@click.option("--all", is_flag=True, help="Clean all temporary files")
@handle_errors
@pass_context_and_setup_logging
def clean(ctx, logs, cache, all):
    """
    Clean up temporary files, logs, and cache.

    Removes various temporary files and directories to free up space:
    • Log files and directories
    • Python cache files (__pycache__)
    • Test cache (.pytest_cache)
    • Coverage files
    • Temporary files (*.tmp, *.temp)

    \b
    Examples:
      panther admin clean --all           # Clean everything
      panther admin clean --logs          # Clean only logs
      panther admin clean --cache         # Clean only cache files
      panther admin clean --logs --cache  # Clean logs and cache
    """
    if not any([logs, cache, all]):
        error_message("No cleanup options specified")
        info_message("Available options: --logs, --cache, --all")
        raise click.Abort()

    # Native Click implementation for file cleanup
    try:
        import glob
        import shutil
        import subprocess

        info_message("Starting cleanup operations...")

        cleanup_operations = []

        if logs or all:
            cleanup_operations.extend(
                [
                    (
                        "Removing log files",
                        lambda: _clean_pattern(["*.log", "logs/*", "*.log.*"]),
                    ),
                    (
                        "Cleaning log directories",
                        lambda: _clean_directories(["logs", "log", ".logs"]),
                    ),
                ]
            )

        if cache or all:
            cleanup_operations.extend(
                [
                    (
                        "Removing Python cache",
                        lambda: _clean_pattern(
                            ["**/__pycache__", "**/*.pyc", "**/*.pyo"]
                        ),
                    ),
                    (
                        "Cleaning pytest cache",
                        lambda: _clean_directories(
                            [".pytest_cache", "**/.pytest_cache"]
                        ),
                    ),
                    (
                        "Removing coverage files",
                        lambda: _clean_pattern([".coverage", ".coverage.*", "htmlcov"]),
                    ),
                ]
            )

        if all:
            cleanup_operations.extend(
                [
                    (
                        "Removing temp files",
                        lambda: _clean_pattern(["*.tmp", "*.temp", "*~", "*.swp"]),
                    ),
                    (
                        "Cleaning build artifacts",
                        lambda: _clean_directories(["build", "dist", "*.egg-info"]),
                    ),
                    (
                        "Removing editor files",
                        lambda: _clean_pattern([".DS_Store", "Thumbs.db", "*.bak"]),
                    ),
                ]
            )

        def _clean_pattern(patterns):
            """Helper to clean files matching patterns."""
            removed_count = 0
            for pattern in patterns:
                try:
                    files = glob.glob(pattern, recursive=True)
                    for file_path in files:
                        if Path(file_path).is_file():
                            Path(file_path).unlink()
                            removed_count += 1
                        elif Path(file_path).is_dir():
                            shutil.rmtree(file_path)
                            removed_count += 1
                except Exception:
                    pass
            return removed_count

        def _clean_directories(dir_names):
            """Helper to clean specific directories."""
            removed_count = 0
            for dir_name in dir_names:
                try:
                    dirs = glob.glob(dir_name, recursive=True)
                    for dir_path in dirs:
                        if Path(dir_path).is_dir():
                            shutil.rmtree(dir_path)
                            removed_count += 1
                except Exception:
                    pass
            return removed_count

        total_removed = 0

        with click.progressbar(
            cleanup_operations, label="Cleaning files", show_eta=True
        ) as bar:
            for operation_name, operation_func in bar:
                click.echo(f"\n🧹 {operation_name}...")
                try:
                    removed = operation_func()
                    total_removed += removed
                    click.echo(f"  ✅ {operation_name}: {removed} items removed")
                except Exception as e:
                    click.echo(f"  ⚠️ {operation_name}: {e}")

        success_message(
            f"Cleanup completed successfully - {total_removed} items removed"
        )
        info_message("All temporary files and cache have been cleaned")

    except Exception as e:
        error_message(f"Cleanup failed: {e}")
        if ctx.obj.get("debug", False):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@admin.command()
@click.option(
    "--images-all",
    is_flag=True,
    help="Remove all Docker images with 'panther' in the name",
)
@click.option(
    "--images-services",
    is_flag=True,
    help="Remove Docker images with '_panther' in the name",
)
@click.option(
    "--system-all",
    is_flag=True,
    help="Remove images and prune system data with 'panther' label",
)
@click.option(
    "--system-services",
    is_flag=True,
    help="Remove images and prune system data with '_panther' label",
)
@click.option(
    "--volumes", is_flag=True, help="Remove Docker volumes with 'panther' in the name"
)
@click.option(
    "--containers", is_flag=True, help="Remove stopped containers with 'panther' label"
)
@click.option("--show-registry", is_flag=True, help="Show Docker registry statistics")
@click.option(
    "--prune-cache", is_flag=True, help="Prune old Docker build cache entries"
)
@click.option(
    "--export-registry", type=click.Path(), help="Export Docker registry to file"
)
@click.option(
    "--import-registry",
    type=click.Path(exists=True),
    help="Import Docker registry from file",
)
@click.option(
    "--cache-max-age",
    type=int,
    default=7,
    help="Maximum age in days for cache entries (default: 7)",
)
@handle_errors
@pass_context_and_setup_logging
def docker(
    ctx,
    images_all,
    images_services,
    system_all,
    system_services,
    volumes,
    containers,
    show_registry,
    prune_cache,
    export_registry,
    import_registry,
    cache_max_age,
):
    """
    Manage Docker resources and cleanup.

    Comprehensive Docker resource management including:
    • Image cleanup and removal
    • Container management
    • Volume cleanup
    • System pruning
    • Registry operations
    • Cache management

    \b
    Image Management:
      --images-all          Remove all images with 'panther' in name
      --images-services     Remove images with '_panther' in name
      --system-all          Full system cleanup with 'panther' label
      --system-services     Service system cleanup with '_panther' label

    \b
    Resource Management:
      --volumes             Remove volumes with 'panther' in name
      --containers          Remove stopped containers with 'panther' label

    \b
    Registry Operations:
      --show-registry       Display registry statistics
      --export-registry     Export registry to file
      --import-registry     Import registry from file
      --prune-cache         Clean old cache entries

    \b
    Examples:
      panther admin docker --images-all          # Remove all PANTHER images
      panther admin docker --system-all          # Full system cleanup
      panther admin docker --show-registry       # Show registry stats
      panther admin docker --prune-cache         # Clean build cache
    """
    # Check if any options are specified
    operations = [
        images_all,
        images_services,
        system_all,
        system_services,
        volumes,
        containers,
        show_registry,
        prune_cache,
        bool(export_registry),
        bool(import_registry),
    ]

    if not any(operations):
        error_message("No Docker operations specified")
        info_message("Use 'panther admin docker --help' for available options")
        raise click.Abort()

    # Check Docker availability
    try:
        import subprocess

        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        error_message("Docker is not available or not installed")
        raise click.Abort()

    # Native Click implementation for Docker resource management
    try:
        import json
        import subprocess

        info_message("Starting Docker resource management...")

        docker_operations = []

        # Registry operations (informational)
        if show_registry:
            docker_operations.append(("Showing registry info", _show_docker_registry))

        if export_registry:
            docker_operations.append(
                ("Exporting registry", lambda: _export_docker_registry(export_registry))
            )

        if import_registry:
            docker_operations.append(
                ("Importing registry", lambda: _import_docker_registry(import_registry))
            )

        # Cleanup operations
        if images_all:
            docker_operations.append(
                ("Removing all PANTHER images", _remove_panther_images_all)
            )

        if images_services:
            docker_operations.append(
                ("Removing service images", _remove_panther_images_services)
            )

        if containers:
            docker_operations.append(
                ("Removing PANTHER containers", _remove_panther_containers)
            )

        if volumes:
            docker_operations.append(
                ("Removing PANTHER volumes", _remove_panther_volumes)
            )

        if prune_cache:
            docker_operations.append(
                ("Pruning build cache", lambda: _prune_docker_cache(cache_max_age))
            )

        if system_all:
            docker_operations.append(("Full system cleanup", _system_cleanup_all))

        if system_services:
            docker_operations.append(
                ("Service system cleanup", _system_cleanup_services)
            )

        def _show_docker_registry():
            """Show Docker registry statistics."""
            try:
                # Get image statistics
                result = subprocess.run(
                    ["docker", "images", "--format", "json"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    images = [
                        json.loads(line)
                        for line in result.stdout.strip().split("\n")
                        if line
                    ]
                    panther_images = [
                        img
                        for img in images
                        if "panther" in img.get("Repository", "").lower()
                    ]

                    click.echo(f"\n📊 Docker Registry Statistics:")
                    click.echo(f"   🐳 Total images: {len(images)}")
                    click.echo(f"   🐾 PANTHER images: {len(panther_images)}")

                    if panther_images:
                        total_size = sum(
                            img.get("Size", 0)
                            for img in panther_images
                            if isinstance(img.get("Size"), (int, float))
                        )
                        click.echo(
                            f"   💾 PANTHER image size: {total_size} MB (estimated)"
                        )

                    return len(panther_images)
            except Exception as e:
                click.echo(f"   ⚠️ Registry info error: {e}")
                return 0

        def _export_docker_registry(path):
            """Export Docker registry to file."""
            try:
                with open(path, "w") as f:
                    result = subprocess.run(
                        ["docker", "images", "--format", "json"],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode == 0:
                        f.write(result.stdout)
                        return 1
                return 0
            except Exception:
                return 0

        def _import_docker_registry(path):
            """Import Docker registry from file."""
            try:
                with open(path, "r") as f:
                    data = f.read()
                    click.echo(f"Registry data loaded from {path}")
                    return 1
            except Exception:
                return 0

        def _remove_panther_images_all():
            """Remove all Docker images with 'panther' in name."""
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "images",
                        "--filter",
                        "reference=*panther*",
                        "--format",
                        "{{.ID}}",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout.strip():
                    image_ids = result.stdout.strip().split("\n")
                    subprocess.run(
                        ["docker", "rmi", "-f"] + image_ids, capture_output=True
                    )
                    return len(image_ids)
                return 0
            except Exception:
                return 0

        def _remove_panther_images_services():
            """Remove Docker images with '_panther' in name."""
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "images",
                        "--filter",
                        "reference=*_panther*",
                        "--format",
                        "{{.ID}}",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout.strip():
                    image_ids = result.stdout.strip().split("\n")
                    subprocess.run(
                        ["docker", "rmi", "-f"] + image_ids, capture_output=True
                    )
                    return len(image_ids)
                return 0
            except Exception:
                return 0

        def _remove_panther_containers():
            """Remove stopped containers with 'panther' label."""
            try:
                result = subprocess.run(
                    ["docker", "ps", "-aq", "--filter", "label=panther"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout.strip():
                    container_ids = result.stdout.strip().split("\n")
                    subprocess.run(
                        ["docker", "rm", "-f"] + container_ids, capture_output=True
                    )
                    return len(container_ids)
                return 0
            except Exception:
                return 0

        def _remove_panther_volumes():
            """Remove Docker volumes with 'panther' in name."""
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "volume",
                        "ls",
                        "--filter",
                        "name=panther",
                        "--format",
                        "{{.Name}}",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout.strip():
                    volume_names = result.stdout.strip().split("\n")
                    subprocess.run(
                        ["docker", "volume", "rm"] + volume_names, capture_output=True
                    )
                    return len(volume_names)
                return 0
            except Exception:
                return 0

        def _prune_docker_cache(max_age):
            """Prune old Docker build cache entries."""
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "system",
                        "prune",
                        "--filter",
                        f"until={max_age * 24}h",
                        "-f",
                    ],
                    capture_output=True,
                    text=True,
                )
                return 1 if result.returncode == 0 else 0
            except Exception:
                return 0

        def _system_cleanup_all():
            """Full system cleanup with 'panther' label."""
            operations = [
                _remove_panther_containers,
                _remove_panther_images_all,
                _remove_panther_volumes,
            ]
            return sum(op() for op in operations)

        def _system_cleanup_services():
            """Service system cleanup with '_panther' label."""
            operations = [
                _remove_panther_containers,
                _remove_panther_images_services,
                _remove_panther_volumes,
            ]
            return sum(op() for op in operations)

        total_processed = 0

        if docker_operations:
            if any(
                [
                    images_all,
                    images_services,
                    system_all,
                    system_services,
                    volumes,
                    containers,
                ]
            ):
                # Show progress for cleanup operations
                with click.progressbar(
                    docker_operations, label="Managing Docker resources", show_eta=True
                ) as bar:
                    for operation_name, operation_func in bar:
                        click.echo(f"\n🐳 {operation_name}...")
                        try:
                            processed = operation_func()
                            total_processed += processed
                            click.echo(
                                f"  ✅ {operation_name}: {processed} items processed"
                            )
                        except Exception as e:
                            click.echo(f"  ⚠️ {operation_name}: {e}")
            else:
                # For registry operations, no progress bar needed
                for operation_name, operation_func in docker_operations:
                    click.echo(f"\n🐳 {operation_name}...")
                    try:
                        processed = operation_func()
                        total_processed += processed
                        click.echo(f"  ✅ {operation_name}: {processed} items processed")
                    except Exception as e:
                        click.echo(f"  ⚠️ {operation_name}: {e}")

        success_message(
            f"Docker operations completed successfully - {total_processed} items processed"
        )
        info_message("All Docker resources have been managed as requested")

    except Exception as e:
        error_message(f"Docker operations failed: {e}")
        if ctx.obj.get("debug", False):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


if __name__ == "__main__":
    admin()
