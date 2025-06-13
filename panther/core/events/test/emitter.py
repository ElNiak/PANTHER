"""
Test Event Emitter

This module provides typed event emission for test case lifecycle events.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from panther.core.observer.management.event_manager import EventManager

from panther.core.events.base.event_emitter_base import EntityEventEmitterBase
from panther.core.events.test.events import *


class TestEventEmitter(EntityEventEmitterBase):
    """Type-safe event emitter for test events."""

    def __init__(self, event_manager: "EventManager", test_id: str):
        """
        Initialize test event emitter.

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
        self, test_name: str, description: str | None = None, config: dict[str, Any] | None = None
    ) -> None:
        """Emit test created event."""
        self._create_and_emit_entity_event(
            TestCreatedEvent, test_name=test_name, description=description, config=config
        )

    def emit_setup_started(
        self, service_count: int | None = None, service_names: list[str] | None = None
    ) -> None:
        """Emit test setup started event."""
        self._create_and_emit_entity_event(
            TestSetupStartedEvent, service_count=service_count, service_names=service_names
        )

    def emit_setup_completed(
        self, services: list[str] | None = None, duration_seconds: float | None = None
    ) -> None:
        """Emit test setup completed event."""
        event = TestSetupCompletedEvent(
            test_id=self.test_id, services=services, duration_seconds=duration_seconds
        )
        self.event_manager.notify(event)

    def emit_setup_failed(
        self, error_message: str, error_type: str | None = None, failed_component: str | None = None
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
        self, environment_type: str, environment_config: dict[str, Any] | None = None
    ) -> None:
        """Emit test environment setup started event."""
        event = TestEnvironmentSetupStartedEvent(
            test_id=self.test_id,
            environment_type=environment_type,
            environment_config=environment_config,
        )
        self.event_manager.notify(event)

    def emit_environment_setup_completed(
        self, environment_type: str, environment_details: dict[str, Any] | None = None
    ) -> None:
        """Emit test environment setup completed event."""
        event = TestEnvironmentSetupCompletedEvent(
            test_id=self.test_id,
            environment_type=environment_type,
            environment_details=environment_details,
        )
        self.event_manager.notify(event)

    def emit_environment_setup_failed(
        self, environment_type: str, error_message: str, error_type: str | None = None
    ) -> None:
        """Emit test environment setup failed event."""
        event = TestEnvironmentSetupFailedEvent(
            test_id=self.test_id,
            environment_type=environment_type,
            error_message=error_message,
            error_type=error_type,
        )
        self.event_manager.notify(event)

    def emit_deployment_started(self, services_to_deploy: list[str] | None = None) -> None:
        """Emit test deployment started event."""
        event = TestDeploymentStartedEvent(
            test_id=self.test_id, services_to_deploy=services_to_deploy
        )
        self.event_manager.notify(event)

    def emit_deployment_completed(
        self,
        deployed_services: list[str] | None = None,
        deployment_details: dict[str, Any] | None = None,
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
        failed_services: list[str] | None = None,
        error_type: str | None = None,
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
        self, steps: list[str] | None = None, expected_duration: float | None = None
    ) -> None:
        """Emit test execution started event."""
        event = TestExecutionStartedEvent(
            test_id=self.test_id, steps=steps, expected_duration=expected_duration
        )
        self.event_manager.notify(event)

    def emit_step_started(
        self,
        step_name: str,
        step_type: str | None = None,
        step_config: dict[str, Any] | None = None,
    ) -> None:
        """Emit test step started event."""
        event = TestStepStartedEvent(
            test_id=self.test_id, step_name=step_name, step_type=step_type, step_config=step_config
        )
        self.event_manager.notify(event)

    def emit_step_completed(
        self,
        step_name: str,
        duration_seconds: float | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Emit test step completed event."""
        event = TestStepCompletedEvent(
            test_id=self.test_id,
            step_name=step_name,
            duration_seconds=duration_seconds,
            result=result,
        )
        self.event_manager.notify(event)

    def emit_step_failed(
        self, step_name: str, error_message: str, error_type: str | None = None
    ) -> None:
        """Emit test step failed event."""
        event = TestStepFailedEvent(
            test_id=self.test_id,
            step_name=step_name,
            error_message=error_message,
            error_type=error_type,
        )
        self.event_manager.notify(event)

    def emit_assertions_started(self, assertions: list[dict[str, Any]] | None = None) -> None:
        """Emit test assertions started event."""
        event = TestAssertionsStartedEvent(test_id=self.test_id, assertions=assertions)
        self.event_manager.notify(event)

    def emit_assertion_checked(
        self,
        assertion_type: str,
        assertion_config: dict[str, Any],
        passed: bool,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Emit assertion checked event."""
        event = TestAssertionCheckedEvent(
            test_id=self.test_id,
            assertion_type=assertion_type,
            assertion_config=assertion_config,
            passed=passed,
            result=result,
        )
        self.event_manager.notify(event)

    def emit_assertions_completed(
        self,
        total_assertions: int,
        passed_assertions: int,
        failed_assertions: int,
        all_passed: bool,
    ) -> None:
        """Emit test assertions completed event."""
        event = TestAssertionsCompletedEvent(
            test_id=self.test_id,
            total_assertions=total_assertions,
            passed_assertions=passed_assertions,
            failed_assertions=failed_assertions,
            all_passed=all_passed,
        )
        self.event_manager.notify(event)

    def emit_assertions_failed(self, error_message: str, error_type: str | None = None) -> None:
        """Emit test assertions failed event."""
        event = TestAssertionsFailedEvent(
            test_id=self.test_id, error_message=error_message, error_type=error_type
        )
        self.event_manager.notify(event)

    def emit_execution_completed(
        self,
        duration_seconds: float | None = None,
        steps_completed: int | None = None,
        assertions_passed: bool | None = None,
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
        self, error_message: str, error_type: str | None = None, phase: str | None = None
    ) -> None:
        """Emit test execution failed event."""
        event = TestExecutionFailedEvent(
            test_id=self.test_id, error_message=error_message, error_type=error_type, phase=phase
        )
        self.event_manager.notify(event)

    def emit_teardown_started(self) -> None:
        """Emit test teardown started event."""
        event = TestTeardownStartedEvent(test_id=self.test_id)
        self.event_manager.notify(event)

    def emit_teardown_completed(self, duration_seconds: float | None = None) -> None:
        """Emit test teardown completed event."""
        event = TestTeardownCompletedEvent(test_id=self.test_id, duration_seconds=duration_seconds)
        self.event_manager.notify(event)

    def emit_completed(
        self, total_duration_seconds: float | None = None, summary: dict[str, Any] | None = None
    ) -> None:
        """Emit test completed event."""
        event = TestCompletedEvent(
            test_id=self.test_id, total_duration_seconds=total_duration_seconds, summary=summary
        )
        self.event_manager.notify(event)

    def emit_failed(
        self,
        error_message: str,
        error_type: str | None = None,
        phase: str | None = None,
        summary: dict[str, Any] | None = None,
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
