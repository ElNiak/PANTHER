"""Real-time log viewer component."""

from nicegui import ui


class LogViewer:
    """Real-time log viewer using NiceGUI's ui.log component.

    Wraps ui.log with convenience methods for pushing log lines
    and managing the display.
    """

    def __init__(self, max_lines: int = 500):
        self.max_lines = max_lines
        self.log = ui.log(max_lines=max_lines).classes("w-full h-64")

    def push(self, message: str):
        """Push a new log line."""
        self.log.push(message)

    def clear(self):
        """Clear all log lines."""
        self.log.clear()
