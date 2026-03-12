"""Tester plugin not found exception."""

from .fast_fail import ErrorSeverity, PluginLoadException


class TesterPluginNotFound(PluginLoadException):
    """Exception raised when a tester plugin is not found."""

    def __init__(self, plugin_name: str):
        """Initialize with the missing plugin name."""
        super().__init__(
            message=f"Tester plugin '{plugin_name}' not found.",
            plugin_name=plugin_name,
            plugin_type="tester",
            severity=ErrorSeverity.HIGH,
        )
