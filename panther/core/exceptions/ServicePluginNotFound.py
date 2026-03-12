"""Service plugin not found exception."""

from .fast_fail import ErrorSeverity, PluginLoadException


class ServicePluginNotFound(PluginLoadException):
    """Exception raised when a service plugin is not found."""

    def __init__(self, plugin_name: str):
        """Initialize with the missing plugin name."""
        super().__init__(
            message=f"Service plugin '{plugin_name}' not found.",
            plugin_name=plugin_name,
            plugin_type="service",
            severity=ErrorSeverity.HIGH,
        )
