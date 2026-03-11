"""Notifications — typed toast notification helpers.

Provides four convenience functions that wrap NiceGUI's ``ui.notify()``
with pre-configured type and position settings for the PANTHER (Protocol
ANalysis and Testing Harness for Extensible Research) web dashboard.
All notifications appear in the top-right corner and are colour-coded:

* ``notify_success`` — green (positive).
* ``notify_error`` — red (negative).
* ``notify_warning`` — amber (warning).
* ``notify_info`` — blue (info).

These helpers ensure consistent notification styling across all pages
without requiring each caller to remember the NiceGUI ``type`` and
``position`` parameters.
"""

from nicegui import ui


def notify_success(message: str):
    """Show a green success toast notification in the top-right corner.

    Args:
        message: Text to display in the notification.
    """
    ui.notify(message, type="positive", position="top-right")


def notify_error(message: str):
    """Show a red error toast notification in the top-right corner.

    Args:
        message: Text to display in the notification.
    """
    ui.notify(message, type="negative", position="top-right")


def notify_warning(message: str):
    """Show an amber warning toast notification in the top-right corner.

    Args:
        message: Text to display in the notification.
    """
    ui.notify(message, type="warning", position="top-right")


def notify_info(message: str):
    """Show a blue informational toast notification in the top-right corner.

    Args:
        message: Text to display in the notification.
    """
    ui.notify(message, type="info", position="top-right")
