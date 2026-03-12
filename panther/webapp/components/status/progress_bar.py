"""ProgressBar — experiment execution progress indicator.

Renders a horizontal progress bar with a textual phase label for the
PANTHER (Protocol ANalysis and Testing Harness for Extensible Research)
web dashboard.  The bar is driven by the experiment orchestrator which
calls ``update()`` as the experiment transitions through phases
(initializing, deploying, running tests, collecting outputs, etc.).
"""

from nicegui import ui


class ExperimentProgress:
    """Linear progress bar with a phase label for experiment execution.

    Displays a text label (e.g. ``"Running tests..."``) alongside a
    ``ui.linear_progress`` bar.  Call ``update(phase, value)`` to advance
    the indicator, or ``reset()`` to return to the idle state.

    The component renders into the currently active NiceGUI container.

    Example::

        progress = ExperimentProgress()
        progress.update("Deploying...", 0.3)
        progress.update("Running tests...", 0.7)
        progress.reset()
    """

    def __init__(self):
        """Initialize progress bar widgets in the current NiceGUI container."""
        with ui.row().classes("w-full items-center gap-2"):
            self._label = ui.label("Idle").classes("text-caption text-grey-7")
            self._bar = ui.linear_progress(value=0, show_value=False).classes(
                "flex-grow"
            )

    def update(self, phase: str, value: float):
        """Update progress bar.

        Args:
            phase: Current phase label (e.g. "Initializing...", "Running tests...")
            value: Progress value between 0.0 and 1.0
        """
        self._label.text = phase
        self._bar.value = max(0.0, min(1.0, value))

    def reset(self):
        """Reset to idle state."""
        self._label.text = "Idle"
        self._bar.value = 0
