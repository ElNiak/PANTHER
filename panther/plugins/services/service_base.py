"""
Base service implementation with standardized event handling.
"""

import logging
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.services_interface import IServiceManager


class ServiceBase(IServiceManager):
    """
    Base class for service managers that implements common functionality,
    particularly around standardized event handling.

    This class provides default implementations of common service operations that ensure
    proper event notifications are emitted.
    """

    def prepare(self, plugin_loader: PluginLoader | None = None):
        """
        Prepare the service for use by building the necessary resources.

        This method should be overridden by subclasses, but they should call super().prepare()
        to ensure proper event notifications.

        Args:
            plugin_loader: Optional plugin loader to use for preparation
        """
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.logger.debug(f"Preparing service {self.service_name}")
        self.plugin_loader = plugin_loader

        try:
            # Actual preparation logic should be implemented in _do_prepare
            result = self._do_prepare(plugin_loader)

            # Notify success
            details = {
                "implementation": self.implementation_name,
                "protocol": self.service_protocol.name if self.service_protocol else "unknown",
            }
            self.notify_service_started(details)

            return result
        except Exception as e:
            # Notify error
            self.notify_service_error(
                error_type="preparation_failed",
                error_message=str(e),
                details={
                    "implementation": self.implementation_name,
                    "exception_type": type(e).__name__,
                },
            )
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
        self.logger.debug(f"Stopping service {self.service_name}")

        try:
            # Actual stop logic should be implemented in _do_stop
            result = self._do_stop()

            # Notify success
            details = {"implementation": self.implementation_name, "clean_shutdown": True}
            self.notify_service_stopped(True, details)

            return result
        except Exception as e:
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

        This method should be overridden by subclasses.

        Returns:
            True if the service was stopped successfully, False otherwise
        """
        return True
