"""LogViewer — scrollable, auto-tailing log display.

Wraps NiceGUI's ``ui.log`` widget with a simplified push/clear API for
the PANTHER (Protocol ANalysis and Testing Harness for Extensible Research)
web dashboard.  The underlying ``ui.log`` component automatically scrolls
to the bottom when new lines arrive (auto-tail behaviour) and caps the
displayed line count to ``max_lines`` to bound memory usage.
"""

from nicegui import ui


class LogViewer:
    """Real-time log viewer using NiceGUI's ``ui.log`` component.

    Renders a scrollable log pane that auto-scrolls to the latest entry.
    Older lines beyond ``max_lines`` are automatically discarded by
    NiceGUI on the client side.

    Args:
        max_lines: Maximum number of log lines retained in the display.
            Defaults to 500.

    Example::

        viewer = LogViewer(max_lines=200)
        viewer.push("Container started on port 4433")
        viewer.clear()
    """

    def __init__(self, max_lines: int = 500):
        """Initialise the log viewer with the given line limit."""
        self.max_lines = max_lines
        self.log = ui.log(max_lines=max_lines).classes("w-full h-64")

    def push(self, message: str):
        """Push a new log line."""
        self.log.push(message)

    def clear(self):
        """Clear all log lines."""
        self.log.clear()
