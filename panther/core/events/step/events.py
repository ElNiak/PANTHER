"""Step Events.

This module defines events specific to step execution and management.
Uses factory classmethods on the base StepEvent class instead of
individual subclasses for most event types.
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

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def execution_started(
        cls,
        step_id,
        step_name,
        test_case_id=None,
        step_config=None,
        prerequisites=None,
    ):
        """Create execution started event."""
        return cls(
            StepEventType.EXECUTION_STARTED,
            step_id,
            step_name,
            test_case_id,
            data={
                "step_config": step_config or {},
                "prerequisites": prerequisites or [],
                "action": "step_execution_started",
            },
        )

    @classmethod
    def execution_completed(
        cls,
        step_id,
        step_name,
        test_case_id=None,
        duration=None,
        result=None,
        output=None,
    ):
        """Create execution completed event."""
        return cls(
            StepEventType.EXECUTION_COMPLETED,
            step_id,
            step_name,
            test_case_id,
            data={
                "duration": duration,
                "result": result or {},
                "output": output,
                "action": "step_execution_completed",
            },
        )

    @classmethod
    def execution_failed(
        cls,
        step_id,
        step_name,
        test_case_id=None,
        error_message="",
        error_details=None,
        duration=None,
        retry_count=0,
    ):
        """Create execution failed event."""
        return cls(
            StepEventType.EXECUTION_FAILED,
            step_id,
            step_name,
            test_case_id,
            data={
                "error_message": error_message,
                "error_details": error_details or {},
                "duration": duration,
                "retry_count": retry_count,
                "action": "step_execution_failed",
            },
        )

    @classmethod
    def progress(
        cls,
        step_id,
        step_name,
        test_case_id=None,
        progress_percentage=None,
        progress_message="",
        current_operation=None,
    ):
        """Create progress event."""
        return cls(
            StepEventType.PROGRESS,
            step_id,
            step_name,
            test_case_id,
            data={
                "progress_percentage": progress_percentage,
                "progress_message": progress_message,
                "current_operation": current_operation,
                "action": "step_progress",
            },
        )

    @classmethod
    def unsupported(
        cls,
        step_id,
        step_name,
        test_case_id=None,
        reason="",
        alternative_steps=None,
    ):
        """Create unsupported event."""
        return cls(
            StepEventType.UNSUPPORTED,
            step_id,
            step_name,
            test_case_id,
            data={
                "reason": reason,
                "alternative_steps": alternative_steps or [],
                "action": "step_unsupported",
            },
        )

    @classmethod
    def skipped(
        cls,
        step_id,
        step_name,
        test_case_id=None,
        skip_reason="",
        skip_condition=None,
    ):
        """Create skipped event."""
        return cls(
            StepEventType.SKIPPED,
            step_id,
            step_name,
            test_case_id,
            data={
                "skip_reason": skip_reason,
                "skip_condition": skip_condition,
                "action": "step_skipped",
            },
        )
