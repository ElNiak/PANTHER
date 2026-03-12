"""Centralized registry for all event emitters with service state validation.

Provides `EmitterRegistry`, the single coordination point between
event producers and the service state management system.  Ensures singleton
emitter instances per type, validates service state transitions before
event emission, and manages per-entity memory cleanup.

Usage::

    from panther.core.events.emitter_registry import EmitterRegistry
    from panther.core.observer.management.event_manager import EventManager

    registry = EmitterRegistry(EventManager.get_instance())

    # Get domain emitters
    test_emitter = registry.get_emitter("test", test_name="my-test")
    svc_emitter = registry.get_emitter("service")

    # Cleanup after completion
    registry.cleanup_test_emitter("my-test")
    registry.cleanup_service_state("svc-1")
"""

import threading
from typing import Dict, List, Optional

from panther.core.events.assertion.emitter import AssertionEventEmitter
from panther.core.events.environment.emitter import EnvironmentEventEmitter
from panther.core.events.experiment.emitter import ExperimentEventEmitter
from panther.core.events.metrics.emitter import MetricsEventEmitter
from panther.core.events.plugin.emitter import PluginEventEmitter
from panther.core.events.service.emitter import ServiceEventEmitter
from panther.core.events.service.states import ServiceStateManager
from panther.core.events.step.emitter import StepEventEmitter
from panther.core.events.test.emitter import TestEventEmitter
from panther.core.observer.management.event_manager import EventManager


class EmitterRegistry:
    """Centralized registry for all event emitters with state validation.

    Manages the complete lifecycle of event emitters, ensuring singleton
    instances per emitter type while providing state-aware service event
    emission. Integrates with ``ServiceStateManager`` to validate state
    transitions before emission.

    Service State Machine (validated by this registry)::

        [*] --> CREATED --> PREPARING --> PREPARED --> DEPLOYING --> DEPLOYED
        DEPLOYED --> STARTING --> RUNNING --> READY
        READY --> STOPPING --> STOPPED --> DESTROYING --> DESTROYED --> [*]
        STOPPED --> STARTING (restart)
        Any --> ERROR --> STOPPING | DESTROYING | DESTROYED

    Emitter Instances (created in ``__init__``):
        - ``experiment_emitter``: `ExperimentEventEmitter`
        - ``service_emitter``: `ServiceEventEmitter`
        - ``environment_emitter``: `EnvironmentEventEmitter`
        - ``step_emitter``: `StepEventEmitter`
        - ``plugin_emitter``: `PluginEventEmitter`
        - ``assertion_emitter``: `AssertionEventEmitter`
        - ``metrics_emitter``: `MetricsEventEmitter`
        - ``test_emitters``: ``Dict[str, TestEventEmitter]`` (created on demand)

    Memory Management:
        - **Test emitters**: Created on-demand, cleaned up via
          `cleanup_test_emitter()` after test completion.
        - **Service states**: Per ``service_id``, cleaned up via
          `cleanup_service_state()`.
        - **Global emitters**: Persistent throughout application lifecycle.
    """

    def __init__(self, event_manager: EventManager):
        """Initialize the emitter registry with all required emitters.

        Args:
            event_manager: The shared EventManager instance
        """
        self.event_manager = event_manager
        self._lock = threading.Lock()

        # Service state managers for lifecycle validation (per service_id)
        self.service_states: Dict[str, ServiceStateManager] = {}

        # Create single instances of each emitter type
        self.experiment_emitter = ExperimentEventEmitter(event_manager, "global")
        self.service_emitter = ServiceEventEmitter(event_manager)
        self.environment_emitter = EnvironmentEventEmitter(event_manager)
        self.step_emitter = StepEventEmitter(event_manager)
        self.plugin_emitter = PluginEventEmitter(event_manager)
        self.assertion_emitter = AssertionEventEmitter(event_manager)
        self.metrics_emitter = MetricsEventEmitter(event_manager)

        # Dictionary to store test-specific emitters
        self.test_emitters: Dict[str, TestEventEmitter] = {}

    def get_test_emitter(self, test_name: str) -> TestEventEmitter:
        """Get or create a test-specific emitter (thread-safe).

        Args:
            test_name: The name of the test case

        Returns:
            TestEventEmitter: The test-specific emitter instance
        """
        with self._lock:
            if test_name not in self.test_emitters:
                self.test_emitters[test_name] = TestEventEmitter(
                    self.event_manager, test_name
                )
            return self.test_emitters[test_name]

    def get_emitter(self, emitter_type: str, test_name: str = "default_test"):
        """Get an emitter by type string.

        Args:
            emitter_type: One of ``"experiment"``, ``"service"``,
                ``"environment"``, ``"step"``, ``"plugin"``,
                ``"assertion"``, ``"metrics"``, or ``"test"``.
            test_name: Test name used when ``emitter_type="test"`` to
                retrieve or create a test-specific emitter.

        Returns:
            The corresponding emitter instance.

        Raises:
            ValueError: If *emitter_type* is not recognized.
        """
        if emitter_type == "test":
            # For test emitters, return or create a test-specific emitter
            return self.get_test_emitter(test_name)

        emitter_map = {
            "experiment": self.experiment_emitter,
            "service": self.service_emitter,
            "environment": self.environment_emitter,
            "step": self.step_emitter,
            "plugin": self.plugin_emitter,
            "assertion": self.assertion_emitter,
            "metrics": self.metrics_emitter,
        }

        if emitter_type not in emitter_map:
            raise ValueError(f"Unknown emitter type: {emitter_type}")

        return emitter_map[emitter_type]

    def emit_service_created_with_validation(
        self,
        service_id: str,
        service_name: str,
        service_type: str,
        implementation: str,
        config: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Emit service created event with state validation.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            service_type: Type of service
            implementation: Implementation name
            config: Optional configuration data

        Returns:
            bool: True if event was emitted successfully
        """
        state_manager = self.get_service_state(service_id)
        from panther.core.events.service.states import ServiceState

        # CREATED is the initial state — skip validation for fresh state managers.
        # Only validate if re-creating from a different state.
        if state_manager.current_state != ServiceState.CREATED:
            if not state_manager.can_transition_to(ServiceState.CREATED):
                self.service_emitter.logger.warning(
                    "Cannot create service %s — invalid state transition from %s",
                    service_id,
                    state_manager.current_state,
                )
                return False
            state_manager.transition_to(
                ServiceState.CREATED, trigger="service_creation"
            )

        self.service_emitter.emit_service_created(
            service_id=service_id,
            service_name=service_name,
            service_type=service_type,
            implementation=implementation,
            config=config,
        )
        return True

    def emit_service_preparation_started_with_validation(
        self, service_id: str, service_name: str, preparation_type: str = "default"
    ) -> bool:
        """Emit service preparation started event with state validation."""
        state_manager = self.get_service_state(service_id)
        from panther.core.events.service.states import ServiceState

        if not state_manager.can_transition_to(ServiceState.PREPARING):
            self.service_emitter.logger.warning(
                "Cannot transition service %s from %s to PREPARING",
                service_id,
                state_manager.current_state,
            )
            return False

        state_manager.transition_to(ServiceState.PREPARING, trigger="preparation_start")
        self.service_emitter.emit_service_preparation_started(
            service_id=service_id,
            service_name=service_name,
        )
        return True

    def emit_service_deployment_started_with_validation(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        deployment_config: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Emit service deployment started event with state validation."""
        state_manager = self.get_service_state(service_id)
        from panther.core.events.service.states import ServiceState

        if not state_manager.can_transition_to(ServiceState.DEPLOYING):
            self.service_emitter.logger.warning(
                "Cannot transition service %s from %s to DEPLOYING",
                service_id,
                state_manager.current_state,
            )
            return False

        state_manager.transition_to(ServiceState.DEPLOYING, trigger="deployment_start")
        self.service_emitter.emit_service_deployment_started(
            service_id=service_id,
            service_name=service_name,
            environment=environment,
            deployment_config=deployment_config,
        )
        return True

    def emit_service_ready_with_validation(
        self,
        service_id: str,
        service_name: str,
        readiness_checks: Optional[Dict[str, bool]] = None,
    ) -> bool:
        """Emit service ready event with state validation."""
        state_manager = self.get_service_state(service_id)
        from panther.core.events.service.states import ServiceState

        if not state_manager.can_transition_to(ServiceState.READY):
            self.service_emitter.logger.warning(
                "Cannot transition service %s from %s to READY",
                service_id,
                state_manager.current_state,
            )
            return False

        state_manager.transition_to(ServiceState.READY, trigger="service_ready")
        self.service_emitter.emit_service_ready(
            service_id=service_id,
            service_name=service_name,
            readiness_checks=readiness_checks,
        )
        return True

    def emit_service_deployment_completed_with_validation(
        self,
        service_id: str,
        service_name: str,
        environment: str,
        endpoint: Optional[str] = None,
        ports: Optional[List[int]] = None,
        deployment_details: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Emit service deployment completed event with state validation."""
        state_manager = self.get_service_state(service_id)
        from panther.core.events.service.states import ServiceState

        if not state_manager.can_transition_to(ServiceState.DEPLOYED):
            self.service_emitter.logger.warning(
                "Cannot transition service %s from %s to DEPLOYED",
                service_id,
                state_manager.current_state,
            )
            return False

        state_manager.transition_to(
            ServiceState.DEPLOYED, trigger="deployment_completed"
        )
        self.service_emitter.emit_service_deployment_completed(
            service_id=service_id,
            service_name=service_name,
            environment=environment,
            endpoint=endpoint,
            ports=ports,
            deployment_details=deployment_details,
        )
        return True

    def emit_service_started_with_validation(
        self,
        service_id: str,
        service_name: str,
        pid: Optional[int] = None,
        start_time: Optional[str] = None,
    ) -> bool:
        """Emit service started event with state validation."""
        state_manager = self.get_service_state(service_id)
        from panther.core.events.service.states import ServiceState

        if not state_manager.can_transition_to(ServiceState.RUNNING):
            self.service_emitter.logger.warning(
                "Cannot transition service %s from %s to RUNNING",
                service_id,
                state_manager.current_state,
            )
            return False

        state_manager.transition_to(ServiceState.RUNNING, trigger="service_started")
        self.service_emitter.emit_service_started(
            service_id=service_id,
            service_name=service_name,
            pid=pid,
            start_time=start_time,
        )
        return True

    def emit_service_stopped_with_validation(
        self,
        service_id: str,
        service_name: str,
        exit_code: Optional[int] = None,
        reason: Optional[str] = None,
        uptime_seconds: Optional[float] = None,
    ) -> bool:
        """Emit service stopped event with state validation."""
        state_manager = self.get_service_state(service_id)
        from panther.core.events.service.states import ServiceState

        if not state_manager.can_transition_to(ServiceState.STOPPED):
            self.service_emitter.logger.warning(
                "Cannot transition service %s from %s to STOPPED",
                service_id,
                state_manager.current_state,
            )
            return False

        state_manager.transition_to(ServiceState.STOPPED, trigger="service_stopped")
        self.service_emitter.emit_service_stopped(
            service_id=service_id,
            service_name=service_name,
            exit_code=exit_code,
            reason=reason,
            uptime_seconds=uptime_seconds,
        )
        return True

    def emit_service_error_with_validation(
        self,
        service_id: str,
        service_name: str,
        error_message: str,
        error_type: Optional[str] = None,
        error_details: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Emit service error event with state validation."""
        state_manager = self.get_service_state(service_id)
        from panther.core.events.service.states import ServiceState

        if not state_manager.can_transition_to(ServiceState.ERROR):
            self.service_emitter.logger.warning(
                "Cannot transition service %s from %s to ERROR",
                service_id,
                state_manager.current_state,
            )
            return False

        state_manager.transition_to(ServiceState.ERROR, trigger="service_error")
        self.service_emitter.emit_service_error(
            service_id=service_id,
            service_name=service_name,
            error_message=error_message,
            error_type=error_type,
            error_details=error_details,
        )
        return True

    def cleanup_test_emitter(self, test_name: str):
        """Remove a test-specific emitter after test completion (thread-safe)."""
        with self._lock:
            if test_name in self.test_emitters:
                del self.test_emitters[test_name]

    def get_service_state(self, service_id: str) -> ServiceStateManager:
        """Get or create a service-specific state manager (thread-safe)."""
        with self._lock:
            if service_id not in self.service_states:
                self.service_states[service_id] = ServiceStateManager(service_id)
            return self.service_states[service_id]

    def cleanup_service_state(self, service_id: str):
        """Remove a service-specific state manager after service cleanup."""
        with self._lock:
            if service_id in self.service_states:
                del self.service_states[service_id]
