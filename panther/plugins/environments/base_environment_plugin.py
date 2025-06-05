"""
Base Environment Plugin Module

This module provides a base class for all environment plugins in the enhanced architecture.
"""

import logging
from abc import abstractmethod
from typing import Any

from panther.core.observer.events import Event
from panther.plugins.enhanced_plugin_interface import IPantherPlugin, IPluginRegistry
from panther.plugins.environments.environment_event_methods import EnvironmentPluginEventMixin
from panther.plugins.environments.enhanced_environment_event_methods import (
    EnhancedEnvironmentPluginEventMixin,
)


class BaseEnvironmentPlugin(
    IPantherPlugin, EnvironmentPluginEventMixin, EnhancedEnvironmentPluginEventMixin
):
    """
    Base class for all environment plugins in PANTHER.

    This class combines the standardized plugin interface with environment-specific
    functionality and event emission methods.
    """

    def __init__(
        self, plugin_id: str, plugin_registry: IPluginRegistry, config: dict[str, Any] = None
    ):
        """
        Initialize the environment plugin.

        Args:
            plugin_id: Unique identifier for this plugin instance
            plugin_registry: Registry for plugin management and event dispatching
            config: Configuration for the plugin
        """
        self.plugin_id = plugin_id
        self.plugin_registry = plugin_registry
        self.config = config or {}
        self.logger = logging.getLogger(f"EnvironmentPlugin.{plugin_id}")
        self._status = {
            "state": "created",
            "details": {},
        }
        self.resources = {}

    def initialize(self) -> bool:
        """
        Initialize the environment plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            self._status["state"] = "initializing"
            result = self._initialize_environment()
            self._status["state"] = "initialized" if result else "initialization_failed"
            return result
        except Exception as e:
            self.logger.exception(f"Error initializing environment plugin {self.plugin_id}: {e}")
            self._status["state"] = "initialization_failed"
            self._status["details"]["error"] = str(e)
            return False

    def start(self) -> bool:
        """
        Start the environment.

        Returns:
            bool: True if environment setup was successful, False otherwise
        """
        try:
            if self._status["state"] != "initialized":
                self.logger.error(
                    f"Cannot start environment plugin {self.plugin_id}: not properly initialized"
                )
                return False

            self._status["state"] = "setting_up"
            environment_id = self._get_environment_id()
            environment_type = self._get_environment_type()

            # Notify that environment setup has started
            self.notify_environment_setup_started(
                {
                    "environment_id": environment_id,
                    "environment_type": environment_type,
                }
            )

            # Set up the environment
            result = self._setup_environment()

            # Notify that environment setup has completed
            self.notify_environment_setup_completed(
                result,
                {
                    "environment_id": environment_id,
                    "environment_type": environment_type,
                },
            )

            self._status["state"] = "running" if result else "setup_failed"
            return result
        except Exception as e:
            self.logger.exception(f"Error setting up environment plugin {self.plugin_id}: {e}")
            self._status["state"] = "setup_failed"
            self._status["details"]["error"] = str(e)

            # Notify failure
            environment_id = self._get_environment_id()
            self.notify_environment_setup_completed(
                False,
                {
                    "environment_id": environment_id,
                    "error": str(e),
                },
            )

            return False

    def stop(self) -> bool:
        """
        Stop the environment.

        Returns:
            bool: True if environment teardown was successful, False otherwise
        """
        try:
            if self._status["state"] != "running":
                self.logger.warning(f"Environment plugin {self.plugin_id} not running, cannot stop")
                return True

            self._status["state"] = "tearing_down"
            environment_id = self._get_environment_id()

            # Tear down the environment
            result = self._teardown_environment()

            # Notify that environment has been torn down
            self.notify_environment_teardown(
                result,
                {
                    "environment_id": environment_id,
                },
            )

            self._status["state"] = "stopped" if result else "teardown_failed"
            return result
        except Exception as e:
            self.logger.exception(f"Error tearing down environment plugin {self.plugin_id}: {e}")
            self._status["state"] = "teardown_failed"
            self._status["details"]["error"] = str(e)

            # Notify failure
            environment_id = self._get_environment_id()
            self.notify_environment_teardown(
                False,
                {
                    "environment_id": environment_id,
                    "error": str(e),
                },
            )

            return False

    def get_status(self) -> dict[str, Any]:
        """
        Get the current status of the environment plugin.

        Returns:
            Dict[str, Any]: Status information
        """
        # Get any custom status information from the implementation
        custom_status = self._get_custom_status()

        # Add resource information to status
        resource_status = {
            f"resource_{resource_id}": status for resource_id, status in self.resources.items()
        }

        # Merge with base status
        status = {**self._status}
        status["details"] = {
            **status.get("details", {}),
            **resource_status,
            **(custom_status or {}),
        }

        return status

    def configure(self, config: dict[str, Any]) -> bool:
        """
        Configure the environment plugin.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        try:
            self.config = config
            return self._configure_environment(config)
        except Exception as e:
            self.logger.exception(f"Error configuring environment plugin {self.plugin_id}: {e}")
            return False

    def handle_event(self, event: Event) -> None:
        """
        Handle an incoming event.

        Args:
            event: The event to handle
        """
        try:
            self._handle_environment_event(event)
        except Exception as e:
            self.logger.exception(
                f"Error handling event in environment plugin {self.plugin_id}: {e}"
            )

    def get_subscribed_events(self) -> list[str]:
        """
        Get the list of event types this plugin is interested in.

        Returns:
            List[str]: List of event type identifiers
        """
        # Combine base environment events with any additional events from the implementation
        base_events = ["environment.setup.request", "environment.teardown.request"]
        additional_events = self._get_additional_subscribed_events()
        return base_events + additional_events

    def allocate_resource(
        self, resource_type: str, resource_id: str, details: dict[str, Any] = None
    ) -> bool:
        """
        Allocate a resource and emit the appropriate event.

        Args:
            resource_type: Type of resource to allocate
            resource_id: Unique identifier for the resource
            details: Additional details about the resource

        Returns:
            bool: True if allocation was successful, False otherwise
        """
        try:
            # Attempt to allocate the resource
            result = self._allocate_resource(resource_type, resource_id, details or {})

            if result:
                # Store the resource status
                self.resources[resource_id] = {
                    "status": "allocated",
                    "type": resource_type,
                    **(details or {}),
                }

                # Emit resource allocated event
                self.emit_environment_resource_allocated(
                    environment_id=self._get_environment_id(),
                    resource_id=resource_id,
                    resource_type=resource_type,
                    resource_details=details,
                )

            return result
        except Exception as e:
            self.logger.exception(f"Error allocating resource {resource_id}: {e}")
            return False

    def release_resource(self, resource_id: str) -> bool:
        """
        Release a previously allocated resource and emit the appropriate event.

        Args:
            resource_id: Unique identifier for the resource

        Returns:
            bool: True if release was successful, False otherwise
        """
        if resource_id not in self.resources:
            self.logger.warning(f"Resource {resource_id} not found, cannot release")
            return False

        resource_info = self.resources[resource_id]
        resource_type = resource_info["type"]

        try:
            # Attempt to release the resource
            result = self._release_resource(resource_id, resource_info)

            if result:
                # Update resource status
                self.resources[resource_id]["status"] = "released"

                # Emit resource released event
                self.emit_environment_resource_released(
                    environment_id=self._get_environment_id(),
                    resource_id=resource_id,
                    resource_type=resource_type,
                    success=True,
                )

            return result
        except Exception as e:
            self.logger.exception(f"Error releasing resource {resource_id}: {e}")

            # Emit resource released event with error
            self.emit_environment_resource_released(
                environment_id=self._get_environment_id(),
                resource_id=resource_id,
                resource_type=resource_type,
                success=False,
                error_message=str(e),
            )

            return False

    # Abstract methods to be implemented by concrete environment plugins

    @abstractmethod
    def _initialize_environment(self) -> bool:
        """
        Initialize the specific environment implementation.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def _setup_environment(self) -> bool:
        """
        Set up the specific environment implementation.

        Returns:
            bool: True if environment setup was successful, False otherwise
        """
        pass

    @abstractmethod
    def _teardown_environment(self) -> bool:
        """
        Tear down the specific environment implementation.

        Returns:
            bool: True if environment teardown was successful, False otherwise
        """
        pass

    @abstractmethod
    def _configure_environment(self, config: dict[str, Any]) -> bool:
        """
        Configure the specific environment implementation.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        pass

    @abstractmethod
    def _get_environment_id(self) -> str:
        """
        Get the unique identifier for the environment.

        Returns:
            str: Environment identifier
        """
        pass

    @abstractmethod
    def _get_environment_type(self) -> str:
        """
        Get the type of the environment.

        Returns:
            str: Environment type
        """
        pass

    @abstractmethod
    def is_network_environment(self) -> bool:
        """
        Check if this is a network environment.

        Returns:
            bool: True if this is a network environment, False otherwise
        """
        pass

    # Optional methods with default implementations

    def _handle_environment_event(self, event: Event) -> None:
        """
        Handle environment-specific events.

        Default implementation does nothing.

        Args:
            event: The event to handle
        """
        pass

    def _get_custom_status(self) -> dict[str, Any]:
        """
        Get custom status information specific to the environment implementation.

        Returns:
            Dict[str, Any]: Custom status information
        """
        return {}

    def _get_additional_subscribed_events(self) -> list[str]:
        """
        Get additional event types this environment is interested in, beyond the base ones.

        Returns:
            List[str]: List of additional event type identifiers
        """
        return []

    def _allocate_resource(
        self, resource_type: str, resource_id: str, details: dict[str, Any]
    ) -> bool:
        """
        Allocate a resource in the environment.

        Default implementation returns True without doing anything.

        Args:
            resource_type: Type of resource to allocate
            resource_id: Unique identifier for the resource
            details: Additional details about the resource

        Returns:
            bool: True if allocation was successful, False otherwise
        """
        return True

    def _release_resource(self, resource_id: str, resource_info: dict[str, Any]) -> bool:
        """
        Release a previously allocated resource.

        Default implementation returns True without doing anything.

        Args:
            resource_id: Unique identifier for the resource
            resource_info: Information about the resource

        Returns:
            bool: True if release was successful, False otherwise
        """
        return True
