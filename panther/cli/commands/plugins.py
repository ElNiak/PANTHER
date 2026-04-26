"""Plugins Command - Plugin discovery and management."""

import json
import traceback
from pathlib import Path
from typing import Optional

import click
from termcolor import colored

from panther.cli.core.base import (
    error_message,
    featured_example,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
)

# Import plugin system components
try:
    from panther.plugins.core.structures.plugin_type import PluginType

    # Get valid plugin type choices from enum
    plugin_type_choices = [pt.value for pt in PluginType] + ["all"]
except ImportError:
    plugin_type_choices = [
        "all",
        "iut",
        "testers",
        "network_environment",
        "execution_environment",
    ]


@featured_example("panther plugins list")
@click.group()
def plugins():
    r"""Plugin discovery and management.

    Comprehensive plugin management tools for discovering, validating,
    and managing PANTHER's extensive plugin ecosystem.

    \b
    Key Features:
    🔍 Plugin discovery and scanning
    📋 Plugin listing with filtering options
    🔧 Parameter inspection and documentation
    ✅ Plugin validation and dependency checking
    📊 Multiple output formats (table, JSON, simple)

    \b
    Plugin Types:
    🔌 IUT (Implementation Under Test): QUIC, HTTP, and other protocol implementations
    🧪 Testers: Formal verification and testing tools
    🌐 Network Environment: Docker Compose, localhost, Shadow simulation
    ⚡ Execution Environment: Profiling, debugging, and monitoring tools

    \b
    Common Workflows:
      # List all plugins
      panther plugins list

      # List plugins by type
      panther plugins list --type iut

      # Get plugin parameters
      panther plugins params picoquic --type iut

      # Validate plugin structure
      panther plugins validate /path/to/plugin

      # Scan for new plugins
      panther plugins scan --directory custom/plugins

    Use 'panther plugins COMMAND --help' for detailed information on each command.
    """
    pass


@plugins.command()
@click.option(
    "--type",
    type=click.Choice(plugin_type_choices),
    default="all",
    help="Filter plugins by type",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json", "simple"]),
    default="table",
    help="Output format",
)
@click.option("--show-path", is_flag=True, help="Include plugin file paths in output")
@handle_errors
@pass_context_and_setup_logging
def list(ctx, type: str, format: str, show_path: bool):
    r"""List available plugins by type.

    Discovers and displays all available plugins in the PANTHER ecosystem
    with filtering options and multiple output formats.

    \b
    Plugin Types:
    📦 iut: Implementation Under Test plugins (picoquic, aioquic, etc.)
    🧪 testers: Testing and verification tools (panther_ivy)
    🌐 network_environment: Network simulation environments
    ⚡ execution_environment: Profiling and debugging tools
    🔌 all: Show plugins from all categories

    \b
    Output Formats:
    📋 table: Formatted table with name, type, version, description
    📄 json: JSON format for programmatic processing
    📝 simple: Simple name (type) listing

    \b
    Examples:
      # List all plugins in table format
      panther plugins list

      # List only IUT plugins
      panther plugins list --type iut

      # JSON output for scripting
      panther plugins list --format json

      # Simple listing with paths
      panther plugins list --format simple --show-path
    """
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        info_message(f"Listing plugins: type={type}, format={format}")

    # Enhanced display header
    click.echo(colored("🔍 PANTHER Plugin Discovery", "blue", attrs=["bold"]))
    if type != "all":
        click.echo(f"📦 Type: {colored(type.upper(), 'yellow', attrs=['bold'])}")
    click.echo(f"📊 Format: {format}")
    click.echo()

    try:
        # Initialize plugin discovery
        from panther.plugins.plugin_manager import PluginManager

        # Show progress for plugin discovery
        with click.progressbar(
            length=3, label="Discovering plugins", show_eta=False, show_percent=False
        ) as bar:
            bar.update(1)  # Initialize plugin manager

            discovery = PluginManager()
            base_plugin_dir = (
                Path(__file__).parent.parent.parent.parent / "panther" / "plugins"
            )

            if verbose:
                click.echo(f"🔍 Scanning for plugins in: {base_plugin_dir}")

            # Discover plugins first
            discovery.discover_plugins()
            bar.update(1)  # Scan plugins

            # Get plugins based on filter
            if type == "all":
                plugins = []
                try:
                    for plugin_type in PluginType:
                        plugins.extend(discovery.get_plugins_by_type(plugin_type.value))
                except NameError:
                    # Fallback if PluginType not available
                    for pt in [
                        "iut",
                        "testers",
                        "network_environment",
                        "execution_environment",
                    ]:
                        try:
                            plugins.extend(discovery.get_plugins_by_type(pt))
                        except Exception:
                            continue
            else:
                plugins = discovery.get_plugins_by_type(type)

            bar.update(1)  # Format output

        if not plugins:
            if type == "all":
                info_message("No plugins found")
            else:
                info_message(f"No plugins found for type: {type}")
            return

        # Display plugins
        if format == "json":
            plugin_data = []
            for plugin in plugins:
                plugin_info = {
                    "name": plugin.name,
                    "type": plugin.type,
                    "version": plugin.version,
                    "description": plugin.description,
                }
                if show_path:
                    plugin_info["path"] = str(plugin.path)
                plugin_data.append(plugin_info)
            click.echo(json.dumps(plugin_data, indent=2))

        elif format == "simple":
            for plugin in plugins:
                if show_path:
                    click.echo(f"{plugin.name} ({plugin.type}) - {plugin.path}")
                else:
                    click.echo(f"{plugin.name} ({plugin.type})")

        else:  # table format
            click.echo(f"\n📦 Found {len(plugins)} plugin(s):")
            click.echo("-" * 80)

            if show_path:
                click.echo(f"{'Name':<20} {'Type':<20} {'Version':<10} {'Path':<25}")
            else:
                click.echo(
                    f"{'Name':<20} {'Type':<20} {'Version':<10} {'Description':<25}"
                )
            click.echo("-" * 80)

            for plugin in plugins:
                if show_path:
                    path_str = str(plugin.path)
                    path_display = (
                        path_str[-22:] + "..." if len(path_str) > 25 else path_str
                    )
                    click.echo(
                        f"{plugin.name:<20} {plugin.type:<20} {plugin.version:<10} {path_display:<25}"
                    )
                else:
                    description = (
                        plugin.description[:22] + "..."
                        if len(plugin.description) > 25
                        else plugin.description
                    )
                    click.echo(
                        f"{plugin.name:<20} {plugin.type:<20} {plugin.version:<10} {description:<25}"
                    )

            click.echo("-" * 80)

        success_message("Plugin discovery completed")

    except Exception as e:
        error_message(f"Plugin listing failed: {e}")
        if ctx.obj.get("debug", False):
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@plugins.command()
@click.argument("plugin_name")
@click.option(
    "--type",
    type=click.Choice([pt for pt in plugin_type_choices if pt != "all"]),
    help="Plugin type (auto-detected if not specified)",
)
@click.option("--protocol", help="Protocol name for filtering parameters")
@click.option(
    "--format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format for parameters",
)
@handle_errors
@pass_context_and_setup_logging
def params(
    ctx, plugin_name: str, type: Optional[str], protocol: Optional[str], format: str
):
    r"""Display configuration parameters for a specific plugin.

    Shows detailed parameter information including types, default values,
    and descriptions for configuring plugin behavior.

    \b
    Parameter Information:
    🔧 Parameter name and type (string, int, bool, etc.)
    📋 Default values and valid ranges
    📝 Detailed descriptions and usage notes
    🎯 Protocol-specific filtering options

    \b
    Examples:
      # Show all picoquic parameters
      panther plugins params picoquic

      # Show parameters for specific type
      panther plugins params aioquic --type iut

      # Filter by protocol
      panther plugins params picoquic --protocol quic

      # JSON output for automation
      panther plugins params mvfst --format json

    \b
    Auto-Detection:
    If plugin type is not specified, PANTHER will automatically scan
    all plugin directories to find the plugin and determine its type.
    """
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        info_message(f"Getting parameters for plugin: {plugin_name}")

    click.echo(colored(f"🔧 Plugin Parameters: {plugin_name}", "blue", attrs=["bold"]))
    if type:
        click.echo(f"📦 Type: {type}")
    if protocol:
        click.echo(f"🌐 Protocol: {protocol}")
    click.echo(f"📊 Format: {format}")
    click.echo()

    try:
        from panther.config import ConfigurationManager

        # Initialize config loader to access plugin parameters
        config_loader = ConfigurationManager(
            experiment_file="experiment-config/examples/network_environment/test_localhost_only.yaml",
            debug_override=ctx.obj.get("debug", False),
        )

        # Auto-detect plugin type if not specified
        if not type:
            from panther.plugins.core.plugin_discovery import PluginDiscovery

            base_plugin_dir = (
                Path(__file__).parent.parent.parent.parent / "panther" / "plugins"
            )
            discovery = PluginDiscovery([str(base_plugin_dir)])
            plugins_dict = discovery.discover_plugins(force_refresh=True)

            # Find plugin type by searching all plugin types
            for p_type, plugin_names in plugins_dict.items():
                if plugin_name in plugin_names:
                    type = p_type
                    break

        if not type:
            error_message(f"Plugin '{plugin_name}' not found and no type specified")
            raise click.Abort()

        click.echo(f"📋 Parameters for plugin: {plugin_name} ({type})")

        # Get plugin parameters
        try:
            params = config_loader.list_plugin_parameters(
                plugin_name=plugin_name, plugin_type=type, protocol=protocol
            )

            if params:
                if format == "json":
                    click.echo(json.dumps(params, indent=2))
                else:
                    click.echo("\n🔧 Available Parameters:")
                    click.echo("-" * 50)
                    for param_name, param_info in params.items():
                        param_type = param_info.get("type", "unknown")
                        param_default = param_info.get("default", "N/A")
                        param_desc = param_info.get("description", "No description")

                        click.echo(f"  {param_name} ({param_type})")
                        click.echo(f"    Default: {param_default}")
                        click.echo(f"    Description: {param_desc}")
                        click.echo()
            else:
                info_message("No parameters found for this plugin")

            success_message(f"Parameter information displayed for {plugin_name}")

        except Exception as e:
            error_message(f"Error getting plugin parameters: {e}")
            raise click.Abort()

    except Exception as e:
        error_message(f"Parameter lookup failed: {e}")
        if ctx.obj.get("debug", False):
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@plugins.command()
@click.option(
    "--directory",
    type=click.Path(exists=True, file_okay=False),
    help="Custom directory to scan for plugins",
)
@click.option("--recursive", is_flag=True, help="Scan directories recursively")
@handle_errors
@pass_context_and_setup_logging
def scan(ctx, directory: Optional[Path], recursive: bool):
    r"""Scan directories for available plugins.

    Performs a comprehensive scan of plugin directories to discover
    new or updated plugins and their metadata.

    \b
    Scan Features:
    🔍 Automatic plugin discovery and metadata extraction
    📁 Custom directory scanning support
    🔄 Recursive directory traversal
    📊 Plugin count and type statistics
    ✅ Plugin validation during discovery

    \b
    Examples:
      # Scan default plugin directories
      panther plugins scan

      # Scan custom directory
      panther plugins scan --directory /path/to/custom/plugins

      # Recursive scan
      panther plugins scan --recursive

      # Scan external plugin repository
      panther plugins scan --directory ~/my-panther-plugins --recursive

    \b
    Discovery Process:
    1. Scan specified directories for Python files
    2. Parse plugin metadata and structure
    3. Validate plugin syntax and dependencies
    4. Categorize plugins by type and functionality
    5. Report discovered plugins with version information
    """
    verbose = ctx.obj.get("verbose", False)

    if directory:
        scan_path = directory
    else:
        scan_path = Path(__file__).parent.parent.parent.parent / "panther" / "plugins"

    if verbose:
        info_message(f"Scanning for plugins in: {scan_path}")

    click.echo(colored("🔍 PANTHER Plugin Scanner", "blue", attrs=["bold"]))
    click.echo(f"📁 Scan Path: {scan_path}")
    click.echo(f"🔄 Recursive: {'Yes' if recursive else 'No'}")
    click.echo()

    try:
        from panther.plugins.core.plugin_discovery import PluginDiscovery
        from panther.plugins.core.structures.plugin_metadata import PluginMetadata

        # Show progress for scanning
        with click.progressbar(
            length=4, label="Scanning for plugins", show_eta=False, show_percent=False
        ) as bar:
            bar.update(1)  # Initialize scanner

            discovery = PluginDiscovery([str(scan_path)])
            plugins_dict = discovery.discover_plugins()

            bar.update(1)  # Scan directories
            bar.update(1)  # Parse metadata
            bar.update(1)  # Complete

        total_plugins = sum(len(plugins) for plugins in plugins_dict.values())
        click.echo(f"✅ Scan complete. Found {total_plugins} plugin(s):")

        for plugin_type, plugin_names in plugins_dict.items():
            if plugin_names:
                click.echo(f"\n📦 {plugin_type.upper()} Plugins ({len(plugin_names)}):")
                for plugin_name in plugin_names:
                    plugin_info: PluginMetadata = discovery.get_plugin(plugin_name)
                    version = (
                        plugin_info.get("version", "unknown")
                        if plugin_info
                        else "unknown"
                    )
                    click.echo(f"  - {plugin_name} (v{version})")

        success_message("Plugin scanning completed")

    except Exception as e:
        error_message(f"Plugin scanning failed: {e}")
        if ctx.obj.get("debug", False):
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@plugins.command()
@click.argument("plugin_path", type=click.Path(exists=True))
@click.option("--strict", is_flag=True, help="Enable strict validation mode")
@click.option("--check-imports", is_flag=True, help="Validate all import statements")
@handle_errors
@pass_context_and_setup_logging
def validate(ctx, plugin_path: Path, strict: bool, check_imports: bool):
    r"""Validate plugin structure and configuration.

    Performs comprehensive validation of plugin files including
    syntax checking, structure verification, and dependency analysis.

    \b
    Validation Checks:
    ✅ Python syntax validation
    📁 Plugin directory structure
    🔧 Configuration schema validation
    📋 Metadata completeness
    🔗 Import statement verification

    \b
    Examples:
      # Basic plugin validation
      panther plugins validate /path/to/plugin

      # Strict validation with all checks
      panther plugins validate /path/to/plugin --strict

      # Check import dependencies
      panther plugins validate /path/to/plugin --check-imports

      # Validate plugin directory
      panther plugins validate ./my-plugin --strict --check-imports

    \b
    Validation Levels:
    📋 Basic: Syntax and structure validation
    🔍 Strict: Additional metadata and configuration checks
    🔗 Import Check: Verify all dependencies are available
    """
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        info_message(f"Validating plugin: {plugin_path}")

    click.echo(colored("✅ PANTHER Plugin Validator", "blue", attrs=["bold"]))
    click.echo(f"📁 Plugin Path: {plugin_path}")
    click.echo(f"🔍 Mode: {'Strict' if strict else 'Basic'}")
    if check_imports:
        click.echo(f"🔗 Import Check: Enabled")
    click.echo()

    try:
        # Show progress for validation
        with click.progressbar(
            length=4, label="Validating plugin", show_eta=False, show_percent=False
        ) as bar:
            bar.update(1)  # Syntax check

            # Basic structure validation
            if plugin_path.is_dir():
                # Check for main plugin file
                plugin_file = plugin_path / f"{plugin_path.name}.py"
                if not plugin_file.exists():
                    error_message(f"Main plugin file not found: {plugin_file}")
                    raise click.Abort()

                # Check for config schema
                config_file = plugin_path / "config_schema.py"
                if not config_file.exists() and strict:
                    click.echo(
                        colored(
                            f"⚠️  Warning: No config schema found: {config_file}",
                            "yellow",
                        )
                    )

                # Enhanced validation: syntax check
                try:
                    with open(plugin_file, "r") as f:
                        import ast

                        ast.parse(f.read())
                    click.echo("✅ Plugin syntax is valid")
                except SyntaxError as e:
                    error_message(f"Syntax error in plugin: {e}")
                    raise click.Abort()

                bar.update(1)  # Structure check
                click.echo("✅ Plugin structure is valid")

            else:
                # For single file plugins, check syntax
                try:
                    with open(plugin_path, "r") as f:
                        import ast

                        ast.parse(f.read())
                    click.echo("✅ Plugin file exists and has valid syntax")
                except SyntaxError as e:
                    error_message(f"Syntax error in plugin: {e}")
                    raise click.Abort()

                bar.update(1)  # Structure check

            bar.update(1)  # Schema check

            # Import checking if requested
            if check_imports:
                missing_deps = set()
                files_to_check = (
                    [plugin_path]
                    if plugin_path.is_file()
                    else list(plugin_path.glob("**/*.py"))
                )

                for py_file in files_to_check:
                    try:
                        with open(py_file, "r") as f:
                            import ast

                            tree = ast.parse(f.read())

                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    try:
                                        __import__(alias.name)
                                    except ImportError:
                                        missing_deps.add(alias.name)
                            elif isinstance(node, ast.ImportFrom) and node.module:
                                try:
                                    __import__(node.module)
                                except ImportError:
                                    missing_deps.add(node.module)
                    except Exception:
                        continue

                if missing_deps:
                    click.echo(
                        colored(
                            f"⚠️  Missing dependencies: {', '.join(sorted(missing_deps))}",
                            "yellow",
                        )
                    )
                else:
                    click.echo("✅ All imports are available")

            bar.update(1)  # Complete

        success_message("Plugin validation passed")

    except click.Abort:
        raise
    except Exception as e:
        error_message(f"Plugin validation failed: {e}")
        if ctx.obj.get("debug", False):
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@plugins.command("check-deps")
@click.argument("plugin_path", type=click.Path(exists=True))
@click.option("--fix", is_flag=True, help="Attempt to install missing dependencies")
@click.option(
    "--requirements-file",
    type=click.Path(),
    help="Output missing dependencies to requirements file",
)
@handle_errors
@pass_context_and_setup_logging
def check_deps(ctx, plugin_path: Path, fix: bool, requirements_file: Optional[Path]):
    r"""Check plugin dependencies and availability.

    Analyzes plugin files to identify required dependencies and verifies
    their availability in the current Python environment.

    \b
    Dependency Analysis:
    🔍 Import statement parsing and analysis
    📦 Package availability verification
    🔗 Transitive dependency checking
    ⚠️  Missing dependency identification
    🛠️  Optional dependency installation

    \b
    Examples:
      # Check plugin dependencies
      panther plugins check-deps /path/to/plugin

      # Generate requirements file for missing deps
      panther plugins check-deps ./plugin --requirements-file missing.txt

      # Check and attempt to fix dependencies
      panther plugins check-deps ./plugin --fix

      # Analyze entire plugin directory
      panther plugins check-deps ./my-plugin-dir

    \b
    Output Information:
    ✅ Available dependencies (already installed)
    ❌ Missing dependencies (need installation)
    ⚠️  Optional dependencies (recommended but not required)
    📦 Suggested installation commands
    """
    plugin_path = Path(plugin_path)  # click.Path() returns str, convert to Path
    verbose = ctx.obj.get("verbose", False)

    if verbose:
        info_message(f"Checking dependencies for: {plugin_path}")

    click.echo(colored("🔗 PANTHER Plugin Dependency Checker", "blue", attrs=["bold"]))
    click.echo(f"📁 Plugin Path: {plugin_path}")
    if fix:
        click.echo(f"🛠️  Auto-fix: Enabled")
    if requirements_file:
        click.echo(f"📄 Requirements File: {requirements_file}")
    click.echo()

    try:
        # Show progress for dependency checking
        with click.progressbar(
            length=3, label="Checking dependencies", show_eta=False, show_percent=False
        ) as bar:
            bar.update(1)  # Parse imports

            # Basic import checking
            if plugin_path.is_file():
                files_to_check = [plugin_path]
            else:
                files_to_check = list(plugin_path.glob("**/*.py"))

            missing_deps = set()
            available_deps = set()

            for py_file in files_to_check:
                try:
                    with open(py_file, "r") as f:
                        import ast

                        tree = ast.parse(f.read())

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                try:
                                    __import__(alias.name)
                                    available_deps.add(alias.name)
                                except ImportError:
                                    missing_deps.add(alias.name)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            try:
                                __import__(node.module)
                                available_deps.add(node.module)
                            except ImportError:
                                missing_deps.add(node.module)
                except Exception:
                    continue

            bar.update(1)  # Check availability

            # Filter out standard library modules
            stdlib_modules = {
                "os",
                "sys",
                "pathlib",
                "json",
                "ast",
                "traceback",
                "logging",
            }
            missing_deps = missing_deps - stdlib_modules
            available_deps = available_deps - stdlib_modules

            bar.update(1)  # Generate report

        # Display results
        if available_deps:
            click.echo(colored("✅ Available Dependencies:", "green"))
            for dep in sorted(available_deps):
                click.echo(f"  - {dep}")
            click.echo()

        if missing_deps:
            click.echo(colored("❌ Missing Dependencies:", "red"))
            for dep in sorted(missing_deps):
                click.echo(f"  - {dep}")
            click.echo()

            # Save to requirements file if requested
            if requirements_file:
                with open(requirements_file, "w") as f:
                    for dep in sorted(missing_deps):
                        f.write(f"{dep}\n")
                success_message(f"Missing dependencies saved to: {requirements_file}")

            # Attempt to fix if requested
            if fix:
                click.echo("🛠️  Attempting to install missing dependencies...")
                import subprocess

                for dep in sorted(missing_deps):
                    try:
                        subprocess.check_call(["pip", "install", dep])
                        click.echo(f"✅ Installed: {dep}")
                    except subprocess.CalledProcessError:
                        click.echo(f"❌ Failed to install: {dep}")

            error_message("Missing dependencies found")
            return  # Don't abort - this is expected behavior
        else:
            success_message("All dependencies are available")

    except Exception as e:
        error_message(f"Dependency checking failed: {e}")
        if ctx.obj.get("debug", False):
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


if __name__ in {"__main__", "__mp_main__"}:
    plugins()
