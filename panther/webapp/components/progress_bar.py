"""Experiment progress bar component."""

from nicegui import ui


class ExperimentProgress:
    """Progress bar with phase label for experiment execution."""

    def __init__(self):
        """Initialize progress bar widgets."""
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
