#!/usr/bin/env python3
"""
PANTHER CLI - Main entry point

This module provides the command-line interface for the PANTHER framework.
"""

import argparse
import logging
import sys
from pathlib import Path

# Import the plugin creation utility functions
try:
    from panther.plugins.plugin_creator import (
        is_development_mode,
        create_plugin,
        run_tutorial,
        launch_interactive_tutorials,
    )
except ImportError:
    # Fallback if the import fails (can happen during development)
    import importlib.util
    import sys

    # Try to load the module directly
    plugin_creator_path = Path(__file__).parent / "plugins" / "plugin_creator.py"
    if plugin_creator_path.exists():
        spec = importlib.util.spec_from_file_location(
            "plugin_creator", plugin_creator_path
        )
        if spec is not None and spec.loader is not None:
            plugin_creator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_creator)
            is_development_mode = plugin_creator.is_development_mode
            create_plugin = plugin_creator.create_plugin
            run_tutorial = plugin_creator.run_tutorial
            launch_interactive_tutorials = plugin_creator.launch_interactive_tutorials
        else:
            raise ImportError("Could not import plugin_creator module")
    else:
        raise ImportError("Could not find plugin_creator.py module")

from panther.core.experiment_manager import ExperimentManager
from panther.config.config_manager import ConfigLoader
from panther.config.plugin_params import list_plugin_parameters


def main():
    """Main entry point for the PANTHER CLI."""
    parser = argparse.ArgumentParser(description="Panther CLI")
    # TODO manage dir of the experiments configs
    parser.add_argument(
        "--experiment-config",
        type=str,
        default="experiment-config/experiment_config.yaml",
        help="Path to the configuration directory.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Flag to validate the configuration.",
    )
    parser.add_argument(
        "--list-plugin-params",
        type=str,
        metavar="PLUGIN_NAME",
        help="List available parameters for the specified plugin.",
    )
    parser.add_argument(
        "--plugin-type",
        type=str,
        choices=["iut", "tester", "network_environment", "execution_environment"],
        help="Type of plugin to show parameters for. Optional - will be auto-detected if not provided.",
    )
    parser.add_argument(
        "--protocol",
        type=str,
        help="Protocol for IUT/tester plugins (e.g., quic, http, minip). Optional - will be auto-detected if not provided.",
    )

    # Plugin creation and tutorial subcommands
    create_group = parser.add_argument_group("Plugin Creation and Tutorials")
    create_group.add_argument(
        "--create-plugin",
        nargs=2,
        metavar=("TYPE", "NAME"),
        help="Create a new plugin. TYPE can be service, environment, or protocol. NAME is the plugin name.",
    )
    create_group.add_argument(
        "--create-subplugin",
        nargs=3,
        metavar=("PLUGIN_TYPE", "PLUGIN_NAME", "SUBPLUGIN_TYPE"),
        help="Create a new subplugin within an existing plugin. PLUGIN_TYPE can be service, environment, or protocol. "
        "PLUGIN_NAME is the name of the existing plugin. SUBPLUGIN_TYPE is the type of subplugin to create "
        "(e.g., iut, tester, network_environment, execution_environment).",
    )
    create_group.add_argument(
        "--with-subplugins",
        action="store_true",
        help="Create default subplugins when creating a new plugin.",
    )
    create_group.add_argument(
        "--tutorial",
        type=str,
        choices=["service", "environment", "protocol"],
        help="Run an interactive tutorial for the specified plugin type.",
    )
    create_group.add_argument(
        "--interactive-tutorials",
        action="store_true",
        help="Launch the interactive tutorial menu.",
    )
    create_group.add_argument(
        "--dev-mode",
        action="store_true",
        help="Force development mode for plugin creation (put plugins in source tree).",
    )
    create_group.add_argument(
        "--production-mode",
        action="store_true",
        help="Force production mode for plugin creation (put plugins in user directory).",
    )

    parser.add_argument(
        "--exec-env-dir",
        type=str,
        help="Path to the execution plugin additional directory.",
    )
    parser.add_argument(
        "--net-env-dir",
        type=str,
        help="Path to the network plugin additional directory.",
    )
    parser.add_argument(
        "--iut-dir",
        type=str,
        help="Path to a new IUT plugin additional directory.",
    )
    parser.add_argument(
        "--tester-dir",
        type=str,
        help="Path to a new tester plugin additional directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Path to the output directory.",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Name of the experiment.",
    )
    parser.add_argument(
        "--teardown",
        action="store_true",
        help="Flag to teardown an existing experiment.",
    )
    parser.add_argument(
        "--webapp",
        action="store_true",
        help="Start the web app to configurate the experiments.",
    )
    args = parser.parse_args()

    # Handle plugin creation
    if args.create_plugin:
        plugin_type, plugin_name = args.create_plugin

        # Determine mode based on arguments or auto-detect
        dev_mode = None  # Auto-detect by default
        if args.dev_mode:
            dev_mode = True
        elif args.production_mode:
            dev_mode = False

        try:
            # Pass the with_subplugins flag
            success = create_plugin(
                plugin_type,
                plugin_name,
                in_development_mode=dev_mode,
                create_subplugins=args.with_subplugins,
            )
            return 0 if success else 1
        except Exception as e:
            print(f"❌ Error creating plugin: {e}")
            return 1

    # Handle subplugin creation
    if args.create_subplugin:
        plugin_type, plugin_name, subplugin_type = args.create_subplugin

        # Determine mode based on arguments or auto-detect
        dev_mode = None  # Auto-detect by default
        if args.dev_mode:
            dev_mode = True
        elif args.production_mode:
            dev_mode = False

        try:
            # Import the subplugin creation function
            from panther.plugins.plugin_creator import create_subplugin

            success = create_subplugin(
                plugin_type, plugin_name, subplugin_type, in_development_mode=dev_mode
            )
            return 0 if success else 1
        except Exception as e:
            print(f"❌ Error creating subplugin: {e}")
            return 1

    # Handle tutorial execution
    if args.tutorial:
        try:
            return run_tutorial(args.tutorial)
        except Exception as e:
            print(f"❌ Error running tutorial: {e}")
            return 1

    # Handle interactive tutorial menu
    if args.interactive_tutorials:
        try:
            # Import the interactive tutorials function
            from panther.plugins.plugin_creator import launch_interactive_tutorials

            launch_interactive_tutorials()
            return 0
        except Exception as e:
            print(f"❌ Error launching interactive tutorials: {e}")
            return 1

    if args.list_plugin_params:
        config_loader = ConfigLoader(
            args.experiment_config,
            args.output_dir,
            args.exec_env_dir,
            args.net_env_dir,
            args.iut_dir,
            args.tester_dir,
        )

        # Use the dedicated function for listing plugin parameters
        params = list_plugin_parameters(
            plugin_name=args.list_plugin_params,
            plugin_type=args.plugin_type,
            protocol=args.protocol,  # Pass the protocol parameter
        )

        if not params:
            return 1

        # Print parameters in a readable format
        print(
            f"\n{'Parameter':<20} {'Type':<30} {'Default':<20} {'Required':<10} Description"
        )
        print("-" * 100)
        for name, info in params.items():
            default = str(info["default"]) if info["default"] is not None else "None"
            required = "Yes" if info["required"] else "No"
            desc = info["description"]

            # Handle special version field with additional information
            if name == "version" and "value" in info:
                version_info = info["value"]
                if hasattr(version_info, "version") and version_info.version:
                    desc += f" (Version: {version_info.version})"
                if hasattr(version_info, "commit") and version_info.commit:
                    desc += f" (Commit: {version_info.commit})"
                if info.get("note"):
                    desc += f" - {info['note']}"

            print(f"{name:<20} {info['type']:<30} {default:<20} {required:<10} {desc}")

            # If this is a version field with client/server details, show them
            if name == "version" and "value" in info:
                version_info = info["value"]
                if hasattr(version_info, "client") and version_info.client:
                    print("  ├─ client: Configuration for client role")
                if hasattr(version_info, "server") and version_info.server:
                    print("  └─ server: Configuration for server role")

        return 0
    elif args.teardown:
        experiment_dir = getattr(args, "experiment_dir", None)
        if not experiment_dir:
            print(
                "Please provide the experiment directory to teardown using '--experiment-dir'."
            )
            return 1
        raise NotImplementedError("Teardown functionality is not implemented yet.")
    elif args.validate_config:
        print("Validating the configuration.")
        config_loader = ConfigLoader(
            args.experiment_config,
            args.output_dir,
            args.exec_env_dir,
            args.net_env_dir,
            args.iut_dir,
            args.tester_dir,
        )
        # We get the global configurations
        global_config = config_loader.load_and_validate_global_config()
        # We create the experiment manager
        experiment_manager = ExperimentManager(
            global_config=global_config, experiment_name=args.experiment_name
        )
        config_loader.load_and_validate_experiment_config()
        return 0
    else:
        # We start by loading the configuration
        config_loader = ConfigLoader(
            args.experiment_config,
            args.output_dir,
            args.exec_env_dir,
            args.net_env_dir,
            args.iut_dir,
            args.tester_dir,
        )
        # We get the global configurations
        global_config = config_loader.load_and_validate_global_config()
        if args.webapp:
            raise NotImplementedError(
                "WebApplication functionality is not fully implemented yet."
            )
            try:
                from panther.webapp.web_app import run

                run(config_loader, global_config, args)
                return 0
            except Exception as e:
                logging.error(e)
                return 1
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
        else:
            try:
                # We create the experiment manager
                experiment_manager = ExperimentManager(
                    global_config=global_config, experiment_name=args.experiment_name
                )
                experiment_config = config_loader.load_and_validate_experiment_config()
                # Once we have the experiments configurations, we can initialize the experiment
                experiment_manager.initialize_experiments(experiment_config)
                # Start the experiment
                experiment_manager.run_tests()
                return 0
            except Exception as e:
                logging.error(e)
                return 1
            finally:
                config_loader.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
