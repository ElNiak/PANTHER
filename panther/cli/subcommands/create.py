"""
Create Command - Plugin and component creation
"""

import logging
from argparse import ArgumentParser, _SubParsersAction
from typing import Any

from panther.cli.base import BaseCommand


class CreateCommand(BaseCommand):
    """Handle plugin and component creation commands."""

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the create subcommand parser."""
        parser = subparsers.add_parser(
            "create",
            help="Create new plugins and components",
            description="Create new plugins, subplugins, and other PANTHER components",
        )

        subcommands = parser.add_subparsers(
            dest="create_action", help="Creation actions", metavar="ACTION"
        )

        # Plugin subcommand
        plugin_parser = subcommands.add_parser(
            "plugin",
            help="Create new plugin",
            description="Create a new plugin with specified type and name",
        )
        plugin_parser.add_argument(
            "plugin_type",
            choices=["service", "environment", "protocol"],
            help="Type of plugin to create",
        )
        plugin_parser.add_argument("plugin_name", help="Name of the plugin to create")
        plugin_parser.add_argument(
            "--dev-mode", action="store_true", help="Create plugin in development mode"
        )
        plugin_parser.add_argument(
            "--production-mode",
            action="store_true",
            help="Create plugin in production mode",
        )
        plugin_parser.add_argument(
            "--with-subplugins",
            action="store_true",
            help="Create plugin with subplugin support",
        )

        # Subplugin subcommand
        subplugin_parser = subcommands.add_parser(
            "subplugin",
            help="Create new subplugin",
            description="Create a new subplugin for an existing plugin",
        )
        subplugin_parser.add_argument(
            "plugin_type",
            choices=["service", "environment", "protocol"],
            help="Type of parent plugin",
        )
        subplugin_parser.add_argument("plugin_name", help="Name of the parent plugin")
        subplugin_parser.add_argument(
            "subplugin_name", help="Name of the subplugin to create"
        )
        subplugin_parser.add_argument(
            "--dev-mode",
            action="store_true",
            help="Create subplugin in development mode",
        )
        subplugin_parser.add_argument(
            "--production-mode",
            action="store_true",
            help="Create subplugin in production mode",
        )

        # Template subcommand
        template_parser = subcommands.add_parser(
            "template",
            help="Create configuration template",
            description="Create configuration file templates",
        )
        template_parser.add_argument(
            "template_type",
            choices=["experiment", "service", "environment"],
            help="Type of template to create",
        )
        template_parser.add_argument("--output", type=str, help="Output file path")

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        """Handle the create command execution."""
        if not hasattr(args, "create_action") or args.create_action is None:
            cls.get_instance().logger.info(
                "❌ No create action specified. Use 'panther create --help' for options."
            )
            return 1

        if args.create_action == "plugin":
            return cls._handle_create_plugin(args)
        elif args.create_action == "subplugin":
            return cls._handle_create_subplugin(args)
        elif args.create_action == "template":
            return cls._handle_create_template(args)
        else:
            cls.get_instance().logger.info(f"❌ Unknown create action: {args.create_action}")
            return 1

    @classmethod
    def _handle_create_plugin(cls, args: Any) -> int:
        """Handle plugin creation."""
        try:
            from panther.tools.plugins.plugin_creator import create_plugin

            plugin_type = args.plugin_type
            plugin_name = args.plugin_name

            # Determine development mode
            dev_mode = None
            if args.dev_mode:
                dev_mode = True
            elif args.production_mode:
                dev_mode = False

            cls.get_instance().logger.info(f"🔧 Creating {plugin_type} plugin: {plugin_name}")

            success = create_plugin(
                plugin_type,
                plugin_name,
                in_development_mode=dev_mode,
                create_subplugins=args.with_subplugins,
            )

            if success:
                cls.get_instance().logger.info(f"✅ Plugin '{plugin_name}' created successfully")
                return 0
            else:
                cls.get_instance().logger.info(f"❌ Failed to create plugin '{plugin_name}'")
                return 1

        except Exception as e:
            cls.get_instance().logger.info(f"❌ Error creating plugin: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return 1

    @classmethod
    def _handle_create_subplugin(cls, args: Any) -> int:
        """Handle subplugin creation."""
        try:
            from panther.tools.plugins.plugin_creator import create_subplugin

            plugin_type = args.plugin_type
            plugin_name = args.plugin_name
            subplugin_name = args.subplugin_name

            # Determine development mode
            dev_mode = None
            if args.dev_mode:
                dev_mode = True
            elif args.production_mode:
                dev_mode = False

            cls.get_instance().logger.info(
                f"🔧 Creating subplugin '{subplugin_name}' for {plugin_type} plugin '{plugin_name}'"
            )

            success = create_subplugin(
                plugin_type, plugin_name, subplugin_name, in_development_mode=dev_mode
            )

            if success:
                cls.get_instance().logger.info(f"✅ Subplugin '{subplugin_name}' created successfully")
                return 0
            else:
                cls.get_instance().logger.info(f"❌ Failed to create subplugin '{subplugin_name}'")
                return 1

        except Exception as e:
            cls.get_instance().logger.info(f"❌ Error creating subplugin: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return 1

    @classmethod
    def _handle_create_template(cls, args: Any) -> int:
        """Handle template creation."""
        try:
            template_type = args.template_type
            output_path = args.output

            cls.get_instance().logger.info(f"🔧 Creating {template_type} template")

            # Template content based on type
            templates = {
                "experiment": cls._get_experiment_template(),
                "service": cls._get_service_template(),
                "environment": cls._get_environment_template(),
            }

            template_content = templates.get(template_type)
            if not template_content:
                cls.get_instance().logger.info(f"❌ Unknown template type: {template_type}")
                return 1

            if output_path:
                from pathlib import Path

                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, "w") as f:
                    f.write(template_content)

                cls.get_instance().logger.info(f"✅ Template created: {output_file}")
            else:
                cls.get_instance().logger.info(template_content)

            return 0

        except Exception as e:
            cls.get_instance().logger.info(f"❌ Error creating template: {e}")
            return 1

    @classmethod
    def _get_experiment_template(cls) -> str:
        """Get experiment configuration template."""
        return """# PANTHER Experiment Configuration Template
logging:
  level: INFO
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"

observers:
  logger:
    enabled: true
    log_level: "INFO"
    enable_colors: true
  metrics:
    enabled: true
    collect_system_metrics: true
  storage:
    enabled: true
    storage_path: "outputs/storage"

paths:
  output_dir: "outputs"
  log_dir: "outputs/logs"
  plugin_dir: "panther/plugins"

docker:
  force_build_docker_image: false

tests:
  - name: "Your Test Name"
    description: "Description of your test"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: your_implementation
          type: iut
        protocol:
          name: your_protocol
          version: your_version
          role: server
        timeout: 100
      client:
        implementation:
          name: your_implementation
          type: iut
        protocol:
          name: your_protocol
          version: your_version
          role: client
          target: server
        timeout: 100
    steps:
      wait: 60
"""

    @classmethod
    def _get_service_template(cls) -> str:
        """Get service plugin template."""
        return """# Service Plugin Configuration Template
"""

    @classmethod
    def _get_environment_template(cls) -> str:
        """Get environment plugin template."""
        return """# Environment Plugin Configuration Template
"""
