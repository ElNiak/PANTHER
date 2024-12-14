
class ServicePluginNotFound(Exception):
    """Exception raised when a service plugin is not found."""

    def __init__(self, plugin_name):
        self.plugin_name = plugin_name
        self.message = f"Service plugin '{self.plugin_name}' not found."
        super().__init__(self.message)