"""Test events for test case lifecycle management.

Uses factory classmethods on the base TestEvent class instead of
individual subclasses for most event types. Subclasses are kept
where isinstance() checks or custom attributes require them.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

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

    def __init__(
        self,
        event_type: TestEventType,
        test_id: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize with event type, test ID, and optional data."""
        super().__init__(
            name=event_type.value,
            entity_type=EventType.TEST,
            entity_id=test_id,
            data=data,
        )
        self.event_type = event_type

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def created(cls, test_id, test_name, description=None, config=None):
        """Create created event."""
        return cls(
            TestEventType.CREATED,
            test_id,
            data={
                "test_name": test_name,
                "description": description,
                "config": config or {},
            },
        )

    @classmethod
    def setup_started(cls, test_id, service_count=None, service_names=None):
        """Create setup started event."""
        return cls(
            TestEventType.SETUP_STARTED,
            test_id,
            data={"service_count": service_count, "service_names": service_names or []},
        )

    @classmethod
    def setup_completed(cls, test_id, services=None, duration_seconds=None):
        """Create setup completed event."""
        return cls(
            TestEventType.SETUP_COMPLETED,
            test_id,
            data={"services": services or [], "duration_seconds": duration_seconds},
        )

    @classmethod
    def setup_failed(
        cls, test_id, error_message, error_type=None, failed_component=None
    ):
        """Create setup failed event."""
        return cls(
            TestEventType.SETUP_FAILED,
            test_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "failed_component": failed_component,
            },
        )

    @classmethod
    def environment_setup_started(
        cls, test_id, environment_type, environment_config=None
    ):
        """Create environment setup started event."""
        return cls(
            TestEventType.ENVIRONMENT_SETUP_STARTED,
            test_id,
            data={
                "environment_type": environment_type,
                "environment_config": environment_config or {},
            },
        )

    @classmethod
    def environment_setup_completed(
        cls, test_id, environment_type, environment_details=None
    ):
        """Create environment setup completed event."""
        return cls(
            TestEventType.ENVIRONMENT_SETUP_COMPLETED,
            test_id,
            data={
                "environment_type": environment_type,
                "environment_details": environment_details or {},
            },
        )

    @classmethod
    def environment_setup_failed(
        cls, test_id, environment_type, error_message, error_type=None
    ):
        """Create environment setup failed event."""
        return cls(
            TestEventType.ENVIRONMENT_SETUP_FAILED,
            test_id,
            data={
                "environment_type": environment_type,
                "error_message": error_message,
                "error_type": error_type,
            },
        )

    @classmethod
    def deployment_started(cls, test_id, services_to_deploy=None):
        """Create deployment started event."""
        return cls(
            TestEventType.DEPLOYMENT_STARTED,
            test_id,
            data={"services_to_deploy": services_to_deploy or []},
        )

    @classmethod
    def deployment_completed(
        cls, test_id, deployed_services=None, deployment_details=None
    ):
        """Create deployment completed event."""
        return cls(
            TestEventType.DEPLOYMENT_COMPLETED,
            test_id,
            data={
                "deployed_services": deployed_services or [],
                "deployment_details": deployment_details or {},
            },
        )

    @classmethod
    def deployment_failed(
        cls, test_id, error_message, failed_services=None, error_type=None
    ):
        """Create deployment failed event."""
        return cls(
            TestEventType.DEPLOYMENT_FAILED,
            test_id,
            data={
                "error_message": error_message,
                "failed_services": failed_services or [],
                "error_type": error_type,
            },
        )

    @classmethod
    def execution_started(cls, test_id, steps=None, expected_duration=None):
        """Create execution started event."""
        return cls(
            TestEventType.EXECUTION_STARTED,
            test_id,
            data={"steps": steps or [], "expected_duration": expected_duration},
        )

    @classmethod
    def step_started(cls, test_id, step_name, step_type=None, step_config=None):
        """Create step started event."""
        return cls(
            TestEventType.STEP_STARTED,
            test_id,
            data={
                "step_name": step_name,
                "step_type": step_type,
                "step_config": step_config or {},
            },
        )

    @classmethod
    def step_completed(cls, test_id, step_name, duration_seconds=None, result=None):
        """Create step completed event."""
        return cls(
            TestEventType.STEP_COMPLETED,
            test_id,
            data={
                "step_name": step_name,
                "duration_seconds": duration_seconds,
                "result": result or {},
            },
        )

    @classmethod
    def step_failed(cls, test_id, step_name, error_message, error_type=None):
        """Create step failed event."""
        return cls(
            TestEventType.STEP_FAILED,
            test_id,
            data={
                "step_name": step_name,
                "error_message": error_message,
                "error_type": error_type,
            },
        )

    @classmethod
    def assertions_started(cls, test_id, assertions=None):
        """Create assertions started event."""
        return cls(
            TestEventType.ASSERTIONS_STARTED,
            test_id,
            data={"assertions": assertions or []},
        )

    @classmethod
    def assertion_checked(
        cls, test_id, assertion_type, assertion_config, passed, result=None
    ):
        """Create assertion checked event."""
        return cls(
            TestEventType.ASSERTION_CHECKED,
            test_id,
            data={
                "assertion_type": assertion_type,
                "assertion_config": assertion_config,
                "passed": passed,
                "result": result or {},
            },
        )

    @classmethod
    def assertions_completed(
        cls, test_id, total_assertions, passed_assertions, failed_assertions, all_passed
    ):
        """Create assertions completed event."""
        return cls(
            TestEventType.ASSERTIONS_COMPLETED,
            test_id,
            data={
                "total_assertions": total_assertions,
                "passed_assertions": passed_assertions,
                "failed_assertions": failed_assertions,
                "all_passed": all_passed,
            },
        )

    @classmethod
    def assertions_failed(cls, test_id, error_message, error_type=None):
        """Create assertions failed event."""
        return cls(
            TestEventType.ASSERTIONS_FAILED,
            test_id,
            data={"error_message": error_message, "error_type": error_type},
        )

    @classmethod
    def execution_completed(
        cls,
        test_id,
        duration_seconds=None,
        steps_completed=None,
        assertions_passed=None,
    ):
        """Create execution completed event."""
        return cls(
            TestEventType.EXECUTION_COMPLETED,
            test_id,
            data={
                "duration_seconds": duration_seconds,
                "steps_completed": steps_completed,
                "assertions_passed": assertions_passed,
            },
        )

    @classmethod
    def execution_failed(cls, test_id, error_message, error_type=None, phase=None):
        """Create execution failed event."""
        return cls(
            TestEventType.EXECUTION_FAILED,
            test_id,
            data={
                "error_message": error_message,
                "error_type": error_type,
                "phase": phase,
            },
        )

    @classmethod
    def teardown_started(cls, test_id):
        """Create teardown started event."""
        return cls(TestEventType.TEARDOWN_STARTED, test_id)

    @classmethod
    def teardown_completed(cls, test_id, duration_seconds=None):
        """Create teardown completed event."""
        return cls(
            TestEventType.TEARDOWN_COMPLETED,
            test_id,
            data={"duration_seconds": duration_seconds},
        )


# -- Subclasses kept for isinstance() or custom attribute compatibility --------


class TestCompletedEvent(TestEvent):
    """Event emitted when test completes successfully."""

    def __init__(
        self,
        test_id: str,
        test_name: Optional[str] = None,
        total_duration_seconds: Optional[float] = None,
        summary: Optional[Dict[str, Any]] = None,
    ):
        """Initialize with test ID and completion summary."""
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
        test_name: Optional[str] = None,
        error_message: str = "",
        error_type: Optional[str] = None,
        phase: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ):
        """Initialize with test ID, failure reason, and context."""
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
        self.failure_reason = error_message
        self.error_message = error_message


class TestResultEvent(TestEvent):
    """Event for basic test results."""

    def __init__(
        self,
        name: str,
        test_name: str,
        result: bool,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize with test name, pass/fail result, and optional metadata."""
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
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        category: str = "default",
    ):
        """Initialize with test name, result, and categorization info."""
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

    def add_tag(self, tag: str) -> None:
        """Add a tag to the event if it doesn't already exist."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.data["tags"] = self.tags
