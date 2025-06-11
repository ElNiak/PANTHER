"""
Environment Event Classes

This module defines event classes for environment lifecycle management.
"""

from typing import Any

from panther.core.events.base.event_base import BaseEvent, EventType


class EnvironmentEvent(BaseEvent):
    """Base class for all environment-related events."""

    def __init__(
        self,
        name: str,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        data: dict[str, Any] | None = None,
    ):
        super().__init__(name, EventType.ENVIRONMENT, environment_id, data)
        self.environment_name = environment_name
        self.environment_type = environment_type

    def get_full_name(self) -> str:
        """Get the full event name with environment prefix."""
        return f"environment.{self.name}"


class EnvironmentCreatedEvent(EnvironmentEvent):
    """Event emitted when an environment is created."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        config: dict[str, Any] | None = None,
    ):
        super().__init__(
            "created",
            environment_id,
            environment_name,
            environment_type,
            {
                "config": config or {},
                "environment_type": environment_type,
            },
        )
        self.config = config or {}


class EnvironmentInitializationStartedEvent(EnvironmentEvent):
    """Event emitted when environment initialization starts."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        initialization_type: str = "default",
    ):
        super().__init__(
            "initialization_started",
            environment_id,
            environment_name,
            environment_type,
            {
                "initialization_type": initialization_type,
            },
        )
        self.initialization_type = initialization_type


class EnvironmentInitializationCompletedEvent(EnvironmentEvent):
    """Event emitted when environment initialization completes."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        duration: float,
        initialization_details: dict[str, Any] | None = None,
    ):
        super().__init__(
            "initialization_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "duration": duration,
                "initialization_details": initialization_details or {},
            },
        )
        self.duration = duration
        self.initialization_details = initialization_details or {}


class EnvironmentInitializationFailedEvent(EnvironmentEvent):
    """Event emitted when environment initialization fails."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ):
        super().__init__(
            "initialization_failed",
            environment_id,
            environment_name,
            environment_type,
            {
                "error_message": error_message,
                "error_details": error_details or {},
            },
        )
        self.error_message = error_message
        self.error_details = error_details or {}


class EnvironmentSetupStartedEvent(EnvironmentEvent):
    """Event emitted when environment setup starts."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        setup_config: dict[str, Any] | None = None,
    ):
        super().__init__(
            "setup_started",
            environment_id,
            environment_name,
            environment_type,
            {
                "setup_config": setup_config or {},
            },
        )
        self.setup_config = setup_config or {}


class EnvironmentSetupCompletedEvent(EnvironmentEvent):
    """Event emitted when environment setup completes."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        duration: float,
        resources_allocated: dict[str, Any] | None = None,
    ):
        super().__init__(
            "setup_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "duration": duration,
                "resources_allocated": resources_allocated or {},
            },
        )
        self.duration = duration
        self.resources_allocated = resources_allocated or {}


class EnvironmentSetupFailedEvent(EnvironmentEvent):
    """Event emitted when environment setup fails."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ):
        super().__init__(
            "setup_failed",
            environment_id,
            environment_name,
            environment_type,
            {
                "error_message": error_message,
                "error_details": error_details or {},
            },
        )
        self.error_message = error_message
        self.error_details = error_details or {}


class EnvironmentReadyEvent(EnvironmentEvent):
    """Event emitted when environment is ready for use."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        readiness_checks: dict[str, Any] | None = None,
    ):
        super().__init__(
            "ready",
            environment_id,
            environment_name,
            environment_type,
            {
                "readiness_checks": readiness_checks or {},
            },
        )
        self.readiness_checks = readiness_checks or {}


class EnvironmentTeardownStartedEvent(EnvironmentEvent):
    """Event emitted when environment teardown starts."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        teardown_reason: str = "test_completed",
    ):
        super().__init__(
            "teardown_started",
            environment_id,
            environment_name,
            environment_type,
            {
                "teardown_reason": teardown_reason,
            },
        )
        self.teardown_reason = teardown_reason


class EnvironmentTeardownCompletedEvent(EnvironmentEvent):
    """Event emitted when environment teardown completes."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        duration: float,
        resources_released: dict[str, Any] | None = None,
    ):
        super().__init__(
            "teardown_completed",
            environment_id,
            environment_name,
            environment_type,
            {
                "duration": duration,
                "resources_released": resources_released or {},
            },
        )
        self.duration = duration
        self.resources_released = resources_released or {}


class EnvironmentTeardownFailedEvent(EnvironmentEvent):
    """Event emitted when environment teardown fails."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_details: dict[str, Any] | None = None,
    ):
        super().__init__(
            "teardown_failed",
            environment_id,
            environment_name,
            environment_type,
            {
                "error_message": error_message,
                "error_details": error_details or {},
            },
        )
        self.error_message = error_message
        self.error_details = error_details or {}


class EnvironmentDestroyedEvent(EnvironmentEvent):
    """Event emitted when environment is destroyed."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        cleanup_duration: float,
        cleanup_details: dict[str, Any] | None = None,
    ):
        super().__init__(
            "destroyed",
            environment_id,
            environment_name,
            environment_type,
            {
                "cleanup_duration": cleanup_duration,
                "cleanup_details": cleanup_details or {},
            },
        )
        self.cleanup_duration = cleanup_duration
        self.cleanup_details = cleanup_details or {}


class EnvironmentErrorEvent(EnvironmentEvent):
    """Event emitted when an environment error occurs."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        error_message: str,
        error_type: str = "unknown",
        error_details: dict[str, Any] | None = None,
        recovery_possible: bool = False,
    ):
        super().__init__(
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
        self.error_message = error_message
        self.error_type = error_type
        self.error_details = error_details or {}
        self.recovery_possible = recovery_possible


class EnvironmentResourceEvent(EnvironmentEvent):
    """Event emitted for environment resource management."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        resource_type: str,
        resource_action: str,
        resource_details: dict[str, Any] | None = None,
    ):
        super().__init__(
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
        self.resource_type = resource_type
        self.resource_action = resource_action
        self.resource_details = resource_details or {}


class EnvironmentConfigurationEvent(EnvironmentEvent):
    """Event emitted for environment configuration changes."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        config_change: str,
        old_config: dict[str, Any] | None = None,
        new_config: dict[str, Any] | None = None,
    ):
        super().__init__(
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
        self.config_change = config_change
        self.old_config = old_config or {}
        self.new_config = new_config or {}


class EnvironmentMonitoringEvent(EnvironmentEvent):
    """Event emitted for environment monitoring data."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        metric_name: str,
        metric_value: Any,
        metric_unit: str = "",
        additional_metrics: dict[str, Any] | None = None,
    ):
        super().__init__(
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
        self.metric_name = metric_name
        self.metric_value = metric_value
        self.metric_unit = metric_unit
        self.additional_metrics = additional_metrics or {}


# Network Environment Events (specialized environment events)


class NetworkEnvironmentEvent(EnvironmentEvent):
    """Base class for network environment events."""

    def __init__(
        self,
        name: str,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        network_config: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ):
        merged_data = data or {}
        merged_data.update(
            {"network_config": network_config or {}, "environment_subtype": "network"}
        )
        super().__init__(name, environment_id, environment_name, environment_type, merged_data)

    @property
    def network_config(self) -> dict[str, Any]:
        return self.data.get("network_config", {})


class NetworkSetupStartedEvent(NetworkEnvironmentEvent):
    """Event emitted when network environment setup starts."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        network_config: dict[str, Any] | None = None,
        interfaces: list | None = None,
    ):
        super().__init__(
            "network.setup.started",
            environment_id,
            environment_name,
            environment_type,
            network_config,
            {"interfaces": interfaces or [], "action": "network_setup_started"},
        )

    @property
    def interfaces(self) -> list:
        return self.data.get("interfaces", [])


class NetworkSetupCompletedEvent(NetworkEnvironmentEvent):
    """Event emitted when network environment setup completes."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        network_config: dict[str, Any] | None = None,
        allocated_resources: dict[str, Any] | None = None,
        duration: float | None = None,
    ):
        super().__init__(
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

    @property
    def allocated_resources(self) -> dict[str, Any]:
        return self.data.get("allocated_resources", {})

    @property
    def duration(self) -> float | None:
        return self.data.get("duration")


class NetworkSetupFailedEvent(NetworkEnvironmentEvent):
    """Event emitted when network environment setup fails."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        network_config: dict[str, Any] | None = None,
        error_message: str = "",
        error_details: dict[str, Any] | None = None,
    ):
        super().__init__(
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

    @property
    def error_message(self) -> str:
        return self.data.get("error_message", "")

    @property
    def error_details(self) -> dict[str, Any]:
        return self.data.get("error_details", {})


class NetworkTeardownStartedEvent(NetworkEnvironmentEvent):
    """Event emitted when network environment teardown starts."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        network_config: dict[str, Any] | None = None,
        teardown_reason: str = "test_completed",
    ):
        super().__init__(
            "network.teardown.started",
            environment_id,
            environment_name,
            environment_type,
            network_config,
            {"teardown_reason": teardown_reason, "action": "network_teardown_started"},
        )

    @property
    def teardown_reason(self) -> str:
        return self.data.get("teardown_reason", "")


class NetworkTeardownCompletedEvent(NetworkEnvironmentEvent):
    """Event emitted when network environment teardown completes."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        network_config: dict[str, Any] | None = None,
        released_resources: dict[str, Any] | None = None,
        duration: float | None = None,
    ):
        super().__init__(
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

    @property
    def released_resources(self) -> dict[str, Any]:
        return self.data.get("released_resources", {})

    @property
    def duration(self) -> float | None:
        return self.data.get("duration")


# Execution Environment Events (specialized environment events)


class ExecutionEnvironmentEvent(EnvironmentEvent):
    """Base class for execution environment events."""

    def __init__(
        self,
        name: str,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        execution_config: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ):
        merged_data = data or {}
        merged_data.update(
            {"execution_config": execution_config or {}, "environment_subtype": "execution"}
        )
        super().__init__(name, environment_id, environment_name, environment_type, merged_data)

    @property
    def execution_config(self) -> dict[str, Any]:
        return self.data.get("execution_config", {})


class ExecutionEnvironmentSetupStartedEvent(ExecutionEnvironmentEvent):
    """Event emitted when execution environment setup starts."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        execution_config: dict[str, Any] | None = None,
        resource_limits: dict[str, Any] | None = None,
    ):
        super().__init__(
            "execution.setup.started",
            environment_id,
            environment_name,
            environment_type,
            execution_config,
            {"resource_limits": resource_limits or {}, "action": "execution_setup_started"},
        )

    @property
    def resource_limits(self) -> dict[str, Any]:
        return self.data.get("resource_limits", {})


class ExecutionEnvironmentSetupCompletedEvent(ExecutionEnvironmentEvent):
    """Event emitted when execution environment setup completes."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        execution_config: dict[str, Any] | None = None,
        allocated_resources: dict[str, Any] | None = None,
        duration: float | None = None,
    ):
        super().__init__(
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

    @property
    def allocated_resources(self) -> dict[str, Any]:
        return self.data.get("allocated_resources", {})

    @property
    def duration(self) -> float | None:
        return self.data.get("duration")


class ExecutionEnvironmentResourceMonitoringEvent(ExecutionEnvironmentEvent):
    """Event emitted for execution environment resource monitoring."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        execution_config: dict[str, Any] | None = None,
        cpu_usage: float | None = None,
        memory_usage: float | None = None,
        additional_metrics: dict[str, Any] | None = None,
    ):
        super().__init__(
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

    @property
    def cpu_usage(self) -> float | None:
        return self.data.get("cpu_usage")

    @property
    def memory_usage(self) -> float | None:
        return self.data.get("memory_usage")

    @property
    def additional_metrics(self) -> dict[str, Any]:
        return self.data.get("additional_metrics", {})


class ExecutionEnvironmentLimitExceededEvent(ExecutionEnvironmentEvent):
    """Event emitted when execution environment limits are exceeded."""

    def __init__(
        self,
        environment_id: str,
        environment_name: str,
        environment_type: str,
        execution_config: dict[str, Any] | None = None,
        limit_type: str = "unknown",
        current_value: float | None = None,
        limit_value: float | None = None,
        action_taken: str = "none",
    ):
        super().__init__(
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

    @property
    def limit_type(self) -> str:
        return self.data.get("limit_type", "unknown")

    @property
    def current_value(self) -> float | None:
        return self.data.get("current_value")

    @property
    def limit_value(self) -> float | None:
        return self.data.get("limit_value")

    @property
    def action_taken(self) -> str:
        return self.data.get("action_taken", "none")
