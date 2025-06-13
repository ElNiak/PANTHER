"""
Command Generation Utilities

This module provides common command generation patterns used across service managers.
Integrates with PANTHER's ShellCommand system and environment plugins.
"""

import logging
from typing import Any
from pathlib import Path

# Import PANTHER's command system
from panther.core.command_processor.command import ShellCommand

logger = logging.getLogger(__name__)


class CommandGenerationError(Exception):
    """Exception raised when command generation fails."""

    pass


class CommandUtils:
    """Utility class for common command generation patterns."""

    @staticmethod
    def generate_basic_service_commands() -> dict[str, list]:
        """
        Generate basic empty command structure used by most service managers.

        Returns:
            dict: Basic command structure with empty lists
        """
        return {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": [],
            "post_run_cmds": [],
        }

    @staticmethod
    def create_shell_command(
        command: str,
        working_dir: str | None = None,
        environment: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> ShellCommand:
        """
        Create a ShellCommand object with proper structure.

        Args:
            command: Command string to execute
            working_dir: Working directory for command
            environment: Environment variables
            timeout: Command timeout

        Returns:
            ShellCommand: Properly structured command object
        """
        return ShellCommand(
            command=command, working_dir=working_dir, environment=environment or {}, timeout=timeout
        )

    @staticmethod
    def create_shell_commands_from_list(
        commands: list[str | dict | ShellCommand],
    ) -> list[ShellCommand]:
        """
        Convert a list of various command formats to ShellCommand objects.

        Args:
            commands: List of commands in various formats

        Returns:
            list: List of ShellCommand objects
        """
        result = []
        for cmd in commands:
            if isinstance(cmd, ShellCommand):
                result.append(cmd)
            elif isinstance(cmd, str):
                result.append(ShellCommand.from_string(cmd))
            elif isinstance(cmd, dict):
                result.append(ShellCommand.from_dict(cmd))
            else:
                # Fallback to string conversion
                result.append(ShellCommand.from_string(str(cmd)))
        return result

    @staticmethod
    def create_run_command(
        working_dir: str | Path,
        command_binary: str,
        command_args: str | list[str],
        timeout: int = 60,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a standardized run command structure.

        Args:
            working_dir: Working directory for the command
            command_binary: Binary/executable to run
            command_args: Arguments for the command
            timeout: Command timeout in seconds
            environment: Environment variables

        Returns:
            dict: Run command structure
        """
        return {
            "working_dir": str(working_dir),
            "command_binary": command_binary,
            "command_args": (
                command_args if isinstance(command_args, str) else " ".join(command_args)
            ),
            "timeout": timeout,
            "environment": environment or {},
        }

    @staticmethod
    def merge_command_structures(*command_dicts: dict[str, Any]) -> dict[str, Any]:
        """
        Merge multiple command structures, combining lists and updating dicts.

        Args:
            *command_dicts: Command dictionaries to merge

        Returns:
            dict: Merged command structure
        """
        result = CommandUtils.generate_basic_service_commands()

        for cmd_dict in command_dicts:
            if not isinstance(cmd_dict, dict):
                continue

            for key, value in cmd_dict.items():
                if key in result and isinstance(result[key], list) and isinstance(value, list):
                    result[key].extend(value)
                elif key == "run_cmd" and isinstance(value, dict):
                    if "run_cmd" not in result:
                        result["run_cmd"] = {}
                    result["run_cmd"].update(value)
                else:
                    result[key] = value

        return result

    @staticmethod
    def validate_command_structure(command_dict: dict[str, Any]) -> bool:
        """
        Validate that a command structure has the required fields.

        Args:
            command_dict: Command dictionary to validate

        Returns:
            bool: True if valid

        Raises:
            CommandGenerationError: If structure is invalid
        """
        required_keys = [
            "pre_compile_cmds",
            "compile_cmds",
            "post_compile_cmds",
            "pre_run_cmds",
            "post_run_cmds",
        ]

        for key in required_keys:
            if key not in command_dict:
                raise CommandGenerationError(f"Missing required key: {key}")
            if not isinstance(command_dict[key], list):
                raise CommandGenerationError(f"Key {key} must be a list")

        if "run_cmd" in command_dict:
            run_cmd = command_dict["run_cmd"]
            if not isinstance(run_cmd, dict):
                raise CommandGenerationError("run_cmd must be a dictionary")

            run_cmd_required = ["working_dir", "command_binary", "command_args", "timeout"]
            for key in run_cmd_required:
                if key not in run_cmd:
                    raise CommandGenerationError(f"run_cmd missing required key: {key}")

        return True

    @staticmethod
    def add_environment_variable(command_dict: dict[str, Any], key: str, value: str) -> None:
        """
        Add an environment variable to a command structure.

        Args:
            command_dict: Command dictionary to modify
            key: Environment variable name
            value: Environment variable value
        """
        if "run_cmd" not in command_dict:
            command_dict["run_cmd"] = CommandUtils.create_run_command(".", "", "")

        if "environment" not in command_dict["run_cmd"]:
            command_dict["run_cmd"]["environment"] = {}

        command_dict["run_cmd"]["environment"][key] = value

    @staticmethod
    def add_pre_run_command(command_dict: dict[str, Any], command: str) -> None:
        """
        Add a pre-run command to the command structure.

        Args:
            command_dict: Command dictionary to modify
            command: Command to add
        """
        if "pre_run_cmds" not in command_dict:
            command_dict["pre_run_cmds"] = []

        command_dict["pre_run_cmds"].append(command)

    @staticmethod
    def add_post_run_command(command_dict: dict[str, Any], command: str) -> None:
        """
        Add a post-run command to the command structure.

        Args:
            command_dict: Command dictionary to modify
            command: Command to add
        """
        if "post_run_cmds" not in command_dict:
            command_dict["post_run_cmds"] = []

        command_dict["post_run_cmds"].append(command)


class ServiceManagerCommandMixin:
    """
    Mixin class that provides common command generation methods for service managers.

    This mixin reduces duplication across service manager implementations by providing
    standard implementations of common command generation patterns.
    """

    def initialize_commands(self) -> None:
        """Initialize the command structure with defaults."""
        if not hasattr(self, "run_cmd"):
            self.run_cmd = CommandUtils.generate_basic_service_commands()

    def generate_pre_compile_commands(self) -> list[str]:
        """Generate pre-compile commands. Override in subclasses as needed."""
        return []

    def generate_compile_commands(self) -> list[str]:
        """Generate compile commands. Override in subclasses as needed."""
        return []

    def generate_post_compile_commands(self) -> list[str]:
        """Generate post-compile commands. Override in subclasses as needed."""
        return []

    def generate_pre_run_commands(self) -> list[str]:
        """Generate pre-run commands. Override in subclasses as needed."""
        return []

    def generate_post_run_commands(self) -> list[str]:
        """Generate post-run commands. Override in subclasses as needed."""
        return []

    def create_standard_run_command(
        self,
        command_binary: str,
        command_args: str | list[str] = "",
        working_dir: str | None = None,
        timeout: int = 60,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create a standard run command with service-specific defaults.

        Args:
            command_binary: Binary to execute
            command_args: Command arguments
            working_dir: Working directory (defaults to service working dir)
            timeout: Command timeout
            environment: Environment variables

        Returns:
            dict: Run command structure
        """
        if working_dir is None:
            working_dir = getattr(self, "working_dir", ".")

        return CommandUtils.create_run_command(
            working_dir=working_dir,
            command_binary=command_binary,
            command_args=command_args,
            timeout=timeout,
            environment=environment,
        )

    def finalize_commands(self) -> dict[str, Any]:
        """
        Finalize and validate all commands for this service.

        Returns:
            dict: Complete command structure
        """
        self.initialize_commands()

        # Update command structure with generated commands
        self.run_cmd.update(
            {
                "pre_compile_cmds": self.generate_pre_compile_commands(),
                "compile_cmds": self.generate_compile_commands(),
                "post_compile_cmds": self.generate_post_compile_commands(),
                "pre_run_cmds": self.generate_pre_run_commands(),
                "post_run_cmds": self.generate_post_run_commands(),
            }
        )

        # Ensure run_cmd is present
        if "run_cmd" not in self.run_cmd:
            self.run_cmd["run_cmd"] = self.create_standard_run_command(
                "echo", "No run command defined"
            )

        # Validate the structure
        try:
            CommandUtils.validate_command_structure(self.run_cmd)
        except CommandGenerationError as e:
            logger.error(f"Command validation failed for {self.__class__.__name__}: {e}")
            raise

        return self.run_cmd
