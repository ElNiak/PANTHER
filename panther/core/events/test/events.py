"""
Test Events

This module defines events specific to test case lifecycle management.
"""

from enum import Enum
from typing import Any

from panther.core.events.base.event_base import BaseEvent, EventType


class TestEventType(Enum):
    """Test-specific event types."""

    CREATED = "created"
    SETUP_STARTED = "setup_started"
    SETUP_COMPLETED = "setup_completed"
    SETUP_FAILED = "setup_failed"
    ENVIRONMENT_SETUP_STARTED = "environment_setup_started"
    ENVIRONMENT_SETUP_COMPLETED = "environment_setup_completed"
    ENVIRONMENT_SETUP_FAILED = "environment_setup_failed"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"
    EXECUTION_STARTED = "execution_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    ASSERTIONS_STARTED = "assertions_started"
    ASSERTION_CHECKED = "assertion_checked"
    ASSERTIONS_COMPLETED = "assertions_completed"
    ASSERTIONS_FAILED = "assertions_failed"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    TEARDOWN_STARTED = "teardown_started"
    TEARDOWN_COMPLETED = "teardown_completed"
    COMPLETED = "completed"
    FAILED = "failed"


class TestEvent(BaseEvent):
    """Base class for all test events."""

    def __init__(self, event_type: TestEventType, test_id: str, data: dict[str, Any] | None = None):
        super().__init__(
            name=event_type.value, entity_type=EventType.TEST, entity_id=test_id, data=data
        )
        self.event_type = event_type


class TestCreatedEvent(TestEvent):
    """Event emitted when a test case is created."""

    def __init__(
        self,
        test_id: str,
        test_name: str,
        description: str | None = None,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=TestEventType.CREATED,
            test_id=test_id,
            data={"test_name": test_name, "description": description, "config": config or {}},
        )


class TestSetupStartedEvent(TestEvent):
    """Event emitted when test setup starts."""

    def __init__(
        self, test_id: str, service_count: int | None = None, service_names: list[str] | None = None
    ):
        super().__init__(
            event_type=TestEventType.SETUP_STARTED,
            test_id=test_id,
            data={"service_count": service_count, "service_names": service_names or []},
        )


class TestSetupCompletedEvent(TestEvent):
    """Event emitted when test setup completes."""

    def __init__(
        self, test_id: str, services: list[str] | None = None, duration_seconds: float | None = None
    ):
        super().__init__(
            event_type=TestEventType.SETUP_COMPLETED,
            test_id=test_id,
            data={"services": services or [], "duration_seconds": duration_seconds},
        )


class TestSetupFailedEvent(TestEvent):
    """Event emitted when test setup fails."""

    def __init__(
        self,
        test_id: str,
        error_message: str,
        error_type: str | None = None,
        failed_component: str | None = None,
    ):
        super().__init__(
            event_type=TestEventType.SETUP_FAILED,
            test_id=test_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "failed_component": failed_component,
            },
        )


class TestEnvironmentSetupStartedEvent(TestEvent):
    """Event emitted when test environment setup starts."""

    def __init__(
        self, test_id: str, environment_type: str, environment_config: dict[str, Any] | None = None
    ):
        super().__init__(
            event_type=TestEventType.ENVIRONMENT_SETUP_STARTED,
            test_id=test_id,
            data={
                "environment_type": environment_type,
                "environment_config": environment_config or {},
            },
        )


class TestEnvironmentSetupCompletedEvent(TestEvent):
    """Event emitted when test environment setup completes."""

    def __init__(
        self, test_id: str, environment_type: str, environment_details: dict[str, Any] | None = None
    ):
        super().__init__(
            event_type=TestEventType.ENVIRONMENT_SETUP_COMPLETED,
            test_id=test_id,
            data={
                "environment_type": environment_type,
                "environment_details": environment_details or {},
            },
        )


class TestEnvironmentSetupFailedEvent(TestEvent):
    """Event emitted when test environment setup fails."""

    def __init__(
        self, test_id: str, environment_type: str, error_message: str, error_type: str | None = None
    ):
        super().__init__(
            event_type=TestEventType.ENVIRONMENT_SETUP_FAILED,
            test_id=test_id,
            data={
                "environment_type": environment_type,
                "error_message": error_message,
                "error_type": error_type,
            },
        )


class TestDeploymentStartedEvent(TestEvent):
    """Event emitted when test service deployment starts."""

    def __init__(self, test_id: str, services_to_deploy: list[str] | None = None):
        super().__init__(
            event_type=TestEventType.DEPLOYMENT_STARTED,
            test_id=test_id,
            data={"services_to_deploy": services_to_deploy or []},
        )


class TestDeploymentCompletedEvent(TestEvent):
    """Event emitted when test service deployment completes."""

    def __init__(
        self,
        test_id: str,
        deployed_services: list[str] | None = None,
        deployment_details: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=TestEventType.DEPLOYMENT_COMPLETED,
            test_id=test_id,
            data={
                "deployed_services": deployed_services or [],
                "deployment_details": deployment_details or {},
            },
        )


class TestDeploymentFailedEvent(TestEvent):
    """Event emitted when test service deployment fails."""

    def __init__(
        self,
        test_id: str,
        error_message: str,
        failed_services: list[str] | None = None,
        error_type: str | None = None,
    ):
        super().__init__(
            event_type=TestEventType.DEPLOYMENT_FAILED,
            test_id=test_id,
            data={
                "error_message": error_message,
                "failed_services": failed_services or [],
                "error_type": error_type,
            },
        )


class TestExecutionStartedEvent(TestEvent):
    """Event emitted when test execution starts."""

    def __init__(
        self, test_id: str, steps: list[str] | None = None, expected_duration: float | None = None
    ):
        super().__init__(
            event_type=TestEventType.EXECUTION_STARTED,
            test_id=test_id,
            data={"steps": steps or [], "expected_duration": expected_duration},
        )


class TestStepStartedEvent(TestEvent):
    """Event emitted when a test step starts."""

    def __init__(
        self,
        test_id: str,
        step_name: str,
        step_type: str | None = None,
        step_config: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=TestEventType.STEP_STARTED,
            test_id=test_id,
            data={"step_name": step_name, "step_type": step_type, "step_config": step_config or {}},
        )


class TestStepCompletedEvent(TestEvent):
    """Event emitted when a test step completes."""

    def __init__(
        self,
        test_id: str,
        step_name: str,
        duration_seconds: float | None = None,
        result: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=TestEventType.STEP_COMPLETED,
            test_id=test_id,
            data={
                "step_name": step_name,
                "duration_seconds": duration_seconds,
                "result": result or {},
            },
        )


class TestStepFailedEvent(TestEvent):
    """Event emitted when a test step fails."""

    def __init__(
        self, test_id: str, step_name: str, error_message: str, error_type: str | None = None
    ):
        super().__init__(
            event_type=TestEventType.STEP_FAILED,
            test_id=test_id,
            data={"step_name": step_name, "error_message": error_message, "error_type": error_type},
        )


class TestAssertionsStartedEvent(TestEvent):
    """Event emitted when test assertions validation starts."""

    def __init__(self, test_id: str, assertions: list[dict[str, Any]] | None = None):
        super().__init__(
            event_type=TestEventType.ASSERTIONS_STARTED,
            test_id=test_id,
            data={"assertions": assertions or []},
        )


class TestAssertionCheckedEvent(TestEvent):
    """Event emitted when an assertion is checked."""

    def __init__(
        self,
        test_id: str,
        assertion_type: str,
        assertion_config: dict[str, Any],
        passed: bool,
        result: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=TestEventType.ASSERTION_CHECKED,
            test_id=test_id,
            data={
                "assertion_type": assertion_type,
                "assertion_config": assertion_config,
                "passed": passed,
                "result": result or {},
            },
        )


class TestAssertionsCompletedEvent(TestEvent):
    """Event emitted when test assertions validation completes."""

    def __init__(
        self,
        test_id: str,
        total_assertions: int,
        passed_assertions: int,
        failed_assertions: int,
        all_passed: bool,
    ):
        super().__init__(
            event_type=TestEventType.ASSERTIONS_COMPLETED,
            test_id=test_id,
            data={
                "total_assertions": total_assertions,
                "passed_assertions": passed_assertions,
                "failed_assertions": failed_assertions,
                "all_passed": all_passed,
            },
        )


class TestAssertionsFailedEvent(TestEvent):
    """Event emitted when assertions validation fails with an error."""

    def __init__(self, test_id: str, error_message: str, error_type: str | None = None):
        super().__init__(
            event_type=TestEventType.ASSERTIONS_FAILED,
            test_id=test_id,
            data={"error_message": error_message, "error_type": error_type},
        )


class TestExecutionCompletedEvent(TestEvent):
    """Event emitted when test execution completes successfully."""

    def __init__(
        self,
        test_id: str,
        duration_seconds: float | None = None,
        steps_completed: int | None = None,
        assertions_passed: bool | None = None,
    ):
        super().__init__(
            event_type=TestEventType.EXECUTION_COMPLETED,
            test_id=test_id,
            data={
                "duration_seconds": duration_seconds,
                "steps_completed": steps_completed,
                "assertions_passed": assertions_passed,
            },
        )


class TestExecutionFailedEvent(TestEvent):
    """Event emitted when test execution fails."""

    def __init__(
        self,
        test_id: str,
        error_message: str,
        error_type: str | None = None,
        phase: str | None = None,
    ):
        super().__init__(
            event_type=TestEventType.EXECUTION_FAILED,
            test_id=test_id,
            data={"error_message": error_message, "error_type": error_type, "phase": phase},
        )


class TestTeardownStartedEvent(TestEvent):
    """Event emitted when test teardown starts."""

    def __init__(self, test_id: str):
        super().__init__(event_type=TestEventType.TEARDOWN_STARTED, test_id=test_id)


class TestTeardownCompletedEvent(TestEvent):
    """Event emitted when test teardown completes."""

    def __init__(self, test_id: str, duration_seconds: float | None = None):
        super().__init__(
            event_type=TestEventType.TEARDOWN_COMPLETED,
            test_id=test_id,
            data={"duration_seconds": duration_seconds},
        )


class TestCompletedEvent(TestEvent):
    """Event emitted when test completes successfully."""

    def __init__(
        self,
        test_id: str,
        test_name: str | None = None,
        total_duration_seconds: float | None = None,
        summary: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=TestEventType.COMPLETED,
            test_id=test_id,
            data={
                "test_name": test_name or test_id,
                "total_duration_seconds": total_duration_seconds,
                "summary": summary or {},
            },
        )
        self.test_name = test_name or test_id
        self.test_id = test_id


class TestFailedEvent(TestEvent):
    """Event emitted when test fails."""

    def __init__(
        self,
        test_id: str,
        test_name: str | None = None,
        error_message: str = "",
        error_type: str | None = None,
        phase: str | None = None,
        summary: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=TestEventType.FAILED,
            test_id=test_id,
            data={
                "test_name": test_name or test_id,
                "error_message": error_message,
                "error_type": error_type,
                "phase": phase,
                "summary": summary or {},
            },
        )
        self.test_name = test_name or test_id
        self.test_id = test_id


class TestResultEvent(TestEvent):
    """Event for basic test results."""

    def __init__(
        self,
        name: str,
        test_name: str,
        result: bool,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=TestEventType.COMPLETED if result else TestEventType.FAILED,
            test_id=test_name,
            data=data or {},
        )
        self.test_name = test_name
        self.result = result
        self.metadata = metadata or {}


class EnhancedResultEvent(TestEvent):
    """Event for enhanced test results with categorization and tags."""

    def __init__(
        self,
        name: str,
        test_name: str,
        result: bool,
        result_data: Any = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        category: str = "default",
    ):
        data = {
            "result_data": result_data,
            "category": category,
            "tags": tags or [],
        }

        super().__init__(
            event_type=TestEventType.COMPLETED if result else TestEventType.FAILED,
            test_id=test_name,
            data=data,
        )
        self.test_name = test_name
        self.result = result
        self.metadata = metadata or {}
        self.tags = tags or []
        self.category = category

    def get_result_data(self) -> Any:
        """Get the result data."""
        return self.data.get("result_data")
