"""
Command Builder Base Class

This module provides a base class for building commands in a standardized way,
reducing duplication across service implementations.
"""

from typing import Any, Dict, List, Optional

from panther.core.command_processor.models.shell_command import ShellCommand
from panther.core.utils.logging_mixin import LoggerMixin


class CommandBuilder(LoggerMixin):
    """

    Base class for building commands with common patterns.

    Reduces duplication in command argument construction across service managers.
    """

    def __init__(self):
        super().__init__()
        self._command_args: List[str] = []
        self._env_vars: Dict[str, str] = {}

    def reset(self) -> "CommandBuilder":
        """Reset the builder to start fresh."""
        self._command_args = []
        self._env_vars = {}
        return self

    def add_argument(self, arg: str) -> "CommandBuilder":
        """Add a single argument."""
        self._command_args.append(str(arg))
        return self

    def add_arguments(self, *args: str) -> "CommandBuilder":
        """Add multiple arguments."""
        self._command_args.extend(str(arg) for arg in args)
        return self

    def add_flag(self, flag: str, condition: bool = True) -> "CommandBuilder":
        """Add a flag if condition is True."""
        if condition:
            self._command_args.append(flag)
        return self

    def add_option(
        self, option: str, value: Any, condition: bool = True
    ) -> "CommandBuilder":
        """Add an option with value if condition is True."""
        if condition and value is not None:
            self._command_args.extend([option, str(value)])
        return self

    def add_environment(
        self, key: str, value: str, condition: bool = True
    ) -> "CommandBuilder":
        """Add an environment variable."""
        if condition:
            self._env_vars[key] = value
        return self

    def add_environments(
        self, env_vars: Dict[str, str], condition: bool = True
    ) -> "CommandBuilder":
        """Add multiple environment variables."""
        if condition:
            self._env_vars.update(env_vars)
        return self

    def build_args(self) -> List[str]:
        """Build and return the command arguments."""
        return self._command_args.copy()

    def build_env(self) -> Dict[str, str]:
        """Build and return the environment variables."""
        return self._env_vars.copy()

    def build_structured_command(
        self, command: str, working_dir: Optional[str] = None
    ) -> ShellCommand:
        """Build a ShellCommand object."""
        # Build full command with args
        full_command = (
            f"{command} {' '.join(self.build_args())}" if self.build_args() else command
        )

        return ShellCommand(
            command=full_command, environment=self.build_env(), working_dir=working_dir
        )
