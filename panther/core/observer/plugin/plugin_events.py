"""
Plugin Events Module

This module defines domain-specific event classes for different plugin types.
These events facilitate communication between plugins in an event-driven architecture.
"""

from typing import Any

from panther.core.observer.core.core_events import Event


# Base event class for plugin communication
class PluginEvent(Event):
    """Base class for plugin-to-plugin communication events."""

    def __init__(self, name: str, source_plugin_id: str, data: dict[str, Any] = None):
        """
        Initialize a new PluginEvent.

        Args:
            name: Event name/identifier
            source_plugin_id: ID of the plugin that generated the event
            data: Additional event data
        """
        super().__init__(name=name, data=data or {})
        self.source_plugin_id = source_plugin_id
        self.data["source_plugin_id"] = source_plugin_id

    def get_source_plugin_id(self) -> str:
        """
        Get the ID of the plugin that generated this event.

        Returns:
            str: Source plugin ID
        """
        return self.source_plugin_id


# Service plugin events
class ServiceEvent(PluginEvent):
    """Base class for service-related events."""

    def __init__(
        self, name: str, service_id: str, source_plugin_id: str, data: dict[str, Any] = None
    ):
        """
        Initialize a new ServiceEvent.

        Args:
            name: Event name/identifier
            service_id: ID of the service
            source_plugin_id: ID of the plugin that generated the event
            data: Additional event data
        """
        super().__init__(f"service.{name}", source_plugin_id, data or {})
        self.service_id = service_id
        self.data["service_id"] = service_id


class ServiceStartingEvent(ServiceEvent):
    """Event emitted when a service is starting."""

    def __init__(
        self, service_id: str, source_plugin_id: str, service_type: str, data: dict[str, Any] = None
    ):
        """
        Initialize a new ServiceStartingEvent.

        Args:
            service_id: ID of the service
            source_plugin_id: ID of the plugin that generated the event
            service_type: Type of the service
            data: Additional event data
        """
        super().__init__("starting", service_id, source_plugin_id, data or {})
        self.service_type = service_type
        self.data["service_type"] = service_type


class ServiceReadyEvent(ServiceEvent):
    """Event emitted when a service is ready to accept connections."""

    def __init__(
        self,
        service_id: str,
        source_plugin_id: str,
        endpoint: str,
        service_type: str,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a new ServiceReadyEvent.

        Args:
            service_id: ID of the service
            source_plugin_id: ID of the plugin that generated the event
            endpoint: Service endpoint (e.g., host:port)
            service_type: Type of the service
            data: Additional event data
        """
        super().__init__("ready", service_id, source_plugin_id, data or {})
        self.endpoint = endpoint
        self.service_type = service_type
        self.data["endpoint"] = endpoint
        self.data["service_type"] = service_type


class ServiceStoppingEvent(ServiceEvent):
    """Event emitted when a service is about to stop."""

    def __init__(
        self,
        service_id: str,
        source_plugin_id: str,
        reason: str = None,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a new ServiceStoppingEvent.

        Args:
            service_id: ID of the service
            source_plugin_id: ID of the plugin that generated the event
            reason: Reason for stopping
            data: Additional event data
        """
        super().__init__("stopping", service_id, source_plugin_id, data or {})
        self.reason = reason
        if reason:
            self.data["reason"] = reason


class ServiceStoppedEvent(ServiceEvent):
    """Event emitted when a service has stopped."""

    def __init__(
        self,
        service_id: str,
        source_plugin_id: str,
        success: bool,
        error_message: str = None,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a new ServiceStoppedEvent.

        Args:
            service_id: ID of the service
            source_plugin_id: ID of the plugin that generated the event
            success: Whether the service stopped successfully
            error_message: Error message if stop was unsuccessful
            data: Additional event data
        """
        super().__init__("stopped", service_id, source_plugin_id, data or {})
        self.success = success
        self.error_message = error_message
        self.data["success"] = success
        if error_message:
            self.data["error_message"] = error_message


class ServiceRequestEvent(PluginEvent):
    """Event emitted when a plugin requests a service."""

    def __init__(
        self,
        requester_id: str,
        service_type: str,
        parameters: dict[str, Any] = None,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a new ServiceRequestEvent.

        Args:
            requester_id: ID of the requester plugin
            service_type: Type of service being requested
            parameters: Parameters for the service request
            data: Additional event data
        """
        super().__init__("service.request", requester_id, data or {})
        self.service_type = service_type
        self.parameters = parameters or {}
        self.data["service_type"] = service_type
        self.data["parameters"] = self.parameters


# Environment plugin events
class EnvironmentEvent(PluginEvent):
    """Base class for environment-related events."""

    def __init__(
        self, name: str, environment_id: str, source_plugin_id: str, data: dict[str, Any] = None
    ):
        """
        Initialize a new EnvironmentEvent.

        Args:
            name: Event name/identifier
            environment_id: ID of the environment
            source_plugin_id: ID of the plugin that generated the event
            data: Additional event data
        """
        super().__init__(f"environment.{name}", source_plugin_id, data or {})
        self.environment_id = environment_id
        self.data["environment_id"] = environment_id


class EnvironmentResourceEvent(EnvironmentEvent):
    """Base class for environment resource events."""

    def __init__(
        self,
        name: str,
        environment_id: str,
        resource_id: str,
        resource_type: str,
        source_plugin_id: str,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a new EnvironmentResourceEvent.

        Args:
            name: Event name/identifier
            environment_id: ID of the environment
            resource_id: ID of the resource
            resource_type: Type of resource
            source_plugin_id: ID of the plugin that generated the event
            data: Additional event data
        """
        super().__init__(name, environment_id, source_plugin_id, data or {})
        self.resource_id = resource_id
        self.resource_type = resource_type
        self.data["resource_id"] = resource_id
        self.data["resource_type"] = resource_type


class EnvironmentResourceAllocatedEvent(EnvironmentResourceEvent):
    """Event emitted when an environment resource has been allocated."""

    def __init__(
        self,
        environment_id: str,
        resource_id: str,
        resource_type: str,
        source_plugin_id: str,
        resource_details: dict[str, Any] = None,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a new EnvironmentResourceAllocatedEvent.

        Args:
            environment_id: ID of the environment
            resource_id: ID of the allocated resource
            resource_type: Type of resource
            source_plugin_id: ID of the plugin that generated the event
            resource_details: Details about the allocated resource
            data: Additional event data
        """
        super().__init__(
            "resource.allocated",
            environment_id,
            resource_id,
            resource_type,
            source_plugin_id,
            data or {},
        )
        self.resource_details = resource_details or {}
        self.data["resource_details"] = self.resource_details


class EnvironmentResourceReleasedEvent(EnvironmentResourceEvent):
    """Event emitted when an environment resource has been released."""

    def __init__(
        self,
        environment_id: str,
        resource_id: str,
        resource_type: str,
        source_plugin_id: str,
        success: bool = True,
        error_message: str = None,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a new EnvironmentResourceReleasedEvent.

        Args:
            environment_id: ID of the environment
            resource_id: ID of the released resource
            resource_type: Type of resource
            source_plugin_id: ID of the plugin that generated the event
            success: Whether the resource was released successfully
            error_message: Error message if release was unsuccessful
            data: Additional event data
        """
        super().__init__(
            "resource.released",
            environment_id,
            resource_id,
            resource_type,
            source_plugin_id,
            data or {},
        )
        self.success = success
        self.error_message = error_message
        self.data["success"] = success
        if error_message:
            self.data["error_message"] = error_message


# Tester plugin events
class TesterEvent(PluginEvent):
    """Base class for tester-related events."""

    def __init__(self, name: str, test_id: str, source_plugin_id: str, data: dict[str, Any] = None):
        """
        Initialize a new TesterEvent.

        Args:
            name: Event name/identifier
            test_id: ID of the test
            source_plugin_id: ID of the plugin that generated the event
            data: Additional event data
        """
        super().__init__(f"tester.{name}", source_plugin_id, data or {})
        self.test_id = test_id
        self.data["test_id"] = test_id


class TestStartingEvent(TesterEvent):
    """Event emitted when a test is starting."""

    def __init__(
        self, test_id: str, source_plugin_id: str, test_type: str, data: dict[str, Any] = None
    ):
        """
        Initialize a new TestStartingEvent.

        Args:
            test_id: ID of the test
            source_plugin_id: ID of the plugin that generated the event
            test_type: Type of the test
            data: Additional event data
        """
        super().__init__("starting", test_id, source_plugin_id, data or {})
        self.test_type = test_type
        self.data["test_type"] = test_type


class TestCompletedEvent(TesterEvent):
    """Event emitted when a test has completed."""

    def __init__(
        self,
        test_id: str,
        source_plugin_id: str,
        success: bool,
        result: dict[str, Any] = None,
        error_message: str = None,
        data: dict[str, Any] = None,
    ):
        """
        Initialize a new TestCompletedEvent.

        Args:
            test_id: ID of the test
            source_plugin_id: ID of the plugin that generated the event
            success: Whether the test completed successfully
            result: Test result data
            error_message: Error message if test was unsuccessful
            data: Additional event data
        """
        super().__init__("completed", test_id, source_plugin_id, data or {})
        self.success = success
        self.result = result or {}
        self.error_message = error_message
        self.data["success"] = success
        self.data["result"] = self.result
        if error_message:
            self.data["error_message"] = error_message
