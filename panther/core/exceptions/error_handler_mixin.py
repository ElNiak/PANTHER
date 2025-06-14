"""
Error Handler Mixin

This module provides a mixin for standardized error handling patterns,
reducing duplication of error handling and logging logic.
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from panther.core.utils.logging_mixin import LoggerMixin


class ErrorHandlerMixin(LoggerMixin):
    """
    Mixin that provides standardized error handling patterns.

    Reduces duplication of try-except blocks and error logging across the codebase.
    """

    def handle_error(
        self,
        error: Exception,
        operation: str,
        reraise: bool = True,
        emit_event: bool = True,
        log_level: str = "error",
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Handle an error with logging and optional event emission.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
            reraise: Whether to re-raise the exception
            emit_event: Whether to emit an error event
            log_level: Logging level to use (error, warning, info)
            additional_context: Additional context for logging/events
        """
        # Build error message
        error_msg = f"Failed to {operation}: {type(error).__name__}: {str(error)}"

        # Log the error
        logger_method = getattr(self.logger, log_level, self.logger.error)
        if log_level == "error":
            logger_method(error_msg, exc_info=True)
        else:
            logger_method(error_msg)

        # Emit error event if requested
        if emit_event and hasattr(self, "event_emitter") and self.event_emitter:
            # If the object has an event emitter, use it to emit error events
            # Use the correct method name for service event emitter
            if hasattr(self.event_emitter, "emit_service_error"):
                self.event_emitter.emit_service_error(
                    service_id=getattr(self, "service_name", self.__class__.__name__),
                    service_name=getattr(self, "service_name", self.__class__.__name__),
                    error_type=type(error).__name__,
                    error_message=error_msg,
                    details={
                        "operation": operation,
                        "error": str(error),
                        "additional_context": additional_context or {},
                    },
                )
            elif hasattr(self.event_emitter, "emit_error"):
                # Fallback for other event emitters
                self.event_emitter.emit_error(
                    error_message=error_msg,
                    error_type=type(error).__name__,
                    error_details={
                        "operation": operation,
                        "error": str(error),
                        "additional_context": additional_context or {},
                    },
                )

        # Re-raise if requested
        if reraise:
            raise error

    def safe_execute(
        self,
        operation: Callable,
        operation_name: str,
        default_return: Any = None,
        error_return: Any = None,
        allowed_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        emit_event: bool = True,
        **kwargs,
    ) -> Any:
        """
        Safely execute an operation with error handling.

        Args:
            operation: The callable to execute
            operation_name: Name of the operation for logging
            default_return: Default return value if operation succeeds
            error_return: Return value if operation fails
            allowed_exceptions: Tuple of exceptions to catch (default: Exception)
            emit_event: Whether to emit error events
            **kwargs: Arguments to pass to the operation

        Returns:
            Result of operation or error_return on failure
        """
        allowed_exceptions = allowed_exceptions or (Exception,)

        try:
            result = operation(**kwargs)
            return result if result is not None else default_return
        except allowed_exceptions as e:
            self.handle_error(e, operation_name, reraise=False, emit_event=emit_event)
            return error_return

    def with_error_handling(
        self,
        operation_name: Optional[str] = None,
        reraise: bool = True,
        emit_event: bool = True,
        allowed_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        error_return: Any = None,
        transform_error: Optional[Type[Exception]] = None,
    ):
        """
        Decorator for methods with standardized error handling.

        Usage:
            @with_error_handling("initialization")
            def initialize(self):
                # method implementation

        Args:
            operation_name: Name of operation (defaults to method name)
            reraise: Whether to re-raise exceptions
            emit_event: Whether to emit error events
            allowed_exceptions: Exceptions to catch
            error_return: Value to return on error (if not reraising)
            transform_error: Transform caught exception to this type
        """
        allowed_exceptions = allowed_exceptions or (Exception,)

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                op_name = operation_name or func.__name__.replace("_", " ")

                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    self.handle_error(e, op_name, reraise=False, emit_event=emit_event)

                    if transform_error:
                        raise transform_error(f"Failed to {op_name}: {str(e)}") from e
                    elif reraise:
                        raise
                    else:
                        return error_return

            return wrapper

        return decorator

    def log_and_reraise(
        self,
        error: Exception,
        context: str,
        error_type: Optional[Type[Exception]] = None,
    ) -> None:
        """
        Log an error and re-raise it, optionally as a different type.

        Args:
            error: The original exception
            context: Context for the error message
            error_type: Optional exception type to raise instead
        """
        self.logger.error(
            f"{context}: {type(error).__name__}: {str(error)}", exc_info=True
        )

        if error_type and not isinstance(error, error_type):
            raise error_type(f"{context}: {str(error)}") from error
        else:
            raise error

    def handle_multiple_errors(
        self,
        operations: List[Tuple[Callable, str, Dict[str, Any]]],
        continue_on_error: bool = False,
        collect_errors: bool = True,
    ) -> Tuple[List[Any], List[Exception]]:
        """
        Execute multiple operations with error handling.

        Args:
            operations: List of (callable, name, kwargs) tuples
            continue_on_error: Whether to continue after an error
            collect_errors: Whether to collect all errors

        Returns:
            Tuple of (results, errors)
        """
        results = []
        errors = []

        for operation, name, kwargs in operations:
            try:
                result = operation(**kwargs)
                results.append(result)
            except Exception as e:
                self.handle_error(
                    e, name, reraise=not continue_on_error, emit_event=True
                )

                if collect_errors:
                    errors.append(e)

                if continue_on_error:
                    results.append(None)
                else:
                    break

        return results, errors

    def create_error_context(
        self, operation: str, phase: Optional[str] = None, **additional_fields
    ) -> Dict[str, Any]:
        """
        Create a standardized error context dictionary.

        Args:
            operation: The operation being performed
            phase: Optional phase of the operation
            **additional_fields: Additional context fields

        Returns:
            Error context dictionary
        """
        context = {
            "operation": operation,
            "component": self.__class__.__name__,
        }

        if phase:
            context["phase"] = phase

        context.update(additional_fields)

        return context
