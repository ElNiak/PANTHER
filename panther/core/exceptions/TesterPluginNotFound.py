
class TesterPluginNotFound(Exception):
    """Exception raised when a tester plugin is not found."""

    def __init__(self, plugin_name):
        self.plugin_name = plugin_name
        self.message = f"Tester plugin '{self.plugin_name}' not found."
        super().__init__(self.message)