"""Command Builder Base Class.

Provides a fluent interface for accumulating command arguments and environment
variables, then emitting them as a list of strings (``build_args``) or a dict
(``build_env``), or as a fully-formed ``ShellCommand`` (``build_structured_command``).

Example:
    ::

        builder = CommandBuilder()
        args = (
            builder
            .reset()
            .add_argument("picoquic_sample")
            .add_flag("-l", condition=True)
            .add_option("-p", "4433")
            .add_environment("SSLKEYLOGFILE", "/tmp/keys.log")
            .build_args()
        )
        env = builder.build_env()
        # args == ["picoquic_sample", "-l", "-p", "4433"]
        # env  == {"SSLKEYLOGFILE": "/tmp/keys.log"}
"""

from typing import Any, Dict, List, Optional

from panther.core.command_processor.models.shell_command import ShellCommand
from panther.core.utils.logging_mixin import LoggerMixin


class CommandBuilder(LoggerMixin):
    """Base class for building commands with common patterns.

    Uses the builder (fluent) pattern so callers can chain ``add_*`` calls
    and finish with ``build_args()`` / ``build_env()`` /
    ``build_structured_command()``.  All ``add_*`` methods accept an optional
    ``condition`` flag so arguments are only appended when the condition is met,
    eliminating if/else boilerplate in callers.

    Subclass ``ServiceCommandBuilder`` for protocol-testing helpers such as
    certificate, ALPN, and role-specific parameter injection.
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
