"""Service Events.

This module defines events specific to service lifecycle management.
Uses factory classmethods on the base ServiceEvent class instead of
individual subclasses for most event types.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

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
    """Base class for all service events.

    Most service events are created via factory classmethods rather than
    individual subclasses. The event_type discriminant identifies the
    specific event kind.
    """

    def __init__(
        self,
        event_type: ServiceEventType,
        service_id: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize service event."""
        super().__init__(
            name=event_type.value,
            entity_type=EventType.SERVICE,
            entity_id=service_id,
            data=data,
        )
        self.event_type = event_type

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def created(
        cls,
        service_id: str,
        service_name: str,
        service_type: str,
        implementation: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create created event."""
        return cls(
            ServiceEventType.CREATED,
            service_id,
            data={
                "service_name": service_name,
                "service_type": service_type,
                "implementation": implementation,
                "config": config or {},
            },
        )

    @classmethod
    def preparation_started(
        cls,
        service_id: str,
        service_name: str,
        preparation_steps: Optional[List[str]] = None,
    ) -> "ServiceEvent":
        """Create preparation started event."""
        return cls(
            ServiceEventType.PREPARATION_STARTED,
            service_id,
            data={
                "service_name": service_name,
                "preparation_steps": preparation_steps or [],
            },
        )

    @classmethod
    def preparation_completed(
        cls,
        service_id: str,
        service_name: str,
        duration_seconds: Optional[float] = None,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create preparation completed event."""
        return cls(
            ServiceEventType.PREPARATION_COMPLETED,
            service_id,
            data={
                "service_name": service_name,
                "duration_seconds": duration_seconds,
                "artifacts": artifacts or {},
            },
        )

    @classmethod
    def preparation_failed(
        cls,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: Optional[str] = None,
        failed_step: Optional[str] = None,
    ) -> "ServiceEvent":
        """Create preparation failed event."""
        return cls(
            ServiceEventType.PREPARATION_FAILED,
            service_id,
            data={
                "service_name": service_name,
                "error_message": error_message,
                "error_type": error_type,
                "failed_step": failed_step,
            },
        )

    @classmethod
    def deployment_started(
        cls,
        service_id: str,
        service_name: str,
        environment: str,
        deployment_config: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create deployment started event."""
        return cls(
            ServiceEventType.DEPLOYMENT_STARTED,
            service_id,
            data={
                "service_name": service_name,
                "environment": environment,
                "deployment_config": deployment_config or {},
            },
        )

    @classmethod
    def deployment_completed(
        cls,
        service_id: str,
        service_name: str,
        environment: str,
        endpoint: Optional[str] = None,
        ports: Optional[List[int]] = None,
        deployment_details: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create deployment completed event."""
        return cls(
            ServiceEventType.DEPLOYMENT_COMPLETED,
            service_id,
            data={
                "service_name": service_name,
                "environment": environment,
                "endpoint": endpoint,
                "ports": ports or [],
                "deployment_details": deployment_details or {},
            },
        )

    @classmethod
    def deployment_failed(
        cls,
        service_id: str,
        service_name: str,
        environment: str,
        error_message: str,
        error_type: Optional[str] = None,
    ) -> "ServiceEvent":
        """Create deployment failed event."""
        return cls(
            ServiceEventType.DEPLOYMENT_FAILED,
            service_id,
            data={
                "service_name": service_name,
                "environment": environment,
                "error_message": error_message,
                "error_type": error_type,
            },
        )

    @classmethod
    def started(
        cls,
        service_id: str,
        service_name: str,
        pid: Optional[int] = None,
        start_time: Optional[str] = None,
    ) -> "ServiceEvent":
        """Create started event."""
        return cls(
            ServiceEventType.STARTED,
            service_id,
            data={"service_name": service_name, "pid": pid, "start_time": start_time},
        )

    @classmethod
    def ready(
        cls,
        service_id: str,
        service_name: str,
        readiness_checks: Optional[Dict[str, bool]] = None,
    ) -> "ServiceEvent":
        """Create ready event."""
        return cls(
            ServiceEventType.READY,
            service_id,
            data={
                "service_name": service_name,
                "readiness_checks": readiness_checks or {},
            },
        )

    @classmethod
    def health_check_passed(
        cls,
        service_id: str,
        service_name: str,
        check_type: str,
        endpoint: Optional[str] = None,
        response_time_ms: Optional[float] = None,
    ) -> "ServiceEvent":
        """Create health check passed event."""
        return cls(
            ServiceEventType.HEALTH_CHECK_PASSED,
            service_id,
            data={
                "service_name": service_name,
                "check_type": check_type,
                "endpoint": endpoint,
                "response_time_ms": response_time_ms,
            },
        )

    @classmethod
    def health_check_failed(
        cls,
        service_id: str,
        service_name: str,
        check_type: str,
        error_message: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> "ServiceEvent":
        """Create health check failed event."""
        return cls(
            ServiceEventType.HEALTH_CHECK_FAILED,
            service_id,
            data={
                "service_name": service_name,
                "check_type": check_type,
                "error_message": error_message,
                "endpoint": endpoint,
                "status_code": status_code,
            },
        )

    @classmethod
    def stopped(
        cls,
        service_id: str,
        service_name: str,
        exit_code: Optional[int] = None,
        reason: Optional[str] = None,
        uptime_seconds: Optional[float] = None,
    ) -> "ServiceEvent":
        """Create stopped event."""
        return cls(
            ServiceEventType.STOPPED,
            service_id,
            data={
                "service_name": service_name,
                "exit_code": exit_code,
                "reason": reason,
                "uptime_seconds": uptime_seconds,
            },
        )

    @classmethod
    def error(
        cls,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create error event."""
        return cls(
            ServiceEventType.ERROR,
            service_id,
            data={
                "service_name": service_name,
                "error_message": error_message,
                "error_type": error_type,
                "error_details": error_details or {},
            },
        )

    @classmethod
    def destroyed(
        cls,
        service_id: str,
        service_name: str,
        cleanup_details: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create destroyed event."""
        return cls(
            ServiceEventType.DESTROYED,
            service_id,
            data={
                "service_name": service_name,
                "cleanup_details": cleanup_details or {},
            },
        )

    @classmethod
    def test_results(
        cls,
        service_id: str,
        service_name: str,
        test_results: Dict[str, Any],
        overall_success: bool,
        test_summary: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create test results event."""
        return cls(
            ServiceEventType.TEST_RESULTS,
            service_id,
            data={
                "service_name": service_name,
                "test_results": test_results,
                "overall_success": overall_success,
                "test_summary": test_summary or {},
                "action": "service_test_results",
            },
        )

    @classmethod
    def command_generation_started(
        cls,
        service_id: str,
        service_name: str,
        phase: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create command generation started event."""
        return cls(
            ServiceEventType.PREPARATION_STARTED,
            service_id,
            data={
                "service_name": service_name,
                "phase": phase,
                "config": config or {},
                "action": "command_generation_started",
            },
        )

    @classmethod
    def command_generated(
        cls,
        service_id: str,
        service_name: str,
        phase: str,
        command: str,
        command_type: Optional[str] = None,
    ) -> "ServiceEvent":
        """Create command generated event."""
        return cls(
            ServiceEventType.PREPARATION_COMPLETED,
            service_id,
            data={
                "service_name": service_name,
                "phase": phase,
                "command": command,
                "command_type": command_type,
                "action": "command_generated",
            },
        )

    @classmethod
    def command_modified(
        cls,
        service_id: str,
        service_name: str,
        phase: str,
        original_command: str,
        modified_command: str,
        modifier: str,
        modification_details: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create command modified event."""
        return cls(
            ServiceEventType.PREPARATION_COMPLETED,
            service_id,
            data={
                "service_name": service_name,
                "phase": phase,
                "original_command": original_command,
                "modified_command": modified_command,
                "modifier": modifier,
                "modification_details": modification_details or {},
                "action": "command_modified",
            },
        )

    @classmethod
    def config_generated(
        cls,
        service_id: str,
        config_type: str,
        config_path: str,
        config_content: Optional[str] = None,
        services_included: Optional[List[str]] = None,
    ) -> "ServiceEvent":
        """Create config generated event."""
        return cls(
            ServiceEventType.DEPLOYMENT_STARTED,
            service_id,
            data={
                "config_type": config_type,
                "config_path": config_path,
                "config_content": config_content,
                "services_included": services_included or [],
                "action": "config_generated",
            },
        )

    @classmethod
    def tester_analysis_started(
        cls,
        service_id: str,
        tester_name: str,
        inputs: Dict[str, str],
        analysis_type: str,
    ) -> "ServiceEvent":
        """Create tester analysis started event."""
        return cls(
            ServiceEventType.TEST_RESULTS,
            service_id,
            data={
                "tester_name": tester_name,
                "inputs": inputs,
                "analysis_type": analysis_type,
                "action": "tester_analysis_started",
            },
        )

    @classmethod
    def tester_analysis_completed(
        cls,
        service_id: str,
        tester_name: str,
        passed: bool,
        failed_checks: List[str],
        warnings: Optional[List[str]] = None,
        detailed_results: Optional[Dict[str, Any]] = None,
    ) -> "ServiceEvent":
        """Create tester analysis completed event."""
        return cls(
            ServiceEventType.TEST_RESULTS,
            service_id,
            data={
                "tester_name": tester_name,
                "passed": passed,
                "failed_checks": failed_checks,
                "warnings": warnings or [],
                "detailed_results": detailed_results or {},
                "action": "tester_analysis_completed",
            },
        )


# -- Subclasses kept for isinstance() compatibility ---------------------------
# These are used in observer isinstance() checks (logger_observer.py).


class DockerBuildStartedEvent(ServiceEvent):
    """Event emitted when Docker build starts for a service."""

    def __init__(
        self,
        service_id: str,
        service_name: str,
        dockerfile_path: str,
        image_name: Optional[str] = None,
    ):
        """Initialize with service ID, name, dockerfile path, and image name."""
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
        error_message: Optional[str] = None,
        build_duration: Optional[float] = None,
    ):
        """Initialize with service ID, image name, and build result."""
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
        build_duration: Optional[float] = None,
    ):
        """Initialize with service ID, dockerfile path, and error details."""
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
