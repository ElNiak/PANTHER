"""
Base service implementation with standardized event handling.
"""

import logging
import os

from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.service_event_methods import ServiceManagerEventMixin
from panther.plugins.services.services_interface import IServiceManager
from panther.core.observer.event_emitter import EventEmitter


class ServiceBase(IServiceManager, ServiceManagerEventMixin):
    """
    Base class for service managers that implements common functionality,
    particularly around standardized event handling.

    This class provides default implementations of common service operations that ensure
    proper event notifications are emitted through the event-driven architecture.

    Attributes:
        service_config_to_test: The configuration for the service being tested.
        service_type (str): The type of service.
        protocol: The protocol configuration.
        implementation_name (str): Name of the implementation.
        logger (logging.Logger): Logger for the service manager.
        event_emitter (EventEmitter): Emitter for standardized events.
    """

    def __init__(
        self,
        service_config_to_test,
        service_type: str,
        protocol,
        implementation_name: str,
    ):
        super().__init__(service_config_to_test, service_type, protocol, implementation_name)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.event_emitter = None  # Will be set by the plugin manager
        self._plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self._initialize_event_emitter()

    def _initialize_event_emitter(self):
        """
        Initialize the event emitter if the event manager is available.
        """
        if hasattr(self, "event_manager") and self.event_manager:
            self.event_emitter = EventEmitter(self.event_manager)

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service with proper event notifications.

        Args:
            plugin_loader: Plugin loader for creating dependencies
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.debug("Preparing service %s", self.service_name)
        self.plugin_loader = plugin_loader

        try:
            # Notify preparation started
            self.notify_service_event(
                "preparation_started",
                {
                    "service_name": self.service_name,
                    "service_type": self.service_type,
                    "implementation": self.implementation_name,
                },
            )

            # Perform preparation
            result = self._do_prepare(plugin_loader)

            # Notify preparation completed
            self.notify_service_started(
                details={
                    "implementation": self.implementation_name,
                    "protocol": self.service_protocol.name if self.service_protocol else "unknown",
                }
            )

            return result
        # Using a general exception handler here is intended to catch all possible errors
        # during service preparation to ensure proper error notification
        except Exception as e:  # pylint: disable=broad-except
            # Notify error
            self.notify_service_error(
                error_type="preparation_failed",
                error_message=str(e),
                details={
                    "implementation": self.implementation_name,
                    "exception_type": type(e).__name__,
                },
            )

    def _do_prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Perform the actual preparation work.

        This method should be overridden by subclasses.

        Args:
            plugin_loader: Optional plugin loader to use for preparation
        """
        raise NotImplementedError("Subclasses must implement _do_prepare")

    def stop(self):
        """
        Stop the service.

        This default implementation just handles event notification.
        Subclasses should override _do_stop to implement actual stop logic.
        """
        self.logger.debug("Stopping service %s", self.service_name)

        try:
            # Notify stopping
            self.notify_service_event(
                "stopping",
                {
                    "service_name": self.service_name,
                    "service_type": self.service_type,
                },
            )

            # Actual stop logic should be implemented in _do_stop
            result = self._do_stop()

            # Notify success
            details = {"implementation": self.implementation_name, "clean_shutdown": True}
            self.notify_service_stopped(True, details)

            return result
        # Using a general exception handler to ensure proper error notification
        except Exception as e:  # pylint: disable=broad-except
            # Notify error
            details = {
                "implementation": self.implementation_name,
                "exception_type": type(e).__name__,
            }
            self.notify_service_stopped(False, details)
            self.notify_service_error(
                error_type="stop_failed", error_message=str(e), details=details
            )
            raise

    def _do_stop(self):
        """
        Perform the actual service stop work.

        To be implemented by subclasses. The default implementation just returns True.

        Returns:
            Implementation-specific result. By default, returns True to indicate success.

        Raises:
            NotImplementedError: This base implementation doesn't raise, but subclasses may.
        """
        # Default implementation just succeeds
        self.logger.debug("Default _do_stop implementation called for %s", self.service_name)
        return True

    def notify_service_event(self, event_name: str, details: dict = None):
        """
        Notify of a generic service event.

        Args:
            event_name: The name of the event
            details: Additional details about the event
        """
        if hasattr(self, "event_emitter") and self.event_emitter:
            self.event_emitter.emit_event(f"service.{event_name}", details or {})
