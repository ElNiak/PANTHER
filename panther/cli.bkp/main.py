#!/usr/bin/env python3
"""
PANTHER CLI - Main entry point

This module provides the main command-line interface parser and dispatcher for
the PANTHER framework, implementing a modular command architecture with consistent
error handling and user experience patterns.

**Command Architecture**:
- **BaseCommand Pattern**: All commands inherit from BaseCommand with consistent
  register_parser() and handle() interface
- **Subparser Registration**: Commands register themselves via static methods
- **Command Discovery**: Dynamic command mapping with error handling
- **Global Options**: Consistent debug and version handling across all commands

**CLI Design Patterns**:
- **Argument Parser Hierarchy**: Global options inherited by all subcommands
- **Bash Completion**: argcomplete integration for tab completion
- **Debug Mode**: Conditional detailed logging and error reporting
- **Graceful Cancellation**: Keyboard interrupt handling with proper exit codes

**User Experience Features**:
- Rich help text with practical examples
- Emoji indicators for visual feedback (when appropriate)
- Consistent error message formatting
- Progressive disclosure (basic help → detailed command help)

**Integration Points**:
- LoggerFactory for consistent logging across framework
- Configuration system integration through command handlers
- Plugin system integration for extensible functionality
"""

import argparse
import logging
import sys
from pathlib import Path

import argcomplete

from panther.cli.subcommands import (
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
    """Create and configure the main argument parser.

    Builds the hierarchical argument parser structure with global options
    and subcommand registration. Uses argparse subparsers for modular
    command organization and consistent help text formatting.

    **Parser Architecture**:
    - Global options (--debug, --version) available to all commands
    - Subparser registration for modular command system
    - Rich help text with practical examples
    - Raw description formatter for preserved formatting

    **Command Registration**:
    Each command class registers itself via CommandClass.register_parser(subparsers),
    following the Command pattern for consistent interface and error handling.

    Returns:
        argparse.ArgumentParser: Configured main parser with all subcommands registered

    Note:
        argcomplete.autocomplete() must be called on the returned parser
        to enable bash completion support.
    """
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
    """Main CLI entry point and command dispatcher.

    Orchestrates the complete CLI experience including:
    - Global argument parsing and validation
    - Debug logging initialization with LoggerFactory integration
    - Command discovery and dispatch through command_map
    - Consistent error handling and user feedback
    - Bash completion support via argcomplete

    **Command Dispatch Architecture**:
    Uses a command_map dictionary to dispatch to appropriate command handlers,
    following the Command pattern for consistent interface and error handling.
    Each command implements:
    - register_parser(subparsers): Define CLI arguments and subcommands
    - handle(args): Execute command logic with structured error handling

    **Error Handling Strategy**:
    - KeyboardInterrupt: Graceful cancellation with user message (exit 130)
    - General exceptions: User-friendly error messages in normal mode
    - Debug mode: Full stacktraces for development and troubleshooting
    - Unknown commands: Help text display with error indication

    **Debug Mode Integration**:
    When --debug is specified, initializes LoggerFactory with:
    - DEBUG level logging across all components
    - Colored output for better development experience
    - Detailed exception information via exc_info=True

    Returns:
        int: Exit code following Unix conventions:
             0 = success
             1 = general error
             130 = terminated by Control-C

    Example:
        >>> sys.exit(main() or 0)  # Ensures 0 exit code for None return
    """
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
                logging.error(f"❌ Error: {e}", exc_info=True)
            else:
                logging.error(f"❌ Error: {e}")
            return 1
    else:
        logging.error(f"❌ Unknown command: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
