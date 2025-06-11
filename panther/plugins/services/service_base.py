"""
Base service implementation with standardized event handling.
"""

import logging
import os

from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.service_event_methods import ServiceManagerEventMixin
from panther.plugins.services.services_interface import IServiceManager


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
        event_emitter (ServiceEventEmitter): Emitter for standardized service events.
    """

    def __init__(
        self,
        service_config_to_test,
        service_type: str,
        protocol,
        implementation_name: str,
        event_manager=None,
    ):
        # Pass event_manager to parent class constructor so it's properly initialized
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._plugin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def render_template_with_structured_args(
        self, template_name, params=None, command_args=None, env_vars=None
    ):
        """
        Render a template using structured arguments, ensuring proper escaping and formatting.

        Args:
            template_name: The name of the template to render
            params: Basic template parameters
            command_args: Structured command arguments
            env_vars: Environment variables to include

        Returns:
            str: The rendered template string
        """
        try:
            self.logger.debug("Rendering structured template '%s'", template_name)
            return self.render_commands(params or {}, template_name, command_args, env_vars)
        except Exception as e:
            self.logger.error("Failed to render structured template '%s': %s", template_name, e)
            if not os.path.isdir(self.templates_dir):
                self.logger.error("Templates directory '%s' does not exist", self.templates_dir)
            else:
                templates = os.listdir(self.templates_dir)
                self.logger.error("Available templates in '%s': %s", self.templates_dir, templates)
            raise

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service with proper event notifications.

        Args:
            plugin_loader: Plugin loader for creating dependencies
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.debug("Preparing service %s", self.service_name)
        self.plugin_loader = plugin_loader

        # Note: event_emitter is already initialized in IServiceManager parent class
        # It uses ServiceEventEmitter which provides typed service events
        if hasattr(self, "event_emitter") and self.event_emitter:
            self.logger.debug("ServiceEventEmitter already initialized")

        try:
            # Get test case name from service_config_to_test if available
            test_case = getattr(self.service_config_to_test, "test_case", "unknown_test")

            # Defensive check for event_emitter before emitting events
            if hasattr(self, "event_emitter") and self.event_emitter:
                # Notify preparation started
                self.notify_service_event(
                    "preparation_started",
                    {
                        "service_name": self.service_name,
                        "service_type": self.service_type,
                        "implementation": self.implementation_name,
                        "test_case": test_case,
                    },
                )
                self.logger.debug("Emitted service preparation started event")

            # Perform preparation
            result = self._do_prepare(plugin_loader)

            # Also emit service started event with defensive check
            if hasattr(self, "event_emitter") and self.event_emitter:
                self.notify_service_started(
                    details={
                        "service_name": self.service_name,
                        "implementation": self.implementation_name,
                        "protocol": (
                            self.service_protocol.name if self.service_protocol else "unknown"
                        ),
                        "test_case": test_case,
                    }
                )
                self.logger.debug("Emitted service started event")

            return result

        # Using a general exception handler here is intended to catch all possible errors
        # during service preparation to ensure proper error notification
        except Exception as e:  # pylint: disable=broad-except
            # Get test case name from service_config_to_test if available
            test_case = getattr(self.service_config_to_test, "test_case", "unknown_test")

            # Defensive check for event_emitter before emitting events
            if hasattr(self, "event_emitter") and self.event_emitter:
                # Notify general error
                self.notify_service_error(
                    error_type="preparation_failed",
                    error_message=str(e),
                    details={
                        "service_name": self.service_name,
                        "implementation": self.implementation_name,
                        "exception_type": type(e).__name__,
                        "test_case": test_case,
                    },
                )
                self.logger.debug("Emitted service error event")

            # Re-raise the exception
            raise

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
        # Use the mixin methods from ServiceManagerEventMixin instead
        # This method can be overridden if needed, but typically the specific
        # notify methods from ServiceManagerEventMixin should be used
        self.logger.debug("Service event '%s' with details: %s", event_name, details)
