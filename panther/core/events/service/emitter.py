"""
Service Event Emitter

This module provides a type-safe event emitter for service-related events.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from panther.core.observer.event_manager import EventManager

from panther.core.events.service.events import (
    ServiceCreatedEvent,
    ServicePreparationStartedEvent,
    ServicePreparationCompletedEvent,
    ServicePreparationFailedEvent,
    ServiceDeploymentStartedEvent,
    ServiceDeploymentCompletedEvent,
    ServiceDeploymentFailedEvent,
    ServiceStartedEvent,
    ServiceReadyEvent,
    ServiceHealthCheckPassedEvent,
    ServiceHealthCheckFailedEvent,
    ServiceStoppedEvent,
    ServiceErrorEvent,
    ServiceDestroyedEvent,
)


class ServiceEventEmitter:
    """
    Type-safe event emitter for service-related events.

    This class provides methods for emitting all service lifecycle events
    with proper typing and validation.
    """

    def __init__(self, event_manager: "EventManager"):
        """
        Initialize the service event emitter.

        Args:
            event_manager: Event manager to use for event emission
        """
        self.event_manager = event_manager

    def emit_service_created(
        self,
        service_id: str,
        service_name: str,
        service_type: str,
        implementation: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a service created event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            service_type: Type of service (iut, tester, etc.)
            implementation: Implementation name
            config: Service configuration
        """
        event = ServiceCreatedEvent(
            service_id=service_id,
            service_name=service_name,
            service_type=service_type,
            implementation=implementation,
            config=config,
        )
        self.event_manager.notify(event)

    def emit_service_preparation_started(
        self, service_id: str, service_name: str, preparation_steps: list[str] | None = None
    ) -> None:
        """
        Emit a service preparation started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            preparation_steps: List of preparation steps to be performed
        """
        event = ServicePreparationStartedEvent(
            service_id=service_id, service_name=service_name, preparation_steps=preparation_steps
        )
        self.event_manager.notify(event)

    def emit_service_preparation_completed(
        self,
        service_id: str,
        service_name: str,
        duration_seconds: float | None = None,
        artifacts: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a service preparation completed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            duration_seconds: Time taken for preparation in seconds
            artifacts: Artifacts created during preparation
        """
        event = ServicePreparationCompletedEvent(
            service_id=service_id,
            service_name=service_name,
            duration_seconds=duration_seconds,
            artifacts=artifacts,
        )
        self.event_manager.notify(event)

    def emit_service_preparation_failed(
        self,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: str | None = None,
        failed_step: str | None = None,
    ) -> None:
        """
        Emit a service preparation failed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            error_message: Error message describing the failure
            error_type: Type/category of error
            failed_step: The preparation step that failed
        """
        event = ServicePreparationFailedEvent(
            service_id=service_id,
            service_name=service_name,
            error_message=error_message,
            error_type=error_type,
            failed_step=failed_step,
        )
        self.event_manager.notify(event)

    def emit_service_deployment_started(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        deployment_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a service deployment started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            environment: Target environment for deployment
            deployment_config: Deployment configuration
        """
        event = ServiceDeploymentStartedEvent(
            service_id=service_id,
            service_name=service_name,
            environment=environment,
            deployment_config=deployment_config,
        )
        self.event_manager.notify(event)

    def emit_service_deployment_completed(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        endpoint: str | None = None,
        ports: list[int] | None = None,
        deployment_details: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a service deployment completed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            environment: Target environment for deployment
            endpoint: Service endpoint if available
            ports: Service ports if available
            deployment_details: Additional deployment details
        """
        event = ServiceDeploymentCompletedEvent(
            service_id=service_id,
            service_name=service_name,
            environment=environment,
            endpoint=endpoint,
            ports=ports,
            deployment_details=deployment_details,
        )
        self.event_manager.notify(event)

    def emit_service_deployment_failed(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        error_message: str,
        error_type: str | None = None,
    ) -> None:
        """
        Emit a service deployment failed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            environment: Target environment for deployment
            error_message: Error message describing the failure
            error_type: Type/category of error
        """
        event = ServiceDeploymentFailedEvent(
            service_id=service_id,
            service_name=service_name,
            environment=environment,
            error_message=error_message,
            error_type=error_type,
        )
        self.event_manager.notify(event)

    def emit_service_started(
        self,
        service_id: str,
        service_name: str,
        pid: int | None = None,
        start_time: str | None = None,
    ) -> None:
        """
        Emit a service started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            pid: Process ID if available
            start_time: Service start time
        """
        event = ServiceStartedEvent(
            service_id=service_id, service_name=service_name, pid=pid, start_time=start_time
        )
        self.event_manager.notify(event)

    def emit_service_ready(
        self, service_id: str, service_name: str, readiness_checks: dict[str, bool] | None = None
    ) -> None:
        """
        Emit a service ready event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            readiness_checks: Results of readiness checks
        """
        event = ServiceReadyEvent(
            service_id=service_id, service_name=service_name, readiness_checks=readiness_checks
        )
        self.event_manager.notify(event)

    def emit_service_health_check_passed(
        self,
        service_id: str,
        service_name: str,
        check_type: str,
        endpoint: str | None = None,
        response_time_ms: float | None = None,
    ) -> None:
        """
        Emit a service health check passed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            check_type: Type of health check performed
            endpoint: Endpoint that was checked
            response_time_ms: Response time in milliseconds
        """
        event = ServiceHealthCheckPassedEvent(
            service_id=service_id,
            service_name=service_name,
            check_type=check_type,
            endpoint=endpoint,
            response_time_ms=response_time_ms,
        )
        self.event_manager.notify(event)

    def emit_service_health_check_failed(
        self,
        service_id: str,
        service_name: str,
        check_type: str,
        error_message: str,
        endpoint: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """
        Emit a service health check failed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            check_type: Type of health check performed
            error_message: Error message describing the failure
            endpoint: Endpoint that was checked
            status_code: HTTP status code if applicable
        """
        event = ServiceHealthCheckFailedEvent(
            service_id=service_id,
            service_name=service_name,
            check_type=check_type,
            error_message=error_message,
            endpoint=endpoint,
            status_code=status_code,
        )
        self.event_manager.notify(event)

    def emit_service_stopped(
        self,
        service_id: str,
        service_name: str,
        exit_code: int | None = None,
        reason: str | None = None,
        uptime_seconds: float | None = None,
    ) -> None:
        """
        Emit a service stopped event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            exit_code: Process exit code if available
            reason: Reason for stopping
            uptime_seconds: Service uptime in seconds
        """
        event = ServiceStoppedEvent(
            service_id=service_id,
            service_name=service_name,
            exit_code=exit_code,
            reason=reason,
            uptime_seconds=uptime_seconds,
        )
        self.event_manager.notify(event)

    def emit_service_error(
        self,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: str | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a service error event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            error_message: Error message
            error_type: Type/category of error
            error_details: Additional error details
        """
        event = ServiceErrorEvent(
            service_id=service_id,
            service_name=service_name,
            error_message=error_message,
            error_type=error_type,
            error_details=error_details,
        )
        self.event_manager.notify(event)

    def emit_service_destroyed(
        self, service_id: str, service_name: str, cleanup_details: dict[str, Any] | None = None
    ) -> None:
        """
        Emit a service destroyed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            cleanup_details: Details about what was cleaned up
        """
        event = ServiceDestroyedEvent(
            service_id=service_id, service_name=service_name, cleanup_details=cleanup_details
        )
        self.event_manager.notify(event)
