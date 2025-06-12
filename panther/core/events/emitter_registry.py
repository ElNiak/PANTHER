"""
EmitterRegistry for centralized management of event emitters.

This module provides a centralized registry for all event emitters in PANTHER,
ensuring single instances and preventing duplication issues.
"""

from panther.core.observer.management.event_manager import EventManager
from panther.core.events import (
    ExperimentEventEmitter,
    TestEventEmitter,
    ServiceEventEmitter,
    EnvironmentEventEmitter,
    StepEventEmitter,
    PluginEventEmitter,
    AssertionEventEmitter,
    MetricsEventEmitter,
)
from panther.core.state import StateManager


class EmitterRegistry:
    """
    Centralized registry for all event emitters in PANTHER.

    This class ensures that only one instance of each emitter type exists
    and provides controlled access to test-specific emitters.
    """

    def __init__(self, event_manager: EventManager, state_manager: StateManager | None = None):
        """
        Initialize the emitter registry with all required emitters.

        Args:
            event_manager: The shared EventManager instance
            state_manager: Optional StateManager for state tracking
        """
        self.event_manager = event_manager
        self.state_manager = state_manager or StateManager()

        # Create single instances of each emitter type
        self.experiment_emitter = ExperimentEventEmitter(event_manager, "global")
        self.service_emitter = ServiceEventEmitter(event_manager)
        self.environment_emitter = EnvironmentEventEmitter(event_manager)
        self.step_emitter = StepEventEmitter(event_manager)
        self.plugin_emitter = PluginEventEmitter(event_manager)
        self.assertion_emitter = AssertionEventEmitter(event_manager)
        self.metrics_emitter = MetricsEventEmitter(event_manager)

        # Dictionary to store test-specific emitters
        self.test_emitters: dict[str, TestEventEmitter] = {}

    def get_test_emitter(self, test_name: str) -> TestEventEmitter:
        """
        Get or create a test-specific emitter.

        Args:
            test_name: The name of the test case

        Returns:
            TestEventEmitter: The test-specific emitter instance
        """
        if test_name not in self.test_emitters:
            self.test_emitters[test_name] = TestEventEmitter(self.event_manager, test_name)
        return self.test_emitters[test_name]

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

    def get_all_emitters(self) -> dict[str, object]:
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
