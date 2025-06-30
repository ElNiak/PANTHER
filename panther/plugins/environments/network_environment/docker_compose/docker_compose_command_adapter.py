"""
Docker Compose specific command adapter for PANTHER framework.

This module provides an adapter that adapts commands for Docker Compose environments.
"""

import logging
import re
from typing import Any, Dict

from panther.core.command_processor import IEnvironmentCommandAdapter, ShellCommand


class DockerComposeCommandAdapter(IEnvironmentCommandAdapter):
    """

    from typing import Any, Dict, DictDocker Compose specific command adapter."""

    def adapt_commands(self, commands: Dict[str, Any]) -> Dict[str, ShellCommand]:
        """
        Adapt commands for Docker Compose environment.

        This performs any Docker Compose specific transformations needed
        for the environment.

        Args:
            commands: Processed commands

        Returns:
            Docker Compose adapted commands
        """
        # Process each command phase
        adapted_commands = {}

        # Debug logging

        logger = logging.getLogger(__name__)
        logger.debug(
            "DockerComposeCommandAdapter processing commands: %s", commands.keys()
        )

        if isinstance(commands, ShellCommand):
            # If commands is a single ShellCommand, adapt it directly
            logger.debug("Processing single ShellCommand: %s", commands)
            return self._process_command(commands)
        for phase, cmd_list in commands.items():
            if isinstance(cmd_list, list):
                # Process each command in the list
                logger.debug("Processing phase '%s' with commands: %s", phase, cmd_list)
                adapted_commands[phase] = [
                    self._process_command(cmd) for cmd in cmd_list
                ]
            elif isinstance(cmd_list, ShellCommand):
                # Process single ShellCommand
                logger.debug(
                    "Processing phase '%s' with single ShellCommand: %s",
                    phase,
                    cmd_list,
                )
                adapted_commands[phase] = self._process_command(cmd_list)
            elif isinstance(cmd_list, str):
                logger.debug(
                    "Processing phase '%s' with string command: %s", phase, cmd_list
                )
                adapted_commands[phase] = ShellCommand.from_string(cmd_list)
            elif phase == "run_cmd":
                # Handle structured command dictionaries for run_cmd phase
                logger.debug(
                    "Processing phase '%s' with structured command dict: %s",
                    phase,
                    cmd_list,
                )
                # Return as list for consistency with other phases
                adapted_commands[phase] = cmd_list
            else:
                logger.warning(
                    "Unexpected command type in phase '%s': %s", phase, type(cmd_list)
                )
                # For other types, just keep as is
                adapted_commands[phase] = cmd_list

        return adapted_commands

    def _process_command(self, cmd):
        """Process individual command to identify its type."""
        logger = logging.getLogger(__name__)
        logger.debug(
            "Processing command: %s - %s",
            type(cmd),
            f"{cmd[:10]}..." if isinstance(cmd, str) else cmd,
        )
        if isinstance(cmd, ShellCommand):
            # Check if it's a variable assignment
            if self._is_variable_assignment(cmd.raw_command):
                cmd.is_variable_assignment = True
                cmd.is_shell_builtin = False  # Override to handle differently
            return cmd
        elif isinstance(cmd, str):
            return ShellCommand.from_string(cmd)
        return cmd

    def _process_structured_command(self, cmd_dict: Dict[str, Any]) -> ShellCommand:
        """
        Process a structured command dictionary and convert to ShellCommand.

        Structured commands have format:
        {
            "working_dir": str,
            "command_binary": str,
            "command_args": str,
            "timeout": int,
            "command_env": dict
        }

        Args:
            cmd_dict: Structured command dictionary

        Returns:
            ShellCommand object
        """
        logger = logging.getLogger(__name__)

        # Extract components from structured command
        working_dir = cmd_dict.get("working_dir", "")
        command_binary = cmd_dict.get("command_binary", "")
        command_args = cmd_dict.get("command_args", "")
        timeout = cmd_dict.get("timeout", 120)
        command_env = cmd_dict.get("command_env", {})

        # Construct full command string
        if command_args:
            full_command = f"{command_binary} {command_args}".strip()
        else:
            full_command = command_binary.strip()

        logger.debug(
            "Converting structured command to ShellCommand: working_dir=%s, binary=%s, args=%s",
            working_dir,
            command_binary,
            command_args,
        )

        # Create ShellCommand with all components
        shell_cmd = ShellCommand.from_string(full_command)

        # Set additional attributes
        if working_dir:
            shell_cmd.working_dir = working_dir
        if timeout != 120:  # Only set if different from default
            shell_cmd.timeout = timeout
        if command_env:
            shell_cmd.environment_variables = command_env

        return shell_cmd

    def _is_variable_assignment(self, cmd_str: str) -> bool:
        """
        Check if a command is a variable assignment.

        Variable assignments have the pattern: VAR=value or VAR=$(command)
        """
        # Pattern matches: VARNAME=value or VARNAME=$(...)
        pattern = r"^\s*[A-Za-z_][A-Za-z0-9_]*=.*"
        return bool(re.match(pattern, cmd_str.strip()))
