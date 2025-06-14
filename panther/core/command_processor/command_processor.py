"""
Base implementation of command processor for PANTHER framework.

This module provides a command processor that handles command structures
and prepares them for various environments.
"""

import logging
from typing import Any
from panther.core.command_processor.command import ShellCommand, combine_shell_constructs
from .interfaces import ICommandProcessor


class CommandProcessor(ICommandProcessor):
    """Base implementation of command processor."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_commands(
        self, commands: dict[str, Any], target_format: str = "generic"
    ) -> dict[str, Any]:
        """
        Process a command structure into a target format.

        Args:
            commands: Dictionary containing command structure
            target_format: Target format identifier

        Returns:
            Dictionary with processed commands
        """
        processed_commands = {}

        # Process each command type in the dictionary
        for cmd_type, cmds in commands.items():
            self.logger.debug("Processing command type '%s'", cmd_type)
            if cmd_type == "pre_run_cmds":
                self.logger.debug("pre_run_cmds content: %s", cmds)

            if cmd_type == "run_cmd":
                # Handle the special structure of run_cmd
                processed_commands["run_cmd"] = self._process_run_cmd(cmds)
            else:
                # Process regular command lists
                processed_commands[cmd_type] = self.process_command_list(cmds)

        return processed_commands

    def _process_run_cmd(self, run_cmd: dict[str, Any]) -> dict[str, Any]:
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
                self.logger.warning("Error processing env vars: %s. Using empty dict.", e)
        elif run_cmd.get("command_env"):
            try:
                env_vars = {k: str(v) for k, v in run_cmd["command_env"].items()}
            except (AttributeError, TypeError) as e:
                self.logger.warning("Error processing command_env vars: %s. Using empty dict.", e)

        return {
            "working_dir": run_cmd.get("working_dir", ""),
            "command_binary": run_cmd.get("command_binary", "").strip().replace("\n", ""),
            "command_args": command_args,
            "environment": env_vars,
            "timeout": run_cmd.get("timeout", 60),
        }

    def process_command_list(
        self, commands: list[Any], detect_properties: bool = True
    ) -> list[dict[str, Any]]:
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
        combined_cmds = combine_shell_constructs(valid_cmds)
        if not combined_cmds:
            # Use original valid commands as fallback
            combined_cmds = valid_cmds

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

    def _validate_and_convert_commands(self, commands: list[Any]) -> list[ShellCommand | str]:
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

    def detect_command_properties(self, command: str) -> dict[str, bool]:
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
                    or (len(command.split("\n")) > 1 and command.split("\n")[1].strip() == "{")
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
