"""Environment Event Classes.

This module defines event classes for environment lifecycle management.
Uses factory classmethods on base classes instead of individual subclasses.
"""

from typing import Any, Dict, Optional

from panther.core.events.base.event_base import BaseEvent, EventType


class EnvironmentEvent(BaseEvent):
    """Base class for all environment-related events."""

    def __init__(
        self,
        name: str,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize environment event."""
        super().__init__(name, EventType.ENVIRONMENT, environment_id, data)
        self.environment_name = environment_name
        self.environment_type = environment_type

    def get_full_name(self) -> str:
        """Get the full event name with environment prefix."""
        return f"environment.{self.name}"

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def created(cls, environment_id, environment_name, environment_type, config=None):
        """Create created event."""
        return cls(
            "created",
            environment_id,
            environment_name,
            environment_type,
            {"config": config or {}, "environment_type": environment_type},
        )

    @classmethod
    def initialization_started(
        cls,
        environment_id,
        environment_name,
        environment_type,
        initialization_type="default",
    ):
        """Create initialization started event."""
        return cls(
            "initialization_started",
            environment_id,
            environment_name,
            environment_type,
            {"initialization_type": initialization_type},
        )

    @classmethod
    def initialization_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        duration,
        initialization_details=None,
    ):
        """Create initialization completed event."""
        return cls(
            "initialization_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "duration": duration,
                "initialization_details": initialization_details or {},
            },
        )

    @classmethod
    def initialization_failed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        error_message,
        error_details=None,
    ):
        """Create initialization failed event."""
        return cls(
            "initialization_failed",
            environment_id,
            environment_name,
            environment_type,
            {"error_message": error_message, "error_details": error_details or {}},
        )

    @classmethod
    def setup_started(
        cls, environment_id, environment_name, environment_type, setup_config=None
    ):
        """Create setup started event."""
        return cls(
            "setup_started",
            environment_id,
            environment_name,
            environment_type,
            {"setup_config": setup_config or {}},
        )

    @classmethod
    def setup_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        duration,
        resources_allocated=None,
    ):
        """Create setup completed event."""
        return cls(
            "setup_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "duration": duration,
                "resources_allocated": resources_allocated or {},
            },
        )

    @classmethod
    def setup_failed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        error_message,
        error_details=None,
    ):
        """Create setup failed event."""
        return cls(
            "setup_failed",
            environment_id,
            environment_name,
            environment_type,
            {"error_message": error_message, "error_details": error_details or {}},
        )

    @classmethod
    def ready(
        cls,
        environment_id,
        environment_name,
        environment_type,
        readiness_checks=None,
    ):
        """Create ready event."""
        return cls(
            "ready",
            environment_id,
            environment_name,
            environment_type,
            {"readiness_checks": readiness_checks or {}},
        )

    @classmethod
    def teardown_started(
        cls,
        environment_id,
        environment_name,
        environment_type,
        teardown_reason="test_completed",
    ):
        """Create teardown started event."""
        return cls(
            "teardown_started",
            environment_id,
            environment_name,
            environment_type,
            {"teardown_reason": teardown_reason},
        )

    @classmethod
    def teardown_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        duration,
        resources_released=None,
    ):
        """Create teardown completed event."""
        return cls(
            "teardown_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "duration": duration,
                "resources_released": resources_released or {},
            },
        )

    @classmethod
    def teardown_failed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        error_message,
        error_details=None,
    ):
        """Create teardown failed event."""
        return cls(
            "teardown_failed",
            environment_id,
            environment_name,
            environment_type,
            {"error_message": error_message, "error_details": error_details or {}},
        )

    @classmethod
    def deployment_started(
        cls,
        environment_id,
        environment_name,
        environment_type,
        services,
        deployment_config=None,
    ):
        """Create deployment started event."""
        return cls(
            "deployment_started",
            environment_id,
            environment_name,
            environment_type,
            {"services": services, "deployment_config": deployment_config or {}},
        )

    @classmethod
    def deployment_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        success,
        deployed_services,
        duration,
        deployment_details=None,
    ):
        """Create deployment completed event."""
        return cls(
            "deployment_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "success": success,
                "deployed_services": deployed_services,
                "duration": duration,
                "deployment_details": deployment_details or {},
            },
        )

    @classmethod
    def deployment_failed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        error_message,
        error_type="deployment_error",
        failed_services=None,
        error_details=None,
    ):
        """Create deployment failed event."""
        return cls(
            "deployment_failed",
            environment_id,
            environment_name,
            environment_type,
            {
                "error_message": error_message,
                "error_type": error_type,
                "failed_services": failed_services or [],
                "error_details": error_details or {},
            },
        )

    @classmethod
    def destroyed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        cleanup_duration,
        cleanup_details=None,
    ):
        """Create destroyed event."""
        return cls(
            "destroyed",
            environment_id,
            environment_name,
            environment_type,
            {
                "cleanup_duration": cleanup_duration,
                "cleanup_details": cleanup_details or {},
            },
        )

    @classmethod
    def error(
        cls,
        environment_id,
        environment_name,
        environment_type,
        error_message,
        error_type="unknown",
        error_details=None,
        recovery_possible=False,
    ):
        """Create error event."""
        return cls(
            "error",
            environment_id,
            environment_name,
            environment_type,
            {
                "error_message": error_message,
                "error_type": error_type,
                "error_details": error_details or {},
                "recovery_possible": recovery_possible,
            },
        )

    @classmethod
    def resource(
        cls,
        environment_id,
        environment_name,
        environment_type,
        resource_type,
        resource_action,
        resource_details=None,
    ):
        """Create resource event."""
        return cls(
            "resource",
            environment_id,
            environment_name,
            environment_type,
            {
                "resource_type": resource_type,
                "resource_action": resource_action,
                "resource_details": resource_details or {},
            },
        )

    @classmethod
    def configuration(
        cls,
        environment_id,
        environment_name,
        environment_type,
        config_change,
        old_config=None,
        new_config=None,
    ):
        """Create configuration event."""
        return cls(
            "configuration",
            environment_id,
            environment_name,
            environment_type,
            {
                "config_change": config_change,
                "old_config": old_config or {},
                "new_config": new_config or {},
            },
        )

    @classmethod
    def monitoring(
        cls,
        environment_id,
        environment_name,
        environment_type,
        metric_name,
        metric_value,
        metric_unit="",
        additional_metrics=None,
    ):
        """Create monitoring event."""
        return cls(
            "monitoring",
            environment_id,
            environment_name,
            environment_type,
            {
                "metric_name": metric_name,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "additional_metrics": additional_metrics or {},
            },
        )

    @classmethod
    def modification_started(
        cls,
        environment_id,
        environment_name,
        environment_type,
        target_service,
        modification_type,
    ):
        """Create modification started event."""
        return cls(
            "modification_started",
            environment_id,
            environment_name,
            environment_type,
            {
                "target_service": target_service,
                "modification_type": modification_type,
            },
        )

    @classmethod
    def modification_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        modifications=None,
        modification_summary="",
    ):
        """Create modification completed event."""
        return cls(
            "modification_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "modifications": modifications or {},
                "modification_summary": modification_summary,
            },
        )

    @classmethod
    def output_collection_started(
        cls,
        environment_id,
        environment_name,
        environment_type,
        collection_targets=None,
        collection_config=None,
    ):
        """Create output collection started event."""
        return cls(
            "output_collection_started",
            environment_id,
            environment_name,
            environment_type,
            {
                "collection_targets": collection_targets or [],
                "collection_config": collection_config or {},
                "action": "output_collection_started",
            },
        )

    @classmethod
    def output_collected(
        cls,
        environment_id,
        environment_name,
        environment_type,
        output_type,
        output_path,
        output_size=None,
        metadata=None,
    ):
        """Create output collected event."""
        return cls(
            "output_collected",
            environment_id,
            environment_name,
            environment_type,
            {
                "output_type": output_type,
                "output_path": output_path,
                "output_size": output_size,
                "metadata": metadata or {},
                "action": "output_collected",
            },
        )

    @classmethod
    def outputs_collected(
        cls,
        environment_id,
        environment_name,
        environment_type,
        outputs,
        total_count,
        total_size=None,
    ):
        """Create outputs collected event."""
        return cls(
            "outputs_collected",
            environment_id,
            environment_name,
            environment_type,
            {
                "outputs": outputs,
                "total_count": total_count,
                "total_size": total_size,
                "action": "outputs_collected",
            },
        )

    @classmethod
    def output_collection_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        outputs,
        total_outputs,
        collection_duration=None,
        collection_summary=None,
    ):
        """Create output collection completed event."""
        return cls(
            "output_collection_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "outputs": outputs,
                "total_outputs": total_outputs,
                "collection_duration": collection_duration,
                "collection_summary": collection_summary or {},
                "action": "output_collection_completed",
            },
        )


class NetworkEnvironmentEvent(EnvironmentEvent):
    """Base class for network environment events."""

    def __init__(
        self,
        name: str,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        network_config: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize network environment event."""
        merged_data = data or {}
        merged_data.update(
            {"network_config": network_config or {}, "environment_subtype": "network"}
        )
        super().__init__(
            name, environment_id, environment_name, environment_type, merged_data
        )

    @property
    def network_config(self) -> Dict[str, Any]:
        """Return the network configuration."""
        return self.data.get("network_config", {})

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def network_setup_started(
        cls,
        environment_id,
        environment_name,
        environment_type,
        network_config=None,
        interfaces=None,
    ):
        """Create network setup started event."""
        return cls(
            "network.setup.started",
            environment_id,
            environment_name,
            environment_type,
            network_config,
            {"interfaces": interfaces or [], "action": "network_setup_started"},
        )

    @classmethod
    def network_setup_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        network_config=None,
        allocated_resources=None,
        duration=None,
    ):
        """Create network setup completed event."""
        return cls(
            "network.setup.completed",
            environment_id,
            environment_name,
            environment_type,
            network_config,
            {
                "allocated_resources": allocated_resources or {},
                "duration": duration,
                "action": "network_setup_completed",
            },
        )

    @classmethod
    def network_setup_failed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        network_config=None,
        error_message="",
        error_details=None,
    ):
        """Create network setup failed event."""
        return cls(
            "network.setup.failed",
            environment_id,
            environment_name,
            environment_type,
            network_config,
            {
                "error_message": error_message,
                "error_details": error_details or {},
                "action": "network_setup_failed",
            },
        )

    @classmethod
    def network_teardown_started(
        cls,
        environment_id,
        environment_name,
        environment_type,
        network_config=None,
        teardown_reason="test_completed",
    ):
        """Create network teardown started event."""
        return cls(
            "network.teardown.started",
            environment_id,
            environment_name,
            environment_type,
            network_config,
            {
                "teardown_reason": teardown_reason,
                "action": "network_teardown_started",
            },
        )

    @classmethod
    def network_teardown_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        network_config=None,
        released_resources=None,
        duration=None,
    ):
        """Create network teardown completed event."""
        return cls(
            "network.teardown.completed",
            environment_id,
            environment_name,
            environment_type,
            network_config,
            {
                "released_resources": released_resources or {},
                "duration": duration,
                "action": "network_teardown_completed",
            },
        )


class ExecutionEnvironmentEvent(EnvironmentEvent):
    """Base class for execution environment events."""

    def __init__(
        self,
        name: str,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        execution_config: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize execution environment event."""
        merged_data = data or {}
        merged_data.update(
            {
                "execution_config": execution_config or {},
                "environment_subtype": "execution",
            }
        )
        super().__init__(
            name, environment_id, environment_name, environment_type, merged_data
        )

    @property
    def execution_config(self) -> Dict[str, Any]:
        """Return the execution configuration."""
        return self.data.get("execution_config", {})

    # -- Factory classmethods --------------------------------------------------

    @classmethod
    def execution_setup_started(
        cls,
        environment_id,
        environment_name,
        environment_type,
        execution_config=None,
        resource_limits=None,
    ):
        """Create execution setup started event."""
        return cls(
            "execution.setup.started",
            environment_id,
            environment_name,
            environment_type,
            execution_config,
            {
                "resource_limits": resource_limits or {},
                "action": "execution_setup_started",
            },
        )

    @classmethod
    def execution_setup_completed(
        cls,
        environment_id,
        environment_name,
        environment_type,
        execution_config=None,
        allocated_resources=None,
        duration=None,
    ):
        """Create execution setup completed event."""
        return cls(
            "execution.setup.completed",
            environment_id,
            environment_name,
            environment_type,
            execution_config,
            {
                "allocated_resources": allocated_resources or {},
                "duration": duration,
                "action": "execution_setup_completed",
            },
        )

    @classmethod
    def execution_resource_monitoring(
        cls,
        environment_id,
        environment_name,
        environment_type,
        execution_config=None,
        cpu_usage=None,
        memory_usage=None,
        additional_metrics=None,
    ):
        """Create execution resource monitoring event."""
        return cls(
            "execution.monitoring",
            environment_id,
            environment_name,
            environment_type,
            execution_config,
            {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "additional_metrics": additional_metrics or {},
                "action": "execution_monitoring",
            },
        )

    @classmethod
    def execution_limit_exceeded(
        cls,
        environment_id,
        environment_name,
        environment_type,
        execution_config=None,
        limit_type="unknown",
        current_value=None,
        limit_value=None,
        action_taken="none",
    ):
        """Create execution limit exceeded event."""
        return cls(
            "execution.limit.exceeded",
            environment_id,
            environment_name,
            environment_type,
            execution_config,
            {
                "limit_type": limit_type,
                "current_value": current_value,
                "limit_value": limit_value,
                "action_taken": action_taken,
                "action": "execution_limit_exceeded",
            },
        )
