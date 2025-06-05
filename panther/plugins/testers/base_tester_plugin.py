"""
Base Tester Plugin Module

This module provides a base class for all tester plugins in the enhanced architecture.
"""

import logging
from abc import abstractmethod
from typing import Any

from panther.core.observer.events import Event
from panther.plugins.enhanced_plugin_interface import IPantherPlugin, IPluginRegistry
from panther.plugins.testers.tester_plugin_event_methods import TesterPluginEventMixin


class BaseTesterPlugin(IPantherPlugin, TesterPluginEventMixin):
    """
    Base class for all tester plugins in PANTHER.

    This class combines the standardized plugin interface with tester-specific
    functionality and event emission methods.
    """

    def __init__(
        self, plugin_id: str, plugin_registry: IPluginRegistry, config: dict[str, Any] = None
    ):
        """
        Initialize the tester plugin.

        Args:
            plugin_id: Unique identifier for this plugin instance
            plugin_registry: Registry for plugin management and event dispatching
            config: Configuration for the plugin
        """
        self.plugin_id = plugin_id
        self.plugin_registry = plugin_registry
        self.config = config or {}
        self.logger = logging.getLogger(f"TesterPlugin.{plugin_id}")
        self._status = {
            "state": "created",
            "details": {},
        }
        self.test_results = {}

    def initialize(self) -> bool:
        """
        Initialize the tester plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            self._status["state"] = "initializing"
            result = self._initialize_tester()
            self._status["state"] = "initialized" if result else "initialization_failed"
            return result
        except Exception as e:
            self.logger.exception(f"Error initializing tester plugin {self.plugin_id}: {e}")
            self._status["state"] = "initialization_failed"
            self._status["details"]["error"] = str(e)
            return False

    def start(self) -> bool:
        """
        Start the tester.

        Returns:
            bool: True if tester started successfully, False otherwise
        """
        try:
            if self._status["state"] != "initialized":
                self.logger.error(
                    f"Cannot start tester plugin {self.plugin_id}: not properly initialized"
                )
                return False

            self._status["state"] = "starting"
            result = self._start_tester()
            self._status["state"] = "running" if result else "start_failed"
            return result
        except Exception as e:
            self.logger.exception(f"Error starting tester plugin {self.plugin_id}: {e}")
            self._status["state"] = "start_failed"
            self._status["details"]["error"] = str(e)
            return False

    def stop(self) -> bool:
        """
        Stop the tester.

        Returns:
            bool: True if tester stopped successfully, False otherwise
        """
        try:
            if self._status["state"] != "running":
                self.logger.warning(f"Tester plugin {self.plugin_id} not running, cannot stop")
                return True

            self._status["state"] = "stopping"
            result = self._stop_tester()
            self._status["state"] = "stopped" if result else "stop_failed"
            return result
        except Exception as e:
            self.logger.exception(f"Error stopping tester plugin {self.plugin_id}: {e}")
            self._status["state"] = "stop_failed"
            self._status["details"]["error"] = str(e)
            return False

    def get_status(self) -> dict[str, Any]:
        """
        Get the current status of the tester plugin.

        Returns:
            Dict[str, Any]: Status information
        """
        # Get any custom status information from the implementation
        custom_status = self._get_custom_status()

        # Add test result summary to status
        result_summary = self._create_result_summary()

        # Merge with base status
        status = {**self._status}
        status["details"] = {
            **status.get("details", {}),
            "results_summary": result_summary,
            **(custom_status or {}),
        }

        return status

    def configure(self, config: dict[str, Any]) -> bool:
        """
        Configure the tester plugin.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        try:
            self.config = config
            return self._configure_tester(config)
        except Exception as e:
            self.logger.exception(f"Error configuring tester plugin {self.plugin_id}: {e}")
            return False

    def handle_event(self, event: Event) -> None:
        """
        Handle an incoming event.

        Args:
            event: The event to handle
        """
        try:
            self._handle_tester_event(event)
        except Exception as e:
            self.logger.exception(f"Error handling event in tester plugin {self.plugin_id}: {e}")

    def get_subscribed_events(self) -> list[str]:
        """
        Get the list of event types this plugin is interested in.

        Returns:
            List[str]: List of event type identifiers
        """
        # Combine base tester events with any additional events from the implementation
        base_events = ["tester.run.request", "service.ready"]
        additional_events = self._get_additional_subscribed_events()
        return base_events + additional_events

    def run_test(self, test_id: str, test_config: dict[str, Any] = None) -> bool:
        """
        Run a test and emit the appropriate events.

        Args:
            test_id: Unique identifier for the test
            test_config: Configuration for the test

        Returns:
            bool: True if the test was started successfully, False otherwise
        """
        try:
            if self._status["state"] != "running":
                self.logger.error(f"Cannot run test: tester plugin {self.plugin_id} not running")
                return False

            # Get test type
            test_type = test_config.get("test_type", "unknown") if test_config else "unknown"

            # Emit test starting event
            self.emit_test_starting(test_id, test_type)

            # Run the test
            result, details = self._run_test(test_id, test_config or {})

            # Store test result
            self.test_results[test_id] = {
                "success": result,
                "details": details or {},
            }

            # Emit test completed event
            self.emit_test_completed(
                test_id,
                success=result,
                result=details,
                error_message=details.get("error") if not result and details else None,
            )

            return result
        except Exception as e:
            self.logger.exception(f"Error running test {test_id}: {e}")

            # Emit test completed event with error
            self.emit_test_completed(
                test_id,
                success=False,
                error_message=str(e),
            )

            return False

    # Abstract methods to be implemented by concrete tester plugins

    @abstractmethod
    def _initialize_tester(self) -> bool:
        """
        Initialize the specific tester implementation.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def _start_tester(self) -> bool:
        """
        Start the specific tester implementation.

        Returns:
            bool: True if tester started successfully, False otherwise
        """
        pass

    @abstractmethod
    def _stop_tester(self) -> bool:
        """
        Stop the specific tester implementation.

        Returns:
            bool: True if tester stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def _configure_tester(self, config: dict[str, Any]) -> bool:
        """
        Configure the specific tester implementation.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        pass

    @abstractmethod
    def _run_test(self, test_id: str, test_config: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
        """
        Run a specific test.

        Args:
            test_id: Unique identifier for the test
            test_config: Configuration for the test

        Returns:
            tuple[bool, Dict[str, Any]]: Tuple containing success flag and test result details
        """
        pass

    # Optional methods with default implementations

    def _handle_tester_event(self, event: Event) -> None:
        """
        Handle tester-specific events.

        Default implementation checks for test run requests and service ready events.

        Args:
            event: The event to handle
        """
        event_type = event.get_type()

        if event_type == "tester.run.request":
            # Extract test info and run the test
            test_id = event.data.get("test_id", f"test_{len(self.test_results)}")
            test_config = event.data.get("config", {})
            self.run_test(test_id, test_config)

        elif event_type == "service.ready":
            # Check if we need to run tests against this service
            service_id = event.data.get("service_id")
            service_type = event.data.get("service_type")

            if service_id and service_type:
                self._on_service_ready(service_id, service_type, event.data)

    def _get_custom_status(self) -> dict[str, Any]:
        """
        Get custom status information specific to the tester implementation.

        Returns:
            Dict[str, Any]: Custom status information
        """
        return {}

    def _get_additional_subscribed_events(self) -> list[str]:
        """
        Get additional event types this tester is interested in, beyond the base ones.

        Returns:
            List[str]: List of additional event type identifiers
        """
        return []

    def _create_result_summary(self) -> dict[str, Any]:
        """
        Create a summary of test results.

        Returns:
            Dict[str, Any]: Test result summary
        """
        total = len(self.test_results)
        successful = sum(1 for result in self.test_results.values() if result.get("success", False))

        return {
            "total_tests": total,
            "successful_tests": successful,
            "failed_tests": total - successful,
            "success_rate": (successful / total) * 100 if total > 0 else 0,
        }

    def _on_service_ready(
        self, service_id: str, service_type: str, details: dict[str, Any]
    ) -> None:
        """
        Handle a service ready event.

        Default implementation does nothing.

        Args:
            service_id: ID of the service that's ready
            service_type: Type of the service
            details: Additional details about the service
        """
        pass
