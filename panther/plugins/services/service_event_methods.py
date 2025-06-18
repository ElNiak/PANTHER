"""
Methods for IServiceManager to emit standardized events.
"""

from typing import Any, Dict, Optional


class ServiceManagerEventMixin:
    """
    Mixin providing standardized event emission methods for service managers.

    This class extends IServiceManager with helper methods to emit standard events.
    It supports the event-driven architecture by providing consistent event emission patterns.
    """

    def _get_service_identifier(self):
        """
        Get a service identifier using a fallback mechanism.

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
        """
        Notify that the service has started using the event emitter.

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
        """
        Notify that the service has stopped using the event emitter.

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
        """
        Notify that the service has encountered an error using the event emitter.

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

    def notify_service_event(
        self, event_name: str, details: Optional[Dict[str, Any]] = None
    ):
        """
        Notify a custom service event using the event emitter.

        Args:
            event_name: Name of the service event
            details: Additional details about the event
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            # Get service identifier with fallback mechanism
            service_name = self._get_service_identifier()
            service_type = getattr(self, "service_type", "unknown")
            implementation = getattr(self, "implementation_name", "unknown")

            # Generate a unique service ID
            service_id = f"{service_type}_{implementation}_{service_name}"

            # Map common event names to specific emitter methods
            if event_name == "service_created":
                # Try to use state-aware method first
                if hasattr(self.event_emitter, "emit_service_created_with_validation"):
                    success = self.event_emitter.emit_service_created_with_validation(
                        service_id=service_id,
                        service_name=service_name,
                        service_type=service_type,
                        implementation=implementation,
                        config=details,
                    )
                    if not success:
                        # Fallback to direct emission
                        self.event_emitter.service_emitter.emit_service_created(
                            service_id=service_id,
                            service_name=service_name,
                            service_type=service_type,
                            implementation=implementation,
                            config=details,
                        )
                else:
                    self.event_emitter.emit_service_created(
                        service_id=service_id,
                        service_name=service_name,
                        service_type=service_type,
                        implementation=implementation,
                        config=details,
                    )
            elif event_name == "service_ready":
                # Try to use state-aware method first
                if hasattr(self.event_emitter, "emit_service_ready_with_validation"):
                    success = self.event_emitter.emit_service_ready_with_validation(
                        service_id=service_id,
                        service_name=service_name,
                        readiness_checks=(
                            details.get("readiness_checks") if details else None
                        ),
                    )
                    if not success:
                        # Fallback to direct emission
                        self.event_emitter.service_emitter.emit_service_ready(
                            service_id=service_id,
                            service_name=service_name,
                            readiness_checks=(
                                details.get("readiness_checks") if details else None
                            ),
                        )
                else:
                    self.event_emitter.emit_service_ready(
                        service_id=service_id,
                        service_name=service_name,
                        readiness_checks=(
                            details.get("readiness_checks") if details else None
                        ),
                    )
            elif event_name == "service_destroyed":
                self.event_emitter.emit_service_destroyed(
                    service_id=service_id,
                    service_name=service_name,
                    cleanup_details=details,
                )
            else:
                # For other events, emit as generic service error with event context
                self.event_emitter.emit_service_error(
                    service_id=service_id,
                    service_name=service_name,
                    error_message=f"Custom event: {event_name}",
                    error_type="custom_event",
                    error_details={"event_name": event_name, **(details or {})},
                )

    def notify_service_step_progress(
        self,
        step_id: str,
        progress: float,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Notify progress during a service operation step.

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
                self.event_emitter.emit_service_deployment_started(
                    service_id=service_id,
                    service_name=service_name,
                    environment=(
                        details.get("environment", "default") if details else "default"
                    ),
                    deployment_config=details,
                )
            elif step_id.startswith("prepare"):
                self.event_emitter.emit_service_preparation_started(
                    service_id=service_id,
                    service_name=service_name,
                    preparation_steps=[message] if message else None,
                )
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
        """
        Notify completion of a service operation step.

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
                    self.event_emitter.emit_service_deployment_completed(
                        service_id=service_id,
                        service_name=service_name,
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
                    self.event_emitter.emit_service_ready(
                        service_id=service_id,
                        service_name=service_name,
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
        """
        Notify a service-related metric value.

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
