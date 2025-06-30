"""
Service Command Builder

This module provides a specialized command builder for service managers with
common patterns used in protocol testing implementations.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from panther.config.core.models import ProtocolRole
from panther.core.command_processor.builders import CommandBuilder
from panther.core.command_processor.core.processor import CommandProcessor
from panther.core.command_processor.core.validator import CommandValidator
from panther.core.command_processor.models.shell_command import ShellCommand
from panther.core.command_processor.utils.shell_utils import validate_redirection_syntax


class ServiceCommandBuilder(CommandBuilder):
    """
    Specialized command builder for service managers with common patterns.

    Handles both command arguments (for main executables) and shell commands
    (for setup, preparation, etc.).
    """

    def __init__(self, role: ProtocolRole):
        super().__init__()
        self.role = role
        self._shell_commands: List[ShellCommand] = []
        self._validator = CommandValidator()
        self._logger = logging.getLogger(__name__)

    def add_certificates(
        self,
        params: Dict[str, Any],
        cert_param_key: str = "param",
        cert_file_key: str = "file",
    ) -> "ServiceCommandBuilder":
        """Add certificate parameters if present."""
        if "certificates" in params:
            certs = params["certificates"]

            # Add certificate file
            if "cert" in certs:
                self.add_option(
                    certs["cert"].get(cert_param_key, "-c"),
                    certs["cert"].get(cert_file_key),
                )

            # Add key file
            if "key" in certs:
                self.add_option(
                    certs["key"].get(cert_param_key, "-k"),
                    certs["key"].get(cert_file_key),
                )

            # Add CA certificate if present
            if "ca" in certs:
                self.add_option(
                    certs["ca"].get(cert_param_key, "--ca"),
                    certs["ca"].get(cert_file_key),
                )

        return self

    def add_protocol_params(
        self, params: Dict[str, Any], alpn_param: str = "--alpn"
    ) -> "ServiceCommandBuilder":
        """Add protocol-specific parameters."""
        if "protocol" in params:
            protocol = params["protocol"]

            # Add ALPN if present
            if "alpn" in protocol:
                self.add_option(
                    protocol["alpn"].get("param", alpn_param),
                    protocol["alpn"].get("value"),
                )

            # Add version if present
            if "version" in protocol:
                self.add_option(
                    protocol["version"].get("param", "--version"),
                    protocol["version"].get("value"),
                )

        return self

    def add_network_params(
        self, params: Dict[str, Any], port_param: str = "-p"
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
        self,
        params: Dict[str, Any],
        server_port_param: str = "-p",
        client_target_param: str = None,
    ) -> "ServiceCommandBuilder":
        """Add role-specific parameters (server vs client)."""
        if self.role == ProtocolRole.SERVER:
            # Server-specific parameters
            if "network" in params and "port" in params["network"]:
                self.add_option(server_port_param, params["network"]["port"])

            # Add server-specific flags
            if "server_flags" in params:
                for flag in params["server_flags"]:
                    self.add_flag(flag)

        elif self.role == ProtocolRole.CLIENT:
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
        params: Dict[str, Any],
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
        self, params: Dict[str, Any], param_mapping: Dict[str, str]
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
        self,
        params: Dict[str, Any],
        base_command: str,
        working_dir: Optional[str] = None,
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
        description: Optional[str] = None,
        is_function_definition: bool = False,
        is_multiline: bool = False,
        is_critical: bool = True,
        is_variable_assignment: bool = False,
        is_function_call: bool = False,
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        validate_syntax: bool = True,
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
            validate_syntax: Whether to validate shell syntax (default: True)

        Returns:
            Self for method chaining
        """
        # Validate command syntax if requested
        if validate_syntax:
            self._validate_command_syntax(command)

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

    def add_shell_commands(
        self, commands: List[Union[str, ShellCommand]]
    ) -> "ServiceCommandBuilder":
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

    def build_commands(self) -> List[ShellCommand]:
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

    def process_commands(self, target_format: str = "generic") -> List[Dict[str, Any]]:
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

    def _validate_command_syntax(self, command: str) -> None:
        """
        Validate shell command syntax and log warnings for common issues.

        This method performs non-breaking validation - it logs warnings but
        does not raise exceptions to maintain backward compatibility.

        Args:
            command: The shell command to validate
        """
        validation_warnings = []

        # Check redirection syntax using existing utility
        if not validate_redirection_syntax(command):
            validation_warnings.append(
                "REDIRECTION ERROR: Malformed redirection syntax detected"
            )

        # Additional specific checks for template generation issues
        self._check_template_generation_issues(command, validation_warnings)

        # Use existing CommandValidator for comprehensive validation
        validation_result = self._validator.validate_command(command)

        if not validation_result.is_valid:
            validation_warnings.extend(validation_result.errors)

        # Add any warnings from the validator
        if validation_result.warnings:
            validation_warnings.extend(validation_result.warnings)

        # Log all validation issues as warnings (non-breaking)
        if validation_warnings:
            # Use print for immediate visibility during testing
            print(
                f"⚠️  SHELL SYNTAX ERROR: {len(validation_warnings)} issue(s) in command:"
            )
            print(f"   Command: {command[:80]}{'...' if len(command) > 80 else ''}")

            for i, warning in enumerate(validation_warnings, 1):
                print(f"   {i}. {warning}")

            # Add specific fixes for common issues
            if any("redirection" in w.lower() for w in validation_warnings):
                print(f"   💡 FIX: Change '>N/path' to 'N>/path' (e.g., '2>/dev/null')")

            if any("quote" in w.lower() for w in validation_warnings):
                print(
                    f"   💡 FIX: Check for unmatched quotes - ensure all strings are properly quoted"
                )

            if any("dangerous" in w.lower() for w in validation_warnings):
                print(
                    f"   💡 WARNING: This command contains potentially dangerous patterns"
                )

            print(f"   📍 Location: ServiceCommandBuilder.add_command()")

            # Also log through the logger system
            self._logger.warning(
                "Command syntax validation found issues in command: %s",
                command[:60] + "..." if len(command) > 60 else command,
            )
            for warning in validation_warnings:
                self._logger.warning("  - %s", warning)

            # Add helpful context for common redirection issues
            if any("redirection" in w.lower() for w in validation_warnings):
                self._logger.warning(
                    "  Common fix: Change '>N/path' to 'N>/path' (e.g., '2>/dev/null')"
                )

    def _check_template_generation_issues(
        self, command: str, validation_warnings: list
    ) -> None:
        """Check for specific issues common in template-generated commands."""
        import re

        # Check for double eval patterns
        if 'eval "eval' in command or "eval 'eval" in command:
            validation_warnings.append(
                "DOUBLE EVAL ERROR: Command contains nested eval statements"
            )

        # Check for malformed redirections (specific patterns)
        malformed_redirections = re.findall(r">\d+/", command)
        if malformed_redirections:
            validation_warnings.append(
                f"REDIRECTION ERROR: Found malformed redirections: {malformed_redirections}"
            )

        # Check for excessive command chaining (potential template concatenation issues)
        semicolon_count = command.count(";")
        if semicolon_count > 5:
            validation_warnings.append(
                f"COMPLEXITY WARNING: Command contains {semicolon_count} semicolons - consider breaking into multiple commands"
            )

        # Check for HEREDOC abuse (HEREDOC for simple commands)
        if "cat <<" in command and len(command.split("\n")) == 1:
            validation_warnings.append(
                "TEMPLATE ERROR: Using HEREDOC for single-line command - unnecessary complexity"
            )

        # Check for unescaped template variables
        template_vars = re.findall(r"\{\{[^}]+\}\}", command)
        if template_vars:
            validation_warnings.append(
                f"TEMPLATE ERROR: Unprocessed template variables: {template_vars}"
            )

        # Check for dangerous eval patterns in templates
        if re.search(r'eval\s+"[^"]*\$[^"]*"', command):
            validation_warnings.append(
                "SECURITY WARNING: eval with variable interpolation detected"
            )

        # Check for overly long single-line commands (template concatenation issue)
        if "\n" not in command and len(command) > 200:
            validation_warnings.append(
                f"READABILITY WARNING: Single-line command is {len(command)} characters - consider using multiline format"
            )
