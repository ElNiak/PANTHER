"""Centralized registry for all event emitters and state managers.

Provides :class:`EmitterRegistry`, the single coordination point between
event producers and the state management system.  Ensures singleton emitter
instances per type, validates state transitions before event emission, and
manages per-entity memory cleanup.

Usage::

    from panther.core.events.emitter_registry import EmitterRegistry
    from panther.core.observer.management.event_manager import EventManager

    registry = EmitterRegistry(EventManager.get_instance())

    # Get domain emitters
    test_emitter = registry.get_emitter("test", test_name="my-test")
    svc_emitter = registry.get_emitter("service")

    # State-validated emission
    registry.emit_service_created_with_validation(
        "svc-1", "picoquic", "iut", "picoquic"
    )

    # Cleanup after completion
    registry.cleanup_test_emitter("my-test")
    registry.cleanup_service_state("svc-1")
"""

from typing import Dict, List, Optional

from panther.core.events.assertion.emitter import AssertionEventEmitter
from panther.core.events.environment.emitter import EnvironmentEventEmitter
from panther.core.events.environment.states import EnvironmentStateManager
from panther.core.events.experiment.emitter import ExperimentEventEmitter

# Import event-based state managers
from panther.core.events.experiment.states import ExperimentStateManager
from panther.core.events.metrics.emitter import MetricsEventEmitter
from panther.core.events.plugin.emitter import PluginEventEmitter
from panther.core.events.plugin.states import PluginStateManager
from panther.core.events.service.emitter import ServiceEventEmitter
from panther.core.events.service.states import ServiceStateManager
from panther.core.events.step.emitter import StepEventEmitter
from panther.core.events.test.emitter import TestEventEmitter
from panther.core.events.test.states import TestStateManager
from panther.core.observer.management.event_manager import EventManager


class EmitterRegistry:
    """Centralized registry for all event emitters with state validation.

    Manages the complete lifecycle of event emitters, ensuring singleton
    instances per emitter type while providing state-aware event emission.
    Integrates closely with domain state managers to prevent invalid state
    transitions and maintains referential integrity across the event system.

    Service State Machine (validated by this registry)::

        [*] --> CREATED --> PREPARING --> DEPLOYING --> DEPLOYED
        DEPLOYED --> READY --> RUNNING --> STOPPED --> [*]
        RUNNING --> ERROR --> STOPPED

    Emitter Instances (created in ``__init__``):
        - ``experiment_emitter``: :class:`ExperimentEventEmitter`
        - ``service_emitter``: :class:`ServiceEventEmitter`
        - ``environment_emitter``: :class:`EnvironmentEventEmitter`
        - ``step_emitter``: :class:`StepEventEmitter`
        - ``plugin_emitter``: :class:`PluginEventEmitter`
        - ``assertion_emitter``: :class:`AssertionEventEmitter`
        - ``metrics_emitter``: :class:`MetricsEventEmitter`
        - ``test_emitters``: ``Dict[str, TestEventEmitter]`` (created on demand)

    State Manager Instances:
        - ``experiment_state``: Created on demand via :meth:`get_experiment_state`
        - ``plugin_state``: :class:`PluginStateManager` (created immediately)
        - ``service_states``: ``Dict[str, ServiceStateManager]`` (per service)
        - ``test_states``: ``Dict[str, TestStateManager]`` (per test)
        - ``environment_states``: ``Dict[str, EnvironmentStateManager]`` (per env)

    Memory Management:
        - **Test emitters**: Created on-demand, cleaned up via
          :meth:`cleanup_test_emitter` after test completion.
        - **Service states**: Per ``service_id``, cleaned up via
          :meth:`cleanup_service_state`.
        - **Environment states**: Per ``env_id``, cleaned up via
          :meth:`cleanup_environment_state`.
        - **Global emitters**: Persistent throughout application lifecycle.
    """

    def __init__(self, event_manager: EventManager):
        """
        Initialize the emitter registry with all required emitters and state managers.

        Args:
            event_manager: The shared EventManager instance
        """
        self.event_manager = event_manager

        # Initialize containers for event-based state managers
        # Note: Individual state managers are created on-demand with entity IDs
        self.experiment_state: Optional[ExperimentStateManager] = (
            None  # Created when experiment starts
        )
        self.plugin_state = PluginStateManager()  # Can be created immediately
        self.environment_states: Dict[str, EnvironmentStateManager] = (
            {}
        )  # env_id -> state manager
        self.service_states: Dict[str, ServiceStateManager] = (
            {}
        )  # service_id -> state manager
        self.test_states: Dict[str, TestStateManager] = {}  # test_id -> state manager

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
        """
        Get or create a test-specific emitter.

        Args:
            test_name: The name of the test case

        Returns:
            TestEventEmitter: The test-specific emitter instance
        """
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

    def get_experiment_state(self, experiment_id: str) -> ExperimentStateManager:
        """
        Get or create the experiment state manager.

        Args:
            experiment_id: The unique experiment identifier

        Returns:
            ExperimentStateManager: The experiment state manager
        """
        if self.experiment_state is None:
            self.experiment_state = ExperimentStateManager(experiment_id)
        return self.experiment_state

    def emit_service_created_with_validation(
        self,
        service_id: str,
        service_name: str,
        service_type: str,
        implementation: str,
        config: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Emit service created event with state validation.

        Args:
            service_id: Unique service identifier
            service_name: Human-readable service name
            service_type: Type of service
            implementation: Implementation name
            config: Optional configuration data

        Returns:
            bool: True if event was emitted successfully
        """
        # Get or create state manager for this service
        state_manager = self.get_service_state(service_id)

        # Import the state enum
        from panther.core.events.service.states import ServiceState

        # Validate state transition - services should start in CREATED state
        if not state_manager.can_transition_to(ServiceState.CREATED):
            self.service_emitter.logger.warning(
                f"Cannot create service {service_id} - invalid state transition from {state_manager.current_state}"
            )
            return False

        # Perform state transition
        state_manager.transition_to(ServiceState.CREATED, trigger="service_creation")

        # Emit the event
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

    # Test lifecycle state-aware methods
    def emit_test_started_with_validation(
        self,
        test_id: str,
        test_name: str,
        test_description: Optional[str] = None,
        expected_duration: Optional[float] = None,
    ) -> bool:
        """Emit test started event with state validation."""
        state_manager = self.get_test_state(test_id)
        from panther.core.events.test.states import TestState

        if not state_manager.can_transition_to(TestState.RUNNING):
            return False

        state_manager.transition_to(TestState.RUNNING, trigger="test_started")
        test_emitter = self.get_test_emitter(test_name)
        test_emitter.emit_execution_started(
            steps=["setup", "execution", "teardown"],
            expected_duration=expected_duration,
        )
        return True

    def emit_test_completed_with_validation(
        self,
        test_id: str,
        test_name: str,
        success: bool,
        duration: Optional[float] = None,
        results: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Emit test completed event with state validation."""
        state_manager = self.get_test_state(test_id)
        from panther.core.events.test.states import TestState

        target_state = TestState.PASSED if success else TestState.FAILED
        if not state_manager.can_transition_to(target_state):
            return False

        state_manager.transition_to(target_state, trigger="test_completed")
        test_emitter = self.get_test_emitter(test_name)
        test_emitter.emit_completed(
            total_duration_seconds=duration,
            summary=results,
        )
        return True

    def emit_test_failed_with_validation(
        self,
        test_id: str,
        test_name: str,
        error_message: str,
        error_details: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Emit test failed event with state validation."""
        state_manager = self.get_test_state(test_id)
        from panther.core.events.test.states import TestState

        if not state_manager.can_transition_to(TestState.FAILED):
            return False

        state_manager.transition_to(TestState.FAILED, trigger="test_failed")
        test_emitter = self.get_test_emitter(test_name)
        test_emitter.emit_failed(
            error_message=error_message,
            summary=error_details,
        )
        return True

    # Environment lifecycle state-aware methods
    def emit_environment_prepared_with_validation(
        self,
        env_id: str,
        environment_type: str,
        preparation_details: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Emit environment prepared event with state validation."""
        state_manager = self.get_environment_state(env_id)
        from panther.core.events.environment.states import EnvironmentState

        if not state_manager.can_transition_to(EnvironmentState.PREPARED):
            return False

        state_manager.transition_to(
            EnvironmentState.PREPARED, trigger="environment_prepared"
        )
        self.environment_emitter.emit_environment_prepared(
            environment_type=environment_type,
            preparation_details=preparation_details,
        )
        return True

    def emit_environment_deployed_with_validation(
        self,
        env_id: str,
        environment_type: str,
        deployment_details: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Emit environment deployed event with state validation."""
        state_manager = self.get_environment_state(env_id)
        from panther.core.events.environment.states import EnvironmentState

        if not state_manager.can_transition_to(EnvironmentState.DEPLOYED):
            return False

        state_manager.transition_to(
            EnvironmentState.DEPLOYED, trigger="environment_deployed"
        )
        self.environment_emitter.emit_environment_deployed(
            environment_type=environment_type,
            deployment_details=deployment_details,
        )
        return True

    def cleanup_test_emitter(self, test_name: str):
        """
        Remove a test-specific emitter after test completion.

        This helps prevent memory leaks by cleaning up test-specific
        emitters that are no longer needed.

        Args:
            test_name: The name of the test case to clean up
        """
        if test_name in self.test_emitters:
            del self.test_emitters[test_name]
        # Also cleanup the corresponding test state manager
        if test_name in self.test_states:
            del self.test_states[test_name]

    def get_service_state(self, service_id: str) -> ServiceStateManager:
        """
        Get or create a service-specific state manager.

        Args:
            service_id: The unique service identifier

        Returns:
            ServiceStateManager: The service-specific state manager
        """
        if service_id not in self.service_states:
            self.service_states[service_id] = ServiceStateManager(service_id)
        return self.service_states[service_id]

    def get_test_state(self, test_id: str) -> TestStateManager:
        """
        Get or create a test-specific state manager.

        Args:
            test_id: The unique test identifier

        Returns:
            TestStateManager: The test-specific state manager
        """
        if test_id not in self.test_states:
            self.test_states[test_id] = TestStateManager(test_id)
        return self.test_states[test_id]

    def get_environment_state(self, env_id: str) -> EnvironmentStateManager:
        """
        Get or create an environment-specific state manager.

        Args:
            env_id: The unique environment identifier

        Returns:
            EnvironmentStateManager: The environment-specific state manager
        """
        if env_id not in self.environment_states:
            self.environment_states[env_id] = EnvironmentStateManager(env_id)
        return self.environment_states[env_id]

    def cleanup_service_state(self, service_id: str):
        """Remove a service-specific state manager after service cleanup."""
        if service_id in self.service_states:
            del self.service_states[service_id]

    def cleanup_environment_state(self, env_id: str):
        """Remove an environment-specific state manager after environment cleanup."""
        if env_id in self.environment_states:
            del self.environment_states[env_id]

    def get_all_emitters(self) -> Dict[str, object]:
        """
        Get all emitters for debugging or inspection.

        Returns:
            Dict containing all emitter instances
        """
        return {
            "experiment": self.experiment_emitter,
            "service": self.service_emitter,
            "environment": self.environment_emitter,
            "step": self.step_emitter,
            "plugin": self.plugin_emitter,
            "assertion": self.assertion_emitter,
            "metrics": self.metrics_emitter,
            "test_emitters": self.test_emitters.copy(),
        }

    def get_all_state_managers(self) -> Dict[str, object]:
        """
        Get all state managers for debugging or inspection.

        Returns:
            Dict containing all state manager instances
        """
        return {
            "experiment_state": self.experiment_state,
            "plugin_state": self.plugin_state,
            "service_states": self.service_states.copy(),
            "test_states": self.test_states.copy(),
            "environment_states": self.environment_states.copy(),
        }
