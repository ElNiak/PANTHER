"""Service Event Emitter.

This module provides a type-safe event emitter for service-related events.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EventEmitterBase
from panther.core.events.service.events import (
    DockerBuildCompletedEvent,
    DockerBuildFailedEvent,
    DockerBuildStartedEvent,
    ServiceEvent,
)


class ServiceEventEmitter(EventEmitterBase):
    """Type-safe event emitter for service-related events.

    This class provides methods for emitting all service lifecycle events
    with proper typing and validation.
    """

    def __init__(self, event_manager: "EventManager"):
        """Initialize the service event emitter.

        Args:
            event_manager: Event manager to use for event emission
        """
        super().__init__(event_manager)

    def emit_service_created(
        self,
        service_id: str,
        service_name: str,
        service_type: str,
        implementation: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a service created event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            service_type: Type of service (iut, tester, etc.)
            implementation: Implementation name
            config: Service configuration
        """
        event = ServiceEvent.created(
            service_id, service_name, service_type, implementation, config
        )
        self.event_manager.notify(event)

    def emit_service_setup_started(
        self,
        test_case: str,
        service_count: int,
        service_names: Optional[List[str]] = None,
        service_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Emit a service setup started event for a test case.

        Args:
            test_case: Name of the test case
            service_count: Number of services being set up
            service_names: List of service names
            service_metadata: List of service metadata dictionaries containing type and implementation info
        """
        # First emit service created events for each service
        for i, service_name in enumerate(service_names or []):
            service_id = f"{test_case}_{service_name}"

            # Extract metadata if available
            metadata = {}
            if service_metadata and i < len(service_metadata):
                metadata = service_metadata[i]

            service_type = metadata.get("service_type", "unknown")
            implementation = metadata.get("implementation", "unknown")
            config = metadata.get("config", {"test_case": test_case})

            # Emit service created event first
            created_event = ServiceEvent.created(
                service_id, service_name, service_type, implementation, config
            )
            self.event_manager.notify(created_event)

            # Then emit service preparation started event
            prep_event = ServiceEvent.preparation_started(
                service_id, service_name, ["setup"]
            )
            # Add test metadata to the event data
            prep_event.add_data("test_case", test_case)
            prep_event.add_data("service_count", service_count)
            self.event_manager.notify(prep_event)

    def emit_service_preparation_started(
        self,
        service_id: str,
        service_name: str,
        preparation_steps: Optional[List[str]] = None,
        test_case: Optional[str] = None,
    ) -> None:
        """Emit a service preparation started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            preparation_steps: List of preparation steps to be performed
            test_case: Optional test case name for context
        """
        event = ServiceEvent.preparation_started(
            service_id, service_name, preparation_steps
        )
        # Add test metadata if provided
        if test_case:
            event.add_data("test_case", test_case)
        self.event_manager.notify(event)

    def emit_service_preparation_completed(
        self,
        service_id: str,
        service_name: str,
        duration_seconds: Optional[float] = None,
        artifacts: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a service preparation completed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            duration_seconds: Time taken for preparation in seconds
            artifacts: Artifacts created during preparation
        """
        event = ServiceEvent.preparation_completed(
            service_id, service_name, duration_seconds, artifacts
        )
        self.event_manager.notify(event)

    def emit_service_preparation_failed(
        self,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: Optional[str] = None,
        failed_step: Optional[str] = None,
    ) -> None:
        """Emit a service preparation failed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            error_message: Error message describing the failure
            error_type: Type/category of error
            failed_step: The preparation step that failed
        """
        event = ServiceEvent.preparation_failed(
            service_id, service_name, error_message, error_type, failed_step
        )
        self.event_manager.notify(event)

    def emit_service_deployment_started(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        deployment_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a service deployment started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            environment: Target environment for deployment
            deployment_config: Deployment configuration
        """
        event = ServiceEvent.deployment_started(
            service_id, service_name, environment, deployment_config
        )
        self.event_manager.notify(event)

    def emit_service_deployment_completed(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        endpoint: Optional[str] = None,
        ports: Optional[List[int]] = None,
        deployment_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a service deployment completed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            environment: Target environment for deployment
            endpoint: Service endpoint if available
            ports: Service ports if available
            deployment_details: Additional deployment details
        """
        event = ServiceEvent.deployment_completed(
            service_id, service_name, environment, endpoint, ports, deployment_details
        )
        self.event_manager.notify(event)

    def emit_service_deployment_failed(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        error_message: str,
        error_type: Optional[str] = None,
    ) -> None:
        """Emit a service deployment failed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            environment: Target environment for deployment
            error_message: Error message describing the failure
            error_type: Type/category of error
        """
        event = ServiceEvent.deployment_failed(
            service_id, service_name, environment, error_message, error_type
        )
        self.event_manager.notify(event)

    def emit_service_started(
        self,
        service_id: str,
        service_name: str,
        pid: Optional[int] = None,
        start_time: Optional[str] = None,
    ) -> None:
        """Emit a service started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            pid: Process ID if available
            start_time: Service start time
        """
        event = ServiceEvent.started(service_id, service_name, pid, start_time)
        self.event_manager.notify(event)

    def emit_service_ready(
        self,
        service_id: str,
        service_name: str,
        readiness_checks: Optional[Dict[str, bool]] = None,
    ) -> None:
        """Emit a service ready event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            readiness_checks: Results of readiness checks
        """
        event = ServiceEvent.ready(service_id, service_name, readiness_checks)
        self.event_manager.notify(event)

    def emit_service_health_check_passed(
        self,
        service_id: str,
        service_name: str,
        check_type: str,
        endpoint: Optional[str] = None,
        response_time_ms: Optional[float] = None,
    ) -> None:
        """Emit a service health check passed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            check_type: Type of health check performed
            endpoint: Endpoint that was checked
            response_time_ms: Response time in milliseconds
        """
        event = ServiceEvent.health_check_passed(
            service_id, service_name, check_type, endpoint, response_time_ms
        )
        self.event_manager.notify(event)

    def emit_service_health_check_failed(
        self,
        service_id: str,
        service_name: str,
        check_type: str,
        error_message: str,
        endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        """Emit a service health check failed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            check_type: Type of health check performed
            error_message: Error message describing the failure
            endpoint: Endpoint that was checked
            status_code: HTTP status code if applicable
        """
        event = ServiceEvent.health_check_failed(
            service_id, service_name, check_type, error_message, endpoint, status_code
        )
        self.event_manager.notify(event)

    def emit_service_stopped(
        self,
        service_id: str,
        service_name: str,
        exit_code: Optional[int] = None,
        reason: Optional[str] = None,
        uptime_seconds: Optional[float] = None,
    ) -> None:
        """Emit a service stopped event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            exit_code: Process exit code if available
            reason: Reason for stopping
            uptime_seconds: Service uptime in seconds
        """
        event = ServiceEvent.stopped(
            service_id, service_name, exit_code, reason, uptime_seconds
        )
        self.event_manager.notify(event)

    def emit_service_error(
        self,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a service error event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            error_message: Error message
            error_type: Type/category of error
            error_details: Additional error details
        """
        event = ServiceEvent.error(
            service_id, service_name, error_message, error_type, error_details
        )
        self.event_manager.notify(event)

    def emit_service_destroyed(
        self,
        service_id: str,
        service_name: str,
        cleanup_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a service destroyed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            cleanup_details: Details about what was cleaned up
        """
        event = ServiceEvent.destroyed(service_id, service_name, cleanup_details)
        self.event_manager.notify(event)

    def emit_tester_analysis_started(
        self,
        service_id: str,
        service_name: str,
        test_name: str,
        output_types: Optional[List[str]] = None,
        tester_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a tester analysis started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            test_name: Name of the test being analyzed
            output_types: Types of outputs being analyzed
            tester_config: Tester configuration data
        """
        # Map the parameters to match TesterAnalysisStartedEvent signature
        inputs = {
            "test_name": test_name,
            "output_types": str(output_types or []),
            "tester_config": str(tester_config or {}),
        }

        event = ServiceEvent.tester_analysis_started(
            service_id, service_name, inputs, "tester_analysis"
        )
        self.event_manager.notify(event)

    def emit_tester_analysis_completed(
        self,
        service_id: str,
        service_name: str,
        test_name: str,
        analysis_passed: bool = True,
        findings: Optional[Dict[str, Any]] = None,
        summary: str = "",
        duration: Optional[float] = None,
    ) -> None:
        """Emit a tester analysis completed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            test_name: Name of the test analyzed
            analysis_passed: Whether the analysis passed
            findings: Analysis findings/results
            summary: Summary of the analysis
            duration: Duration of the analysis in seconds
        """
        # Extract failed checks and warnings from findings
        failed_checks = []
        warnings = []

        if findings:
            # Handle different formats of findings
            if isinstance(findings, dict):
                failed_checks = findings.get("failed_checks", [])
                warnings = findings.get("warnings", [])
                # If findings has errors or failures, extract them
                if "errors" in findings:
                    failed_checks.extend(findings["errors"])
                if "failures" in findings:
                    failed_checks.extend(findings["failures"])
            elif isinstance(findings, list):
                # If findings is a list, treat as failed checks
                failed_checks = findings

        # Create detailed results including all information
        detailed_results = {
            "test_name": test_name,
            "summary": summary,
            "duration_seconds": duration,
            "findings": findings,
        }

        # Create the event with the correct factory method signature
        event = ServiceEvent.tester_analysis_completed(
            service_id,
            service_name,
            analysis_passed,
            failed_checks,
            warnings,
            detailed_results,
        )
        self.event_manager.notify(event)

    def emit_service_event(
        self,
        event_type: str,
        service_id: str,
        service_name: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a generic service event.

        This method provides a flexible way to emit service events
        that don't fit into the predefined categories.

        Args:
            event_type: Type of event to emit
            service_id: Unique service identifier
            service_name: Human-readable service name
            data: Event-specific data
        """
        # Map generic event types to specific methods if possible
        event_map = {
            "started": self.emit_service_started,
            "stopped": self.emit_service_stopped,
            "error": self.emit_service_error,
            "ready": self.emit_service_ready,
        }

        if event_type in event_map:
            method = event_map[event_type]
            method(service_id=service_id, service_name=service_name)
        else:
            # For unmapped events, emit as a service error with the event data
            self.emit_service_error(
                service_id=service_id,
                service_name=service_name,
                error_message=f"Generic service event: {event_type}",
                error_type="generic_event",
                error_details=data,
            )

    def emit_command_generation_started(
        self,
        service_id: str,
        service_name: str,
        phase: str,
        implementation: Optional[str] = None,
        protocol: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit command generation started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            phase: Command generation phase (pre_compile, compile, etc.)
            implementation: Implementation name
            protocol: Protocol name
            config: Configuration for command generation
        """
        event = ServiceEvent.command_generation_started(
            service_id, service_name, phase, config
        )
        self.event_manager.notify(event)

    def emit_command_generated(
        self,
        service_id: str,
        service_name: str,
        phase: str,
        command: str,
        implementation: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> None:
        """Emit command generated event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            phase: Command generation phase
            command: Generated command
            implementation: Implementation name
            protocol: Protocol name
        """
        event = ServiceEvent.command_generated(service_id, service_name, phase, command)
        self.event_manager.notify(event)

    def emit_docker_build_started(
        self,
        service_id: str,
        service_name: str,
        dockerfile_path: str,
        implementation: Optional[str] = None,
        image_name: Optional[str] = None,
    ) -> None:
        """Emit Docker build started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            dockerfile_path: Path to Dockerfile
            implementation: Implementation name
            image_name: Docker image name being built
        """
        event = DockerBuildStartedEvent(
            service_id=service_id,
            service_name=service_name,
            dockerfile_path=dockerfile_path,
            image_name=image_name or "",
        )
        self.event_manager.notify(event)

    def emit_docker_build_completed(
        self,
        service_id: str,
        service_name: str,
        image_name: str,
        success: bool,
        build_duration: Optional[float] = None,
    ) -> None:
        """Emit Docker build completed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            image_name: Docker image name that was built
            success: Whether build was successful
            build_duration: Build duration in seconds
        """
        event = DockerBuildCompletedEvent(
            service_id=service_id,
            service_name=service_name,
            image_name=image_name,
            success=success,
            build_duration=build_duration or 0,
        )
        self.event_manager.notify(event)

    def emit_docker_build_failed(
        self,
        service_id: str,
        service_name: str,
        error_message: str,
        dockerfile_path: str,
        build_duration: Optional[float] = None,
    ) -> None:
        """Emit Docker build failed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            error_message: Error message describing the failure
            dockerfile_path: Path to Dockerfile that failed to build
            build_duration: Duration of the failed build attempt
        """
        event = DockerBuildFailedEvent(
            service_id=service_id,
            service_name=service_name,
            dockerfile_path=dockerfile_path,
            error_message=error_message,
            build_duration=build_duration,
        )
        self.event_manager.notify(event)

    def emit_service_teardown_started(self, service_event, **kwargs):
        """Emit service teardown started event."""
        # For backward compatibility, handle both old and new style calls
        if hasattr(service_event, "test_name"):
            # New style with ServiceEvent object
            self.emit_service_event(
                "service_teardown_started", service_event.test_name, **kwargs
            )
        else:
            # Old style with direct parameters
            self.emit_service_event("service_teardown_started", service_event, **kwargs)
