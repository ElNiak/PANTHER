"""
Step Events

This module defines events specific to step execution and management.
"""

from enum import Enum
from typing import Any

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
        test_case_id: str | None = None,
        data: dict[str, Any] | None = None,
    ):
        merged_data = data or {}
        merged_data.update({"step_name": step_name, "test_case_id": test_case_id})

        super().__init__(
            name=event_type.value, entity_type=EventType.STEP, entity_id=step_id, data=merged_data
        )
        self.event_type = event_type
        self.step_name = step_name
        self.test_case_id = test_case_id

    @property
    def step_name_property(self) -> str:
        return self.data.get("step_name", "")

    @property
    def test_case_id_property(self) -> str | None:
        return self.data.get("test_case_id")


class StepExecutionStartedEvent(StepEvent):
    """Event emitted when step execution starts."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        step_config: dict[str, Any] | None = None,
        prerequisites: list | None = None,
    ):
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
    def step_config(self) -> dict[str, Any]:
        return self.data.get("step_config", {})

    @property
    def prerequisites(self) -> list:
        return self.data.get("prerequisites", [])


class StepExecutionCompletedEvent(StepEvent):
    """Event emitted when step execution completes successfully."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        duration: float | None = None,
        result: dict[str, Any] | None = None,
        output: str | None = None,
    ):
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
    def duration(self) -> float | None:
        return self.data.get("duration")

    @property
    def result(self) -> dict[str, Any]:
        return self.data.get("result", {})

    @property
    def output(self) -> str | None:
        return self.data.get("output")


class StepExecutionFailedEvent(StepEvent):
    """Event emitted when step execution fails."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        error_message: str = "",
        error_details: dict[str, Any] | None = None,
        duration: float | None = None,
        retry_count: int = 0,
    ):
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
        return self.data.get("error_message", "")

    @property
    def error_details(self) -> dict[str, Any]:
        return self.data.get("error_details", {})

    @property
    def duration(self) -> float | None:
        return self.data.get("duration")

    @property
    def retry_count(self) -> int:
        return self.data.get("retry_count", 0)


class StepProgressEvent(StepEvent):
    """Event emitted to report step execution progress."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        progress_percentage: float | None = None,
        progress_message: str = "",
        current_operation: str | None = None,
    ):
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
    def progress_percentage(self) -> float | None:
        return self.data.get("progress_percentage")

    @property
    def progress_message(self) -> str:
        return self.data.get("progress_message", "")

    @property
    def current_operation(self) -> str | None:
        return self.data.get("current_operation")


class StepUnsupportedEvent(StepEvent):
    """Event emitted when a step is unsupported in the current environment."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        reason: str = "",
        alternative_steps: list | None = None,
    ):
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
        return self.data.get("reason", "")

    @property
    def alternative_steps(self) -> list:
        return self.data.get("alternative_steps", [])


class StepSkippedEvent(StepEvent):
    """Event emitted when a step is skipped."""

    def __init__(
        self,
        step_id: str,
        step_name: str,
        test_case_id: str | None = None,
        skip_reason: str = "",
        skip_condition: str | None = None,
    ):
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
        return self.data.get("skip_reason", "")

    @property
    def skip_condition(self) -> str | None:
        return self.data.get("skip_condition")
