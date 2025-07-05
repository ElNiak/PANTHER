"""
Base classes for CLI subcommands.
"""

import logging
from abc import ABC, abstractmethod
from argparse import ArgumentParser, _SubParsersAction
from typing import Any, Dict


class BaseCommand(ABC):
    """Provide consistent interface for all CLI subcommands.

    BaseCommand establishes a uniform contract for all PANTHER CLI subcommands,
    ensuring consistent argument parsing, error handling, and command execution
    patterns across the entire command-line interface.

    The Command pattern implementation requires subclasses to implement two
    essential methods: register_parser() for CLI argument definition and
    handle() for command execution logic.

    **Design Principles**:
    - **Separation of Concerns**: Parser registration separate from execution
    - **Consistent Interface**: All commands follow identical method signatures
    - **Error Handling**: Standardized return codes and exception management
    - **Testability**: Clear separation enables isolated unit testing

    **Implementation Requirements**:
    Each subclass must implement:
    1. register_parser(): Define command arguments and subcommands
    2. handle(): Execute command logic with proper error handling

    **Return Code Conventions**:
    - 0: Success
    - 1: General error or validation failure
    - 130: Interrupted by user (Ctrl+C)

    Examples:
        >>> class MyCommand(BaseCommand):
        ...     @classmethod
        ...     def register_parser(cls, subparsers):
        ...         parser = subparsers.add_parser('my-command')
        ...         parser.add_argument('--option', help='Command option')
        ...         return parser
        ...
        ...     @classmethod
        ...     def handle(cls, args):
        ...         print(f"Executing with option: {args.option}")
        ...         return 0

    Raises:
        NotImplementedError: If subclass doesn't implement required methods

    Note:
        Commands should use LoggerFactory for consistent logging and follow
        the CLIActionDispatchMixin pattern for complex subcommand handling.
    """

    @classmethod
    @abstractmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the subcommand parser with arguments and options.

        Defines the command-line interface for this command including all
        arguments, options, and subcommands. This method is called during
        CLI initialization to build the complete argument parser hierarchy.

        **Parser Configuration Requirements**:
        - Use descriptive help text for user guidance
        - Set appropriate argument types and validation
        - Include usage examples in description when helpful
        - Configure formatter_class for complex help text

        **Argument Design Patterns**:
        - Required arguments: Use positional arguments or required=True
        - Optional flags: Use action='store_true' for boolean flags
        - Choice validation: Use choices parameter for restricted values
        - File paths: Use type=Path for automatic path validation

        Args:
            subparsers: The subparsers object from main argument parser,
                used to register this command as a subcommand with its
                own argument structure and help documentation.

        Returns:
            ArgumentParser: The configured parser for this command,
                which will be used to parse command-line arguments
                specific to this subcommand.

        Examples:
            Basic parser registration pattern::

                @classmethod
                def register_parser(cls, subparsers):
                    parser = subparsers.add_parser(
                        'validate',
                        help='Validate configuration files'
                    )
                    parser.add_argument('--config', required=True)
                    return parser

        Note:
            Parser registration is separated from command execution to enable
            help text generation without importing heavy dependencies.
        """
        pass

    @classmethod
    @abstractmethod
    def handle(cls, args: Any) -> int:
        """Execute the subcommand with parsed arguments.

        Implements the core command logic using the parsed command-line
        arguments. This method contains the actual functionality of the
        command and is responsible for proper error handling and user feedback.

        **Implementation Guidelines**:
        - Validate arguments before processing
        - Provide clear progress feedback for long operations
        - Use consistent error messages with emoji indicators
        - Return appropriate exit codes for shell scripting
        - Log errors with appropriate detail level

        **Error Handling Strategy**:
        - Catch specific exceptions and provide helpful error messages
        - Use debug mode for detailed stack traces
        - Return non-zero exit codes for any failure condition
        - Provide suggestions for fixing common errors

        Args:
            args: Parsed command-line arguments from argparse.
                Contains all options, flags, and positional arguments
                defined in register_parser() method.

        Returns:
            int: Exit code following Unix conventions:
                0 for success, non-zero for various error conditions.
                Should match shell scripting expectations.

        Examples:
            Basic command handler pattern::

                @classmethod
                def handle(cls, args):
                    try:
                        # Command logic here
                        print("✅ Operation successful")
                        return 0
                    except Exception as e:
                        print(f"❌ Error: {e}")
                        return 1

        Raises:
            Should catch all exceptions and convert to appropriate
            exit codes. Only re-raise if debug mode is enabled
            for development troubleshooting.

        Note:
            Commands should use the LoggerFactory for consistent logging
            and follow CLI UX patterns for user feedback.
        """
        pass


class CLIActionDispatchMixin:
    """Provide standardized action dispatch for CLI commands.

    CLIActionDispatchMixin implements a reusable pattern for commands that
    have multiple subactions (like 'plugins list', 'plugins info', etc.).
    It provides consistent error handling, validation, and user feedback
    across all commands that use the action dispatch pattern.

    **Usage Pattern**:
    Commands with multiple subactions inherit from this mixin and use
    dispatch_action() to route to appropriate handler methods based on
    the parsed action argument.

    **Benefits**:
    - **Consistency**: Same error messages and patterns across commands
    - **DRY Principle**: Eliminates duplicate dispatch logic
    - **Error Handling**: Standardized validation and error reporting
    - **Maintainability**: Single place to update dispatch behavior

    Examples:
        >>> class PluginsCommand(BaseCommand, CLIActionDispatchMixin):
        ...     @classmethod
        ...     def handle(cls, args):
        ...         handlers = {
        ...             'list': cls._handle_list,
        ...             'info': cls._handle_info
        ...         }
        ...         return cls.dispatch_action(
        ...             args, 'plugins_action', handlers, 'plugins'
        ...         )

    Note:
        This mixin should be used with BaseCommand for commands that
        implement multiple subactions through argparse subparsers.
    """

    @classmethod
    def dispatch_action(
        cls,
        args: Any,
        action_attr: str,
        action_handlers: Dict[str, Any],
        command_name: str,
    ) -> int:
        """Dispatch command to appropriate action handler.

        Routes parsed command-line arguments to the correct handler method
        based on the specified action attribute. Provides consistent error
        handling and user feedback for commands with multiple subactions.

        **Dispatch Flow**:
        1. Validate that action attribute exists and has a value
        2. Look up handler method in action_handlers dictionary
        3. Call handler method if found, return error if not found
        4. Provide consistent error messages with command context

        **Error Conditions**:
        - Missing action attribute: User didn't specify a subaction
        - Unknown action: User specified invalid subaction name
        - Handler exceptions: Propagated from individual handler methods

        Args:
            args: Parsed command-line arguments from argparse containing
                all options and the action attribute to dispatch on.
            action_attr: Name of the attribute containing the action to
                dispatch (e.g., 'plugins_action', 'config_action').
            action_handlers: Dictionary mapping action names to their
                corresponding handler methods or functions.
            command_name: Human-readable command name for error messages
                and help text (e.g., 'plugins', 'config').

        Returns:
            int: Exit code from the handler method:
                0 for successful execution
                1 for validation errors or unknown actions

        Examples:
            >>> handlers = {
            ...     'list': cls._handle_list,
            ...     'validate': cls._handle_validate
            ... }
            >>> return cls.dispatch_action(
            ...     args, 'config_action', handlers, 'config'
            ... )

        Raises:
            Exceptions from handler methods are not caught by this method
            and should be handled by the calling command's handle() method.

        Note:
            Handler methods should follow the same signature as BaseCommand.handle()
            and return appropriate exit codes for shell integration.
        """
        if not hasattr(args, action_attr) or getattr(args, action_attr) is None:
            logging.info(
                f"❌ No {command_name} action specified. Use 'panther {command_name} --help' for options."
            )
            return 1

        action = getattr(args, action_attr)
        handler = action_handlers.get(action)
        if handler:
            return handler(args)
        else:
            logging.info(f"❌ Unknown {command_name} action: {action}")
            return 1
