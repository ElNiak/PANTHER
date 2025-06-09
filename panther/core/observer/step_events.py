"""
Step Event Types Module

This module defines event types related to test step execution
to integrate the step execution system with the event infrastructure.
"""

from typing import Any

from panther.core.observer.core.core_events import Event


class StepEvent(Event):
    """
    Step execution related events like start, completion, failure, etc.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new StepEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"step.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for StepEvents has the 'step.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name

    def validate(self) -> bool:
        """
        Validate step event data.

        Returns:
            bool: True if the event data is valid
        """
        return True


class StepExecutionStartedEvent(StepEvent):
    """
    Event triggered when step execution begins.
    """

    def __init__(self, step_name: str, step_type: str, data: dict[str, Any] = None):
        """
        Initialize a step execution started event.

        Args:
            step_name: Name of the step being executed
            step_type: Type of step (e.g., 'command', 'assertion')
            data: Additional event data
        """
        event_data = data or {}
        event_data["step_name"] = step_name
        event_data["step_type"] = step_type
        super().__init__("execution_started", event_data)

    def validate(self) -> bool:
        """Validate that step_name and step_type are present."""
        return (
            "step_name" in self.data
            and bool(self.data["step_name"])
            and "step_type" in self.data
            and bool(self.data["step_type"])
        )


class StepExecutionCompletedEvent(StepEvent):
    """
    Event triggered when step execution completes successfully.
    """

    def __init__(
        self, step_name: str, step_type: str, result: Any = None, data: dict[str, Any] = None
    ):
        """
        Initialize a step execution completed event.

        Args:
            step_name: Name of the step that completed
            step_type: Type of step (e.g., 'command', 'assertion')
            result: Result of the step execution
            data: Additional event data
        """
        event_data = data or {}
        event_data["step_name"] = step_name
        event_data["step_type"] = step_type
        if result is not None:
            event_data["result"] = result
        super().__init__("execution_completed", event_data)

    def validate(self) -> bool:
        """Validate that step_name and step_type are present."""
        return (
            "step_name" in self.data
            and bool(self.data["step_name"])
            and "step_type" in self.data
            and bool(self.data["step_type"])
        )


class StepUnsupportedEvent(StepEvent):
    """
    Event triggered when a step type is not supported.
    """

    def __init__(self, step_name: str, step_type: str, reason: str, data: dict[str, Any] = None):
        """
        Initialize a step unsupported event.

        Args:
            step_name: Name of the unsupported step
            step_type: Type of step that is unsupported
            reason: Reason why the step is unsupported
            data: Additional event data
        """
        event_data = data or {}
        event_data["step_name"] = step_name
        event_data["step_type"] = step_type
        event_data["reason"] = reason
        super().__init__("unsupported", event_data)

    def validate(self) -> bool:
        """Validate that step_name, step_type, and reason are present."""
        return (
            "step_name" in self.data
            and bool(self.data["step_name"])
            and "step_type" in self.data
            and bool(self.data["step_type"])
            and "reason" in self.data
            and bool(self.data["reason"])
        )
