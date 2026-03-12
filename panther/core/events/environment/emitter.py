"""Environment Event Emitter.

This module provides typed event emission for environment lifecycle events.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.environment.events import (
    EnvironmentCreatedEvent,
    EnvironmentDestroyedEvent,
    EnvironmentErrorEvent,
    EnvironmentResourceEvent,
    EnvironmentSetupCompletedEvent,
    EnvironmentSetupFailedEvent,
    EnvironmentSetupStartedEvent,
    EnvironmentTeardownCompletedEvent,
    EnvironmentTeardownFailedEvent,
    EnvironmentTeardownStartedEvent,
    OutputCollectedEvent,
    OutputCollectionCompletedEvent,
    OutputCollectionStartedEvent,
    OutputsCollectedEvent,
)
from panther.core.events.experiment.events import ExperimentFinishedEarlyEvent


class EnvironmentEventEmitter:
    """Type-safe event emitter for environment-related events.

    This class provides methods for emitting all environment lifecycle events
    with proper typing and validation.
    """

    def __init__(self, event_manager: "EventManager"):
        """Initialize the environment event emitter.

        Args:
            event_manager: Event manager to use for event emission
        """
        self.event_manager = event_manager

    def emit_environment_created(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        environment_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an environment created event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment (docker_compose, shadow, etc.)
            environment_config: Environment configuration details
        """
        event = EnvironmentCreatedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            config=environment_config,
        )
        self.event_manager.notify(event)

    def emit_environment_setup_started(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        setup_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an environment setup started event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            setup_config: Setup configuration details
        """
        event = EnvironmentSetupStartedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            setup_config=setup_config,
        )
        self.event_manager.notify(event)

    def emit_environment_setup_completed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        duration_seconds: Optional[float] = None,
        setup_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an environment setup completed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            duration_seconds: Time taken for setup in seconds
            setup_details: Details about the setup
        """
        event = EnvironmentSetupCompletedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            duration=duration_seconds or 0.0,
            resources_allocated=setup_details,
        )
        self.event_manager.notify(event)

    def emit_environment_setup_failed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_type: Optional[str] = None,
        failed_component: Optional[str] = None,
    ) -> None:
        """Emit an environment setup failed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            error_message: Error message describing the failure
            error_type: Type/category of error
            failed_component: Component that failed during setup
        """
        event = EnvironmentSetupFailedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            error_message=error_message,
        )
        self.event_manager.notify(event)

    def emit_environment_teardown_started(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        reason: Optional[str] = None,
    ) -> None:
        """Emit an environment teardown started event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            reason: Reason for teardown
        """
        event = EnvironmentTeardownStartedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
        )
        self.event_manager.notify(event)

    def emit_environment_teardown_completed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        duration_seconds: Optional[float] = None,
        cleanup_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an environment teardown completed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            duration_seconds: Time taken for teardown in seconds
            cleanup_details: Details about the cleanup
        """
        event = EnvironmentTeardownCompletedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            duration=duration_seconds or 0.0,
            resources_released=cleanup_details,
        )
        self.event_manager.notify(event)

    def emit_environment_teardown_failed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_type: Optional[str] = None,
        partial_cleanup: Optional[bool] = None,
    ) -> None:
        """Emit an environment teardown failed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            error_message: Error message describing the failure
            error_type: Type/category of error
            partial_cleanup: Whether partial cleanup was achieved
        """
        event = EnvironmentTeardownFailedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            error_message=error_message,
        )
        self.event_manager.notify(event)

    def emit_environment_destroyed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        cleanup_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an environment destroyed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            cleanup_summary: Summary of what was cleaned up
        """
        event = EnvironmentDestroyedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            cleanup_duration=0.0,
        )
        self.event_manager.notify(event)

    def emit_environment_error(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_type: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an environment error event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            error_message: Error message
            error_type: Type/category of error
            error_details: Additional error details
        """
        if error_type == "early_termination":
            # Special case for early termination errors
            error_message = f"Early termination: {error_message}"
            error_type = "environment_error"
            event = ExperimentFinishedEarlyEvent(
                experiment_id=environment_id,  # Use environment_id as experiment_id
                reason=error_message,
                details={
                    "environment_name": environment_name,
                    "environment_type": environment_type,
                    "error_type": error_type,
                    "error_details": error_details or {},
                },
            )
        else:
            event = EnvironmentErrorEvent(
                environment_id=environment_id,
                environment_name=environment_name,
                environment_type=environment_type,
                error_message=error_message,
                error_type=error_type,
                error_details=error_details,
            )
        self.event_manager.notify(event)

    def emit_environment_resource(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        resource_type: str,
        resource_action: str,
        resource_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an environment resource event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            resource_type: Type of resource (container, network, volume, etc.)
            resource_action: Action performed (created, started, stopped, deleted)
            resource_details: Additional resource details
        """
        event = EnvironmentResourceEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            resource_type=resource_type,
            resource_action=resource_action,
            resource_details=resource_details,
        )
        self.event_manager.notify(event)

    def emit_environment_teardown(
        self, environment_type: str, environment_name: str, reason: Optional[str] = None
    ) -> None:
        """Emit environment teardown event (compatibility wrapper).

        This is a convenience method that wraps emit_environment_teardown_started
        for backward compatibility.

        Args:
            environment_type: Type of environment
            environment_name: Name of the environment
            reason: Reason for teardown
        """
        # Generate a consistent environment ID
        environment_id = f"{environment_type}_{environment_name}"

        self.emit_environment_teardown_started(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            reason=reason,
        )

    def emit_environment_modification_started(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        target_service: str,
        modification_type: str,
    ) -> None:
        """Emit an environment modification started event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            target_service: Name of the service being modified
            modification_type: Type of modification being applied
        """
        from .events import EnvironmentModificationStartedEvent

        event = EnvironmentModificationStartedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            target_service=target_service,
            modification_type=modification_type,
        )
        self.event_manager.notify(event)

    def emit_environment_modification_completed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        modifications: Optional[Dict[str, Any]] = None,
        modification_summary: str = "",
    ) -> None:
        """Emit an environment modification completed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            modifications: Dictionary of modifications applied
            modification_summary: Human-readable summary of modifications
        """
        from .events import EnvironmentModificationCompletedEvent

        event = EnvironmentModificationCompletedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            modifications=modifications,
            modification_summary=modification_summary,
        )
        self.event_manager.notify(event)

    def emit_environment_deployment_started(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        services: List[str],
        deployment_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit environment deployment started event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            services: List of services being deployed
            deployment_config: Deployment configuration details
        """
        from .events import EnvironmentDeploymentStartedEvent

        event = EnvironmentDeploymentStartedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            services=services,
            deployment_config=deployment_config,
        )
        self.event_manager.notify(event)

    def emit_environment_deployment_completed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        success: bool,
        deployed_services: Dict[str, str],
        duration: float,
        deployment_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit environment deployment completed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            success: Whether deployment succeeded
            deployed_services: Dictionary of service names to deployment status
            duration: Time taken for deployment
            deployment_details: Additional deployment details
        """
        from .events import EnvironmentDeploymentCompletedEvent

        event = EnvironmentDeploymentCompletedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            success=success,
            deployed_services=deployed_services,
            duration=duration,
            deployment_details=deployment_details,
        )
        self.event_manager.notify(event)

    def emit_environment_deployment_failed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_type: str = "deployment_error",
        failed_services: Optional[List[str]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit environment deployment failed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            error_message: Error message describing the failure
            error_type: Type of error that occurred
            failed_services: List of services that failed to deploy
            error_details: Additional error details
        """
        from .events import EnvironmentDeploymentFailedEvent

        event = EnvironmentDeploymentFailedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            error_message=error_message,
            error_type=error_type,
            failed_services=failed_services,
            error_details=error_details,
        )
        self.event_manager.notify(event)

    def emit_output_collection_started(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        collection_targets: Optional[List[str]] = None,
        collection_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit output collection started event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            collection_targets: List of environments being collected from
            collection_config: Configuration for the collection process
        """
        event = OutputCollectionStartedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            collection_targets=collection_targets or [],
            collection_config=collection_config or {},
        )
        self.event_manager.notify(event)

    def emit_output_collected(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        output_type: str,
        output_path: str,
        output_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit output collected event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            output_type: Type of output collected (trace, profile, etc.)
            output_path: Path to the collected output file
            output_size: Size of the output file in bytes
            metadata: Additional metadata about the output
        """
        event = OutputCollectedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            output_type=output_type,
            output_path=output_path,
            output_size=output_size,
            metadata=metadata or {},
        )
        self.event_manager.notify(event)

    def emit_outputs_collected(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        outputs: Dict[str, str],
        metadata: Dict[str, Dict[str, Any]],
    ) -> None:
        """Emit batch outputs collected event for all outputs from an environment.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            outputs: Dictionary mapping output_type to output_path
            metadata: Dictionary mapping output_type to metadata
        """
        import os

        # Calculate total size and prepare output details
        total_size = 0
        output_details = {}

        for output_type, output_path in outputs.items():
            output_size = None
            if os.path.exists(output_path):
                output_size = os.path.getsize(output_path)
                if output_size:
                    total_size += output_size

            output_details[output_type] = {
                "output_path": output_path,
                "output_size": output_size,
                "metadata": metadata.get(output_type, {}),
            }

        event = OutputsCollectedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            outputs=output_details,
            total_count=len(outputs),
            total_size=total_size if total_size > 0 else None,
        )
        self.event_manager.notify(event)

    def emit_output_collection_completed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        outputs: Dict[str, str],
        total_outputs: int,
        collection_duration: float,
        collection_summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit output collection completed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            outputs: Dictionary of collected outputs
            total_outputs: Total number of outputs collected
            collection_duration: Duration of the collection process in seconds
            collection_summary: Summary of the collection process
        """
        event = OutputCollectionCompletedEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            outputs=outputs,
            total_outputs=total_outputs,
            collection_duration=collection_duration,
            collection_summary=collection_summary or {},
        )
        self.event_manager.notify(event)

    def emit_output_collection_failed(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_type: str = "collection_error",
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit output collection failed event.

        Args:
            environment_id: Unique environment identifier
            environment_name: Human-readable environment name
            environment_type: Type of environment
            error_message: Error message describing the failure
            error_type: Type of error that occurred
            error_details: Additional error details
        """
        # Create a generic EnvironmentErrorEvent for output collection failures
        event = EnvironmentErrorEvent(
            environment_id=environment_id,
            environment_name=environment_name,
            environment_type=environment_type,
            error_message=f"Output collection failed: {error_message}",
            error_type=error_type,
            error_details=error_details or {},
        )
        self.event_manager.notify(event)
