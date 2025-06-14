"""
Service Events

This module defines events specific to service lifecycle management.
"""

from enum import Enum
from typing import Any

from panther.core.events.base.event_base import BaseEvent, EventType


class ServiceEventType(Enum):
    """Service-specific event types."""

    CREATED = "created"
    PREPARATION_STARTED = "preparation_started"
    PREPARATION_COMPLETED = "preparation_completed"
    PREPARATION_FAILED = "preparation_failed"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"
    STARTED = "started"
    READY = "ready"
    HEALTH_CHECK_PASSED = "health_check_passed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    STOPPED = "stopped"
    ERROR = "error"
    DESTROYED = "destroyed"
    TEST_RESULTS = "test_results"


class ServiceEvent(BaseEvent):
    """Base class for all service events."""

    def __init__(
        self, event_type: ServiceEventType, service_id: str, data: dict[str, Any] | None = None
    ):
        super().__init__(
            name=event_type.value, entity_type=EventType.SERVICE, entity_id=service_id, data=data
        )
        self.event_type = event_type


class ServiceCreatedEvent(ServiceEvent):
    """Event emitted when a service is created."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        service_type: str,
        implementation: str,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.CREATED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "service_type": service_type,
                "implementation": implementation,
                "config": config or {},
            },
        )


class ServicePreparationStartedEvent(ServiceEvent):
    """Event emitted when service preparation starts."""

    def __init__(
        self, service_id: str, service_name: str, preparation_steps: list[str] | None = None
    ):
        super().__init__(
            event_type=ServiceEventType.PREPARATION_STARTED,
            service_id=service_id,
            data={"service_name": service_name, "preparation_steps": preparation_steps or []},
        )


class ServicePreparationCompletedEvent(ServiceEvent):
    """Event emitted when service preparation completes."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        duration_seconds: float | None = None,
        artifacts: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.PREPARATION_COMPLETED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "duration_seconds": duration_seconds,
                "artifacts": artifacts or {},
            },
        )


class ServicePreparationFailedEvent(ServiceEvent):
    """Event emitted when service preparation fails."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: str | None = None,
        failed_step: str | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.PREPARATION_FAILED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "error_message": error_message,
                "error_type": error_type,
                "failed_step": failed_step,
            },
        )


class ServiceDeploymentStartedEvent(ServiceEvent):
    """Event emitted when service deployment starts."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        deployment_config: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.DEPLOYMENT_STARTED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "environment": environment,
                "deployment_config": deployment_config or {},
            },
        )


class ServiceDeploymentCompletedEvent(ServiceEvent):
    """Event emitted when service deployment completes."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        endpoint: str | None = None,
        ports: list[int] | None = None,
        deployment_details: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.DEPLOYMENT_COMPLETED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "environment": environment,
                "endpoint": endpoint,
                "ports": ports or [],
                "deployment_details": deployment_details or {},
            },
        )


class ServiceDeploymentFailedEvent(ServiceEvent):
    """Event emitted when service deployment fails."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        error_message: str,
        error_type: str | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.DEPLOYMENT_FAILED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "environment": environment,
                "error_message": error_message,
                "error_type": error_type,
            },
        )


class ServiceStartedEvent(ServiceEvent):
    """Event emitted when a service starts."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        pid: int | None = None,
        start_time: str | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.STARTED,
            service_id=service_id,
            data={"service_name": service_name, "pid": pid, "start_time": start_time},
        )


class ServiceReadyEvent(ServiceEvent):
    """Event emitted when a service is ready to accept requests."""

    def __init__(
        self, service_id: str, service_name: str, readiness_checks: dict[str, bool] | None = None
    ):
        super().__init__(
            event_type=ServiceEventType.READY,
            service_id=service_id,
            data={"service_name": service_name, "readiness_checks": readiness_checks or {}},
        )


class ServiceHealthCheckPassedEvent(ServiceEvent):
    """Event emitted when a service health check passes."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        check_type: str,
        endpoint: str | None = None,
        response_time_ms: float | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.HEALTH_CHECK_PASSED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "check_type": check_type,
                "endpoint": endpoint,
                "response_time_ms": response_time_ms,
            },
        )


class ServiceHealthCheckFailedEvent(ServiceEvent):
    """Event emitted when a service health check fails."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        check_type: str,
        error_message: str,
        endpoint: str | None = None,
        status_code: int | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.HEALTH_CHECK_FAILED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "check_type": check_type,
                "error_message": error_message,
                "endpoint": endpoint,
                "status_code": status_code,
            },
        )


class ServiceStoppedEvent(ServiceEvent):
    """Event emitted when a service stops."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        exit_code: int | None = None,
        reason: str | None = None,
        uptime_seconds: float | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.STOPPED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "exit_code": exit_code,
                "reason": reason,
                "uptime_seconds": uptime_seconds,
            },
        )


class ServiceErrorEvent(ServiceEvent):
    """Event emitted when a service encounters an error."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: str | None = None,
        error_details: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.ERROR,
            service_id=service_id,
            data={
                "service_name": service_name,
                "error_message": error_message,
                "error_type": error_type,
                "error_details": error_details or {},
            },
        )


class ServiceDestroyedEvent(ServiceEvent):
    """Event emitted when a service is destroyed/cleaned up."""

    def __init__(
        self, service_id: str, service_name: str, cleanup_details: dict[str, Any] | None = None
    ):
        super().__init__(
            event_type=ServiceEventType.DESTROYED,
            service_id=service_id,
            data={"service_name": service_name, "cleanup_details": cleanup_details or {}},
        )


class ServiceTestResultsEvent(ServiceEvent):
    """Event emitted when service test results are available."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        test_results: dict[str, Any],
        overall_success: bool,
        test_summary: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.TEST_RESULTS,
            service_id=service_id,
            data={
                "service_name": service_name,
                "test_results": test_results,
                "overall_success": overall_success,
                "test_summary": test_summary or {},
                "action": "service_test_results",
            },
        )

    @property
    def test_results(self) -> dict[str, Any]:
        return self.data.get("test_results", {})

    @property
    def overall_success(self) -> bool:
        return self.data.get("overall_success", False)

    @property
    def test_summary(self) -> dict[str, Any]:
        return self.data.get("test_summary", {})


class CommandGenerationStartedEvent(ServiceEvent):
    """Event emitted when command generation starts for a service."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        phase: str,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.PREPARATION_STARTED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "phase": phase,
                "config": config or {},
                "action": "command_generation_started",
            },
        )


class CommandGeneratedEvent(ServiceEvent):
    """Event emitted when a command is generated for a service."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        phase: str,
        command: str,
        command_type: str | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.PREPARATION_COMPLETED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "phase": phase,
                "command": command,
                "command_type": command_type,
                "action": "command_generated",
            },
        )


class DockerBuildStartedEvent(ServiceEvent):
    """Event emitted when Docker build starts for a service."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        dockerfile_path: str,
        image_name: str | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.PREPARATION_STARTED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "dockerfile_path": dockerfile_path,
                "image_name": image_name,
                "action": "docker_build_started",
            },
        )


class DockerBuildCompletedEvent(ServiceEvent):
    """Event emitted when Docker build completes for a service."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        image_name: str,
        success: bool,
        error_message: str | None = None,
        build_duration: float | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.PREPARATION_COMPLETED,
            service_id=service_id,
            data={
                "service_name": service_name,
                "image_name": image_name,
                "success": success,
                "error_message": error_message,
                "build_duration": build_duration,
                "action": "docker_build_completed",
            },
        )


class DockerBuildFailedEvent(ServiceEvent):
    """Event emitted when Docker build fails for a service."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        dockerfile_path: str,
        error_message: str,
        build_duration: float | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.ERROR,
            service_id=service_id,
            data={
                "service_name": service_name,
                "dockerfile_path": dockerfile_path,
                "error_message": error_message,
                "build_duration": build_duration,
                "action": "docker_build_failed",
            },
        )


class TesterAnalysisStartedEvent(ServiceEvent):
    """Event emitted when tester starts analyzing collected outputs."""

    def __init__(
        self,
        service_id: str,
        tester_name: str,
        inputs: dict[str, str],
        analysis_type: str,
    ):
        super().__init__(
            event_type=ServiceEventType.TEST_RESULTS,
            service_id=service_id,
            data={
                "tester_name": tester_name,
                "inputs": inputs,
                "analysis_type": analysis_type,
                "action": "tester_analysis_started",
            },
        )


class TesterAnalysisCompletedEvent(ServiceEvent):
    """Event emitted when tester completes analysis of collected outputs."""

    def __init__(
        self,
        service_id: str,
        tester_name: str,
        passed: bool,
        failed_checks: list[str],
        warnings: list[str] | None = None,
        detailed_results: dict[str, Any] | None = None,
    ):
        super().__init__(
            event_type=ServiceEventType.TEST_RESULTS,
            service_id=service_id,
            data={
                "tester_name": tester_name,
                "passed": passed,
                "failed_checks": failed_checks,
                "warnings": warnings or [],
                "detailed_results": detailed_results or {},
                "action": "tester_analysis_completed",
            },
        )
