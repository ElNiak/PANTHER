"""
Plugins Command - Plugin discovery and management
"""

import json
import logging
from argparse import ArgumentParser, _SubParsersAction
from pathlib import Path
from typing import Any

from panther.cli.base import BaseCommand
from panther.plugins.core.structures.plugin_metadata import PluginMetadata
from panther.plugins.core.structures.plugin_type import PluginType


class PluginsCommand(BaseCommand):
    """Handle plugin discovery and management commands."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the plugins subcommand parser."""
        parser = subparsers.add_parser(
            "plugins",
            help="Plugin discovery and management",
            description="Discover, list, and manage PANTHER plugins",
        )

        subcommands = parser.add_subparsers(
            dest="plugins_action", help="Plugin actions", metavar="ACTION"
        )

        # List subcommand
        list_parser = subcommands.add_parser(
            "list",
            help="List available plugins",
            description="List all available plugins by type",
        )
        # Get valid plugin type choices from enum
        plugin_type_choices = [pt.value for pt in PluginType] + ["all"]

        list_parser.add_argument(
            "--type",
            choices=plugin_type_choices,
            default="all",
            help="Filter plugins by type (default: all)",
        )
        list_parser.add_argument(
            "--format",
            choices=["table", "json", "simple"],
            default="table",
            help="Output format (default: table)",
        )

        # Params subcommand
        params_parser = subcommands.add_parser(
            "params",
            help="Show plugin parameters",
            description="Display configuration parameters for a specific plugin",
        )
        params_parser.add_argument("plugin_name", help="Name of the plugin to inspect")
        params_parser.add_argument(
            "--type",
            choices=[pt.value for pt in PluginType],
            help="Plugin type (auto-detected if not specified)",
        )
        params_parser.add_argument(
            "--protocol", help="Protocol name for filtering parameters"
        )

        # Scan subcommand
        scan_parser = subcommands.add_parser(
            "scan",
            help="Scan for plugins",
            description="Scan directories for available plugins",
        )
        scan_parser.add_argument(
            "--directory", type=str, help="Custom directory to scan for plugins"
        )

        # Validate subcommand
        validate_parser = subcommands.add_parser(
            "validate",
            help="Validate plugin",
            description="Validate a plugin's structure and configuration",
        )
        validate_parser.add_argument(
            "plugin_path", help="Path to plugin directory or file"
        )

        # Check-deps subcommand
        deps_parser = subcommands.add_parser(
            "check-deps",
            help="Check plugin dependencies",
            description="Check if plugin dependencies are available",
        )
        deps_parser.add_argument("plugin_path", help="Path to plugin directory or file")

        # Migrate subcommand
        migrate_parser = subcommands.add_parser(
            "migrate",
            help="Migrate plugins",
            description="Migrate plugins to newer formats",
        )
        migrate_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without making changes",
        )
        migrate_parser.add_argument(
            "--force",
            action="store_true",
            help="Force migration even if validation fails",
        )

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        """Handle the plugins command execution."""
        if not hasattr(args, "plugins_action") or args.plugins_action is None:
            cls.get_instance().logger.info(
                "❌ No plugin action specified. Use 'panther plugins --help' for options."
            )
            return 1

        action_handlers = {
            "list": cls._handle_list,
            "params": cls._handle_params,
            "scan": cls._handle_scan,
            "validate": cls._handle_validate,
            "check-deps": cls._handle_check_deps,
            "migrate": cls._handle_migrate,
        }

        handler = action_handlers.get(args.plugins_action)
        if handler:
            return handler(args)
        else:
            cls.get_instance().logger.info(f"❌ Unknown plugin action: {args.plugins_action}")
            return 1

    @classmethod
    def _handle_list(cls, args: Any) -> int:
        """Handle plugin listing."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        try:
            # Initialize plugin discovery
            from pathlib import Path

            from panther.plugins.plugin_manager import PluginManager

            discovery = PluginManager()
            base_plugin_dir = Path(__file__).parent.parent.parent / "plugins"

            cls.get_instance().logger.info(f"🔍 Scanning for plugins in: {base_plugin_dir}")

            # Discover plugins first
            discovery.discover_plugins()

            # Debug: print args
            cls.get_instance().logger.debug(f"Args type: {args.type}, format: {args.format}")

            # Get plugins based on filter
            if args.type == "all":
                plugins = []
                for plugin_type in PluginType:
                    plugins.extend(discovery.get_plugins_by_type(plugin_type.value))
            else:
                plugins = discovery.get_plugins_by_type(args.type)

            if not plugins:
                if args.type == "all":
                    cls.get_instance().logger.info("ℹ️  No plugins found")
                else:
                    cls.get_instance().logger.info(f"ℹ️  No plugins found for type: {args.type}")
                return 0

            # Display plugins
            if args.format == "json":
                plugin_data = []
                for plugin in plugins:
                    plugin_data.append(
                        {
                            "name": plugin.name,
                            "type": plugin.type,
                            "version": plugin.version,
                            "description": plugin.description,
                            "path": str(plugin.path),
                        }
                    )
                cls.get_instance().logger.info(json.dumps(plugin_data, indent=2))

            elif args.format == "simple":
                for plugin in plugins:
                    cls.get_instance().logger.info(f"{plugin.name} ({plugin.type})")

            else:  # table format
                cls.get_instance().logger.info(f"\n📦 Found {len(plugins)} plugin(s):")
                cls.get_instance().logger.info("-" * 80)
                cls.get_instance().logger.info(
                    f"{'Name':<20} {'Type':<20} {'Version':<10} {'Description':<25}"
                )
                cls.get_instance().logger.info("-" * 80)

                for plugin in plugins:
                    description = (
                        plugin.description[:22] + "..."
                        if len(plugin.description) > 25
                        else plugin.description
                    )
                    cls.get_instance().logger.info(
                        f"{plugin.name:<20} {plugin.type:<20} {plugin.version:<10} {description:<25}"
                    )

                cls.get_instance().logger.info("-" * 80)

            return 0

        except Exception as e:
            cls.get_instance().logger.info(f"❌ Error listing plugins: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return 1

    @classmethod
    def _handle_params(cls, args: Any) -> int:
        """Handle plugin parameter display."""
        try:
            from panther.plugins.plugin_manager import PluginManager

            # Initialize plugin manager to access plugin parameters
            plugin_manager = PluginManager()

            plugin_name = args.plugin_name
            plugin_type = args.type
            protocol = args.protocol

            cls.get_instance().logger.info(f"📋 Parameters for plugin: {plugin_name} ({plugin_type})")

            # Get plugin parameters
            try:
                params = plugin_manager.get_plugin(
                    name=plugin_name)
                if not params:
                    cls.get_instance().logger.info(f"❌ Plugin not found: {plugin_name}")
                    return 1
                params = params.to_dict()

                if params:
                    cls.get_instance().logger.info("\n🔧 Available Parameters:")
                    cls.get_instance().logger.info("-" * 50)
                    for param_name, param_info in params.items():
                        param_type = param_info.get("type", "unknown")
                        param_default = param_info.get("default", "N/A")
                        param_desc = param_info.get("description", "No description")

                        cls.get_instance().logger.info(f"  {param_name} ({param_type})")
                        cls.get_instance().logger.info(f"    Default: {param_default}")
                        cls.get_instance().logger.info(f"    Description: {param_desc}")
                else:
                    cls.get_instance().logger.info("ℹ️  No parameters found for this plugin")

            except Exception as e:
                cls.get_instance().logger.error(f"❌ Error getting plugin parameters: {e}")
                return 1

            return 0

        except Exception as e:
            cls.get_instance().logger.error(f"❌ Error displaying plugin parameters: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return 1

    @classmethod
    def _handle_scan(cls, args: Any) -> int:
        """Handle plugin scanning."""
        try:
            from pathlib import Path

            from panther.plugins.core.plugin_discovery import PluginDiscovery

            if args.directory:
                scan_dir = args.directory
            else:
                scan_dir = str(Path(__file__).parent.parent.parent / "plugins")
            cls.get_instance().logger.info(f"🔍 Scanning directory: {scan_dir}")

            discovery = PluginDiscovery([scan_dir])
            plugins_dict = discovery.discover_plugins()

            total_plugins = sum(len(plugins) for plugins in plugins_dict.values())
            cls.get_instance().logger.info(f"✅ Scan complete. Found {total_plugins} plugin(s):")

            for plugin_type, plugin_names in plugins_dict.items():
                if plugin_names:
                    cls.get_instance().logger.info(
                        f"\n📦 {plugin_type.upper()} Plugins ({len(plugin_names)}):"
                    )
                    for plugin_name in plugin_names:
                        plugin_info: PluginMetadata = discovery.get_plugin(plugin_name)
                        version = (
                            plugin_info.get("version", "unknown")
                            if plugin_info
                            else "unknown"
                        )
                        cls.get_instance().logger.info(f"  - {plugin_name} (v{version})")

            return 0

        except Exception as e:
            cls.get_instance().logger.info(f"❌ Error scanning plugins: {e}")
            return 1

    @classmethod
    def _handle_validate(cls, args: Any) -> int:
        """Handle plugin validation."""
        try:
            plugin_path = Path(args.plugin_path)

            if not plugin_path.exists():
                cls.get_instance().logger.info(f"❌ Plugin path not found: {plugin_path}")
                return 1

            cls.get_instance().logger.info(f"🔍 Validating plugin: {plugin_path}")

            # Basic structure validation
            if plugin_path.is_dir():
                # Check for main plugin file
                plugin_file = plugin_path / f"{plugin_path.name}.py"
                if not plugin_file.exists():
                    cls.get_instance().logger.info(f"❌ Main plugin file not found: {plugin_file}")
                    return 1

                # Check for config schema
                config_file = plugin_path / "config_schema.py"
                if not config_file.exists():
                    cls.get_instance().logger.info(f"⚠️  Warning: No config schema found: {config_file}")

                # Enhanced validation: syntax check
                try:
                    with open(plugin_file, "r") as f:
                        import ast

                        ast.parse(f.read())
                    cls.get_instance().logger.info("✅ Plugin syntax is valid")
                except SyntaxError as e:
                    cls.get_instance().logger.info(f"❌ Syntax error in plugin: {e}")
                    return 1

                cls.get_instance().logger.info("✅ Plugin structure is valid")
            else:
                # For single file plugins, check syntax
                try:
                    with open(plugin_path, "r") as f:
                        import ast

                        ast.parse(f.read())
                    cls.get_instance().logger.info("✅ Plugin file exists and has valid syntax")
                except SyntaxError as e:
                    cls.get_instance().logger.info(f"❌ Syntax error in plugin: {e}")
                    return 1

            return 0

        except Exception as e:
            cls.get_instance().logger.info(f"❌ Error validating plugin: {e}")
            return 1

    @classmethod
    def _handle_check_deps(cls, args: Any) -> int:
        """Handle plugin dependency checking."""
        try:
            plugin_path = Path(args.plugin_path)

            if not plugin_path.exists():
                cls.get_instance().logger.info(f"❌ Plugin path not found: {plugin_path}")
                return 1

            cls.get_instance().logger.info(f"🔍 Checking dependencies for: {plugin_path}")

            # Basic import checking
            if plugin_path.is_file():
                files_to_check = [plugin_path]
            else:
                files_to_check = list(plugin_path.glob("**/*.py"))

            missing_deps = set()
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
                cls.get_instance().logger.info(
                    f"⚠️  Missing dependencies: {', '.join(sorted(missing_deps))}"
                )
                return 1
            else:
                cls.get_instance().logger.info("✅ All dependencies are available")
                return 0

        except Exception as e:
            cls.get_instance().logger.info(f"❌ Error checking dependencies: {e}")
            return 1

    @classmethod
    def _handle_migrate(cls, args: Any) -> int:
        """Handle plugin migration."""
        cls.get_instance().logger.info("❌ Plugin migration feature has been removed")
        cls.get_instance().logger.info("   This feature was incomplete and has been deprecated")
        cls.get_instance().logger.info("   Create new plugins using 'panther create plugin' instead")
        return 1
