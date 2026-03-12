"""Environment plugin not found exception."""

from .fast_fail import ErrorSeverity, PluginLoadException


class EnvironmentPluginNotFound(PluginLoadException):
    """Exception raised when the specified environment plugin is not found."""

    def __init__(self, plugin_name: str):
        """Initialize with the missing plugin name."""
        super().__init__(
            message=f"Environment plugin '{plugin_name}' not found.",
            plugin_name=plugin_name,
            plugin_type="environment",
            severity=ErrorSeverity.HIGH,
        )
