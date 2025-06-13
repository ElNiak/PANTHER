"""
Command Builder Base Class

This module provides a base class for building commands in a standardized way,
reducing duplication across service implementations.
"""

from typing import Any, TYPE_CHECKING

from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.command_processor.command import ShellCommand
from panther.plugins.protocols.config_schema import RoleEnum

if TYPE_CHECKING:
    from panther.core.command_processor.command_processor import CommandProcessor


class CommandBuilder(LoggerMixin):
    """
    Base class for building commands with common patterns.

    Reduces duplication in command argument construction across service managers.
    """

    def __init__(self):
        super().__init__()
        self._command_args: list[str] = []
        self._env_vars: dict[str, str] = {}

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

    def add_option(self, option: str, value: Any, condition: bool = True) -> "CommandBuilder":
        """Add an option with value if condition is True."""
        if condition and value is not None:
            self._command_args.extend([option, str(value)])
        return self

    def add_environment(self, key: str, value: str, condition: bool = True) -> "CommandBuilder":
        """Add an environment variable."""
        if condition:
            self._env_vars[key] = value
        return self

    def add_environments(
        self, env_vars: dict[str, str], condition: bool = True
    ) -> "CommandBuilder":
        """Add multiple environment variables."""
        if condition:
            self._env_vars.update(env_vars)
        return self

    def build_args(self) -> list[str]:
        """Build and return the command arguments."""
        return self._command_args.copy()

    def build_env(self) -> dict[str, str]:
        """Build and return the environment variables."""
        return self._env_vars.copy()

    def build_structured_command(
        self, command: str, working_dir: str | None = None
    ) -> ShellCommand:
        """Build a ShellCommand object."""
        # Build full command with args
        full_command = f"{command} {' '.join(self.build_args())}" if self.build_args() else command

        return ShellCommand(
            command=full_command, environment=self.build_env(), working_dir=working_dir
        )


class ServiceCommandBuilder(CommandBuilder):
    """
    Specialized command builder for service managers with common patterns.

    Handles both command arguments (for main executables) and shell commands
    (for setup, preparation, etc.).
    """

    def __init__(self, role: RoleEnum):
        super().__init__()
        self.role = role
        self._shell_commands: list[ShellCommand] = []

    def add_certificates(
        self, params: dict[str, Any], cert_param_key: str = "param", cert_file_key: str = "file"
    ) -> "ServiceCommandBuilder":
        """Add certificate parameters if present."""
        if "certificates" in params:
            certs = params["certificates"]

            # Add certificate file
            if "cert" in certs:
                self.add_option(
                    certs["cert"].get(cert_param_key, "-c"), certs["cert"].get(cert_file_key)
                )

            # Add key file
            if "key" in certs:
                self.add_option(
                    certs["key"].get(cert_param_key, "-k"), certs["key"].get(cert_file_key)
                )

            # Add CA certificate if present
            if "ca" in certs:
                self.add_option(
                    certs["ca"].get(cert_param_key, "--ca"), certs["ca"].get(cert_file_key)
                )

        return self

    def add_protocol_params(
        self, params: dict[str, Any], alpn_param: str = "--alpn"
    ) -> "ServiceCommandBuilder":
        """Add protocol-specific parameters."""
        if "protocol" in params:
            protocol = params["protocol"]

            # Add ALPN if present
            if "alpn" in protocol:
                self.add_option(
                    protocol["alpn"].get("param", alpn_param), protocol["alpn"].get("value")
                )

            # Add version if present
            if "version" in protocol:
                self.add_option(
                    protocol["version"].get("param", "--version"), protocol["version"].get("value")
                )

        return self

    def add_network_params(
        self, params: dict[str, Any], port_param: str = "-p"
    ) -> "ServiceCommandBuilder":
        """Add network-related parameters."""
        if "network" in params:
            network = params["network"]

            # Add port
            if "port" in network:
                self.add_option(port_param, network["port"])

            # Add host/interface binding
            if "host" in network:
                self.add_option(network.get("host_param", "-h"), network["host"])

        return self

    def add_role_specific_params(
        self, params: dict[str, Any], server_port_param: str = "-p", client_target_param: str = None
    ) -> "ServiceCommandBuilder":
        """Add role-specific parameters (server vs client)."""
        if self.role == RoleEnum.server:
            # Server-specific parameters
            if "network" in params and "port" in params["network"]:
                self.add_option(server_port_param, params["network"]["port"])

            # Add server-specific flags
            if "server_flags" in params:
                for flag in params["server_flags"]:
                    self.add_flag(flag)

        elif self.role == RoleEnum.client:
            # Client-specific parameters
            if "target" in params:
                if client_target_param:
                    self.add_option(client_target_param, params["target"])
                else:
                    self.add_argument(params["target"])

            if "network" in params and "port" in params["network"]:
                self.add_argument(str(params["network"]["port"]))

            # Add client-specific flags
            if "client_flags" in params:
                for flag in params["client_flags"]:
                    self.add_flag(flag)

        return self

    def add_logging_params(
        self,
        params: dict[str, Any],
        log_level_param: str = "--log-level",
        log_file_param: str = "--log-file",
    ) -> "ServiceCommandBuilder":
        """Add logging-related parameters."""
        if "logging" in params:
            logging_params = params["logging"]

            # Add log level
            if "level" in logging_params:
                self.add_option(log_level_param, logging_params["level"])

            # Add log file
            if "file" in logging_params:
                self.add_option(log_file_param, logging_params["file"])

        return self

    def add_conditional_params(
        self, params: dict[str, Any], param_mapping: dict[str, str]
    ) -> "ServiceCommandBuilder":
        """Add parameters based on a mapping of param keys to command options."""
        for param_key, command_option in param_mapping.items():
            if param_key in params:
                value = params[param_key]
                if isinstance(value, bool):
                    self.add_flag(command_option, value)
                else:
                    self.add_option(command_option, value)

        return self

    def build_standard_command(
        self, params: dict[str, Any], base_command: str, working_dir: str | None = None
    ) -> ShellCommand:
        """
        Build a standard command with common parameter patterns.

        This method handles the most common parameter patterns for
        QUIC implementations.
        """
        self.reset()

        # Add standard parameter sets
        self.add_certificates(params)
        self.add_protocol_params(params)
        self.add_network_params(params)
        self.add_role_specific_params(params)
        self.add_logging_params(params)

        # Add any additional raw arguments
        if "additional_args" in params:
            self.add_arguments(*params["additional_args"])

        # Add environment variables
        if "environment" in params:
            self.add_environments(params["environment"])

        return self.build_structured_command(base_command, working_dir)

    def add_command(
        self,
        command: str,
        description: str | None = None,
        is_function_definition: bool = False,
        is_multiline: bool = False,
        is_critical: bool = True,
        is_variable_assignment: bool = False,
        is_function_call: bool = False,
        working_dir: str | None = None,
        environment: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> "ServiceCommandBuilder":
        """
        Add a shell command to the command list.

        Args:
            command: The shell command string
            description: Optional description of the command
            is_function_definition: Whether this is a shell function definition
            is_multiline: Whether this command spans multiple lines
            is_critical: Whether failure should halt execution
            is_variable_assignment: Whether this is a variable assignment
            is_function_call: Whether this is a function call
            working_dir: Working directory for command execution
            environment: Environment variables for the command
            timeout: Command timeout in seconds

        Returns:
            Self for method chaining
        """
        shell_cmd = ShellCommand(
            command=command,
            description=description
            or f"Command: {command[:40]}{'...' if len(command) > 40 else ''}",
            is_function_definition=is_function_definition,
            is_multiline=is_multiline,
            is_critical=is_critical,
            is_variable_assignment=is_variable_assignment,
            is_function_call=is_function_call,
            working_dir=working_dir,
            environment=environment or {},
            timeout=timeout,
        )
        self._shell_commands.append(shell_cmd)
        return self

    def add_shell_commands(self, commands: list[str | ShellCommand]) -> "ServiceCommandBuilder":
        """
        Add multiple shell commands.

        Args:
            commands: List of command strings or ShellCommand objects

        Returns:
            Self for method chaining
        """
        for cmd in commands:
            if isinstance(cmd, ShellCommand):
                self._shell_commands.append(cmd)
            else:
                self.add_command(str(cmd))
        return self

    def build_commands(self) -> list[ShellCommand]:
        """
        Build and return the shell commands.

        Returns:
            List of ShellCommand objects
        """
        return self._shell_commands.copy()

    def reset_commands(self) -> "ServiceCommandBuilder":
        """Reset the shell commands list."""
        self._shell_commands = []
        return self

    def reset(self) -> "ServiceCommandBuilder":
        """Reset both command arguments and shell commands."""
        super().reset()
        self._shell_commands = []
        return self

    def process(self, target_format: str = "generic") -> "CommandProcessor":
        """
        Create a CommandProcessor instance with the built commands.
        This enables chaining: builder.add_command("...").process().process_commands(...)

        Args:
            target_format: Target format for command processing

        Returns:
            CommandProcessor instance ready to process the built commands
        """
        from panther.core.command_processor.command_processor import CommandProcessor

        processor = CommandProcessor()

        # Create a command structure that CommandProcessor expects
        command_structure = {
            "pre_compile_cmds": [],
            "compile_cmds": [],
            "post_compile_cmds": [],
            "pre_run_cmds": self._shell_commands,  # Put our commands in pre_run by default
            "run_cmd": {},
            "post_run_cmds": [],
        }

        # Store the command structure and target format for later processing
        processor._pending_structure = command_structure
        processor._target_format = target_format

        return processor

    def process_commands(self, target_format: str = "generic") -> list[dict[str, Any]]:
        """
        Process the built commands and return processed command list.
        Convenience method for: builder.process().process_command_list(builder.build_commands())

        Args:
            target_format: Target format for command processing

        Returns:
            List of processed command dictionaries
        """
        processor = self.process(target_format)
        return processor.process_command_list(self._shell_commands)
