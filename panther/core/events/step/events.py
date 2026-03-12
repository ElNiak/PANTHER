"""Step Events.

This module defines events specific to step execution and management.
"""

from enum import Enum
from typing import Any, Dict, Optional

from panther.core.events.base.event_base import BaseEvent, EventType


class StepEventType(Enum):
    """Step-specific event types."""

    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    PROGRESS = "progress"
    UNSUPPORTED = "unsupported"
    SKIPPED = "skipped"


class StepEvent(BaseEvent):
    """Base class for all step events."""

    def __init__(
        self,
        event_type: StepEventType,
        step_id: str,
        step_name: str,
        test_case_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize step event."""
        merged_data = data or {}
        merged_data.update({"step_name": step_name, "test_case_id": test_case_id})

        super().__init__(
            name=event_type.value,
            entity_type=EventType.STEP,
            entity_id=step_id,
            data=merged_data,
        )
        self.event_type = event_type
        self.step_name = step_name
        self.test_case_id = test_case_id

    @property
    def step_name_property(self) -> str:
        """Return the step name."""
        return self.data.get("step_name", "")

    @property
    def test_case_id_property(self) -> Optional[str]:
        """Return the test case ID."""
        return self.data.get("test_case_id")


class StepExecutionStartedEvent(StepEvent):
    """Event emitted when step execution starts."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: Optional[str] = None,
        step_config: Optional[Dict[str, Any]] = None,
        prerequisites: Optional[list] = None,
    ):
        """Initialize step execution started event."""
        super().__init__(
            event_type=StepEventType.EXECUTION_STARTED,
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            data={
                "step_config": step_config or {},
                "prerequisites": prerequisites or [],
                "action": "step_execution_started",
            },
        )

    @property
    def step_config(self) -> Dict[str, Any]:
        """Return the step configuration."""
        return self.data.get("step_config", {})

    @property
    def prerequisites(self) -> list:
        """Return the prerequisites."""
        return self.data.get("prerequisites", [])


class StepExecutionCompletedEvent(StepEvent):
    """Event emitted when step execution completes successfully."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: Optional[str] = None,
        duration: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None,
        output: Optional[str] = None,
    ):
        """Initialize step execution completed event."""
        super().__init__(
            event_type=StepEventType.EXECUTION_COMPLETED,
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            data={
                "duration": duration,
                "result": result or {},
                "output": output,
                "action": "step_execution_completed",
            },
        )

    @property
    def duration(self) -> Optional[float]:
        """Return the execution duration."""
        return self.data.get("duration")

    @property
    def result(self) -> Dict[str, Any]:
        """Return the execution result."""
        return self.data.get("result", {})

    @property
    def output(self) -> Optional[str]:
        """Return the execution output."""
        return self.data.get("output")


class StepExecutionFailedEvent(StepEvent):
    """Event emitted when step execution fails."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: Optional[str] = None,
        error_message: str = "",
        error_details: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
        retry_count: int = 0,
    ):
        """Initialize step execution failed event."""
        super().__init__(
            event_type=StepEventType.EXECUTION_FAILED,
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            data={
                "error_message": error_message,
                "error_details": error_details or {},
                "duration": duration,
                "retry_count": retry_count,
                "action": "step_execution_failed",
            },
        )

    @property
    def error_message(self) -> str:
        """Return the error message."""
        return self.data.get("error_message", "")

    @property
    def error_details(self) -> Dict[str, Any]:
        """Return the error details."""
        return self.data.get("error_details", {})

    @property
    def duration(self) -> Optional[float]:
        """Return the execution duration before failure."""
        return self.data.get("duration")

    @property
    def retry_count(self) -> int:
        """Return the retry count."""
        return self.data.get("retry_count", 0)


class StepProgressEvent(StepEvent):
    """Event emitted to report step execution progress."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: Optional[str] = None,
        progress_percentage: Optional[float] = None,
        progress_message: str = "",
        current_operation: Optional[str] = None,
    ):
        """Initialize step progress event."""
        super().__init__(
            event_type=StepEventType.PROGRESS,
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            data={
                "progress_percentage": progress_percentage,
                "progress_message": progress_message,
                "current_operation": current_operation,
                "action": "step_progress",
            },
        )

    @property
    def progress_percentage(self) -> Optional[float]:
        """Return the progress percentage."""
        return self.data.get("progress_percentage")

    @property
    def progress_message(self) -> str:
        """Return the progress message."""
        return self.data.get("progress_message", "")

    @property
    def current_operation(self) -> Optional[str]:
        """Return the current operation."""
        return self.data.get("current_operation")


class StepUnsupportedEvent(StepEvent):
    """Event emitted when a step is unsupported in the current environment."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: Optional[str] = None,
        reason: str = "",
        alternative_steps: Optional[list] = None,
    ):
        """Initialize step unsupported event."""
        super().__init__(
            event_type=StepEventType.UNSUPPORTED,
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            data={
                "reason": reason,
                "alternative_steps": alternative_steps or [],
                "action": "step_unsupported",
            },
        )

    @property
    def reason(self) -> str:
        """Return the unsupported reason."""
        return self.data.get("reason", "")

    @property
    def alternative_steps(self) -> list:
        """Return the alternative steps."""
        return self.data.get("alternative_steps", [])


class StepSkippedEvent(StepEvent):
    """Event emitted when a step is skipped."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: Optional[str] = None,
        skip_reason: str = "",
        skip_condition: Optional[str] = None,
    ):
        """Initialize step skipped event."""
        super().__init__(
            event_type=StepEventType.SKIPPED,
            step_id=step_id,
            step_name=step_name,
            test_case_id=test_case_id,
            data={
                "skip_reason": skip_reason,
                "skip_condition": skip_condition,
                "action": "step_skipped",
            },
        )

    @property
    def skip_reason(self) -> str:
        """Return the skip reason."""
        return self.data.get("skip_reason", "")

    @property
    def skip_condition(self) -> Optional[str]:
        """Return the skip condition."""
        return self.data.get("skip_condition")
