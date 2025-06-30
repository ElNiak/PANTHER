from typing import Any, Callable, Dict, List, Optional, Tuple, Type

"""Mixin for standardized error handling and recovery."""

import re
import subprocess
import traceback
from functools import wraps

from panther.core.exceptions.fast_fail import (
    CertificateException,
    ConfigurationException,
    DependencyException,
    DockerComposeException,
    ErrorCategory,
    ErrorSeverity,
    IvyCompilationException,
    NetworkSetupException,
    PantherException,
    PortConflictException,
    ResourceExhaustionException,
    ServiceStartException,
    TimeoutCascadeException,
)


class ErrorHandlerMixin:
    """

    Mixin providing standardized error handling and recovery mechanisms.

    This mixin eliminates duplicated error handling patterns across network environments.
    """

    def handle_deployment_error(
        self,
        error: Exception,
        cleanup_func: Optional[Callable] = None,
        context: str = "deployment",
    ) -> None:
        """
        Handle deployment errors with consistent logging and optional cleanup.

        Args:
            error: The exception that occurred
            cleanup_func: Optional cleanup function to call
            context: Context description for error messages
        """
        # Log the error with full context
        self.logger.error(f"Error during {context}: {type(error).__name__}: {error}")

        # Log additional details for specific error types
        if isinstance(error, subprocess.CalledProcessError):
            self.logger.error(f"Command failed: {' '.join(error.cmd)}")
            if error.stderr:
                self.logger.error(f"Error output: {error.stderr}")
            if error.stdout:
                self.logger.debug(f"Standard output: {error.stdout}")

        # Log full traceback at debug level
        self.logger.debug(f"Full traceback:\n{traceback.format_exc()}")

        # Attempt cleanup if function provided
        if cleanup_func:
            try:
                self.logger.info(f"Attempting cleanup after {context} error")
                cleanup_func()
            except Exception as cleanup_error:
                self.logger.error(f"Cleanup failed: {cleanup_error}")

    def safe_cleanup(self, *cleanup_functions: Callable) -> None:
        """
        Execute multiple cleanup functions safely without raising exceptions.

        Args:
            *cleanup_functions: Variable number of cleanup functions to execute
        """
        for func in cleanup_functions:
            try:
                func_name = getattr(func, "__name__", str(func))
                self.logger.debug(f"Executing cleanup function: {func_name}")
                func()
            except Exception as e:
                self.logger.error(f"Cleanup function {func_name} failed: {e}")
                # Continue with other cleanup functions

    def with_error_handling(self, operation: str, cleanup_on_error: bool = True):
        """
        Decorator for methods that need consistent error handling.

        Args:
            operation: Description of the operation being performed
            cleanup_on_error: Whether to call cleanup on error
        """

        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                try:
                    self.logger.info(f"Starting {operation}")
                    result = func(self, *args, **kwargs)
                    self.logger.info(f"Completed {operation} successfully")
                    return result
                except Exception as e:
                    self.handle_deployment_error(
                        e,
                        cleanup_func=self._safe_cleanup if cleanup_on_error else None,
                        context=operation,
                    )
                    raise

            return wrapper

        return decorator

    def safe_docker_cleanup(self, container_name: str) -> None:
        """
        Safely clean up Docker containers and images.

        Args:
            container_name: Name of the container to clean up
        """
        cleanup_commands = [
            (["docker", "stop", container_name], "stop container"),
            (["docker", "rm", "--force", container_name], "remove container"),
            (["docker", "rmi", "--force", f"{container_name}:latest"], "remove image"),
        ]

        for command, description in cleanup_commands:
            try:
                self.logger.debug(f"Attempting to {description}: {container_name}")
                if hasattr(self, "execute_command"):
                    self.execute_command(command, check=False, timeout=30)
                else:
                    subprocess.run(command, capture_output=True, text=True, timeout=30)
                self.logger.debug(f"Successfully {description}")
            except Exception as e:
                self.logger.debug(f"Failed to {description}: {e}")
                # Continue with next cleanup command

    def safe_process_cleanup(self, processes: List[subprocess.Popen]) -> None:
        """
        Safely terminate a list of processes.

        Args:
            processes: List of Popen objects to terminate
        """
        for proc in processes:
            if proc and proc.poll() is None:
                try:
                    self.logger.debug(f"Terminating process {proc.pid}")
                    proc.terminate()

                    # Wait for graceful termination
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.logger.debug(f"Force killing process {proc.pid}")
                        proc.kill()
                        proc.wait()

                    # Close log files if they exist
                    if hasattr(proc, "_log_files"):
                        for file_handle in proc._log_files:
                            try:
                                file_handle.close()
                            except Exception:
                                pass

                except Exception as e:
                    self.logger.error(f"Error terminating process {proc.pid}: {e}")

    def retry_on_error(
        self,
        func: Callable,
        max_retries: int = 3,
        retry_exceptions: tuple = (Exception),
        delay: int = 5,
        context: str = "operation",
    ) -> Any:
        """
        Retry a function on specified exceptions.

        Args:
            func: Function to execute
            max_retries: Maximum number of retries
            retry_exceptions: Tuple of exceptions to retry on
            delay: Delay between retries in seconds
            context: Context description for logging

        Returns:
            Result of successful function execution

        Raises:
            The last exception if all retries fail
        """
        import time

        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func()
            except retry_exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    self.logger.warning(
                        f"{context} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    self.logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    self.logger.error(
                        f"{context} failed after {max_retries + 1} attempts: {e}"
                    )

        raise last_exception

    def ensure_cleanup_on_exit(self, cleanup_func: Callable) -> None:
        """
        Register a cleanup function to be called on exit.

        Args:
            cleanup_func: Function to call on exit
        """
        import atexit

        def wrapped_cleanup():
            try:
                cleanup_func()
            except Exception as e:
                self.logger.error(f"Exit cleanup failed: {e}")

        atexit.register(wrapped_cleanup)


class ErrorClassifier:
    """Classify subprocess errors and map them to appropriate PantherException types."""

    # Error patterns mapping to exception types and context extractors
    ERROR_PATTERNS = {
        # Port conflicts
        r".*address already in use.*": (
            PortConflictException,
            {"port": r":(\d+)", "service": r"service[_=](\w+)"},
        ),
        r".*bind.*failed.*port.*": (
            PortConflictException,
            {"port": r"port[_= ](\d+)", "service": None},
        ),
        # Disk space issues
        r".*no space left on device.*": (
            ResourceExhaustionException,
            {
                "resource_type": lambda m: "disk_space",
                "current_value": None,
                "threshold": None,
            },
        ),
        r".*insufficient disk space.*": (
            ResourceExhaustionException,
            {
                "resource_type": lambda m: "disk_space",
                "current_value": r"(\d+\.?\d*)\s*[GM]B",
                "threshold": None,
            },
        ),
        # Certificate issues
        r".*certificate.*failed.*": (
            CertificateException,
            {"cert_path": r"(?:cert|certificate)[_= ]([\/\w\-\.]+)", "error": None},
        ),
        r".*certificate.*expired.*": (
            CertificateException,
            {
                "cert_path": r"(?:cert|certificate)[_= ]([\/\w\-\.]+)",
                "error": lambda m: "Certificate expired",
            },
        ),
        r".*certificate.*not found.*": (
            CertificateException,
            {
                "cert_path": r"(?:cert|certificate)[_= ]([\/\w\-\.]+)",
                "error": lambda m: "Certificate not found",
            },
        ),
        # Ivy compilation
        r".*ivy.*compilation failed.*": (
            IvyCompilationException,
            {
                "test_name": r"test[_=](\w+)",
                "output": None,
                "exit_code": r"exit[_= ]code[_= ](\d+)",
            },
        ),
        r".*ivyc.*error.*": (
            IvyCompilationException,
            {"test_name": r"compiling[_= ](\w+)", "output": None, "exit_code": None},
        ),
        # Timeout issues
        r".*timeout.*exceeded.*": (
            TimeoutCascadeException,
            {"count": lambda m: 1, "services": r"service[_=](\w+)"},
        ),
        r".*operation timed out.*": (
            TimeoutCascadeException,
            {"count": lambda m: 1, "services": None},
        ),
        # Docker/container issues
        r".*docker.*daemon.*not.*running.*": (
            DockerComposeException,
            {
                "command": None,
                "returncode": lambda m: -1,
                "stdout": None,
                "stderr": lambda m: "Docker daemon not running",
            },
        ),
        r".*docker-compose.*failed.*": (
            DockerComposeException,
            {
                "command": r"command[_= ](.+)",
                "returncode": r"code[_= ](\d+)",
                "stdout": None,
                "stderr": None,
            },
        ),
        # Network setup issues
        r".*network.*setup.*failed.*": (
            NetworkSetupException,
            {"network_type": r"network[_= ]type[_= ](\w+)", "details": None},
        ),
        r".*failed to create network.*": (
            NetworkSetupException,
            {"network_type": lambda m: "docker", "details": None},
        ),
        # Service start issues
        r".*service.*failed to start.*": (
            ServiceStartException,
            {"service_name": r"service[_= ](\w+)"},
        ),
        r".*container.*failed to start.*": (
            ServiceStartException,
            {"service_name": r"container[_= ](\w+)"},
        ),
        # Configuration issues
        r".*invalid configuration.*": (
            ConfigurationException,
            {
                "config_file": r"file[_= ]([\/\w\-\.]+)",
                "field": r"field[_= ](\w+)",
                "validation_error": None,
            },
        ),
        r".*configuration.*not found.*": (
            ConfigurationException,
            {
                "config_file": r"file[_= ]([\/\w\-\.]+)",
                "field": None,
                "validation_error": lambda m: "Configuration file not found",
            },
        ),
        # Dependency issues
        r".*dependency.*not found.*": (
            DependencyException,
            {
                "dependency": r"dependency[_= ](\w+)",
                "required_version": r"version[_= ]([\d\.]+)",
                "found_version": lambda m: None,
            },
        ),
        r".*version.*mismatch.*": (
            DependencyException,
            {
                "dependency": r"package[_= ](\w+)",
                "required_version": r"required[_= ]([\d\.]+)",
                "found_version": r"found[_= ]([\d\.]+)",
            },
        ),
    }

    @classmethod
    def classify_error(
        cls,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        command: Optional[str] = None,
        returncode: Optional[int] = None,
    ) -> Optional[PantherException]:
        """
        Classify an error message and return appropriate PantherException.

        Args:
            error_message: The error message to classify
            context: Additional context information
            command: The command that failed (if applicable)
            returncode: The return code (if applicable)

        Returns:
            Appropriate PantherException or None if no match found
        """
        context = context or {}

        # Normalize error message
        error_lower = error_message.lower()

        # Try to match against patterns
        for pattern, (exc_class, extractors) in cls.ERROR_PATTERNS.items():
            match = re.search(pattern, error_lower, re.IGNORECASE | re.DOTALL)
            if match:
                # Extract context from error message
                extracted = cls._extract_context(error_message, extractors, match)

                # Merge with provided context
                full_context = {**context, **extracted}

                # Add command and returncode if available
                if command:
                    full_context["command"] = command
                if returncode is not None:
                    full_context["returncode"] = returncode

                # Create appropriate exception
                return cls._create_exception(exc_class, error_message, full_context)

        return None

    @classmethod
    def _extract_context(
        cls, error_message: str, extractors: Dict[str, Any], match: re.Match
    ) -> Dict[str, Any]:
        """Extract context from error message using patterns or functions."""
        extracted = {}

        for key, extractor in extractors.items():
            if extractor is None:
                continue

            if callable(extractor):
                # Extractor is a function
                value = extractor(match)
                if value is not None:
                    extracted[key] = value
            else:
                # Extractor is a regex pattern
                pattern_match = re.search(extractor, error_message, re.IGNORECASE)
                if pattern_match:
                    extracted[key] = pattern_match.group(1)

        return extracted

    @classmethod
    def _create_exception(
        cls, exc_class: Type[PantherException], message: str, context: Dict[str, Any]
    ) -> PantherException:
        """Create the appropriate exception instance."""
        # Map exception classes to their required parameters
        if exc_class == DockerComposeException:
            return exc_class(
                message,
                context.get("command", ""),
                context.get("returncode", -1),
                context.get("stdout", ""),
                context.get("stderr", ""),
            )

        elif exc_class == PortConflictException:
            return exc_class(
                message, int(context.get("port", 0)), context.get("service", "unknown")
            )

        elif exc_class == ResourceExhaustionException:
            return exc_class(
                message,
                context.get("resource_type", "unknown"),
                float(context.get("current_value", 0)),
                float(context.get("threshold", 0)),
            )

        elif exc_class == CertificateException:
            return exc_class(
                message,
                context.get("cert_path", ""),
                context.get("error", "Unknown certificate error"),
            )

        elif exc_class == IvyCompilationException:
            return exc_class(
                message,
                context.get("test_name", ""),
                context.get("output", ""),
                int(context.get("exit_code", -1)),
            )

        elif exc_class == TimeoutCascadeException:
            services = context.get("services", "")
            if isinstance(services, str):
                services = [services] if services else []
            return exc_class(message, int(context.get("count", 1)), services)

        elif exc_class == NetworkSetupException:
            return exc_class(
                message,
                context.get("network_type", "unknown"),
                context.get("details", ""),
            )

        elif exc_class == ServiceStartException:
            return exc_class(message, context.get("service_name", "unknown"))

        elif exc_class == ConfigurationException:
            return exc_class(
                message,
                context.get("config_file", ""),
                context.get("field", ""),
                context.get("validation_error", ""),
            )

        elif exc_class == DependencyException:
            return exc_class(
                message,
                context.get("dependency", ""),
                context.get("required_version", ""),
                context.get("found_version"),
            )

        else:
            # Fallback for any other PantherException subclass
            return exc_class(
                message, ErrorSeverity.MEDIUM, ErrorCategory.COMMAND_EXECUTION, context
            )

    @classmethod
    def classify_subprocess_error(
        cls,
        error: subprocess.CalledProcessError,
        context: Optional[Dict[str, Any]] = None,
    ) -> PantherException:
        """
        Classify a subprocess.CalledProcessError into appropriate PantherException.

        Args:
            error: The subprocess error
            context: Additional context

        Returns:
            Appropriate PantherException
        """
        # Try stderr first, then stdout
        error_message = error.stderr or error.stdout or str(error)

        # Try to classify the error
        classified = cls.classify_error(
            error_message,
            context,
            " ".join(error.cmd) if isinstance(error.cmd, list) else str(error.cmd),
            error.returncode,
        )

        if classified:
            return classified

        # Default to DockerComposeException for docker-related commands
        cmd_str = " ".join(error.cmd) if isinstance(error.cmd, list) else str(error.cmd)
        if "docker" in cmd_str.lower():
            return DockerComposeException(
                f"Docker command failed: {error_message}",
                cmd_str,
                error.returncode,
                error.stdout or "",
                error.stderr or "",
            )

        # Generic service start exception for other failures
        return ServiceStartException(
            f"Command failed: {error_message}", context.get("service_name", "unknown")
        )
