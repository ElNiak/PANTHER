"""Status badge component."""

from nicegui import ui

_STATUS_COLORS = {
    "completed": "green",
    "passed": "green",
    "failed": "red",
    "running": "amber",
    "in_progress": "amber",
    "stopped": "orange",
    "timeout": "orange",
    "idle": "grey",
    "unknown": "grey",
}


def status_badge(status: str) -> ui.badge:
    """Colored badge for experiment/test status.

    Args:
        status: Status string (completed, failed, running, unknown, etc.)

    Returns:
        NiceGUI badge element.
    """
    color = _STATUS_COLORS.get(status.lower(), "grey")
    return ui.badge(status.capitalize(), color=color)
