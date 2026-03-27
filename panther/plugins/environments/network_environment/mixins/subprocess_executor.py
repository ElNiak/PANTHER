"""Mixin for standardized subprocess execution with logging."""

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.exceptions.fast_fail import DockerComposeException


@dataclass
class CommandResult:
    """Result of a subprocess command execution."""

    returncode: int
    stdout: str
    stderr: str
    duration: float
    command: List[str]


class SubprocessExecutorMixin:
    """Mixin providing standardized subprocess execution with consistent error handling and logging.

    This mixin eliminates duplicated subprocess execution patterns across network environments.
    """

    def execute_command(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        capture_output: bool = True,
        check: bool = True,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        log_prefix: Optional[str] = None,
    ) -> CommandResult:
        """Execute a command with standardized error handling and logging.

        Args:
            command: Command and arguments to execute
            timeout: Command timeout in seconds
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise exception on non-zero return code
            cwd: Working directory for command execution
            env: Environment variables for command
            log_prefix: Prefix for log files (e.g., "docker_build")

        Returns:
            CommandResult with execution details

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
            subprocess.TimeoutExpired: If command exceeds timeout
            ValueError: If command contains security risks
        """
        # Input validation for security
        if not command:
            raise ValueError("Command cannot be empty")

        if not isinstance(command, list):
            raise ValueError("Command must be a list of strings, not a single string")

        # Check for potentially dangerous command patterns
        for cmd_part in command:
            if not isinstance(cmd_part, str):
                raise ValueError(
                    f"All command parts must be strings, got {type(cmd_part)}"
                )

        start_time = time.time()

        # Log command execution
        self.logger.debug(f"Executing command: {' '.join(command)}")
        if cwd:
            self.logger.debug(f"Working directory: {cwd}")

        try:
            # Execute command
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,  # We'll handle the check ourselves
                cwd=cwd,
                env=env,
            )

            duration = time.time() - start_time

            # Log output if prefix provided
            if log_prefix and hasattr(self, "output_dir"):
                self._write_command_logs(log_prefix, result.stdout, result.stderr)

            # Create CommandResult
            cmd_result = CommandResult(
                returncode=result.returncode,
                stdout=result.stdout if capture_output else "",
                stderr=result.stderr if capture_output else "",
                duration=duration,
                command=command,
            )

            # Check return code if requested
            if check and result.returncode != 0:
                self.logger.error(
                    f"Command failed with return code {result.returncode}: "
                    f"{' '.join(command)}"
                )
                if result.stderr:
                    self.logger.error(f"Error output: {result.stderr}")

                # Check if this is a docker-compose command that should trigger fast-fail
                if "docker-compose" in command[0] or "docker" in command[0]:
                    raise DockerComposeException(
                        f"Docker command failed with return code {result.returncode}",
                        " ".join(command),
                        result.returncode,
                        result.stdout,
                        result.stderr,
                    )
                else:
                    # Raise CalledProcessError for non-docker commands
                    raise subprocess.CalledProcessError(
                        result.returncode, command, result.stdout, result.stderr
                    )

            self.logger.debug(
                f"Command completed in {duration:.2f}s with return code {result.returncode}"
            )

            return cmd_result

        except subprocess.TimeoutExpired as e:
            self.logger.error(
                f"Command timed out after {timeout}s: {' '.join(command)}"
            )
            raise
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise

    def execute_with_retry(
        self, command: List[str], max_retries: int = 3, retry_delay: int = 5, **kwargs
    ) -> CommandResult:
        """Execute command with automatic retry logic.

        Args:
            command: Command to execute
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries
            **kwargs: Additional arguments passed to execute_command

        Returns:
            CommandResult from successful execution

        Raises:
            Exception: The last exception if all retries fail
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return self.execute_command(command, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    self.logger.warning(
                        f"Command failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {retry_delay}s: {e}"
                    )
                    time.sleep(retry_delay)
                else:
                    self.logger.error(
                        f"Command failed after {max_retries + 1} attempts"
                    )

        raise last_exception

    def execute_docker_command(
        self,
        docker_args: List[str],
        timeout: Optional[int] = 300,
        check: bool = True,
        log_prefix: Optional[str] = None,
    ) -> CommandResult:
        """Execute a Docker command with standard configuration.

        Args:
            docker_args: Arguments to pass to docker command
            timeout: Command timeout (default 5 minutes)
            check: Whether to raise exception on failure
            log_prefix: Prefix for log files

        Returns:
            CommandResult from docker command execution
        """
        command = ["docker"] + docker_args
        return self.execute_command(
            command,
            timeout=timeout,
            check=check,
            log_prefix=log_prefix or f"docker_{docker_args[0]}",
        )

    def execute_with_logging(
        self,
        command: List[str],
        stdout_file: str,
        stderr_file: str,
        timeout: Optional[int] = None,
        check: bool = True,
        **kwargs,
    ) -> CommandResult:
        """Execute command and write output to specified log files.

        This method replicates the common pattern of opening log files
        and writing command output to them.

        Args:
            command: Command to execute
            stdout_file: Path to stdout log file
            stderr_file: Path to stderr log file
            timeout: Command timeout
            check: Whether to raise exception on failure
            **kwargs: Additional arguments for execute_command

        Returns:
            CommandResult from command execution
        """
        # Debug log the file paths
        self.logger.debug(
            f"execute_with_logging called with stdout_file={stdout_file}, type={type(stdout_file)}"
        )
        self.logger.debug(
            f"execute_with_logging called with stderr_file={stderr_file}, type={type(stderr_file)}"
        )

        # Ensure log directories exist
        os.makedirs(os.path.dirname(stdout_file), exist_ok=True)
        os.makedirs(os.path.dirname(stderr_file), exist_ok=True)

        # Execute command
        result = self.execute_command(
            command,
            timeout=timeout,
            check=False,  # We'll handle the check after writing logs
            **kwargs,
        )

        # Write output to files
        with open(stdout_file, "w") as f:
            f.write(result.stdout)

        with open(stderr_file, "w") as f:
            f.write(result.stderr)

        # Log file locations
        self.logger.debug(f"Command stdout written to: {stdout_file}")
        self.logger.debug(f"Command stderr written to: {stderr_file}")

        # Check return code if requested
        if check and result.returncode != 0:
            # Check if this is a docker-compose command that should trigger fast-fail
            if "docker-compose" in command[0] or "docker" in command[0]:
                raise DockerComposeException(
                    f"Docker command failed with return code {result.returncode}",
                    " ".join(command),
                    result.returncode,
                    result.stdout,
                    result.stderr,
                )
            else:
                raise subprocess.CalledProcessError(
                    result.returncode, command, result.stdout, result.stderr
                )

        return result

    def run_background_process(
        self,
        command: List[str],
        log_prefix: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.Popen:
        """Start a process in the background with logging.

        Args:
            command: Command to execute
            log_prefix: Prefix for log files
            cwd: Working directory
            env: Environment variables

        Returns:
            Popen object for the background process
        """
        # Create log file paths
        stdout_file = os.path.join(self.output_dir, "logs", f"{log_prefix}.log")
        stderr_file = os.path.join(self.output_dir, "logs", f"{log_prefix}.err.log")

        # Ensure log directory exists
        os.makedirs(os.path.dirname(stdout_file), exist_ok=True)

        # Open log files
        stdout_handle = open(stdout_file, "w")
        stderr_handle = open(stderr_file, "w")

        self.logger.info("Starting background process: %s", " ".join(command))

        # Start process
        process = subprocess.Popen(
            command,
            stdout=stdout_handle,
            stderr=stderr_handle,
            cwd=cwd,
            env=env,
            text=True,
        )

        # Store process and file handles for cleanup
        if hasattr(self, "processes"):
            self.processes.append(process)

        # Store file handles for cleanup (if needed)
        process._log_files = (stdout_handle, stderr_handle)

        self.logger.info("Background process started with PID: %s", process.pid)

        return process

    def monitor_docker_container(
        self,
        container_name: str,
        expected_count: int = 2,
        timeout: int = 60,
        check_interval: int = 5,
    ) -> bool:
        """Monitor Docker container status.

        Args:
            container_name: Name of container to monitor
            expected_count: Expected number of lines in docker ps output
            timeout: Maximum time to wait
            check_interval: Time between checks

        Returns:
            True if container is running as expected
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = self.execute_docker_command(
                    ["ps", "-f", f"name={container_name}"],
                    check=True,
                )

                lines = result.stdout.strip().split("\n")
                if len(lines) >= expected_count:
                    self.logger.info(f"Container {container_name} is running")
                    return True

            except Exception as e:
                self.logger.debug(f"Error checking container status: {e}")

            time.sleep(check_interval)

        self.logger.error(f"Container {container_name} did not start within {timeout}s")
        return False

    def _write_command_logs(self, prefix: str, stdout: str, stderr: str) -> None:
        """Write command output to log files."""
        if not hasattr(self, "output_dir"):
            return

        log_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)

        if stdout:
            stdout_file = os.path.join(log_dir, f"{prefix}.stdout.log")
            with open(stdout_file, "w") as f:
                f.write(stdout)

        if stderr:
            stderr_file = os.path.join(log_dir, f"{prefix}.stderr.log")
            with open(stderr_file, "w") as f:
                f.write(stderr)
