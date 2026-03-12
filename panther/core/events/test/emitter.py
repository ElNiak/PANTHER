"""Test Event Emitter.

This module provides typed event emission for test case lifecycle events.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EntityEventEmitterBase
from panther.core.events.test.events import *


class TestEventEmitter(EntityEventEmitterBase):
    """Type-safe event emitter for test events."""

    def __init__(self, event_manager: "EventManager", test_id: str):
        """Initialize test event emitter.

        Args:
            event_manager: Event manager to emit events through
            test_id: ID of the test this emitter handles
        """
        super().__init__(event_manager, test_id, "test")

    @property
    def test_id(self) -> str:
        """Get the test ID."""
        return self.entity_id

    def emit_created(
        self,
        test_name: str,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit test created event."""
        self._create_and_emit_entity_event(
            TestCreatedEvent,
            test_name=test_name,
            description=description,
            config=config,
        )

    def emit_setup_started(
        self,
        service_count: Optional[int] = None,
        service_names: Optional[List[str]] = None,
    ) -> None:
        """Emit test setup started event."""
        self._create_and_emit_entity_event(
            TestSetupStartedEvent,
            service_count=service_count,
            service_names=service_names,
        )

    def emit_setup_completed(
        self,
        services: Optional[List[str]] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Emit test setup completed event."""
        event = TestSetupCompletedEvent(
            test_id=self.test_id, services=services, duration_seconds=duration_seconds
        )
        self.event_manager.notify(event)

    def emit_setup_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        failed_component: Optional[str] = None,
    ) -> None:
        """Emit test setup failed event."""
        event = TestSetupFailedEvent(
            test_id=self.test_id,
            error_message=error_message,
            error_type=error_type,
            failed_component=failed_component,
        )
        self.event_manager.notify(event)

    def emit_environment_setup_started(
        self, environment_type: str, environment_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit test environment setup started event."""
        event = TestEnvironmentSetupStartedEvent(
            test_id=self.test_id,
            environment_type=environment_type,
            environment_config=environment_config,
        )
        self.event_manager.notify(event)

    def emit_environment_setup_completed(
        self,
        environment_type: str,
        environment_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit test environment setup completed event."""
        event = TestEnvironmentSetupCompletedEvent(
            test_id=self.test_id,
            environment_type=environment_type,
            environment_details=environment_details,
        )
        self.event_manager.notify(event)

    def emit_environment_setup_failed(
        self,
        environment_type: str,
        error_message: str,
        error_type: Optional[str] = None,
    ) -> None:
        """Emit test environment setup failed event."""
        event = TestEnvironmentSetupFailedEvent(
            test_id=self.test_id,
            environment_type=environment_type,
            error_message=error_message,
            error_type=error_type,
        )
        self.event_manager.notify(event)

    def emit_deployment_started(
        self, services_to_deploy: Optional[List[str]] = None
    ) -> None:
        """Emit test deployment started event."""
        event = TestDeploymentStartedEvent(
            test_id=self.test_id, services_to_deploy=services_to_deploy
        )
        self.event_manager.notify(event)

    def emit_deployment_completed(
        self,
        deployed_services: Optional[List[str]] = None,
        deployment_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit test deployment completed event."""
        event = TestDeploymentCompletedEvent(
            test_id=self.test_id,
            deployed_services=deployed_services,
            deployment_details=deployment_details,
        )
        self.event_manager.notify(event)

    def emit_deployment_failed(
        self,
        error_message: str,
        failed_services: Optional[List[str]] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """Emit test deployment failed event."""
        event = TestDeploymentFailedEvent(
            test_id=self.test_id,
            error_message=error_message,
            failed_services=failed_services,
            error_type=error_type,
        )
        self.event_manager.notify(event)

    def emit_execution_started(
        self,
        steps: Optional[List[str]] = None,
        expected_duration: Optional[float] = None,
    ) -> None:
        """Emit test execution started event."""
        event = TestExecutionStartedEvent(
            test_id=self.test_id, steps=steps, expected_duration=expected_duration
        )
        self.event_manager.notify(event)

    def emit_execution_completed(
        self,
        duration_seconds: Optional[float] = None,
        steps_completed: Optional[int] = None,
        assertions_passed: Optional[bool] = None,
    ) -> None:
        """Emit test execution completed event."""
        event = TestExecutionCompletedEvent(
            test_id=self.test_id,
            duration_seconds=duration_seconds,
            steps_completed=steps_completed,
            assertions_passed=assertions_passed,
        )
        self.event_manager.notify(event)

    def emit_execution_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> None:
        """Emit test execution failed event."""
        event = TestExecutionFailedEvent(
            test_id=self.test_id,
            error_message=error_message,
            error_type=error_type,
            phase=phase,
        )
        self.event_manager.notify(event)

    def emit_teardown_started(self) -> None:
        """Emit test teardown started event."""
        event = TestTeardownStartedEvent(test_id=self.test_id)
        self.event_manager.notify(event)

    def emit_teardown_completed(self, duration_seconds: Optional[float] = None) -> None:
        """Emit test teardown completed event."""
        event = TestTeardownCompletedEvent(
            test_id=self.test_id, duration_seconds=duration_seconds
        )
        self.event_manager.notify(event)

    def emit_completed(
        self,
        total_duration_seconds: Optional[float] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit test completed event."""
        event = TestCompletedEvent(
            test_id=self.test_id,
            total_duration_seconds=total_duration_seconds,
            summary=summary,
        )
        self.event_manager.notify(event)

    def emit_failed(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        phase: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit test failed event."""
        event = TestFailedEvent(
            test_id=self.test_id,
            error_message=error_message,
            error_type=error_type,
            phase=phase,
            summary=summary,
        )
        self.event_manager.notify(event)
