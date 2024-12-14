
class EnvironmentPluginNotFound(Exception):
    """Exception raised when the specified environment plugin is not found."""

    def __init__(self, plugin_name):
        self.plugin_name = plugin_name
        self.message = f"Environment plugin '{self.plugin_name}' not found."
        super().__init__(self.message)