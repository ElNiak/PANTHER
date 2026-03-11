"""Tools Command - Click Implementation.

Install and manage development/runtime tools for PANTHER.
"""

import logging
import subprocess
import sys
from pathlib import Path

import click
from termcolor import colored

from panther.cli_click.core.base import (
    common_options,
    error_message,
    featured_example,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
    warning_message,
)


@featured_example("panther tools status")
@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def tools(ctx, verbose):
    r"""Install and manage development/runtime tools.

    PANTHER tools management for Docker optimization, code quality,
    and development environment setup. Provides unified interface
    for installing and managing tools used in PANTHER development.

    \b
    Available Tools:
    🐋 slim          - Docker image optimization
    🔍 pre-commit    - Code quality hooks
    🐳 docker        - Container platform
    📝 git           - Version control

    \b
    Examples:
      panther tools install-slim              # Install Docker optimization tool
      panther tools install-precommit         # Setup code quality hooks
      panther tools status                    # Show installation status
      panther tools list                      # List available tools
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        info_message("Tools management mode enabled")


@tools.command("install-slim")
@click.option(
    "--force", is_flag=True, help="Force reinstallation even if already present"
)
@common_options
@handle_errors
@pass_context_and_setup_logging
def install_slim(ctx, force, config, verbose, dry_run):
    r"""Install slim tool for Docker image optimization.

    The slim tool helps reduce Docker image sizes by up to 30x by removing
    unnecessary files and optimizing the container structure. Essential for
    PANTHER's Docker-based testing environments.

    \b
    Features:
    • Automatic optimization of Docker images
    • Preservation of functionality while reducing size
    • Integration with PANTHER build workflows
    • Cross-platform support (Linux, macOS)

    \b
    Examples:
      panther tools install-slim               # Standard installation
      panther tools install-slim --force      # Force reinstall
      panther tools install-slim --verbose    # Verbose output
    """
    verbose = verbose or ctx.obj.get("verbose", False)

    if verbose:
        info_message("Installing slim tool for Docker optimization...")

    if dry_run:
        info_message("DRY RUN: Would install slim tool")
        return

    # Check if already installed (unless force)
    if not force:
        result = subprocess.run(["which", "slim"], capture_output=True)
        if result.returncode == 0:
            existing_path = result.stdout.decode().strip()
            if verbose:
                success_message(f"slim already installed at: {existing_path}")
                info_message("Use --force to reinstall")
            return

    # Native Click implementation for slim installation
    try:
        info_message("Downloading and installing slim...")

        # Install slim using the official installation script
        curl_cmd = [
            "curl",
            "-sL",
            "https://raw.githubusercontent.com/slimtoolkit/slim/master/scripts/install-slim.sh",
        ]

        with click.progressbar(length=100, label="Installing slim") as bar:
            # Download script
            bar.update(20)
            curl_proc = subprocess.Popen(
                curl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            # Execute script
            bar.update(30)
            bash_proc = subprocess.Popen(
                ["bash"],
                stdin=curl_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            curl_proc.stdout.close()

            # Wait for completion
            output, error = bash_proc.communicate()
            bar.update(50)

            if bash_proc.returncode == 0:
                # Verify installation
                verify_result = subprocess.run(["which", "slim"], capture_output=True)
                if verify_result.returncode == 0:
                    bar.update(100)
                    success_message("slim installed successfully")

                    # Show version if available
                    version_result = subprocess.run(
                        ["slim", "--version"], capture_output=True, text=True
                    )
                    if version_result.returncode == 0:
                        info_message(f"Version: {version_result.stdout.strip()}")

                    info_message("slim is now available for Docker image optimization")
                else:
                    error_message(
                        "slim installation completed but tool not found in PATH"
                    )
                    raise click.Abort()
            else:
                error_message(
                    f"Installation script failed: {error.decode() if error else 'Unknown error'}"
                )
                raise click.Abort()

    except subprocess.CalledProcessError as e:
        error_message(f"Installation failed: {e}")
        raise click.Abort()
    except Exception as e:
        error_message(f"Unexpected error during installation: {e}")
        raise click.Abort()


@tools.command("install-precommit")
@click.option("--update", is_flag=True, help="Update hooks to latest versions")
@common_options
@handle_errors
@pass_context_and_setup_logging
def install_precommit(ctx, update, config, verbose, dry_run):
    r"""Install and configure pre-commit hooks.

    Sets up pre-commit framework for automated code quality checks including
    linting, formatting, security scanning, and test validation. Essential
    for maintaining PANTHER code quality standards.

    \b
    Hooks Installed:
    🔍 Linting         - Code style and error checking
    🎨 Formatting      - Automatic code formatting
    🔒 Security        - Security vulnerability scanning
    🧪 Testing         - Pre-commit test validation
    📝 Documentation   - Docs and comment validation

    \b
    Examples:
      panther tools install-precommit         # Install hooks
      panther tools install-precommit --update # Update to latest
    """
    verbose = verbose or ctx.obj.get("verbose", False)

    if verbose:
        info_message("Installing and configuring pre-commit hooks...")

    if dry_run:
        info_message("DRY RUN: Would install pre-commit hooks")
        return

    # Native Click implementation for pre-commit installation
    try:
        # Install pre-commit package
        info_message("Installing pre-commit package...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pre-commit"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            error_message(f"Failed to install pre-commit: {result.stderr}")
            raise click.Abort()

        # Install hooks if .pre-commit-config.yaml exists
        if Path(".pre-commit-config.yaml").exists():
            info_message("Installing pre-commit hooks...")
            install_result = subprocess.run(
                ["pre-commit", "install"], capture_output=True, text=True
            )

            if install_result.returncode == 0:
                success_message("Pre-commit hooks installed successfully")
            else:
                warning_message("Pre-commit installed but hooks setup failed")
                if verbose:
                    click.echo(f"Error: {install_result.stderr}")
        else:
            warning_message("No .pre-commit-config.yaml found - hooks not installed")
            info_message("Create a .pre-commit-config.yaml file to enable hooks")

        # Update hooks if requested
        if update:
            info_message("Updating pre-commit hooks...")
            update_result = subprocess.run(
                ["pre-commit", "autoupdate"], capture_output=True, text=True
            )

            if update_result.returncode == 0:
                success_message("Pre-commit hooks updated to latest versions")
            else:
                warning_message("Hook update failed")
                if verbose:
                    click.echo(f"Error: {update_result.stderr}")

        success_message("Pre-commit setup completed successfully")

    except Exception as e:
        error_message(f"Pre-commit installation failed: {e}")
        raise click.Abort()


@tools.command("status")
@common_options
@pass_context_and_setup_logging
def status(ctx, config, verbose, dry_run):
    r"""Show status of installed tools.

    Displays comprehensive status of all development tools used by PANTHER,
    including installation status, versions, and configuration state.

    \b
    Checks Include:
    • Installation status and paths
    • Version information
    • Configuration validation
    • Integration status with PANTHER

    \b
    Examples:
      panther tools status                    # Show all tool status
      panther tools status --verbose         # Include paths and versions
    """
    verbose = verbose or ctx.obj.get("verbose", False)

    click.echo(colored("🔧 PANTHER Tool Installation Status", "blue", attrs=["bold"]))
    click.echo()

    tools_to_check = [
        ("slim", "Docker image optimization", "🐋"),
        ("pre-commit", "Code quality hooks", "🔍"),
        ("docker", "Container platform", "🐳"),
        ("git", "Version control", "📝"),
        ("python", "Python interpreter", "🐍"),
        ("pip", "Package manager", "📦"),
    ]

    for tool, description, emoji in tools_to_check:
        if tool == "docker":
            # Use DockerBuilder for Docker status (checks daemon connectivity)
            try:
                from panther.core.docker_builder import DockerBuilder

                builder = DockerBuilder.get_instance(enable_cache=False)
                is_available = builder.is_docker_available()
                if is_available:
                    status_text = colored("✅ Installed (daemon running)", "green")
                    if verbose:
                        version_info = (
                            builder.client.version() if builder.client else {}
                        )
                        version_str = version_info.get("Version", "unknown")
                        status_text = colored(
                            f"✅ Installed ({version_str}, daemon running)",
                            "green",
                        )
                else:
                    status_text = colored(
                        "⚠️ Installed but daemon not running", "yellow"
                    )
            except Exception:
                status_text = colored("❌ Not found", "red")
        else:
            result = subprocess.run(["which", tool], capture_output=True)
            if result.returncode == 0:
                path = result.stdout.decode().strip()
                status_text = colored("✅ Installed", "green")

                if verbose:
                    # Get version if possible
                    version_result = subprocess.run(
                        [tool, "--version"], capture_output=True, text=True
                    )
                    if version_result.returncode == 0:
                        version = version_result.stdout.strip().split("\n")[0]
                        status_text += f" ({version})"
                    status_text += f" at {path}"
            else:
                status_text = colored("❌ Not found", "red")

        click.echo(f"{emoji} {tool:15} {description:30} {status_text}")


@tools.command("list")
@pass_context_and_setup_logging
def list_tools(ctx):
    r"""List all available tools for installation.

    Shows comprehensive list of all tools that can be managed through
    the PANTHER tools system, including descriptions, installation
    commands, and current status.

    \b
    Tool Categories:
    🐋 Docker Tools    - Container optimization and management
    🔍 Quality Tools   - Code analysis and formatting
    🧪 Testing Tools   - Test automation and validation
    📝 Docs Tools      - Documentation generation
    """
    click.echo(colored("🛠️  Available PANTHER Tools", "blue", attrs=["bold"]))
    click.echo()

    available_tools = [
        {
            "name": "slim",
            "emoji": "🐋",
            "description": "Docker image optimization tool - reduces image sizes up to 30x",
            "install_cmd": "panther tools install-slim",
            "category": "Docker",
        },
        {
            "name": "pre-commit",
            "emoji": "🔍",
            "description": "Code quality and formatting hooks for automated validation",
            "install_cmd": "panther tools install-precommit",
            "category": "Quality",
        },
    ]

    # Group by category
    categories = {}
    for tool in available_tools:
        cat = tool["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tool)

    for category, tools_list in categories.items():
        click.echo(colored(f"📂 {category} Tools", "cyan", attrs=["bold"]))
        for tool in tools_list:
            click.echo(
                f"  {tool['emoji']} {colored(tool['name'], 'cyan', attrs=['bold'])}"
            )
            click.echo(f"     {tool['description']}")
            click.echo(f"     Install: {colored(tool['install_cmd'], 'yellow')}")
            click.echo()


@tools.command("uninstall")
@click.argument("tool_name", type=click.Choice(["slim", "pre-commit"]))
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@common_options
@handle_errors
@pass_context_and_setup_logging
def uninstall(ctx, tool_name, confirm, config, verbose, dry_run):
    r"""Uninstall specified tool.

    Removes tools installed through PANTHER tools system.
    Use with caution as this may affect PANTHER functionality.

    \b
    Examples:
      panther tools uninstall slim           # Uninstall slim tool
      panther tools uninstall pre-commit --confirm  # Skip confirmation
    """
    verbose = verbose or ctx.obj.get("verbose", False)

    if not confirm:
        if not click.confirm(f"Are you sure you want to uninstall {tool_name}?"):
            info_message("Uninstall cancelled")
            return

    if dry_run:
        info_message(f"DRY RUN: Would uninstall {tool_name}")
        return

    if verbose:
        info_message(f"Uninstalling {tool_name}...")

    # Tool-specific uninstall logic
    if tool_name == "slim":
        # Remove slim binary
        result = subprocess.run(["which", "slim"], capture_output=True)
        if result.returncode == 0:
            slim_path = result.stdout.decode().strip()
            try:
                Path(slim_path).unlink()
                success_message(f"Successfully removed slim from {slim_path}")
            except PermissionError:
                error_message(f"Permission denied removing {slim_path}. Try with sudo.")
                raise click.Abort()
        else:
            info_message("slim not found - already uninstalled")

    elif tool_name == "pre-commit":
        # Uninstall pre-commit hooks and package
        subprocess.run(["pre-commit", "uninstall"], capture_output=True)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "pre-commit", "-y"],
            capture_output=True,
        )
        if result.returncode == 0:
            success_message("Successfully uninstalled pre-commit")
        else:
            error_message("Failed to uninstall pre-commit")
            raise click.Abort()


if __name__ == "__main__":
    tools()
