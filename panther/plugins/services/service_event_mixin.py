"""Methods for IServiceManager to emit standardized events."""

from typing import Any, Dict, Optional

from panther.core.events.test.events import (
    TestCompletedEvent,
    TestEvent,
    TestFailedEvent,
)


class ServiceManagerEventMixin:
    """Mixin providing standardized event emission methods for service managers.

    Standalone mixin providing helper methods for service managers to emit standard events.
    It supports the event-driven architecture by providing consistent event emission patterns.

    MRO: Base event mixin. Used by: TesterManagerEventMixin and IUT service managers directly
    """

    def _get_service_identifier(self):
        """Get a service identifier using a fallback mechanism.

        Attempts to get service name from various attributes with increasing fallbacks:
        1. self.name
        2. self.service_name
        3. self.implementation_name with prefix if available
        4. Class name as last resort

        Returns:
            str: The identified service name or a fallback identifier
        """
        if hasattr(self, "name") and self.name:
            return self.name

        if hasattr(self, "service_name") and self.service_name:
            return self.service_name

        # Check if we have implementation_name to use
        if hasattr(self, "implementation_name") and self.implementation_name:
            # If we also know the service type, use it as a prefix
            prefix = ""
            if hasattr(self, "service_type") and self.service_type:
                prefix = f"{self.service_type.lower()}_"
            return f"{prefix}{self.implementation_name}"

        # Last resort - use the class name
        return f"{self.__class__.__name__}"

    def notify_service_started(self, details: Dict[str, Any] | None = None):
        """Notify that the service has started using the event emitter.

        Args:
            details: Additional details about the service start
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")

            # Generate a unique service ID
            service_id = f"{service_type}_{implementation}_{service_name}"

            # Try to use EmitterRegistry's state-aware method if available
            if hasattr(self.event_emitter, "emit_service_started_with_validation"):
                success = self.event_emitter.emit_service_started_with_validation(
                    service_id=service_id,
                    service_name=service_name,
                    pid=details.get("pid") if details else None,
                    start_time=details.get("start_time") if details else None,
                )
                if not success:
                    # Fallback to direct emission if state validation fails
                    self.event_emitter.service_emitter.emit_service_started(
                        service_id=service_id,
                        service_name=service_name,
                        pid=details.get("pid") if details else None,
                        start_time=details.get("start_time") if details else None,
                    )
            else:
                # Fallback to direct ServiceEventEmitter API
                self.event_emitter.emit_service_started(
                    service_id=service_id,
                    service_name=service_name,
                    pid=details.get("pid") if details else None,
                    start_time=details.get("start_time") if details else None,
                )

    def notify_service_stopped(
        self, success: bool, details: Optional[Dict[str, Any]] = None
    ):
        """Notify that the service has stopped using the event emitter.

        Args:
            success: Whether the service stopped cleanly
            details: Additional details about the service stop
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")

            # Generate a unique service ID
            service_id = f"{service_type}_{implementation}_{service_name}"

            # Try to use EmitterRegistry's state-aware method if available
            if hasattr(self.event_emitter, "emit_service_stopped_with_validation"):
                success_emitted = (
                    self.event_emitter.emit_service_stopped_with_validation(
                        service_id=service_id,
                        service_name=service_name,
                        exit_code=0 if success else 1,
                        reason=(
                            details.get(
                                "reason", "Normal termination" if success else "Error"
                            )
                            if details
                            else None
                        ),
                        uptime_seconds=(
                            details.get("uptime_seconds") if details else None
                        ),
                    )
                )
                if not success_emitted:
                    # Fallback to direct emission if state validation fails
                    self.event_emitter.service_emitter.emit_service_stopped(
                        service_id=service_id,
                        service_name=service_name,
                        exit_code=0 if success else 1,
                        reason=(
                            details.get(
                                "reason", "Normal termination" if success else "Error"
                            )
                            if details
                            else None
                        ),
                        uptime_seconds=(
                            details.get("uptime_seconds") if details else None
                        ),
                    )
            else:
                # Fallback to direct ServiceEventEmitter API
                self.event_emitter.emit_service_stopped(
                    service_id=service_id,
                    service_name=service_name,
                    exit_code=0 if success else 1,
                    reason=(
                        details.get(
                            "reason", "Normal termination" if success else "Error"
                        )
                        if details
                        else None
                    ),
                    uptime_seconds=details.get("uptime_seconds") if details else None,
                )

    def notify_service_error(
        self,
        error_type: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Notify that the service has encountered an error using the event emitter.

        Args:
            error_type: Type of error encountered
            error_message: Error message
            details: Additional details about the error
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")

            # Generate a unique service ID
            service_id = f"{service_type}_{implementation}_{service_name}"

            # Try to use EmitterRegistry's state-aware method if available
            if hasattr(self.event_emitter, "emit_service_error_with_validation"):
                success = self.event_emitter.emit_service_error_with_validation(
                    service_id=service_id,
                    service_name=service_name,
                    error_message=error_message,
                    error_type=error_type,
                    error_details=details,
                )
                if not success:
                    # Fallback to direct emission if state validation fails
                    self.event_emitter.service_emitter.emit_service_error(
                        service_id=service_id,
                        service_name=service_name,
                        error_message=error_message,
                        error_type=error_type,
                        error_details=details,
                    )
            else:
                # Fallback to direct ServiceEventEmitter API
                self.event_emitter.emit_service_error(
                    service_id=service_id,
                    service_name=service_name,
                    error_message=error_message,
                    error_type=error_type,
                    error_details=details,
                )

    def notify_service_created(self, config: Optional[Dict[str, Any]] = None):
        """Notify that the service has been created, with state validation.

        Args:
            config: Optional service configuration data
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")
            service_id = f"{service_type}_{implementation}_{service_name}"

            if hasattr(self.event_emitter, "emit_service_created_with_validation"):
                success = self.event_emitter.emit_service_created_with_validation(
                    service_id=service_id,
                    service_name=service_name,
                    service_type=service_type,
                    implementation=implementation,
                    config=config,
                )
                if not success:
                    self.event_emitter.service_emitter.emit_service_created(
                        service_id=service_id,
                        service_name=service_name,
                        service_type=service_type,
                        implementation=implementation,
                        config=config,
                    )
            else:
                self.event_emitter.emit_service_created(
                    service_id=service_id,
                    service_name=service_name,
                    service_type=service_type,
                    implementation=implementation,
                    config=config,
                )

    def notify_service_preparation_started(
        self, details: Optional[Dict[str, Any]] = None
    ):
        """Notify that service preparation has started, with state validation.

        Args:
            details: Additional details about the preparation
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")
            service_id = f"{service_type}_{implementation}_{service_name}"

            if hasattr(
                self.event_emitter,
                "emit_service_preparation_started_with_validation",
            ):
                success = (
                    self.event_emitter.emit_service_preparation_started_with_validation(
                        service_id=service_id,
                        service_name=service_name,
                    )
                )
                if not success:
                    self.event_emitter.service_emitter.emit_service_preparation_started(
                        service_id=service_id,
                        service_name=service_name,
                    )
            else:
                self.event_emitter.emit_service_preparation_started(
                    service_id=service_id,
                    service_name=service_name,
                )

    def notify_service_deployment_started(
        self,
        environment: str = "default",
        deployment_config: Optional[Dict[str, Any]] = None,
    ):
        """Notify that service deployment has started, with state validation.

        Args:
            environment: Deployment environment name
            deployment_config: Optional deployment configuration
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")
            service_id = f"{service_type}_{implementation}_{service_name}"

            if hasattr(
                self.event_emitter,
                "emit_service_deployment_started_with_validation",
            ):
                success = (
                    self.event_emitter.emit_service_deployment_started_with_validation(
                        service_id=service_id,
                        service_name=service_name,
                        environment=environment,
                        deployment_config=deployment_config,
                    )
                )
                if not success:
                    self.event_emitter.service_emitter.emit_service_deployment_started(
                        service_id=service_id,
                        service_name=service_name,
                        environment=environment,
                        deployment_config=deployment_config,
                    )
            else:
                self.event_emitter.emit_service_deployment_started(
                    service_id=service_id,
                    service_name=service_name,
                    environment=environment,
                    deployment_config=deployment_config,
                )

    def notify_service_deployment_completed(
        self,
        environment: str = "default",
        endpoint: Optional[str] = None,
        ports: Optional[list] = None,
        deployment_details: Optional[Dict[str, Any]] = None,
    ):
        """Notify that service deployment has completed, with state validation.

        Args:
            environment: Deployment environment name
            endpoint: Service endpoint URL
            ports: Exposed ports
            deployment_details: Additional deployment details
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")
            service_id = f"{service_type}_{implementation}_{service_name}"

            if hasattr(
                self.event_emitter,
                "emit_service_deployment_completed_with_validation",
            ):
                success = self.event_emitter.emit_service_deployment_completed_with_validation(
                    service_id=service_id,
                    service_name=service_name,
                    environment=environment,
                    endpoint=endpoint,
                    ports=ports,
                    deployment_details=deployment_details,
                )
                if not success:
                    self.event_emitter.service_emitter.emit_service_deployment_completed(
                        service_id=service_id,
                        service_name=service_name,
                        environment=environment,
                        endpoint=endpoint,
                        ports=ports,
                        deployment_details=deployment_details,
                    )
            else:
                self.event_emitter.emit_service_deployment_completed(
                    service_id=service_id,
                    service_name=service_name,
                    environment=environment,
                    endpoint=endpoint,
                    ports=ports,
                    deployment_details=deployment_details,
                )

    def notify_service_ready(self, readiness_checks: Optional[Dict[str, bool]] = None):
        """Notify that the service is ready, with state validation.

        Args:
            readiness_checks: Results of readiness checks
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")
            service_id = f"{service_type}_{implementation}_{service_name}"

            if hasattr(self.event_emitter, "emit_service_ready_with_validation"):
                success = self.event_emitter.emit_service_ready_with_validation(
                    service_id=service_id,
                    service_name=service_name,
                    readiness_checks=readiness_checks,
                )
                if not success:
                    self.event_emitter.service_emitter.emit_service_ready(
                        service_id=service_id,
                        service_name=service_name,
                        readiness_checks=readiness_checks,
                    )
            else:
                self.event_emitter.emit_service_ready(
                    service_id=service_id,
                    service_name=service_name,
                    readiness_checks=readiness_checks,
                )

    def notify_service_event(
        self,
        event_name: str,
        service_id: str = None,
        service_name: str = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Emit service-related events based on event name.

        Delegates to state-validated notify_service_* methods where available,
        falls back to direct emission for events without validation methods.

        Args:
            event_name: Name of the event to emit
            service_id: Service identifier (unused when delegating to notify_service_* methods)
            service_name: Human-readable service name (unused when delegating)
            details: Additional event details
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            if event_name == "service_created":
                self.notify_service_created(config=details)
                return
            elif event_name == "service_started":
                self.notify_service_started(details=details)
                return
            elif event_name == "service_ready":
                self.notify_service_ready(
                    readiness_checks=(
                        details.get("readiness_checks") if details else None
                    ),
                )
                return
            elif event_name == "preparation_started":
                self.notify_service_preparation_started(details=details)
                return
            elif event_name == "service_destroyed":
                self.event_emitter.emit_service_destroyed(
                    service_id=service_id,
                    service_name=service_name,
                    cleanup_details=details,
                )
                return
            elif event_name == "preparation_completed":
                self.event_emitter.emit_service_preparation_completed(
                    service_id=service_id,
                    service_name=service_name,
                    duration_seconds=(
                        details.get("duration_seconds") if details else None
                    ),
                    artifacts=details.get("artifacts") if details else None,
                )
            elif event_name == "preparation_failed":
                self.event_emitter.emit_service_preparation_failed(
                    service_id=service_id,
                    service_name=service_name,
                    error_message=(
                        details.get("error_message", "Preparation failed")
                        if details
                        else "Preparation failed"
                    ),
                    error_type=details.get("error_type") if details else None,
                    failed_step=details.get("failed_step") if details else None,
                )
            elif event_name in ["stopping", "stopped"]:
                self.event_emitter.emit_service_stopped(
                    service_id=service_id,
                    service_name=service_name,
                    exit_code=details.get("exit_code") if details else None,
                    reason=details.get("reason") if details else None,
                    uptime_seconds=details.get("uptime_seconds") if details else None,
                )
            # Map compilation events to tester analysis events
            elif event_name == "compilation_started":
                # Extract test information for analysis
                test_name = "compilation"
                output_types = ["compilation_log", "executable"]
                tester_config = {}

                if details:
                    if "test" in details:
                        test_name = f"compilation_{details['test']}"
                    if "protocol" in details:
                        tester_config["protocol"] = details["protocol"]
                    # Include any additional configuration
                    tester_config.update(details.get("config", {}))

                self.event_emitter.emit_tester_analysis_started(
                    service_id=service_id,
                    service_name=service_name or service_id,
                    test_name=test_name,
                    output_types=output_types,
                    tester_config=tester_config,
                )
            elif event_name == "compilation_completed":
                self.event_emitter.emit_tester_analysis_completed(
                    service_id=service_id,
                    service_name=service_name or service_id,
                    test_name="compilation",
                    analysis_passed=details.get("success", True) if details else True,
                    findings=details.get("findings") if details else None,
                    summary=(
                        details.get("summary", "Compilation completed")
                        if details
                        else "Compilation completed"
                    ),
                    duration=details.get("duration") if details else None,
                )
            elif event_name == "compilation_failed":
                # Create findings dict for failed compilation
                error_messages = (
                    details.get("error_messages", ["Compilation failed"])
                    if details
                    else ["Compilation failed"]
                )
                findings = {
                    "failed_checks": error_messages,
                    "warnings": details.get("warnings", []) if details else [],
                    "errors": error_messages,
                }

                self.event_emitter.emit_tester_analysis_completed(
                    service_id=service_id,
                    service_name=service_name or service_id,
                    test_name="compilation",
                    analysis_passed=False,
                    findings=findings,
                    summary=(
                        details.get("summary", "Compilation failed")
                        if details
                        else "Compilation failed"
                    ),
                    duration=details.get("duration") if details else None,
                )
            # Map build events to Docker build events for consistency
            elif event_name == "build_started":
                self.event_emitter.emit_docker_build_started(
                    service_id=service_id,
                    service_name=service_name or service_id,
                    dockerfile_path=(
                        details.get("dockerfile_path", "Dockerfile")
                        if details
                        else "Dockerfile"
                    ),
                    image_name=details.get("image_name") if details else None,
                )
            elif event_name in ["build_completed", "build_succeeded"]:
                self.event_emitter.emit_docker_build_completed(
                    service_id=service_id,
                    service_name=service_name or service_id,
                    image_name=(
                        details.get("image_name", service_name or service_id)
                        if details
                        else (service_name or service_id)
                    ),
                    success=True,
                    build_duration=details.get("duration") if details else None,
                )
            elif event_name in ["build_failed", "build_error"]:
                self.event_emitter.emit_docker_build_failed(
                    service_id=service_id,
                    service_name=service_name or service_id,
                    dockerfile_path=(
                        details.get("dockerfile_path", "Dockerfile")
                        if details
                        else "Dockerfile"
                    ),
                    error_message=(
                        details.get("error_message", "Build failed")
                        if details
                        else "Build failed"
                    ),
                    build_duration=details.get("duration") if details else None,
                )
            else:
                # For truly unknown events, log a warning instead of treating as error
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "Unknown service event '%s' for service '%s'. Consider adding proper event mapping.",
                    event_name,
                    service_name,
                )
                # For backward compatibility, still emit a generic event but with lower severity
                self.event_emitter.emit_service_error(
                    service_id=service_id,
                    service_name=service_name,
                    error_message=f"Unmapped event: {event_name}",
                    error_type="unmapped_event",
                    error_details={"event_name": event_name, **(details or {})},
                )

    def notify_service_step_progress(
        self,
        step_id: str,
        progress: float,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Notify progress during a service operation step.

        Args:
            step_id: Identifier for the step
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
            details: Additional progress details
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")

            # Generate a unique service ID
            service_id = f"{service_type}_{implementation}_{service_name}"

            # Service-specific progress is better represented as deployment or preparation progress
            if step_id.startswith("deploy"):
                self.notify_service_deployment_started(
                    environment=(
                        details.get("environment", "default") if details else "default"
                    ),
                    deployment_config=details,
                )
            elif step_id.startswith("prepare"):
                self.notify_service_preparation_started(details=details)
            else:
                # For generic steps, we can emit a service error to track the progress
                # This is not ideal but maintains compatibility
                self.event_emitter.emit_service_error(
                    service_id=service_id,
                    service_name=service_name,
                    error_message=f"Progress update: {message or f'Step {step_id} at {progress:.1%}'}",
                    error_type="progress_update",
                    error_details={
                        "step_id": step_id,
                        "progress": progress,
                        **(details or {}),
                    },
                )

    def notify_service_step_completed(
        self, step_id: str, success: bool, result: Optional[Dict[str, Any]] = None
    ):
        """Notify completion of a service operation step.

        Args:
            step_id: Identifier for the step
            success: Whether the step completed successfully
            result: Result data from the step
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")

            # Generate a unique service ID
            service_id = f"{service_type}_{implementation}_{service_name}"

            # Map step completions to appropriate service events
            if step_id.startswith("deploy"):
                if success:
                    self.notify_service_deployment_completed(
                        environment=(
                            result.get("environment", "default")
                            if result
                            else "default"
                        ),
                        endpoint=result.get("endpoint") if result else None,
                        ports=result.get("ports") if result else None,
                        deployment_details=result,
                    )
                else:
                    self.event_emitter.emit_service_deployment_failed(
                        service_id=service_id,
                        service_name=service_name,
                        environment=(
                            result.get("environment", "default")
                            if result
                            else "default"
                        ),
                        error_message=(
                            result.get("error", "Deployment failed")
                            if result
                            else "Deployment failed"
                        ),
                        error_type="deployment_error",
                    )
            elif step_id.startswith("prepare"):
                if success:
                    self.event_emitter.emit_service_preparation_completed(
                        service_id=service_id,
                        service_name=service_name,
                        duration_seconds=result.get("duration") if result else None,
                        artifacts=result,
                    )
                else:
                    self.event_emitter.emit_service_preparation_failed(
                        service_id=service_id,
                        service_name=service_name,
                        error_message=(
                            result.get("error", "Preparation failed")
                            if result
                            else "Preparation failed"
                        ),
                        error_type="preparation_error",
                        failed_step=step_id,
                    )
            else:
                # For generic steps, emit a service ready event if successful
                if success:
                    self.notify_service_ready(
                        readiness_checks={step_id: True},
                    )
                else:
                    self.event_emitter.emit_service_error(
                        service_id=service_id,
                        service_name=service_name,
                        error_message=f"Step {step_id} failed",
                        error_type="step_failure",
                        error_details={"step_id": step_id, "result": result},
                    )

    def notify_service_metric(
        self,
        metric_type: str,
        metric_name: str,
        value: Any,
        step_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Notify a service-related metric value.

        Args:
            metric_type: Type of the metric
            metric_name: Name of the metric
            value: Metric value
            step_id: Optional step identifier
            details: Additional metric details
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")

            # Generate a unique service ID
            service_id = f"{service_type}_{implementation}_{service_name}"

            # Map metrics to health check events when appropriate
            if metric_type == "health" or metric_name.startswith("health_"):
                if value:
                    self.event_emitter.emit_service_health_check_passed(
                        service_id=service_id,
                        service_name=service_name,
                        check_type=metric_name,
                        endpoint=details.get("endpoint") if details else None,
                        response_time_ms=(
                            details.get("response_time_ms") if details else None
                        ),
                    )
                else:
                    self.event_emitter.emit_service_health_check_failed(
                        service_id=service_id,
                        service_name=service_name,
                        check_type=metric_name,
                        error_message=(
                            details.get("error", "Health check failed")
                            if details
                            else "Health check failed"
                        ),
                        endpoint=details.get("endpoint") if details else None,
                        status_code=details.get("status_code") if details else None,
                    )
            else:
                # For other metrics, store as service error with metric context
                # This maintains compatibility while using the new event system
                self.event_emitter.emit_service_error(
                    service_id=service_id,
                    service_name=service_name,
                    error_message=f"Metric: {metric_name}={value}",
                    error_type="metric_report",
                    error_details={
                        "metric_type": metric_type,
                        "metric_name": metric_name,
                        "value": value,
                        "step_id": step_id,
                        **(details or {}),
                    },
                )

    def emit_test_starting(
        self, test_id: str, test_type: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit an event indicating that a test is starting.

        Args:
            test_id: Unique identifier for the test
            test_type: Type of test being started
            details: Additional details about the test
        """
        if not (hasattr(self, "event_emitter") and self.event_emitter):
            self.logger.debug("Skipping event emission: no event_emitter configured")
            return
        event = TestEvent.execution_started(
            test_id,
            steps=details.get("steps", []) if details else [],
        )
        self.event_emitter.emit_event(event)

    def emit_test_completed(
        self,
        test_id: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an event indicating that a test has completed.

        Args:
            test_id: Unique identifier for the test
            success: Whether the test completed successfully
            result: Test result data
            error_message: Error message if test was unsuccessful
            details: Additional details about the test completion
        """
        if not (hasattr(self, "event_emitter") and self.event_emitter):
            self.logger.debug("Skipping event emission: no event_emitter configured")
            return
        if success:
            summary = {"result": result or {}, "details": details or {}}
            event = TestCompletedEvent(
                test_id=test_id,
                summary=summary,
            )
        else:
            event = TestFailedEvent(
                test_id=test_id,
                error_message=error_message or "Test failed",
                summary={"result": result or {}, "details": details or {}},
            )
        self.event_emitter.emit_event(event)

    def handle_event(self, event: "BaseEvent") -> None:
        """Default implementation of handle_event for service managers.

        This provides a basic event handling mechanism that can be overridden
        by specific service manager implementations if they need custom event handling.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug(
            "Service %s received event: %s", self.service_name, event_type
        )

        # Basic event handling for common service events
        # Subclasses can override this method for more specific handling
        if event_type == "ServiceStartRequestedEvent":
            self.logger.info("Service start requested for %s", self.service_name)
        elif event_type == "ServiceStopRequestedEvent":
            self.logger.info("Service stop requested for %s", self.service_name)
        elif event_type == "TestRunRequestedEvent":
            self.logger.info("Test run requested for %s", self.service_name)
        else:
            # Log unhandled events at debug level
            self.logger.debug(
                "Unhandled event type %s for service %s", event_type, self.service_name
            )
