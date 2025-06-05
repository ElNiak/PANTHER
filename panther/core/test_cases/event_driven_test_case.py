"""
Event-Driven Test Case Module

This module provides an implementation of test cases that use event-driven
communication with plugins rather than direct method calls.
"""

import logging
import time
import uuid
from typing import Any

from panther.core.observer.events import (
    TestStartedEvent,
    TestCompletedEvent,
    EnvironmentSetupStartedEvent,
)
from panther.core.observer.core.observer_interface import IObserver
from panther.core.observer.core.core_events import Event
from panther.plugins.plugin_communicator import PluginCommunicator
from panther.plugins.enhanced_plugin_registry import EnhancedPluginRegistry


class EventDrivenTestCase:
    """
    Test case implementation that uses event-driven communication with plugins.

    This class replaces direct method calls with event-based communication,
    promoting separation of concerns and loose coupling between components.
    """

    def __init__(
        self,
        plugin_registry: EnhancedPluginRegistry,
        test_config: dict[str, Any],
        timeout: int = 300,
    ):
        """
        Initialize the test case.

        Args:
            plugin_registry: Registry for plugin management and event dispatching
            test_config: Configuration for the test
            timeout: Timeout for the test execution in seconds
        """
        self.plugin_registry = plugin_registry
        self.test_config = test_config
        self.timeout = timeout
        self.logger = logging.getLogger("EventDrivenTestCase")

        self.test_id = test_config.get("id") or str(uuid.uuid4())
        self.communicator = PluginCommunicator(plugin_registry)

        # Observer to track test-related events
        self.observer = TestCaseObserver(self)
        self.plugin_registry.event_manager.register_observer(self.observer)

        self.status = {
            "state": "created",
            "environment_ready": False,
            "services_ready": False,
            "test_completed": False,
            "success": False,
            "details": {},
        }

    def run(self) -> dict[str, Any]:
        """
        Run the test case.

        This method initiates the test execution using events rather than
        direct method calls, then waits for the test to complete or timeout.

        Returns:
            Dict[str, Any]: Test execution result
        """
        # Start the test
        self.status["state"] = "starting"

        # Emit test started event
        event = TestStartedEvent(
            name="test_started",
            data={
                "test_id": self.test_id,
                "test_config": self.test_config,
            },
        )
        self.plugin_registry.dispatch_event(event)

        # Request environment setup
        self._request_environment_setup()

        # Wait for test completion or timeout
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            if self.status["test_completed"]:
                break

            # Check if environment is ready but services aren't yet
            if self.status["environment_ready"] and not self.status["services_ready"]:
                self._request_services_start()

            # Check if environment and services are ready but test hasn't started yet
            if (
                self.status["environment_ready"]
                and self.status["services_ready"]
                and self.status["state"] == "services_ready"
            ):
                self._request_test_execution()

            time.sleep(1)
        else:
            # Timeout occurred
            self.status["state"] = "timeout"
            self.logger.error(f"Test {self.test_id} timed out after {self.timeout} seconds")

            # Emit test completed event with timeout
            event = TestCompletedEvent(
                name="test_completed",
                data={
                    "test_id": self.test_id,
                    "success": False,
                    "reason": "timeout",
                    "execution_time": self.timeout,
                },
            )
            self.plugin_registry.dispatch_event(event)

        # Clean up
        self.plugin_registry.event_manager.unregister_observer(self.observer)

        # Handle test teardown via events
        if self.status["state"] != "teardown_completed":
            self._request_teardown()

        # Return the final status
        return {
            "test_id": self.test_id,
            "success": self.status["success"],
            "state": self.status["state"],
            "details": self.status["details"],
        }

    def _request_environment_setup(self) -> None:
        """
        Request environment setup via events.
        """
        self.status["state"] = "environment_setup_requested"

        env_type = self.test_config.get("environment", {}).get("type")
        if not env_type:
            self.logger.error("Environment type not specified in test config")
            self.status["state"] = "error"
            return

        # Find an environment plugin of the appropriate type
        environment_plugin_id = self._find_environment_plugin(env_type)
        if not environment_plugin_id:
            self.logger.error(f"No environment plugin found for type: {env_type}")
            self.status["state"] = "error"
            return

        # Emit environment setup event
        event = EnvironmentSetupStartedEvent(
            name="environment_setup_started",
            data={
                "test_id": self.test_id,
                "environment_type": env_type,
                "environment_config": self.test_config.get("environment", {}),
            },
        )
        self.plugin_registry.dispatch_event(event)

    def _request_services_start(self) -> None:
        """
        Request services to start via events.
        """
        self.status["state"] = "services_starting"

        services = self.test_config.get("services", [])
        if not services:
            # No services needed, mark as ready
            self.status["services_ready"] = True
            self.status["state"] = "services_ready"
            return

        # For each service, find a plugin and request it to start
        for service_config in services:
            service_type = service_config.get("type")
            if not service_type:
                continue

            self.communicator.request_service(
                requester_id=self.test_id,
                service_type=service_type,
                parameters=service_config,
            )

    def _request_test_execution(self) -> None:
        """
        Request test execution via events.
        """
        self.status["state"] = "test_execution_requested"

        test_type = self.test_config.get("test_type", "default")

        # Find a tester plugin for this test type
        tester_plugin_id = self._find_tester_plugin(test_type)
        if not tester_plugin_id:
            self.logger.error(f"No tester plugin found for type: {test_type}")
            self.status["state"] = "error"
            return

        # Request the test to be run
        self.communicator.send_custom_event(
            source_plugin_id=self.test_id,
            event_name="tester.run.request",
            data={
                "test_id": self.test_id,
                "config": self.test_config,
            },
            target_plugin_ids=[tester_plugin_id],
        )

    def _request_teardown(self) -> None:
        """
        Request test teardown via events.
        """
        self.status["state"] = "teardown_requested"

        # Emit teardown events for services and environment
        self.communicator.send_custom_event(
            source_plugin_id=self.test_id,
            event_name="service.teardown.request",
            data={
                "test_id": self.test_id,
            },
        )

        self.communicator.send_custom_event(
            source_plugin_id=self.test_id,
            event_name="environment.teardown.request",
            data={
                "test_id": self.test_id,
            },
        )

        # Mark as completed
        self.status["state"] = "teardown_completed"

    def _find_environment_plugin(self, env_type: str) -> str | None:
        """
        Find an appropriate environment plugin for the given type.

        Args:
            env_type: Type of environment needed

        Returns:
            Optional[str]: Plugin ID if found, None otherwise
        """
        # This is a simplified implementation - in a real system, you would
        # query the plugin registry for available environment plugins
        plugins = self.plugin_registry.get_all_plugins()
        for plugin_id, plugin in plugins.items():
            if (
                hasattr(plugin, "_get_environment_type")
                and plugin._get_environment_type() == env_type
            ):
                return plugin_id
        return None

    def _find_tester_plugin(self, test_type: str) -> str | None:
        """
        Find an appropriate tester plugin for the given type.

        Args:
            test_type: Type of test needed

        Returns:
            Optional[str]: Plugin ID if found, None otherwise
        """
        # This is a simplified implementation - in a real system, you would
        # query the plugin registry for available tester plugins
        plugins = self.plugin_registry.get_all_plugins()
        for plugin_id, plugin in plugins.items():
            if (
                hasattr(plugin, "_get_test_types")
                and test_type in getattr(plugin, "_get_test_types", lambda: [])()
            ):
                return plugin_id
        return None

    def update_status(self, updates: dict[str, Any]) -> None:
        """
        Update the test case status.

        Args:
            updates: Status updates to apply
        """
        self.status.update(updates)


class TestCaseObserver(IObserver):
    """
    Observer for test case events.

    This observer tracks events related to a specific test case and updates
    the test case status accordingly.
    """

    def __init__(self, test_case: EventDrivenTestCase):
        """
        Initialize the test case observer.

        Args:
            test_case: Test case to observe events for
        """
        super().__init__()
        self.test_case = test_case
        self.test_id = test_case.test_id
        self.logger = logging.getLogger(f"TestCaseObserver.{self.test_id}")

    def on_event(self, event: Event) -> None:
        """
        Handle an event.

        Args:
            event: Event to handle
        """
        event_type = event.get_type()

        # Check if the event is related to this test case
        if "test_id" in event.data and event.data["test_id"] != self.test_id:
            return

        if event_type == "environment.setup.completed":
            # Environment setup completed
            success = event.data.get("success", False)
            self.test_case.update_status(
                {
                    "environment_ready": success,
                    "state": "environment_ready" if success else "environment_setup_failed",
                }
            )

        elif event_type == "service.ready":
            # A service is ready - check if all required services are ready
            service_id = event.data.get("service_id")
            self.logger.info(f"Service ready: {service_id}")

            # In a real implementation, you would track all required services
            # For simplicity, we'll just mark services as ready
            self.test_case.update_status(
                {
                    "services_ready": True,
                    "state": "services_ready",
                }
            )

        elif event_type == "test.completed":
            # Test execution completed
            success = event.data.get("success", False)
            result = event.data.get("result", {})

            self.test_case.update_status(
                {
                    "test_completed": True,
                    "success": success,
                    "state": "completed",
                    "details": result,
                }
            )
