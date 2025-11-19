"""
Base implementation of command processor for PANTHER framework.

This module provides a command processor that handles command structures
and prepares them for various environments.
"""

import logging
from typing import Any, Dict, List, Union

from panther.core.command_processor.core.interfaces import ICommandProcessor
from panther.core.command_processor.models.shell_command import ShellCommand
from panther.core.command_processor.utils.shell_utils import combine_shell_constructs
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.exceptions.fast_fail import (
    ErrorCategory,
    ErrorSeverity,
    PantherException,
)
from panther.core.utils.feature_logger_mixin import get_feature_logger


class CommandProcessor(ICommandProcessor, ErrorHandlerMixin):
    """Base implementation of command processor."""

    def __init__(self):
        super().__init__()
        self.logger = get_feature_logger(__name__, "command_generation")

    def process_commands(
        self, commands: Dict[str, Any], target_format: str = "generic"
    ) -> Dict[str, Any]:
        """
        Process a command structure into a target format.

        Args:
            commands: Dictionary containing command structure
            target_format: Target format identifier

        Returns:
            Dictionary with processed commands
        """
        try:
            # Fast-fail validation: Check command structure before processing
            self._validate_command_structure(commands)

            processed_commands = {}

            # Create summary of processing instead of verbose logging
            self._log_processing_summary(commands)

            # Process each command type in the dictionary
            for cmd_type, cmds in commands.items():
                # Only log individual command types at DEBUG level if needed
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug("Processing command type '%s'", cmd_type)
                    if cmd_type == "pre_run_cmds" and cmds:
                        # Only show first command to reduce verbosity
                        first_cmd = cmds[0] if isinstance(cmds, list) and cmds else cmds
                        first_cmd_preview = (
                            str(first_cmd)[:100] + "..."
                            if len(str(first_cmd)) > 100
                            else str(first_cmd)
                        )
                        self.logger.debug("pre_run_cmds preview: %s", first_cmd_preview)

                if cmd_type == "run_cmd":
                    # Handle the special structure of run_cmd
                    self.logger.debug("Processing 'run_cmd' structure")
                    processed_commands["run_cmd"] = self._process_run_cmd(cmds)
                else:
                    # Process regular command lists
                    self.logger.debug("Processing '%s' commands", cmd_type)
                    processed_commands[cmd_type] = self.process_command_list(cmds)

            return processed_commands

        except Exception as e:
            # Use fast-fail handler for error processing
            self.handle_error(
                error=e,
                operation="process commands",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.COMMAND_EXECUTION,
                additional_context={
                    "commands": commands,
                    "target_format": target_format,
                },
            )
            # Re-raise to maintain existing behavior
            raise

    def _log_processing_summary(self, commands: Dict[str, Any]) -> None:
        """
        Log a concise summary of command processing instead of verbose details.

        Args:
            commands: Dictionary containing command structure
        """
        if not commands:
            self.logger.info("Processing: No commands to process")
            return

        # Count commands by type
        command_counts = {}
        total_commands = 0

        for cmd_type, cmds in commands.items():
            if isinstance(cmds, list):
                count = len(cmds)
            elif isinstance(cmds, dict):
                count = 1 if cmds else 0
            elif cmds:
                count = 1
            else:
                count = 0

            command_counts[cmd_type] = count
            total_commands += count

        # Create summary message
        if total_commands == 0:
            self.logger.info("Processing: No commands found")
            return

        # Create concise summary
        summary_parts = []
        for cmd_type, count in command_counts.items():
            if count > 0:
                summary_parts.append(f"{cmd_type}({count})")

        summary = f"Processing {total_commands} commands: {', '.join(summary_parts)}"
        self.logger.info(summary)

    def _process_run_cmd(self, run_cmd: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the special run_cmd structure.

        Args:
            run_cmd: The run_cmd dictionary

        Returns:
            Processed run_cmd dictionary
        """
        if not run_cmd:
            # If run_cmd is empty or None, provide a default structure
            return {
                "working_dir": "",
                "command_args": [],
                "environment": {},
                "timeout": 60,
            }

        # Process command_args - handle both string and list formats
        raw_args = run_cmd.get("command_args", "")
        if isinstance(raw_args, list):
            command_args = " ".join(str(arg) for arg in raw_args)
        else:
            command_args = str(raw_args).strip().replace("\n", "")

        # Process environment variables
        env_vars = {}
        if run_cmd.get("environment"):
            try:
                env_vars = {k: str(v) for k, v in run_cmd["environment"].items()}
            except (AttributeError, TypeError) as e:
                self.logger.warning(
                    "Error processing env vars: %s. Using empty dict.", e
                )
        elif run_cmd.get("command_env"):
            try:
                env_vars = {k: str(v) for k, v in run_cmd["command_env"].items()}
            except (AttributeError, TypeError) as e:
                self.logger.warning(
                    "Error processing command_env vars: %s. Using empty dict.", e
                )

        return {
            "working_dir": run_cmd.get("working_dir", ""),
            "command_binary": run_cmd.get("command_binary", "")
            .strip()
            .replace("\n", ""),
            "command_args": command_args,
            "environment": env_vars,
            "timeout": run_cmd.get("timeout", 60),
        }

    def process_command_list(
        self, commands: List[Any], detect_properties: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process a list of commands into a structured format.

        Args:
            commands: List of commands to process
            detect_properties: Whether to detect properties like multiline, function definitions, etc.

        Returns:
            List of processed command dictionaries
        """
        if not commands:
            return []

        # Validate and convert commands to ShellCommand objects
        valid_cmds = self._validate_and_convert_commands(commands)
        if not valid_cmds:
            return []

        # Combine shell constructs
        combined_cmds = combine_shell_constructs(valid_cmds) or valid_cmds

        # Process each command in the combined list
        processed_list = []
        for cmd in combined_cmds:
            if isinstance(cmd, ShellCommand):
                if not cmd.command or cmd.command.strip() == "":
                    continue
                processed_list.append(cmd.to_dict())
            elif isinstance(cmd, str):
                shell_cmd = ShellCommand.from_string(cmd, is_critical=True)

                # Detect properties if requested
                if detect_properties:
                    properties = self.detect_command_properties(cmd)
                    for prop_name, prop_value in properties.items():
                        setattr(shell_cmd, prop_name, prop_value)

                if not shell_cmd.command or shell_cmd.command.strip() == "":
                    continue
                processed_list.append(shell_cmd.to_dict())
            elif isinstance(cmd, dict) and "command" in cmd:
                # Handle dict that resembles a ShellCommand
                shell_cmd = ShellCommand(**cmd)
                if not shell_cmd.command or shell_cmd.command.strip() == "":
                    continue
                processed_list.append(shell_cmd.to_dict())
            else:
                # Try to convert other types to string as a fallback
                try:
                    shell_cmd = ShellCommand.from_string(str(cmd), is_critical=True)
                    # Ensure multiline detection for combined constructs
                    if detect_properties and "\n" in str(cmd):
                        properties = self.detect_command_properties(str(cmd))
                        for prop_name, prop_value in properties.items():
                            setattr(shell_cmd, prop_name, prop_value)

                    if not shell_cmd.command or shell_cmd.command.strip() == "":
                        continue
                    processed_list.append(shell_cmd.to_dict())
                except Exception as e:  # pylint: disable=broad-exception-caught
                    self.logger.warning(
                        "Could not convert command to ShellCommand: %s, error: %s",
                        cmd,
                        e,
                    )
                    # Skip this command

        return processed_list

    def _validate_and_convert_commands(
        self, commands: List[Any]
    ) -> List[Union[ShellCommand, str]]:
        """
        Validate and convert commands to ShellCommand objects.

        Args:
            commands: List of commands to validate and convert

        Returns:
            List of validated ShellCommand objects or strings
        """
        valid_cmds = []
        for c in commands:
            if not c:
                continue
            if isinstance(c, ShellCommand):
                valid_cmds.append(c)
            elif isinstance(c, str) and c.strip():
                valid_cmds.append(ShellCommand.from_string(c))
            elif isinstance(c, dict) and "command" in c and c["command"].strip():
                valid_cmds.append(ShellCommand.from_dict(c))
        return valid_cmds

    def detect_command_properties(self, command: str) -> Dict[str, bool]:
        """
        Detect properties of a command string.

        Args:
            command: Command string to analyze

        Returns:
            Dictionary of detected properties
        """
        properties = {
            "is_multiline": False,
            "is_function_definition": False,
            "is_control_structure": False,
        }

        # Check for multiline
        if "\n" in command:
            properties["is_multiline"] = True
            first_line = command.split("\n")[0].strip().lower()

            # Check for function definition patterns
            if (
                "() {" in command or "(){" in command or "function " in command.lower()
            ) and "}" in command:
                properties["is_function_definition"] = True
            # Check for explicit function definition syntax
            elif first_line.startswith("function ") and (
                first_line.endswith("{") or "{" in first_line
            ):
                properties["is_function_definition"] = True
            # Check for name() { syntax
            elif (
                "(" in first_line
                and ")" in first_line
                and (
                    first_line.endswith("{")
                    or (
                        len(command.split("\n")) > 1
                        and command.split("\n")[1].strip() == "{"
                    )
                    or "{" in command.split("\n")[0]
                )
            ):
                properties["is_function_definition"] = True

            # Check for control structures
            elif (
                first_line.startswith("if ")
                or (first_line.split() and first_line.split()[0].startswith("for"))
                or first_line.startswith("while ")
                or first_line.startswith("case ")
            ):
                properties["is_control_structure"] = True

        return properties

    def _validate_command_structure(self, commands: Dict[str, Any]) -> None:
        """
        Validate command structure before processing.

        Args:
            commands: Dictionary containing command structure

        Raises:
            PantherException: If command structure is invalid
        """
        if not isinstance(commands, dict):
            raise PantherException(
                message=f"Commands must be a dictionary, got {type(commands).__name__}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.COMMAND_EXECUTION,
                context={"commands_type": type(commands).__name__},
            )

        if not commands:
            self.logger.warning("Empty command structure provided")
            return

        # Validate each command type
        for cmd_type, cmds in commands.items():
            if not isinstance(cmd_type, str):
                raise PantherException(
                    message=f"Command type must be string, got {type(cmd_type).__name__}",
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.COMMAND_EXECUTION,
                    context={"command_type": cmd_type, "type": type(cmd_type).__name__},
                )

            # Special validation for run_cmd
            if cmd_type == "run_cmd":
                if cmds and not isinstance(cmds, dict):
                    raise PantherException(
                        message=f"run_cmd must be a dictionary, got {type(cmds).__name__}",
                        severity=ErrorSeverity.HIGH,
                        category=ErrorCategory.COMMAND_EXECUTION,
                        context={"run_cmd_type": type(cmds).__name__},
                    )
            elif cmds is not None:
                # Other command types should be lists, strings, or ShellCommand objects
                if isinstance(cmds, list):
                    # Validate each item in the list
                    for cmd in cmds:
                        if not isinstance(cmd, (str, dict, ShellCommand)):
                            raise PantherException(
                                message=f"Command list items must be string, dict, or ShellCommand, got {type(cmd).__name__}",
                                severity=ErrorSeverity.HIGH,
                                category=ErrorCategory.COMMAND_EXECUTION,
                                context={
                                    "command_type": cmd_type,
                                    "invalid_item_type": type(cmd).__name__,
                                },
                            )
                elif not isinstance(cmds, (str, ShellCommand)):
                    raise PantherException(
                        message=f"Command '{cmd_type}' must be list, string, or ShellCommand, got {type(cmds).__name__}",
                        severity=ErrorSeverity.HIGH,
                        category=ErrorCategory.COMMAND_EXECUTION,
                        context={
                            "command_type": cmd_type,
                            "commands_type": type(cmds).__name__,
                        },
                    )
