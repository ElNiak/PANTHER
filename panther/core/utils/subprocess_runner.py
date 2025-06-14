"""
Subprocess Runner Utilities

This module provides utilities for running subprocess commands with standardized
logging and error handling, reducing duplication across the codebase.
"""

import subprocess
import os
from pathlib import Path
import time

from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.exceptions import ErrorHandlerMixin


class SubprocessResult:
    """Container for subprocess execution results."""

    def __init__(
        self, returncode: int, stdout: str, stderr: str, duration: float, command: str | list[str]
    ):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.command = command

    @property
    def success(self) -> bool:
        """Check if the command executed successfully."""
        return self.returncode == 0

    def raise_for_status(self) -> None:
        """Raise an exception if the command failed."""
        if not self.success:
            raise subprocess.CalledProcessError(
                self.returncode, self.command, output=self.stdout, stderr=self.stderr
            )


class SubprocessRunner(ErrorHandlerMixin, LoggerMixin):
    """
    Utility class for running subprocess commands with consistent logging and error handling.

    Reduces duplication of subprocess execution patterns across the codebase.
    """

    def __init__(self, working_dir: str | Path | None = None):
        """
        Initialize the subprocess runner.

        Args:
            working_dir: Default working directory for commands
        """
        super().__init__()
        self.working_dir = Path(working_dir) if working_dir else Path.cwd()

    def run(
        self,
        command: str | list[str],
        working_dir: str | Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
        check: bool = False,
        capture_output: bool = True,
        log_output: bool = True,
        log_file: str | Path | None = None,
        error_log_file: str | Path | None = None,
        shell: bool = False,
        text: bool = True,
    ) -> SubprocessResult:
        """
        Run a subprocess command with logging and error handling.

        Args:
            command: Command to run (string or list of arguments)
            working_dir: Working directory (defaults to runner's working_dir)
            env: Environment variables
            timeout: Timeout in seconds
            check: Whether to raise on non-zero exit code
            capture_output: Whether to capture stdout/stderr
            log_output: Whether to log command output
            log_file: File to write stdout to
            error_log_file: File to write stderr to
            shell: Whether to run command in shell
            text: Whether to decode output as text

        Returns:
            SubprocessResult with execution details

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
            subprocess.TimeoutExpired: If command times out
        """
        working_dir = Path(working_dir) if working_dir else self.working_dir

        # Build command string for logging
        cmd_str = command if isinstance(command, str) else " ".join(command)
        self.logger.debug("Running command: %s", cmd_str)
        if working_dir != self.working_dir:
            self.logger.debug("Working directory: %s", working_dir)

        # Prepare environment
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        # Prepare arguments
        kwargs = {
            "cwd": str(working_dir),
            "env": run_env,
            "shell": shell,
            "text": text,
        }

        if capture_output:
            kwargs["capture_output"] = True

        if timeout:
            kwargs["timeout"] = timeout

        # Run the command
        start_time = time.time()
        try:
            result = subprocess.run(command, check=False, **kwargs)
            duration = time.time() - start_time

            # Extract output
            stdout = result.stdout if capture_output else ""
            stderr = result.stderr if capture_output else ""

            # Log output if requested
            if log_output and capture_output:
                if stdout and stdout.strip():
                    self.logger.debug("Command stdout:\n%s", stdout)
                if stderr and stderr.strip():
                    self.logger.warning("Command stderr:\n%s", stderr)

            # Write to log files if specified
            if log_file and stdout:
                self._write_log_file(log_file, stdout)
            if error_log_file and stderr:
                self._write_log_file(error_log_file, stderr)

            # Create result
            subprocess_result = SubprocessResult(
                returncode=result.returncode,
                stdout=stdout,
                stderr=stderr,
                duration=duration,
                command=command,
            )

            # Check if requested
            if check:
                subprocess_result.raise_for_status()

            return subprocess_result

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.logger.error("Command timed out after %s seconds: %s", timeout, cmd_str)
            raise

        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            self.logger.error(
                "Command failed with exit code %s: %s\nstdout: %s\nstderr: %s",
                e.returncode,
                cmd_str,
                e.stdout,
                e.stderr,
            )
            raise

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.handle_error(e, f"run command: {cmd_str}")

    def run_with_retry(
        self, command: str | list[str], max_attempts: int = 3, retry_delay: float = 1.0, **kwargs
    ) -> SubprocessResult:
        """
        Run a command with retry logic.

        Args:
            command: Command to run
            max_attempts: Maximum number of attempts
            retry_delay: Delay between attempts in seconds
            **kwargs: Additional arguments for run()

        Returns:
            SubprocessResult from successful execution

        Raises:
            Exception: If all attempts fail
        """
        last_exception = None

        for attempt in range(max_attempts):
            try:
                return self.run(command, **kwargs)
            except Exception as e:  # pylint: disable=broad-exception-caught
                last_exception = e
                if attempt < max_attempts - 1:
                    self.logger.warning(
                        "Attempt %s/%s failed: %s. Retrying in %s seconds...",
                        attempt + 1,
                        max_attempts,
                        e,
                        retry_delay,
                    )
                    time.sleep(retry_delay)

        raise last_exception

    def run_multiple(
        self, commands: list[str | list[str]], stop_on_error: bool = True, **kwargs
    ) -> list[SubprocessResult]:
        """
        Run multiple commands in sequence.

        Args:
            commands: List of commands to run
            stop_on_error: Whether to stop on first error
            **kwargs: Additional arguments for run()

        Returns:
            List of SubprocessResult objects
        """
        results = []

        for command in commands:
            try:
                result = self.run(command, **kwargs)
                results.append(result)
            except Exception as e:  # pylint: disable=broad-exception-caught
                if stop_on_error:
                    raise
                else:
                    # Create a failed result
                    results.append(
                        SubprocessResult(
                            returncode=-1, stdout="", stderr=str(e), duration=0.0, command=command
                        )
                    )

        return results

    def run_docker_compose(
        self, compose_file: str | Path, command: str, services: list[str] | None = None, **kwargs
    ) -> SubprocessResult:
        """
        Run a docker-compose command.

        Args:
            compose_file: Path to docker-compose.yml
            command: Docker compose command (up, down, logs, etc.)
            services: Optional list of services to target
            **kwargs: Additional arguments for run()

        Returns:
            SubprocessResult from command execution
        """
        cmd = ["docker", "compose", "-f", str(compose_file), command]

        # Add service names if specified
        if services:
            cmd.extend(services)

        return self.run(cmd, **kwargs)

    def _write_log_file(self, log_file: str | Path, content: str) -> None:
        """Write content to a log file."""
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def build_command(
        executable: str, args: list[str] | None = None, options: dict[str, str | bool] | None = None
    ) -> list[str]:
        """
        Build a command list from components.

        Args:
            executable: The executable to run
            args: Positional arguments
            options: Options/flags as key-value pairs

        Returns:
            Command as list of strings
        """
        cmd = [executable]

        # Add options
        if options:
            for key, value in options.items():
                if value is True:
                    # Boolean flag
                    cmd.append(f"--{key}")
                elif value is not False and value is not None:
                    # Option with value
                    cmd.extend([f"--{key}", str(value)])

        # Add positional arguments
        if args:
            cmd.extend(args)

        return cmd
