"""
Docker Compose specific command adapter for PANTHER framework.

This module provides an adapter that adapts commands for Docker Compose environments.
"""

from typing import Any, Dict

from panther.core.command_processor.interfaces import IEnvironmentCommandAdapter
from panther.plugins.services.services_interface import ShellCommand


class DockerComposeCommandAdapter(IEnvironmentCommandAdapter):
    """

    from typing import Any, Dict, DictDocker Compose specific command adapter."""

    def adapt_commands(self, commands: Dict[str, Any]) -> Dict[str, Any]:
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
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            "DockerComposeCommandAdapter processing commands: %s", commands.keys()
        )
        if "pre_run_cmds" in commands:
            logger.debug("pre_run_cmds content: %s", commands["pre_run_cmds"])

        for phase, cmd_list in commands.items():
            if isinstance(cmd_list, list):
                # Process each command in the list
                adapted_commands[phase] = [
                    self._process_command(cmd) for cmd in cmd_list
                ]
            else:
                # Handle non-list values (e.g., single commands or other structures)
                adapted_commands[phase] = cmd_list

        return adapted_commands

    def _process_command(self, cmd):
        """Process individual command to identify its type."""
        if isinstance(cmd, ShellCommand):
            # Check if it's a variable assignment
            if self._is_variable_assignment(cmd.raw_command):
                cmd.is_variable_assignment = True
                cmd.is_shell_builtin = False  # Override to handle differently
            return cmd
        elif isinstance(cmd, str):
            # Convert to ShellCommand and check type
            shell_cmd = ShellCommand(cmd)
            if self._is_variable_assignment(cmd):
                shell_cmd.is_variable_assignment = True
                shell_cmd.is_shell_builtin = False
            return shell_cmd
        return cmd

    def _is_variable_assignment(self, cmd_str: str) -> bool:
        """
        Check if a command is a variable assignment.

        Variable assignments have the pattern: VAR=value or VAR=$(command)
        """
        import re

        # Pattern matches: VARNAME=value or VARNAME=$(...)
        pattern = r"^\s*[A-Za-z_][A-Za-z0-9_]*=.*"
        return bool(re.match(pattern, cmd_str.strip()))
