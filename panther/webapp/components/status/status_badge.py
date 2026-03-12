"""StatusBadge — colour-coded status indicator badge.

Provides the ``status_badge()`` function that renders a NiceGUI
``ui.badge`` whose background colour is determined by the status string.
Used throughout the PANTHER (Protocol ANalysis and Testing Harness for
Extensible Research) web dashboard to visually indicate experiment, test,
and service lifecycle states (completed, failed, running, idle, etc.).
"""

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
    """Render a colour-coded badge for experiment/test/service status.

    Maps the status string (case-insensitive) to a colour using the
    ``_STATUS_COLORS`` lookup table.  Unknown statuses default to grey.

    Args:
        status: Status string such as ``"completed"``, ``"failed"``,
            ``"running"``, ``"idle"``, or ``"unknown"``.

    Returns:
        A NiceGUI ``ui.badge`` element with the capitalised status text
        and the mapped background colour.
    """
    color = _STATUS_COLORS.get(status.lower(), "grey")
    return ui.badge(status.capitalize(), color=color)
