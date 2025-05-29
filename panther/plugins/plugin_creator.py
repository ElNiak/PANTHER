#!/usr/bin/env python3
"""
PANTHER Plugin Creation Utilities

This module provides functionality to create new plugins in both development
and production environments. It supports both top-level plugins and subplugins
using Jinja2 templates for dynamic code generation.
"""

import sys
import shutil
import subprocess
import importlib
import importlib.resources
import importlib.util
from pathlib import Path
import site
from typing import Any

# Try to import Jinja2 for template rendering
try:
    import jinja2

    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False

# Plugin hierarchy definition
PLUGIN_HIERARCHY = {
    "services": ["iut", "tester"],
    "environments": ["network_environment", "execution_environment"],
    "protocols": ["client", "server", "peer_to_peer"],
}


def is_development_mode() -> bool:
    """
    Determine if PANTHER is running in development mode (GitHub cloned)
    or production mode (installed package).

    Returns:
        bool: True if in development mode, False if in production mode
    """
    # Check if this file is in a writeable directory (dev mode)
    # or in a system site-packages directory (production mode)
    panther_dir = Path(__file__).parent.resolve()

    # Check if we're in a Python package directory (site-packages)
    site_packages = []
    for path in site.getsitepackages():
        site_packages.append(Path(path))

    # Check if we're in a virtual environment
    if hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        site_packages.append(
            Path(sys.prefix)
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )

    # Check if panther_dir is in any site-packages directory
    for site_pkg in site_packages:
        if str(panther_dir).startswith(str(site_pkg)):
            return False  # We're in production mode (installed package)

    # If we made it here, we're in development mode
    return True


def get_plugin_directory(
    plugin_type: str, in_development_mode: bool | None = None
) -> Path:
    """
    Get the appropriate directory for plugin creation based on mode.

    Args:
        plugin_type: The type of plugin (service, environment, protocol)
        in_development_mode: Force development mode if True, production mode if False
                           If None, auto-detect mode

    Returns:
        Path: The directory where plugins should be created
    """
    if in_development_mode is None:
        in_development_mode = is_development_mode()

    plugin_type = plugin_type.lower()

    # Map plugin type to directory name
    if plugin_type == "service":
        dir_name = "services"
    elif plugin_type == "environment":
        dir_name = "environments"
    elif plugin_type == "protocol":
        dir_name = "protocols"
    else:
        raise ValueError(f"Invalid plugin type: {plugin_type}")

    if in_development_mode:
        # In development mode, use the repository structure
        # Since __file__ is already in the plugins directory, we don't need to add "plugins" again
        return Path(__file__).parent / dir_name
    else:
        # In production mode, use a directory in the user's home
        home_dir = Path.home()
        plugins_dir = home_dir / ".panther" / "plugins" / dir_name
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return plugins_dir


def get_template_directory(plugin_type: str) -> Path:
    """
    Get the template directory for the specified plugin type.

    Args:
        plugin_type: The type of plugin (service, environment, protocol)

    Returns:
        Path: The directory containing the plugin templates
    """
    plugin_type = plugin_type.lower()

    # Map plugin type to directory name
    if plugin_type == "service":
        plugin_dir = "services"
    elif plugin_type == "environment":
        plugin_dir = "environments"
    elif plugin_type == "protocol":
        plugin_dir = "protocols"
    else:
        raise ValueError(f"Invalid plugin type: {plugin_type}")

    in_development_mode = is_development_mode()

    if in_development_mode:
        # In development mode, use the repository structure
        template_dir = Path(__file__).parent / plugin_dir / "tutorials" / "template"
    else:
        # In production mode, we need to get the template from the package resources
        try:
            # Using importlib.resources to get the template directory
            # This works in Python 3.9+ with installed packages
            import importlib.resources

            template_dir_obj = importlib.resources.files(
                f"panther.plugins.{plugin_dir}.tutorials"
            ).joinpath("template")
            template_dir = Path(str(template_dir_obj))
        except (ImportError, AttributeError):
            # Fallback for older Python versions
            import importlib.util as util

            spec = util.find_spec(f"panther.plugins.{plugin_dir}.tutorials")
            if spec is None:
                raise ImportError(
                    f"Could not find template directory for {plugin_type} plugin"
                )

            if spec.origin is None:
                raise ImportError(
                    f"Could not find origin for module path: panther.plugins.{plugin_dir}.tutorials"
                )

            module_dir = Path(spec.origin).parent
            template_dir = module_dir / "template"

    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    return template_dir


def render_jinja_template(
    template_path: Path, output_path: Path, context: dict[str, Any]
) -> bool:
    """
    Render a Jinja2 template to the output path.

    Args:
        template_path: Path to the template file (.j2 extension)
        output_path: Path where the rendered file should be saved
        context: Dictionary of context variables for the template

    Returns:
        bool: True if successful, False otherwise
    """
    if not JINJA_AVAILABLE:
        print("⚠️  Jinja2 not available. Using static templates only.")
        return False

    try:
        # Create Jinja environment with the template directory as the loader
        template_dir = template_path.parent
        template_name = template_path.name
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(template_dir)))  # type: ignore

        # Load and render the template
        template = env.get_template(template_name)
        rendered = template.render(**context)

        # Write the rendered content to the output file
        with open(output_path, "w") as f:
            f.write(rendered)

        return True
    except Exception as e:
        print(f"❌ Error rendering template: {e}")
        return False


def create_subplugin(
    plugin_type: str,
    plugin_name: str,
    subplugin_type: str,
    in_development_mode: bool | None = None,
) -> bool:
    """
    Create a new subplugin within an existing plugin.

    Args:
        plugin_type: The type of plugin (service, environment, protocol)
        plugin_name: The name of the existing plugin
        subplugin_type: The type of subplugin to create
        in_development_mode: Force development mode if True, production mode if False
                           If None, auto-detect mode

    Returns:
        bool: True if subplugin creation was successful, False otherwise
    """
    plugin_type = plugin_type.lower()

    # Map plugin type to directory name
    if plugin_type == "service":
        dir_name = "services"
    elif plugin_type == "environment":
        dir_name = "environments"
    elif plugin_type == "protocol":
        dir_name = "protocols"
    else:
        print(f"❌ Invalid plugin type: {plugin_type}")
        print("Valid types: service, environment, protocol")
        return False

    # Verify that the subplugin type is valid for this plugin type
    if subplugin_type not in PLUGIN_HIERARCHY.get(dir_name, []):
        valid_types = ", ".join(PLUGIN_HIERARCHY.get(dir_name, []))
        print(f"❌ Invalid subplugin type: {subplugin_type} for {plugin_type} plugin")
        print(f"Valid types: {valid_types}")
        return False

    # Determine if we're in development mode
    if in_development_mode is None:
        in_development_mode = is_development_mode()

    # Get the plugin directory
    plugin_dir = get_plugin_directory(plugin_type, in_development_mode)
    plugin_path = plugin_dir / plugin_name

    # Check if the plugin exists
    if not plugin_path.exists():
        print(f"❌ Plugin {plugin_name} does not exist at {plugin_path}")
        return False

    # Create the subplugin directory
    subplugin_dir = plugin_path / subplugin_type
    if subplugin_dir.exists():
        print(f"❌ Subplugin already exists at {subplugin_dir}")
        return False

    subplugin_dir.mkdir(parents=True, exist_ok=True)

    # Get the template directory
    try:
        template_dir = get_template_directory(plugin_type)
        subplugin_template_dir = template_dir / subplugin_type

        # Check if subplugin template exists
        if not subplugin_template_dir.exists():
            print(
                f"⚠️  No specific template found for {subplugin_type}. Using generic template."
            )
            # Use generic template instead
            subplugin_template_dir = template_dir
    except (FileNotFoundError, ImportError) as e:
        print(f"❌ Error: {e}")
        return False

    # Context for template rendering
    context = {
        "plugin_name": plugin_name,
        "plugin_type": plugin_type,
        "subplugin_type": subplugin_type,
        "class_name": f"{plugin_name.title()}{subplugin_type.title()}",
    }

    # Copy template files
    try:
        # Copy regular files and render Jinja templates
        for item in subplugin_template_dir.glob("*"):
            # Skip directories that don't match our subplugin type
            if item.is_dir() and item.name not in [
                subplugin_type,
                subplugin_type.replace("_", ""),
            ]:
                continue

            if item.is_file():
                # Check if it's a Jinja template
                if JINJA_AVAILABLE and item.suffix == ".j2":
                    output_path = subplugin_dir / item.stem
                    render_jinja_template(item, output_path, context)
                else:
                    shutil.copy2(item, subplugin_dir / item.name)

        # Create __init__.py if it doesn't exist
        init_file = subplugin_dir / "__init__.py"
        if not init_file.exists():
            with open(init_file, "w") as f:
                f.write(
                    f'"""\n{subplugin_type.title()} implementation for the {plugin_name} plugin.\n"""\n'
                )

        print(f"✅ Created new {subplugin_type} subplugin in {plugin_name}")
        print(f"Subplugin location: {subplugin_dir}")
        return True

    except Exception as e:
        print(f"❌ Error creating subplugin: {e}")
        shutil.rmtree(subplugin_dir, ignore_errors=True)
        return False


def create_plugin(
    plugin_type: str,
    plugin_name: str,
    in_development_mode: bool | None = None,
    create_subplugins: bool = False,
) -> bool:
    """
    Create a new plugin with the specified name and type.

    Args:
        plugin_type: The type of plugin (service, environment, protocol)
        plugin_name: The name of the new plugin
        in_development_mode: Force development mode if True, production mode if False
                           If None, auto-detect mode
        create_subplugins: Whether to also create the default subplugins

    Returns:
        bool: True if plugin creation was successful, False otherwise
    """
    plugin_type = plugin_type.lower()
    if plugin_type not in ["service", "environment", "protocol"]:
        print(f"❌ Invalid plugin type: {plugin_type}")
        print("Valid types: service, environment, protocol")
        return False

    # Determine if we're in development mode
    if in_development_mode is None:
        in_development_mode = is_development_mode()

    # Get the destination directory
    plugin_dir = get_plugin_directory(plugin_type, in_development_mode)

    # Get the template directory
    try:
        template_dir = get_template_directory(plugin_type)
    except (FileNotFoundError, ImportError) as e:
        print(f"❌ Error: {e}")
        return False

    # Create the plugin directory
    destination_dir = plugin_dir / plugin_name
    if destination_dir.exists():
        print(f"❌ Plugin already exists at {destination_dir}")
        return False

    destination_dir.mkdir(parents=True, exist_ok=True)

    # Map plugin type to directory name for PLUGIN_HIERARCHY lookup
    dir_name = ""
    if plugin_type == "service":
        dir_name = "services"
    elif plugin_type == "environment":
        dir_name = "environments"
    elif plugin_type == "protocol":
        dir_name = "protocols"

    # Context for template rendering
    context = {
        "plugin_name": plugin_name,
        "plugin_type": plugin_type,
        "class_name": f"{plugin_name.title()}{plugin_type.title()}",
    }

    # Copy template files
    try:
        # Copy/render only top-level plugin files (excluding subplugin directories)
        for item in template_dir.glob("*"):
            # Skip subplugin directories
            if item.is_dir() and item.name in PLUGIN_HIERARCHY.get(dir_name, []):
                continue

            if item.is_file():
                # Check if it's a Jinja template
                if JINJA_AVAILABLE and item.suffix == ".j2":
                    output_path = destination_dir / item.stem
                    render_jinja_template(item, output_path, context)
                else:
                    shutil.copy2(item, destination_dir / item.name)
            else:
                # Copy non-subplugin directories
                shutil.copytree(item, destination_dir / item.name)

        print(f"✅ Created new {plugin_type} plugin: {plugin_name}")
        print(f"Plugin location: {destination_dir}")

        # If requested, create default subplugins
        if create_subplugins:
            for subplugin_type in PLUGIN_HIERARCHY.get(dir_name, []):
                print(f"Creating {subplugin_type} subplugin...")
                create_subplugin(
                    plugin_type, plugin_name, subplugin_type, in_development_mode
                )

        return True
    except Exception as e:
        print(f"❌ Error creating plugin: {e}")
        return False


def run_tutorial(plugin_type: str) -> int:
    """
    Run the interactive tutorial for the specified plugin type.

    Args:
        plugin_type: The type of plugin (service, environment, protocol)

    Returns:
        int: Return code (0 for success, non-zero for failure)
    """
    plugin_type = plugin_type.lower()
    if plugin_type not in ["service", "environment", "protocol"]:
        print(f"❌ Invalid plugin type: {plugin_type}")
        print("Valid types: service, environment, protocol")
        return 1

    # Map plugin type to directory name
    if plugin_type == "service":
        plugin_dir = "services"
    elif plugin_type == "environment":
        plugin_dir = "environments"
    elif plugin_type == "protocol":
        plugin_dir = "protocols"
    else:
        # This should never happen due to the check above, but adding for safety
        print(f"❌ Invalid plugin type: {plugin_type}")
        return 1

    in_development_mode = is_development_mode()

    if in_development_mode:
        # In development mode, use the repository structure
        tutorial_script = (
            Path(__file__).parent / plugin_dir / "tutorials" / "tutorial.py"
        )
        if not tutorial_script.exists():
            print(f"❌ Tutorial script not found: {tutorial_script}")
            return 1

        print(f"\nStarting {plugin_type.title()} Plugin Tutorial...")
        result = subprocess.call([sys.executable, str(tutorial_script)])
        return result
    else:
        # In production mode, use the package module structure
        try:
            print(f"\nStarting {plugin_type.title()} Plugin Tutorial...")
            module_path = f"panther.plugins.{plugin_dir}.tutorials.tutorial"
            module = importlib.import_module(module_path)

            # If the module has a main function, call it
            if hasattr(module, "main"):
                module.main()
            else:
                # Otherwise, create an instance of the tutorial class and run it
                class_name = f"{plugin_type.title()}PluginTutorial"
                if hasattr(module, class_name):
                    tutorial_class = getattr(module, class_name)
                    tutorial = tutorial_class()
                    if hasattr(tutorial, "run"):
                        tutorial.run()
                    elif hasattr(tutorial, "run_tutorial"):
                        tutorial.run_tutorial()
                    else:
                        print(f"❌ Could not find run method in {class_name}")
                        return 1
                else:
                    print(f"❌ Could not find {class_name} in {module_path}")
                    return 1
            return 0
        except ImportError as e:
            print(f"❌ Error importing tutorial module: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error running tutorial: {e}")
            return 1


def launch_interactive_tutorials():
    """
    Launches the interactive menu for plugin tutorials.
    This allows users to select which type of plugin tutorial to run.
    """
    print("🌟 PANTHER Interactive Plugin Tutorials")
    print("=" * 50)
    print()
    print("Welcome to the PANTHER plugin development tutorials!")
    print("These interactive tutorials will guide you through creating")
    print("complete plugin implementations for the PANTHER framework.")
    print()

    while True:
        print("Available tutorials:")
        print("1. 🔧 Service Plugin Tutorial")
        print("   Create IUT (Implementation Under Test) and Tester plugins")
        print()
        print("2. 🌐 Environment Plugin Tutorial")
        print("   Create Network and Execution environment plugins")
        print()
        print("3. 📡 Protocol Plugin Tutorial")
        print("   Create Client-Server and Peer-to-Peer protocol plugins")
        print()
        print("4. 📚 View all tutorial documentation")
        print("5. 🚪 Exit")
        print()

        choice = input("Select a tutorial (1-5): ").strip()

        if choice == "1":
            print("\n🔧 Starting Service Plugin Tutorial...")
            run_tutorial("service")

        elif choice == "2":
            print("\n🌐 Starting Environment Plugin Tutorial...")
            run_tutorial("environment")

        elif choice == "3":
            print("\n📡 Starting Protocol Plugin Tutorial...")
            run_tutorial("protocol")

        elif choice == "4":
            print("\n📚 Tutorial Documentation:")

            # Show paths based on development mode or production mode
            if is_development_mode():
                base_path = "panther/plugins"
            else:
                base_path = "~/.panther/plugins"

            print(f"• Service Plugin Tutorial: {base_path}/services/tutorials/")
            print(f"• Environment Plugin Tutorial: {base_path}/environments/tutorials/")
            print(f"• Protocol Plugin Tutorial: {base_path}/protocols/tutorials/")
            print()
            input("Press Enter to continue...")

        elif choice == "5":
            print("\n👋 Happy plugin development with PANTHER!")
            break

        else:
            print("❌ Invalid choice. Please select 1-5.")

        print("\n" + "-" * 50 + "\n")


if __name__ == "__main__":
    # Allow direct execution of this script for tutorial access
    import argparse

    parser = argparse.ArgumentParser(description="PANTHER Plugin Development Tools")
    parser.add_argument(
        "--create",
        nargs=2,
        metavar=("TYPE", "NAME"),
        help="Create a new plugin. TYPE can be service, environment, or protocol. NAME is the plugin name.",
    )
    parser.add_argument(
        "--tutorial",
        choices=["service", "environment", "protocol"],
        help="Run a specific plugin tutorial directly.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch the interactive tutorial menu.",
    )
    args = parser.parse_args()

    if args.create:
        plugin_type, plugin_name = args.create
        create_plugin(plugin_type, plugin_name)
    elif args.tutorial:
        run_tutorial(args.tutorial)
    else:
        # Default to interactive mode
        launch_interactive_tutorials()
