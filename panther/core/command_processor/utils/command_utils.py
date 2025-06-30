"""
Command Generation Utilities

This module provides common command generation patterns used across service managers.
Integrates with PANTHER's ShellCommand system and environment plugins.
"""

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

# Import PANTHER's command system
from panther.core.command_processor.utils.summarizer import CommandSummarizer

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from panther.core.command_processor.models.shell_command import ShellCommand


class CommandGenerationError(Exception):
    """Exception raised when command generation fails."""

    pass


class CommandUtils:
    """Utility class for common command generation patterns."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def extract_working_directory_from_command(
        command: str,
    ) -> Tuple[Optional[str], str]:
        """
        Extract working directory from commands that start with 'cd' followed by '&&'.

        Args:
            command: Command string to analyze

        Returns:
            tuple: (working_directory, cleaned_command)
                - working_directory: Extracted directory path or None if not found
                - cleaned_command: Command string with cd prefix removed
        """
        command = command.strip()

        # Pattern to match: cd <directory> && <remaining_command>
        cd_pattern = r"^cd\s+([^\s&]+)\s*&&\s*(.+)$"
        match = re.match(cd_pattern, command)

        if match:
            working_dir = match.group(1).strip()
            remaining_command = match.group(2).strip()

            # Remove quotes if present
            if (working_dir.startswith('"') and working_dir.endswith('"')) or (
                working_dir.startswith("'") and working_dir.endswith("'")
            ):
                working_dir = working_dir[1:-1]

            return working_dir, remaining_command

        return None, command

    @staticmethod
    def generate_basic_service_commands() -> Dict[str, list]:
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
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> "ShellCommand":
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
        # Lazy import to avoid circular dependency
        from panther.core.command_processor.models.shell_command import ShellCommand

        return ShellCommand(
            command=command,
            working_dir=working_dir,
            environment=environment or {},
            timeout=timeout,
        )

    @staticmethod
    def create_shell_commands_from_list(
        commands: List[Union[str, dict, "ShellCommand"]]
    ) -> List["ShellCommand"]:
        """
        Convert a list of various command formats to ShellCommand objects.
        Automatically extracts working directory from commands starting with 'cd && '.

        Args:
            commands: List of commands in various formats

        Returns:
            list: List of ShellCommand objects
        """
        # Lazy import to avoid circular dependency
        from panther.core.command_processor.models.shell_command import ShellCommand

        result = []
        for cmd in commands:
            if isinstance(cmd, ShellCommand):
                result.append(cmd)
            elif isinstance(cmd, str):
                # Extract working directory if present
                (
                    working_dir,
                    cleaned_cmd,
                ) = CommandUtils.extract_working_directory_from_command(cmd)
                shell_cmd = ShellCommand.from_string(cleaned_cmd)
                if working_dir and shell_cmd.metadata:
                    shell_cmd.metadata.working_directory = working_dir
                result.append(shell_cmd)
            elif isinstance(cmd, dict):
                result.append(ShellCommand.from_dict(cmd))
            else:
                # Fallback to string conversion
                result.append(ShellCommand.from_string(str(cmd)))
        return result

    @staticmethod
    def create_run_command(
        working_dir: Union[str, Path],
        command_binary: str,
        command_args: Union[str, List[str]],
        timeout: int = 60,
        environment: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
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
                command_args
                if isinstance(command_args, str)
                else " ".join(command_args)
            ),
            "timeout": timeout,
            "environment": environment or {},
        }

    @staticmethod
    def merge_command_structures(*command_dicts: Dict[str, Any]) -> Dict[str, Any]:
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
                if (
                    key in result
                    and isinstance(result[key], list)
                    and isinstance(value, list)
                ):
                    result[key].extend(value)
                elif key == "run_cmd" and isinstance(value, dict):
                    if "run_cmd" not in result:
                        result["run_cmd"] = {}
                    result["run_cmd"].update(value)
                else:
                    result[key] = value

        return result

    @staticmethod
    def validate_command_structure(command_dict: Dict[str, Any]) -> bool:
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

            run_cmd_required = [
                "working_dir",
                "command_binary",
                "command_args",
                "timeout",
            ]
            for key in run_cmd_required:
                if key not in run_cmd:
                    raise CommandGenerationError(f"run_cmd missing required key: {key}")

        return True

    @staticmethod
    def add_environment_variable(
        command_dict: Dict[str, Any], key: str, value: str
    ) -> None:
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
    def add_pre_run_command(command_dict: Dict[str, Any], command: str) -> None:
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
    def add_post_run_command(command_dict: Dict[str, Any], command: str) -> None:
        """
        Add a post-run command to the command structure.

        Args:
            command_dict: Command dictionary to modify
            command: Command to add
        """
        if "post_run_cmds" not in command_dict:
            command_dict["post_run_cmds"] = []

        command_dict["post_run_cmds"].append(command)

    @staticmethod
    def log_structured_command_generation(
        logger_instance,
        phase: str,
        commands: List["ShellCommand"],
        level: int = logging.INFO,
    ) -> None:
        """
        Log structured command generation.

        Args:
            logger_instance: Logger to use
            phase: Generation phase (e.g., 'pre-compile', 'run', 'post-run')
            commands: List of commands to log
            level: Logging level to use
        """
        # Lazy import to avoid circular dependency
        from panther.core.command_processor.models.shell_command import ShellCommand

        command_list = [
            cmd.command if isinstance(cmd, ShellCommand) else str(cmd)
            for cmd in commands
        ]
        if not command_list:
            logger_instance.log(level, "No %s commands generated", phase)
            return
        # Use smart summarization for logging
        CommandUtils.log_command_generation(logger_instance, phase, command_list, level)

    @staticmethod
    def log_command_generation(
        logger_instance, phase: str, commands: List[str], level: int = logging.INFO
    ) -> None:
        """
        Log command generation with smart summarization.

        Args:
            logger_instance: Logger to use
            phase: Generation phase (e.g., 'pre-compile', 'run', 'post-run')
            commands: List of generated commands
            level: Logging level to use
        """
        if not commands:
            logger_instance.log(level, "No %s commands generated", phase)
            return

        # Use smart summarization for logging
        summary = CommandSummarizer.summarize_command_list(commands, max_commands=2)
        stats = CommandSummarizer.get_command_stats(commands)

        logger_instance.log(
            level,
            "Generated %s commands: %s | %s",
            phase,
            summary,
            stats.get("top_patterns", []),
        )
