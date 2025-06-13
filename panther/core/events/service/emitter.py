"""
Service Event Emitter

This module provides a type-safe event emitter for service-related events.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EventEmitterBase
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
    ServiceTestResultsEvent,
    CommandGenerationStartedEvent,
    CommandGeneratedEvent,
    DockerBuildStartedEvent,
    DockerBuildCompletedEvent,
    TesterAnalysisStartedEvent,
    TesterAnalysisCompletedEvent,
)


class ServiceEventEmitter(EventEmitterBase):
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
        super().__init__(event_manager)

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
        self._create_and_emit_event(
            ServiceCreatedEvent,
            service_id=service_id,
            service_name=service_name,
            service_type=service_type,
            implementation=implementation,
            config=config,
        )

    def emit_service_setup_started(
        self,
        test_case: str,
        service_count: int,
        service_names: list[str] | None = None,
        service_metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        """
        Emit a service setup started event for a test case.

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
            created_event = ServiceCreatedEvent(
                service_id=service_id,
                service_name=service_name,
                service_type=service_type,
                implementation=implementation,
                config=config,
            )
            self.event_manager.notify(created_event)

            # Then emit service preparation started event
            prep_event = ServicePreparationStartedEvent(
                service_id=service_id,
                service_name=service_name,
                preparation_steps=["setup"],
            )
            # Add test metadata to the event data
            prep_event.add_data("test_case", test_case)
            prep_event.add_data("service_count", service_count)
            self.event_manager.notify(prep_event)

    def emit_service_setup_failed(
        self,
        test_case: str,
        error_message: str,
        service_names: list[str] | None = None,
        error_type: str | None = None,
    ) -> None:
        """
        Emit a service setup failed event for a test case.

        Args:
            test_case: Name of the test case
            error_message: Error message describing the failure
            service_names: List of service names that failed
            error_type: Type/category of error
        """
        # This is a placeholder event using service preparation failed
        # In the future, we might want to create a specific ServiceSetupFailedEvent
        for service_name in service_names or []:
            event = ServicePreparationFailedEvent(
                service_id=f"{test_case}_{service_name}",
                service_name=service_name,
                error_message=error_message,
                error_type=error_type,
                failed_step="setup",
            )
            self.event_manager.notify(event)

    def emit_service_preparation_started(
        self,
        service_id: str,
        service_name: str,
        preparation_steps: list[str] | None = None,
        test_case: str | None = None,
    ) -> None:
        """
        Emit a service preparation started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            preparation_steps: List of preparation steps to be performed
            test_case: Optional test case name for context
        """
        event = ServicePreparationStartedEvent(
            service_id=service_id, service_name=service_name, preparation_steps=preparation_steps
        )
        # Add test metadata if provided
        if test_case:
            event.add_data("test_case", test_case)
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

    def emit_service_setup_completed(
        self,
        test_case: str,
        services: list[str],
        success: bool = True,
        duration_seconds: float | None = None,
    ) -> None:
        """
        Emit service setup completed event for a test case.

        This is a convenience method that emits preparation completed events
        for all services in a test case.

        Args:
            test_case: Name of the test case
            services: List of service names that were set up
            success: Whether the setup was successful
            duration_seconds: Total time taken for setup
        """
        # Emit a preparation completed event for each service
        for service_name in services:
            service_id = f"{test_case}_{service_name}"
            if success:
                self.emit_service_preparation_completed(
                    service_id=service_id,
                    service_name=service_name,
                    duration_seconds=duration_seconds / len(services) if duration_seconds else None,
                )
            else:
                self.emit_service_preparation_failed(
                    service_id=service_id,
                    service_name=service_name,
                    error_message="Setup failed",
                    failed_step="setup",
                )

    def emit_service_deployed(
        self,
        environment: str,
        service_instances: dict[str, Any],
        deployment_details: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit service deployed event for multiple services.

        This is a convenience method that emits deployment completed events
        for all deployed services.

        Args:
            environment: Environment where services were deployed
            service_instances: Dictionary mapping service names to service instances
            deployment_details: Additional deployment details
        """
        for service_name, _ in service_instances.items():
            service_id = f"{environment}_{service_name}"
            self.emit_service_deployment_completed(
                service_id=service_id,
                service_name=service_name,
                environment=environment,
                deployment_details=deployment_details,
            )

    def emit_service_test_results(
        self,
        service_id: str,
        service_name: str,
        test_results: dict[str, Any],
        overall_success: bool,
        test_summary: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a service test results event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            test_results: Test result data from the service
            overall_success: Whether all tests passed
            test_summary: Summary of test execution
        """
        event = ServiceTestResultsEvent(
            service_id=service_id,
            service_name=service_name,
            test_results=test_results,
            overall_success=overall_success,
            test_summary=test_summary,
        )
        self.event_manager.notify(event)

    def emit_tester_analysis_started(
        self,
        service_id: str,
        service_name: str,
        test_name: str,
        output_types: list[str] | None = None,
        tester_config: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a tester analysis started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            test_name: Name of the test being analyzed
            output_types: Types of outputs being analyzed
            tester_config: Tester configuration data
        """
        event = TesterAnalysisStartedEvent(
            service_id=service_id,
            service_name=service_name,
            test_name=test_name,
            output_types=output_types,
            tester_config=tester_config,
        )
        self.event_manager.notify(event)

    def emit_tester_analysis_completed(
        self,
        service_id: str,
        service_name: str,
        test_name: str,
        analysis_results: dict[str, Any] | None = None,
        success: bool = True,
        duration_seconds: float | None = None,
    ) -> None:
        """
        Emit a tester analysis completed event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            test_name: Name of the test analyzed
            analysis_results: Results from the analysis
            success: Whether the analysis was successful
            duration_seconds: Duration of the analysis
        """
        event = TesterAnalysisCompletedEvent(
            service_id=service_id,
            service_name=service_name,
            test_name=test_name,
            analysis_results=analysis_results,
            success=success,
            duration_seconds=duration_seconds,
        )
        self.event_manager.notify(event)

    def emit_service_event(
        self,
        event_type: str,
        service_id: str,
        service_name: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit a generic service event.

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
        implementation: str | None = None,
        protocol: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Emit command generation started event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            phase: Command generation phase (pre_compile, compile, etc.)
            implementation: Implementation name
            protocol: Protocol name
            config: Configuration for command generation
        """
        event = CommandGenerationStartedEvent(
            service_id=service_id,
            service_name=service_name,
            phase=phase,
            config=config,
        )
        self.event_manager.notify(event)

    def emit_command_generated(
        self,
        service_id: str,
        service_name: str,
        phase: str,
        command: str,
        implementation: str | None = None,
        protocol: str | None = None,
    ) -> None:
        """
        Emit command generated event.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            phase: Command generation phase
            command: Generated command
            implementation: Implementation name
            protocol: Protocol name
        """
        event = CommandGeneratedEvent(
            service_id=service_id,
            service_name=service_name,
            phase=phase,
            command=command,
        )
        self.event_manager.notify(event)

    def emit_docker_build_started(
        self,
        service_id: str,
        service_name: str,
        dockerfile_path: str,
        implementation: str | None = None,
        image_name: str | None = None,
    ) -> None:
        """
        Emit Docker build started event.

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
        build_duration: float | None = None,
    ) -> None:
        """
        Emit Docker build completed event.

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
        dockerfile_path: str = "",
        image_name: str = "",
    ) -> None:
        """
        Emit Docker build failed event using service error.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            error_message: Error message describing the failure
            dockerfile_path: Path to Dockerfile
            image_name: Docker image name that failed to build
        """
        self.emit_service_error(
            service_id=service_id,
            service_name=service_name,
            error_message=f"Docker build failed: {error_message}",
            error_type="docker_build_error",
            error_details={
                "dockerfile_path": dockerfile_path,
                "image_name": image_name,
            },
        )
