"""Service-specific command building utilities."""

import logging
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from panther.core.command_processor.command import ShellCommand
from panther.core.command_processor.command_utils import CommandUtils


class ServiceCommandBuilder:
    """Centralized command building utilities for service plugins.

    This class provides high-level methods specifically for building service
    commands, reducing duplication across service implementations.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the command builder.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    @staticmethod
    def build_command(parts: List[str]) -> str:
        """Build a command string from parts with proper escaping.

        Args:
            parts: List of command parts (binary and arguments)

        Returns:
            Properly escaped command string
        """
        # Filter out empty parts
        parts = [p for p in parts if p]

        # Use shlex to properly quote parts that need it
        quoted_parts = []
        for part in parts:
            # Don't quote if it's already quoted or contains shell operators
            if (
                (part.startswith('"') and part.endswith('"'))
                or (part.startswith("'") and part.endswith("'"))
                or any(op in part for op in ["|", ">", "<", "&", ";"])
            ):
                quoted_parts.append(part)
            else:
                quoted_parts.append(shlex.quote(part))

        return " ".join(quoted_parts)

    @staticmethod
    def build_quic_command(
        binary: str,
        role: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        certs: Optional[Dict[str, str]] = None,
        version: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        """Build a QUIC-specific command with common patterns.

        Args:
            binary: Binary name/path
            role: 'client' or 'server'
            host: Target host (for client)
            port: Port number
            certs: Certificate paths dict with 'cert_file', 'key_file', 'cert_dir'
            version: QUIC version
            extra_args: Additional arguments
            **kwargs: Other implementation-specific arguments

        Returns:
            Complete command string
        """
        parts = [binary]

        if role == "server":
            # Server-specific arguments
            if certs:
                if certs.get("cert_file"):
                    parts.extend(["-c", certs["cert_file"]])
                if certs.get("key_file"):
                    parts.extend(["-k", certs["key_file"]])
                elif certs.get("cert_dir"):
                    parts.extend(["-c", certs["cert_dir"]])

            if port:
                parts.extend(["-p", str(port)])

        else:  # client
            # Client typically has host and port as positional args
            if host:
                parts.append(host)
            if port:
                parts.append(str(port))

            if version:
                parts.extend(["-v", version])

        # Add any extra arguments
        if extra_args:
            parts.extend(extra_args)

        return ServiceCommandBuilder.build_command(parts)

    @staticmethod
    def create_service_command_structure(
        role: str,
        binary_path: str,
        working_dir: Union[str, Path],
        run_args: str,
        compile_cmd: Optional[str] = None,
        pre_compile_cmds: Optional[List[str]] = None,
        post_compile_cmds: Optional[List[str]] = None,
        pre_run_cmds: Optional[List[str]] = None,
        post_run_cmds: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Create a complete command structure for a service.

        This method creates the full command structure expected by PANTHER's
        execution system, with all phases properly initialized.

        Args:
            role: Service role (client/server)
            binary_path: Path to the service binary
            working_dir: Working directory for execution
            run_args: Arguments for the run command
            compile_cmd: Compilation command
            pre_compile_cmds: Pre-compilation commands
            post_compile_cmds: Post-compilation commands
            pre_run_cmds: Pre-run commands
            post_run_cmds: Post-run commands
            environment: Environment variables
            timeout: Execution timeout

        Returns:
            Complete command structure dictionary
        """
        # Start with basic structure
        command_dict = CommandUtils.generate_basic_service_commands()

        # Add compilation commands
        if pre_compile_cmds:
            command_dict[
                "pre_compile_cmds"
            ] = CommandUtils.create_shell_commands_from_list(pre_compile_cmds)

        if compile_cmd:
            command_dict["compile_cmds"] = [ShellCommand.from_string(compile_cmd)]

        if post_compile_cmds:
            command_dict[
                "post_compile_cmds"
            ] = CommandUtils.create_shell_commands_from_list(post_compile_cmds)

        # Add pre-run commands
        if pre_run_cmds:
            command_dict["pre_run_cmds"] = CommandUtils.create_shell_commands_from_list(
                pre_run_cmds
            )

        # Add main run command
        command_dict["run_cmd"] = CommandUtils.create_run_command(
            working_dir=working_dir,
            command_binary=binary_path,
            command_args=run_args,
            timeout=timeout,
            environment=environment or {},
        )

        # Add post-run commands
        if post_run_cmds:
            command_dict[
                "post_run_cmds"
            ] = CommandUtils.create_shell_commands_from_list(post_run_cmds)

        # Validate the structure
        CommandUtils.validate_command_structure(command_dict)

        return command_dict

    @staticmethod
    def add_logging_to_command(
        command: str,
        log_file: Optional[str] = None,
        log_level: str = "info",
        append: bool = False,
    ) -> str:
        """Add logging redirection to a command.

        Args:
            command: Base command
            log_file: Log file path
            log_level: Log level (for commands that support it)
            append: Whether to append to log file

        Returns:
            Command with logging
        """
        if not log_file:
            return command

        redirect_op = ">>" if append else ">"

        # Add logging based on common patterns
        if " 2>&1" not in command:
            # Redirect both stdout and stderr to log file
            return f"{command} {redirect_op} {shlex.quote(log_file)} 2>&1"
        else:
            # Command already has redirection, just update the file
            return command.replace(
                "2>&1", f"{redirect_op} {shlex.quote(log_file)} 2>&1"
            )

    @staticmethod
    def create_certificate_generation_command(
        cert_dir: str,
        cert_name: str = "cert",
        key_name: str = "key",
        common_name: str = "localhost",
        days: int = 365,
    ) -> str:
        """Create an OpenSSL command to generate certificates.

        Args:
            cert_dir: Directory to store certificates
            cert_name: Certificate file name (without extension)
            key_name: Key file name (without extension)
            common_name: Common name for the certificate
            days: Certificate validity in days

        Returns:
            OpenSSL command string
        """
        cert_path = shlex.quote(f"{cert_dir}/{cert_name}.pem")
        key_path = shlex.quote(f"{cert_dir}/{key_name}.pem")

        return (
            f"openssl req -x509 -newkey rsa:4096 -nodes "
            f"-keyout {key_path} -out {cert_path} "
            f"-days {days} -subj '/CN={common_name}'"
        )

    @staticmethod
    def create_network_namespace_command(
        command: str,
        namespace: str,
        use_sudo: bool = True,
    ) -> str:
        """Wrap a command to run in a network namespace.

        Args:
            command: Command to wrap
            namespace: Network namespace name
            use_sudo: Whether to use sudo

        Returns:
            Wrapped command
        """
        prefix = "sudo " if use_sudo else ""
        return f"{prefix}ip netns exec {shlex.quote(namespace)} {command}"

    @staticmethod
    def create_resource_limit_command(
        command: str,
        memory_mb: Optional[int] = None,
        cpu_percent: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> str:
        """Add resource limits to a command.

        Args:
            command: Base command
            memory_mb: Memory limit in MB
            cpu_percent: CPU limit as percentage
            timeout_seconds: Timeout in seconds

        Returns:
            Command with resource limits
        """
        parts = []

        # Add timeout
        if timeout_seconds:
            parts.append(f"timeout {timeout_seconds}s")

        # Add memory limit (using ulimit)
        if memory_mb:
            memory_kb = memory_mb * 1024
            parts.append(f"( ulimit -v {memory_kb} && {command} )")
            return " ".join(parts)

        parts.append(command)
        return " ".join(parts)
