from typing import Any, Callable, Dict, List, Optional, Tuple, Type

"""
Error Handler Mixin

This module provides a mixin for standardized error handling patterns,
reducing duplication of error handling and logging logic.
"""

import logging
from functools import wraps

from panther.core.exceptions.fast_fail import (
    ErrorCategory,
    ErrorSeverity,
    FastFailHandler,
    PantherException,
)


class ErrorHandlerMixin:
    """

    Mixin that provides standardized error handling patterns.

    Reduces duplication of try-except blocks and error logging across the codebase.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize FastFailHandler - can be overridden by subclasses
        self._fast_fail_handler = None
        # Initialize logger if not already present
        if not hasattr(self, "logger"):
            self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def fast_fail_handler(self) -> FastFailHandler:
        """Get or create the fast fail handler."""
        if self._fast_fail_handler is None:
            # Create a default handler with fast-fail enabled
            self._fast_fail_handler = FastFailHandler(enabled=True, logger=self.logger)
        return self._fast_fail_handler

    @fast_fail_handler.setter
    def fast_fail_handler(self, handler: FastFailHandler) -> None:
        """Set a custom fast fail handler."""
        self._fast_fail_handler = handler

    def handle_error(
        self,
        error: Exception,
        operation: str,
        reraise: bool = True,
        emit_event: bool = True,
        log_level: str = "error",
        additional_context: Optional[Dict[str, Any]] = None,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
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
            severity: Override severity level for non-PantherException errors
            category: Override category for non-PantherException errors
        """
        # Build error message
        error_msg = f"Failed to {operation}: {type(error).__name__}: {str(error)}"

        # Convert to PantherException if not already one
        if not isinstance(error, PantherException):
            # Determine severity based on log_level if not provided
            if severity is None:
                if log_level == "error":
                    severity = ErrorSeverity.HIGH
                elif log_level == "warning":
                    severity = ErrorSeverity.MEDIUM
                else:
                    severity = ErrorSeverity.LOW

            # Default category if not provided
            if category is None:
                category = ErrorCategory.COMMAND_EXECUTION

            # Create PantherException
            panther_error = PantherException(
                message=str(error),
                severity=severity,
                category=category,
                context={
                    "operation": operation,
                    "additional_context": additional_context or {},
                },
            )
        else:
            panther_error = error
            # Add operation context if not already present
            if "operation" not in panther_error.context:
                panther_error.context["operation"] = operation

        # Use FastFailHandler to determine if we should continue
        should_continue = self.fast_fail_handler.handle_error(
            panther_error, raise_on_critical=reraise
        )

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
                        "severity": panther_error.severity.name,
                        "category": panther_error.category.value,
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
                        "severity": panther_error.severity.name,
                        "category": panther_error.category.value,
                    },
                )

        # Re-raise if requested and not handled by fast-fail
        if reraise and not should_continue:
            raise error

    def safe_execute(
        self,
        operation: Callable,
        operation_name: str,
        default_return: Any = None,
        error_return: Any = None,
        allowed_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        emit_event: bool = True,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
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
            severity: Error severity for fast-fail handling
            category: Error category for fast-fail handling
            **kwargs: Arguments to pass to the operation

        Returns:
            Result of operation or error_return on failure
        """
        allowed_exceptions = allowed_exceptions or (Exception,)

        try:
            result = operation(**kwargs)
            return result if result is not None else default_return
        except allowed_exceptions as e:
            self.handle_error(
                e,
                operation_name,
                reraise=False,
                emit_event=emit_event,
                severity=severity,
                category=category,
            )
            return error_return

    def with_error_handling(
        self,
        operation_name: Optional[str] = None,
        reraise: bool = True,
        emit_event: bool = True,
        allowed_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        error_return: Any = None,
        transform_error: Optional[Type[Exception]] = None,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
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
            severity: Error severity for fast-fail handling
            category: Error category for fast-fail handling
        """
        allowed_exceptions = allowed_exceptions or (Exception,)

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                op_name = operation_name or func.__name__.replace("_", " ")

                try:
                    return func(*args, **kwargs)
                except allowed_exceptions as e:
                    self.handle_error(
                        e,
                        op_name,
                        reraise=False,
                        emit_event=emit_event,
                        severity=severity,
                        category=category,
                    )

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
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
    ) -> Tuple[List[Any], List[Exception]]:
        """
        Execute multiple operations with error handling.

        Args:
            operations: List of (callable, name, kwargs) tuples
            continue_on_error: Whether to continue after an error
            collect_errors: Whether to collect all errors
            severity: Error severity for fast-fail handling
            category: Error category for fast-fail handling

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
                    e,
                    name,
                    reraise=not continue_on_error,
                    emit_event=True,
                    severity=severity,
                    category=category,
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
