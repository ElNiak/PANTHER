"""
Event Core Module

This module defines all core event classes used in the PANTHER framework's observer system.
Use during experiment execution to track and log various system events.
This includes events related to tests, network activities, services, environment setup,
and experiments.
"""

from abc import ABC
from datetime import datetime
import uuid
from typing import Any


class Event(ABC):
    """
    Base event class for all system events.

    This is an enhanced version of the original Event class with additional
    functionality for type identification, validation, and tracking.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new Event.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        self.name = name
        self.data = data or {}
        self.timestamp = datetime.now()
        self.id = uuid.uuid4()

    def get_type(self) -> str:
        """
        Get the event type identifier.
        By default, this returns the event name, but subclasses can override this.

        Returns:
            str: The event type identifier
        """
        return self.name

    def validate(self) -> bool:
        """
        Validate event data against expected schema.
        Base implementation always returns True. Subclasses should override this
        to implement specific validation logic.

        Returns:
            bool: True if the event data is valid, False otherwise
        """
        return True

    def __str__(self):
        """String representation of the event."""
        return f"Event(type='{self.get_type()}', id={self.id}, timestamp={self.timestamp}, data={self.data})"

    def __repr__(self):
        return str(self)


class TestEvent(Event):
    """
    Test execution related events.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new TestEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"test.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for TestEvents has the 'test.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name


class NetworkEvent(Event):
    """
    Network-related events like packet transmissions, connections, etc.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new NetworkEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"network.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for NetworkEvents has the 'network.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name


class ServiceEvent(Event):
    """
    Event emitted when a service-related operation occurs.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize the service event.

        Args:
            name: Service event name (e.g., "service.deployed")
            data: Service event data
                May include 'service_instances' dictionary with service name -> instance mappings
        """
        super().__init__(name=name, data=data or {})

    def get_type(self) -> str:
        """
        Get the event type, which for ServiceEvents has the 'service.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name


class ServiceStartedEvent(ServiceEvent):
    """
    Event emitted when a service starts.
    """

    def __init__(self, service_name: str, data: dict[str, Any] = None):
        """
        Initialize the service started event.

        Args:
            service_name: Name of the service that started
            data: Additional data about the service start
        """
        super().__init__(f"service.{service_name}.started", data)

    def get_type(self) -> str:
        return self.name


class ServiceStoppedEvent(ServiceEvent):
    """
    Event emitted when a service stops.
    """

    def __init__(self, service_name: str, data: dict[str, Any] = None):
        """
        Initialize the service stopped event.

        Args:
            service_name: Name of the service that stopped
            data: Additional data about the service stop
        """
        super().__init__(f"service.{service_name}.stopped", data)

    def get_type(self) -> str:
        return self.name


class EnvironmentEvent(Event):
    """
    Environment-related events such as setup and teardown.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new EnvironmentEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"environment.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for EnvironmentEvents has the 'environment.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name


class StepEvent(Event):
    """
    Test step execution related events.
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


class ExperimentEvent(Event):
    """
    Experiment lifecycle related events.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new ExperimentEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"experiment.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for ExperimentEvents has the 'experiment.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name


# Specific event implementations
class TestStartedEvent(TestEvent):
    """Event emitted when a test case starts execution."""

    def __init__(self, test_name: str, config: dict[str, Any]):
        """
        Initialize a new TestStartedEvent.

        Args:
            test_name: Name of the test being executed
            config: Test configuration details
        """
        super().__init__("started", {"test_name": test_name, "config": config})

    def validate(self) -> bool:
        """
        Validate that the event contains required test information.

        Returns:
            bool: True if required fields are present
        """
        return "test_name" in self.data and "config" in self.data


class TestCompletedEvent(TestEvent):
    """Event emitted when a test case completes execution."""

    def __init__(self, test_name: str, success: bool = True, result: dict[str, Any] = None):
        """
        Initialize a new TestCompletedEvent.

        Args:
            test_name: Name of the completed test
            success: Whether the test was successful
            result: Test result data if available
        """
        super().__init__(
            "completed", {"test_name": test_name, "success": success, "result": result or {}}
        )

    def validate(self) -> bool:
        """
        Validate that the event contains required test completion information.

        Returns:
            bool: True if required fields are present
        """
        return "test_name" in self.data and "success" in self.data


class EnvironmentSetupCompletedEvent(EnvironmentEvent):
    """
    Event emitted when an environment setup is completed.
    """

    def __init__(self, environment_type: str, success: bool = True, details: dict[str, Any] = None):
        """
        Initialize the environment setup completed event.

        Args:
            environment_type: Type of the environment that was set up
            success: Whether the setup was successful
            details: Additional details about the setup
                May include 'environment_instance' with a reference to the actual environment object
        """
        super().__init__(
            name="environment.setup.completed",
            data={
                "environment_type": environment_type,
                "success": success,
                "details": details or {},
            },
        )

    @property
    def environment_type(self) -> str:
        """Get the environment type."""
        return self.data.get("environment_type", "unknown")

    @property
    def success(self) -> bool:
        """Get whether setup was successful."""
        return self.data.get("success", False)

    @property
    def details(self) -> dict[str, Any]:
        """Get setup details."""
        return self.data.get("details", {})


class EnvironmentSetupStartedEvent(EnvironmentEvent):
    """Event emitted when environment setup starts."""

    def __init__(self, environment_type: str, details: dict[str, Any] = None):
        """
        Initialize a new EnvironmentSetupStartedEvent.

        Args:
            environment_type: Type of environment being set up
            details: Additional details about the setup
        """
        super().__init__("setup_started", {"type": environment_type, "details": details or {}})

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "type" in self.data


class EnvironmentTeardownEvent(EnvironmentEvent):
    """Event emitted for environment teardown."""

    def __init__(self, environment_type: str, success: bool, details: dict[str, Any] = None):
        """
        Initialize a new EnvironmentTeardownEvent.

        Args:
            environment_type: Type of environment being torn down
            success: Whether teardown was successful
            details: Additional details about the teardown
        """
        super().__init__(
            "teardown", {"type": environment_type, "success": success, "details": details or {}}
        )

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "type" in self.data and "success" in self.data


class StepProgressEvent(StepEvent):
    """Event emitted to report progress of a step."""

    def __init__(
        self, step_id: str, progress: float, message: str = None, details: dict[str, Any] = None
    ):
        """
        Initialize a new StepProgressEvent.

        Args:
            step_id: Identifier for the step
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
            details: Additional progress details
        """
        super().__init__(
            "progress",
            {
                "step_id": step_id,
                "progress": progress,
                "message": message,
                "details": details or {},
            },
        )

    def validate(self) -> bool:
        """Validate event data has required fields and valid progress."""
        if "step_id" not in self.data or "progress" not in self.data:
            return False
        progress = self.data["progress"]
        return isinstance(progress, (int, float)) and 0.0 <= progress <= 100


class StepCompletedEvent(StepEvent):
    """Event emitted when a step completes."""

    def __init__(self, step_id: str, success: bool, result: dict[str, Any] = None):
        """
        Initialize a new StepCompletedEvent.

        Args:
            step_id: Identifier for the completed step
            success: Whether the step completed successfully
            result: Result data from the step
        """
        super().__init__(
            "completed", {"step_id": step_id, "success": success, "result": result or {}}
        )

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "step_id" in self.data and "success" in self.data


class ExperimentInitializedEvent(ExperimentEvent):
    """Event emitted when an experiment is initialized."""

    def __init__(self, experiment_id: str, config: dict[str, Any]):
        """
        Initialize a new ExperimentInitializedEvent.

        Args:
            experiment_id: Identifier for the experiment
            config: Experiment configuration
        """
        super().__init__("initialized", {"experiment_id": experiment_id, "config": config})

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "experiment_id" in self.data and "config" in self.data


class ExperimentFinishedEarlyEvent(ExperimentEvent):
    """Event emitted when an experiment finishes earlier than expected."""

    def __init__(self, experiment_id: str, reason: str, details: dict[str, Any] = None):
        """
        Initialize a new ExperimentFinishedEarlyEvent.

        Args:
            experiment_id: Identifier for the experiment
            reason: Reason for early termination
            details: Additional details about the early termination
        """
        super().__init__(
            "finished_early",
            {"experiment_id": experiment_id, "reason": reason, "details": details or {}},
        )

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "experiment_id" in self.data and "reason" in self.data


class ExperimentFinishedEvent(ExperimentEvent):
    """Event emitted when an experiment finishes completely."""

    def __init__(self, experiment_id: str, success: bool = True, summary: dict[str, Any] = None):
        """
        Initialize a new ExperimentFinishedEvent.

        Args:
            experiment_id: Unique identifier for the experiment
            success: Whether the experiment completed successfully
            summary: Experiment execution summary with metrics and results
        """
        super().__init__(
            "finished",
            {"experiment_id": experiment_id, "success": success, "summary": summary or {}},
        )

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "experiment_id" in self.data


class TestCaseInitializedEvent(TestEvent):
    """Event emitted when a test case is initialized."""

    def __init__(self, test_id: str, test_name: str, parameters: dict[str, Any] = None):
        """
        Initialize a new TestCaseInitializedEvent.

        Args:
            test_id: Identifier for the test case
            test_name: Name of the test case
            parameters: Test parameters
        """
        super().__init__(
            "initialized",
            {"test_id": test_id, "test_name": test_name, "parameters": parameters or {}},
        )

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "test_id" in self.data and "test_name" in self.data


class TestExecutionStartedEvent(TestEvent):
    """Event emitted when test execution starts."""

    def __init__(self, test_id: str, test_name: str):
        """
        Initialize a new TestExecutionStartedEvent.

        Args:
            test_id: Identifier for the test
            test_name: Name of the test
        """
        super().__init__(
            "execution.started",
            {"test_id": test_id, "test_name": test_name, "start_time": datetime.now().isoformat()},
        )

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "test_id" in self.data and "test_name" in self.data


class TestExecutionCompletedEvent(TestEvent):
    """Event emitted when test execution completes."""

    def __init__(
        self,
        test_id: str,
        test_name: str,
        success: bool,
        results: dict[str, Any] = None,
        duration_ms: float | None = None,
    ):
        """
        Initialize a new TestExecutionCompletedEvent.

        Args:
            test_id: Identifier for the test
            test_name: Name of the test
            success: Whether the test execution was successful
            results: Test results data
            duration_ms: Test execution duration in milliseconds
        """
        super().__init__(
            "execution.completed",
            {
                "test_id": test_id,
                "test_name": test_name,
                "success": success,
                "results": results or {},
                "duration_ms": duration_ms,
                "completion_time": datetime.now().isoformat(),
            },
        )

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "test_id" in self.data and "test_name" in self.data and "success" in self.data


class TestExecutionFailedEvent(TestEvent):
    """Event emitted when test execution fails."""

    def __init__(
        self,
        test_id: str,
        test_name: str,
        error_message: str,
        stack_trace: str | None = None,
        error_details: dict[str, Any] = None,
    ):
        """
        Initialize a new TestExecutionFailedEvent.

        Args:
            test_id: Identifier for the test
            test_name: Name of the test
            error_message: Description of the error
            stack_trace: Optional stack trace from the error
            error_details: Additional details about the error
        """
        super().__init__(
            "execution.failed",
            {
                "test_id": test_id,
                "test_name": test_name,
                "error_message": error_message,
                "stack_trace": stack_trace,
                "error_details": error_details or {},
                "failure_time": datetime.now().isoformat(),
            },
        )

    def validate(self) -> bool:
        """Validate event data has required fields."""
        return "test_id" in self.data and "test_name" in self.data and "error_message" in self.data
