"""
Base Service Plugin Module

This module provides a base class for all service plugins in the enhanced architecture.
"""

import logging
from abc import abstractmethod
from typing import Any

from panther.core.observer.events import Event
from panther.plugins.enhanced_plugin_interface import IPantherPlugin, IPluginRegistry
from panther.plugins.services.service_plugin_event_methods import ServicePluginEventMixin


class BaseServicePlugin(IPantherPlugin, ServicePluginEventMixin):
    """
    Base class for all service plugins in PANTHER.

    This class combines the standardized plugin interface with service-specific
    functionality and event emission methods.
    """

    def __init__(
        self, plugin_id: str, plugin_registry: IPluginRegistry, config: dict[str, Any] = None
    ):
        """
        Initialize the service plugin.

        Args:
            plugin_id: Unique identifier for this plugin instance
            plugin_registry: Registry for plugin management and event dispatching
            config: Configuration for the plugin
        """
        self.plugin_id = plugin_id
        self.plugin_registry = plugin_registry
        self.config = config or {}
        self.logger = logging.getLogger(f"ServicePlugin.{plugin_id}")
        self._status = {
            "state": "created",
            "details": {},
        }

    def initialize(self) -> bool:
        """
        Initialize the service plugin.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            self._status["state"] = "initializing"
            result = self._initialize_service()
            self._status["state"] = "initialized" if result else "initialization_failed"
            return result
        except Exception as e:
            self.logger.exception(f"Error initializing service plugin {self.plugin_id}: {e}")
            self._status["state"] = "initialization_failed"
            self._status["details"]["error"] = str(e)
            return False

    def start(self) -> bool:
        """
        Start the service.

        Returns:
            bool: True if service started successfully, False otherwise
        """
        try:
            if self._status["state"] != "initialized":
                self.logger.error(
                    f"Cannot start service plugin {self.plugin_id}: not properly initialized"
                )
                return False

            self._status["state"] = "starting"
            service_id = self._get_service_id()
            service_type = self._get_service_type()

            # Emit starting event
            self.emit_service_starting(service_id, service_type)

            # Start the service
            result = self._start_service()

            if result:
                self._status["state"] = "running"
                # Emit ready event if an endpoint is available
                endpoint = self._get_service_endpoint()
                if endpoint:
                    self.emit_service_ready(service_id, service_type, endpoint)
            else:
                self._status["state"] = "start_failed"

            return result
        except Exception as e:
            self.logger.exception(f"Error starting service plugin {self.plugin_id}: {e}")
            self._status["state"] = "start_failed"
            self._status["details"]["error"] = str(e)
            return False

    def stop(self) -> bool:
        """
        Stop the service.

        Returns:
            bool: True if service stopped successfully, False otherwise
        """
        try:
            if self._status["state"] != "running":
                self.logger.warning(f"Service plugin {self.plugin_id} not running, cannot stop")
                return True

            self._status["state"] = "stopping"
            service_id = self._get_service_id()

            # Emit stopping event
            self.emit_service_stopping(service_id)

            # Stop the service
            result = self._stop_service()

            # Emit stopped event
            self.emit_service_stopped(
                service_id,
                success=result,
                error_message=None if result else "Service failed to stop cleanly",
            )

            self._status["state"] = "stopped" if result else "stop_failed"
            return result
        except Exception as e:
            self.logger.exception(f"Error stopping service plugin {self.plugin_id}: {e}")
            self._status["state"] = "stop_failed"
            self._status["details"]["error"] = str(e)

            # Emit stopped event with error
            service_id = self._get_service_id()
            self.emit_service_stopped(service_id, success=False, error_message=str(e))

            return False

    def get_status(self) -> dict[str, Any]:
        """
        Get the current status of the service plugin.

        Returns:
            Dict[str, Any]: Status information
        """
        # Get any custom status information from the implementation
        custom_status = self._get_custom_status()

        # Merge with base status
        status = {**self._status}
        if custom_status:
            status["details"] = {**status.get("details", {}), **custom_status}

        return status

    def configure(self, config: dict[str, Any]) -> bool:
        """
        Configure the service plugin.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        try:
            self.config = config
            return self._configure_service(config)
        except Exception as e:
            self.logger.exception(f"Error configuring service plugin {self.plugin_id}: {e}")
            return False

    def handle_event(self, event: Event) -> None:
        """
        Handle an incoming event.

        Args:
            event: The event to handle
        """
        try:
            self._handle_service_event(event)
        except Exception as e:
            self.logger.exception(f"Error handling event in service plugin {self.plugin_id}: {e}")

    def get_subscribed_events(self) -> list[str]:
        """
        Get the list of event types this plugin is interested in.

        Returns:
            List[str]: List of event type identifiers
        """
        # Combine base service events with any additional events from the implementation
        base_events = ["service.request"]
        additional_events = self._get_additional_subscribed_events()
        return base_events + additional_events

    # Abstract methods to be implemented by concrete service plugins

    @abstractmethod
    def _initialize_service(self) -> bool:
        """
        Initialize the specific service implementation.

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def _start_service(self) -> bool:
        """
        Start the specific service implementation.

        Returns:
            bool: True if service started successfully, False otherwise
        """
        pass

    @abstractmethod
    def _stop_service(self) -> bool:
        """
        Stop the specific service implementation.

        Returns:
            bool: True if service stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    def _configure_service(self, config: dict[str, Any]) -> bool:
        """
        Configure the specific service implementation.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration was successful, False otherwise
        """
        pass

    @abstractmethod
    def _get_service_id(self) -> str:
        """
        Get the unique identifier for the service.

        Returns:
            str: Service identifier
        """
        pass

    @abstractmethod
    def _get_service_type(self) -> str:
        """
        Get the type of the service.

        Returns:
            str: Service type
        """
        pass

    @abstractmethod
    def _get_service_endpoint(self) -> str | None:
        """
        Get the endpoint for the service, if available.

        Returns:
            Optional[str]: Service endpoint (e.g., host:port) or None
        """
        pass

    # Optional methods with default implementations

    def _handle_service_event(self, event: Event) -> None:
        """
        Handle service-specific events.

        Default implementation does nothing.

        Args:
            event: The event to handle
        """
        pass

    def _get_custom_status(self) -> dict[str, Any]:
        """
        Get custom status information specific to the service implementation.

        Returns:
            Dict[str, Any]: Custom status information
        """
        return {}

    def _get_additional_subscribed_events(self) -> list[str]:
        """
        Get additional event types this service is interested in, beyond the base ones.

        Returns:
            List[str]: List of additional event type identifiers
        """
        return []
