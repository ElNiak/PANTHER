"""Mixin for standardized error handling and recovery."""

import subprocess
import traceback
from functools import wraps
from typing import Any, Callable, List, Optional


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

    def with_error_handling(
        self,
        operation: str,
        cleanup_on_error: bool = True,
    ):
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
        retry_exceptions: tuple = (Exception,),
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
