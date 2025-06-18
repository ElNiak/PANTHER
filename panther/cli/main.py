#!/usr/bin/env python3
"""
PANTHER CLI - Main entry point

This module provides the main command-line interface parser and dispatcher.
"""

import argparse
import logging
import sys
from pathlib import Path

import argcomplete

from .subcommands import (
    AdminCommand,
    CheckCommand,
    ConfigCommand,
    CreateCommand,
    MetricsCommand,
    PluginsCommand,
    RunCommand,
    ToolsCommand,
    TutorialCommand,
)


def create_parser():
    """Create and configure the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="panther",
        description="PANTHER - Protocol Analysis and Testing for Heterogeneous Execution and Research",
        epilog="""
Examples:
  panther run --config experiment.yaml          # Run experiment
  panther config validate --config config.yaml # Validate configuration
  panther plugins list                          # List available plugins
  panther create plugin service my_service      # Create new service plugin
  panther tutorial run service                  # Run service tutorial
  panther check --all                           # Run all code quality checks
  panther metrics list                          # List available metrics
  panther tools install-slim                    # Install Docker optimization tool

For more information on each command, use:
  panther COMMAND --help
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
        help="Show version and exit",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )

    # Register subcommands
    RunCommand.register_parser(subparsers)
    ConfigCommand.register_parser(subparsers)
    PluginsCommand.register_parser(subparsers)
    CreateCommand.register_parser(subparsers)
    TutorialCommand.register_parser(subparsers)
    AdminCommand.register_parser(subparsers)
    CheckCommand.register_parser(subparsers)
    MetricsCommand.register_parser(subparsers)
    ToolsCommand.register_parser(subparsers)

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()

    # Enable bash completion
    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Set up debug logging if requested
    if hasattr(args, "debug") and args.debug:
        from panther.core.utils.logger_factory import LoggerFactory

        # Initialize LoggerFactory with debug level and colors
        LoggerFactory.initialize(
            {
                "level": "DEBUG",
                "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
                "enable_colors": True,
            }
        )

    # Handle no command provided
    if not hasattr(args, "command") or args.command is None:
        parser.print_help()
        return 1

    # Dispatch to appropriate command handler
    command_map = {
        "run": RunCommand.handle,
        "config": ConfigCommand.handle,
        "plugins": PluginsCommand.handle,
        "create": CreateCommand.handle,
        "tutorial": TutorialCommand.handle,
        "admin": AdminCommand.handle,
        "check": CheckCommand.handle,
        "metrics": MetricsCommand.handle,
        "tools": ToolsCommand.handle,
    }

    if args.command in command_map:
        try:
            return command_map[args.command](args)
        except KeyboardInterrupt:
            logging.info("\n⚠️  Operation cancelled by user")
            return 130
        except Exception as e:
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            else:
                logging.info(f"❌ Error: {e}")
            return 1
    else:
        logging.info(f"❌ Unknown command: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
