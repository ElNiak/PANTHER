"""
Event Emitter Mixin

This module provides a mixin for standardized event emission patterns,
reducing duplication across components that emit events.
"""

from typing import Any
from datetime import datetime

from panther.core.utils.logging_mixin import LoggerMixin


class EventEmitterMixin(LoggerMixin):
    """
    Mixin that provides common event emission patterns.

    Reduces duplication of event emission logic across managers and components.
    """

    def emit_event_safely(
        self, event_method: callable, *args, error_context: str = "emit event", **kwargs
    ) -> bool:
        """
        Safely emit an event with error handling.

        Args:
            event_method: The event emitter method to call
            *args: Positional arguments for the event method
            error_context: Context string for error messages
            **kwargs: Keyword arguments for the event method

        Returns:
            bool: True if event was emitted successfully
        """
        if not hasattr(self, "event_emitter") or not self.event_emitter:
            self.logger.debug(f"No event emitter available to {error_context}")
            return False

        try:
            event_method(*args, **kwargs)
            return True
        except Exception as e:
            self.logger.warning(f"Failed to {error_context}: {type(e).__name__}: {str(e)}")
            return False

    def emit_lifecycle_event(
        self,
        event_type: str,
        entity_name: str | None = None,
        details: dict[str, Any] | None = None,
        reason: str | None = None,
        error: Exception | None = None,
    ) -> bool:
        """
        Emit a lifecycle event (initialized, started, completed, failed).

        Args:
            event_type: Type of event (initialized, started, completed, failed)
            entity_name: Name of the entity (defaults to class name)
            details: Additional event details
            reason: Reason for the event (primarily for failures)
            error: Exception object if event is a failure

        Returns:
            bool: True if event was emitted successfully
        """
        if not hasattr(self, "event_emitter") or not self.event_emitter:
            return False

        entity_name = entity_name or self.__class__.__name__
        base_details = {
            "entity": entity_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if details:
            base_details.update(details)

        # Handle different event types
        event_method_name = f"emit_{event_type}"
        event_method = getattr(self.event_emitter, event_method_name, None)

        if not event_method:
            self.logger.warning(f"Event method '{event_method_name}' not found")
            return False

        # Build kwargs based on event type
        kwargs = {"details": base_details}

        if event_type == "failed" and (reason or error):
            kwargs["reason"] = reason or str(error)
            if error:
                base_details["error_type"] = type(error).__name__
                base_details["error_message"] = str(error)

        return self.emit_event_safely(
            event_method, error_context=f"emit {event_type} event", **kwargs
        )

    def emit_phase_event(
        self,
        phase: str,
        status: str,
        entity_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Emit a phase-based event (setup_started, setup_completed, etc.).

        Args:
            phase: Phase name (setup, preparation, execution, teardown)
            status: Status (started, completed, failed)
            entity_type: Type of entity (defaults to lowercase class name)
            metadata: Additional metadata for the event

        Returns:
            bool: True if event was emitted successfully
        """
        if not hasattr(self, "event_emitter") or not self.event_emitter:
            return False

        entity_type = entity_type or self.__class__.__name__.lower()

        # Build event method name
        event_method_name = f"notify_{phase}_{status}"

        # Try entity-specific method first
        event_method = None
        if hasattr(self.event_emitter, event_method_name):
            event_method = getattr(self.event_emitter, event_method_name)
        # Fallback to generic emit method
        elif hasattr(self.event_emitter, "emit"):
            event_method = self.event_emitter.emit

        if not event_method:
            self.logger.debug(f"No event method found for {phase}_{status}")
            return False

        details = {
            "phase": phase,
            "status": status,
            "entity_type": entity_type,
            "instance": self.__class__.__name__,
        }

        if metadata:
            details.update(metadata)

        return self.emit_event_safely(
            event_method, error_context=f"emit {phase} {status} event", details=details
        )

    def emit_error_event(
        self,
        operation: str,
        error: Exception,
        phase: str | None = None,
        additional_details: dict[str, Any] | None = None,
    ) -> bool:
        """
        Emit an error event with standardized error details.

        Args:
            operation: Operation that failed
            error: The exception that occurred
            phase: Optional phase where error occurred
            additional_details: Additional context

        Returns:
            bool: True if event was emitted successfully
        """
        details = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "entity": self.__class__.__name__,
        }

        if phase:
            details["phase"] = phase

        if additional_details:
            details.update(additional_details)

        # Try to emit via failed event
        if hasattr(self, "event_emitter") and self.event_emitter:
            if hasattr(self.event_emitter, "emit_failed"):
                return self.emit_event_safely(
                    self.event_emitter.emit_failed,
                    reason=f"{operation} failed: {str(error)}",
                    details=details,
                    error_context="emit error event",
                )
            elif hasattr(self.event_emitter, "emit_finished_early"):
                return self.emit_event_safely(
                    self.event_emitter.emit_finished_early,
                    reason=f"{operation} Error: {type(error).__name__}",
                    details=details,
                    error_context="emit error event",
                )

        return False

    def with_event_emission(
        self,
        operation: str,
        phase: str | None = None,
        emit_start: bool = True,
        emit_complete: bool = True,
        emit_error: bool = True,
    ):
        """
        Decorator for methods to automatically emit events.

        Usage:
            @self.with_event_emission("initialization")
            def initialize(self):
                # method implementation

        Args:
            operation: Name of the operation
            phase: Optional phase name
            emit_start: Whether to emit start event
            emit_complete: Whether to emit completion event
            emit_error: Whether to emit error event on exception
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                # Emit start event
                if emit_start:
                    self.emit_lifecycle_event(
                        "started", details={"operation": operation, "phase": phase}
                    )

                try:
                    # Execute the function
                    result = func(*args, **kwargs)

                    # Emit completion event
                    if emit_complete:
                        self.emit_lifecycle_event(
                            "completed", details={"operation": operation, "phase": phase}
                        )

                    return result

                except Exception as e:
                    # Emit error event
                    if emit_error:
                        self.emit_error_event(operation, e, phase)
                    raise

            return wrapper

        return decorator
