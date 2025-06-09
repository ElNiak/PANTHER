"""
Service Event Types Module

This module defines event types related to service lifecycle and deployment
to integrate the service management system with the event infrastructure.
"""

from typing import Any

from panther.core.observer.core.core_events import Event


class ServiceEvent(Event):
    """
    Service-related events like setup, deployment, failure, etc.
    """

    def __init__(self, name: str, data: dict[str, Any] = None):
        """
        Initialize a new ServiceEvent.

        Args:
            name: The name/identifier of the event
            data: Dictionary containing event data
        """
        super().__init__(f"service.{name}", data)

    def get_type(self) -> str:
        """
        Get the event type, which for ServiceEvents has the 'service.' prefix.

        Returns:
            str: The event type identifier
        """
        return self.name

    def validate(self) -> bool:
        """
        Validate service event data.

        Returns:
            bool: True if the event data is valid
        """
        return True


class ServiceSetupStartedEvent(ServiceEvent):
    """
    Event triggered when service setup begins.
    """

    def __init__(
        self,
        test_case: str,
        service_count: int,
        service_names: list[str] = None,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a service setup started event.

        Args:
            test_case: Name of the test case
            service_count: Number of services to set up
            service_names: Names of the services being set up
            data: Additional event data
        """
        event_data = data or {}
        event_data["test_case"] = test_case
        event_data["service_count"] = service_count
        if service_names:
            event_data["service_names"] = service_names
        super().__init__("setup_started", event_data)

    def validate(self) -> bool:
        """Validate that test_case and service_count are present."""
        return (
            "test_case" in self.data
            and bool(self.data["test_case"])
            and "service_count" in self.data
        )


class ServiceSetupCompletedEvent(ServiceEvent):
    """
    Event triggered when service setup completes successfully.
    """

    def __init__(
        self, test_case: str, services: list[str], success: bool = True, data: dict[str, Any] = None
    ):
        """
        Initialize a service setup completed event.

        Args:
            test_case: Name of the test case
            services: List of service names that were set up
            success: Whether setup was successful
            data: Additional event data
        """
        event_data = data or {}
        event_data["test_case"] = test_case
        event_data["services"] = services
        event_data["success"] = success
        super().__init__("setup_completed", event_data)

    def validate(self) -> bool:
        """Validate that test_case and services are present."""
        return (
            "test_case" in self.data
            and bool(self.data["test_case"])
            and "services" in self.data
            and isinstance(self.data["services"], list)
        )


class ServiceSetupFailedEvent(ServiceEvent):
    """
    Event triggered when service setup fails.
    """

    def __init__(
        self, test_case: str, error_message: str, error_type: str, data: dict[str, Any] = None
    ):
        """
        Initialize a service setup failed event.

        Args:
            test_case: Name of the test case
            error_message: Error message from the failure
            error_type: Type of error that occurred
            data: Additional event data
        """
        event_data = data or {}
        event_data["test_case"] = test_case
        event_data["error_message"] = error_message
        event_data["error_type"] = error_type
        super().__init__("setup_failed", event_data)

    def validate(self) -> bool:
        """Validate that test_case and error_message are present."""
        return (
            "test_case" in self.data
            and bool(self.data["test_case"])
            and "error_message" in self.data
            and bool(self.data["error_message"])
        )


class ServiceDeploymentEvent(ServiceEvent):
    """
    Event triggered when service deployment occurs.
    """

    def __init__(self, service_name: str, deployment_status: str, data: dict[str, Any] = None):
        """
        Initialize a service deployment event.

        Args:
            service_name: Name of the service being deployed
            deployment_status: Status of the deployment (e.g., 'started', 'completed')
            data: Additional event data
        """
        event_data = data or {}
        event_data["service_name"] = service_name
        event_data["deployment_status"] = deployment_status
        super().__init__("deployment", event_data)

    def validate(self) -> bool:
        """Validate that service_name and deployment_status are present."""
        return (
            "service_name" in self.data
            and bool(self.data["service_name"])
            and "deployment_status" in self.data
            and bool(self.data["deployment_status"])
        )


class ServiceDeploymentFailedEvent(ServiceEvent):
    """
    Event triggered when service deployment fails.
    """

    def __init__(self, service_name: str, error: str, data: dict[str, Any] = None):
        """
        Initialize a service deployment failed event.

        Args:
            service_name: Name of the service that failed deployment
            error: Error message or description
            data: Additional event data
        """
        event_data = data or {}
        event_data["service_name"] = service_name
        event_data["error"] = error
        super().__init__("deployment_failed", event_data)

    def validate(self) -> bool:
        """Validate that service_name and error are present."""
        return (
            "service_name" in self.data
            and bool(self.data["service_name"])
            and "error" in self.data
            and bool(self.data["error"])
        )
