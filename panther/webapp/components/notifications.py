"""Typed notification helpers."""

from nicegui import ui


def notify_success(message: str):
    """Green success notification."""
    ui.notify(message, type="positive", position="top-right")


def notify_error(message: str):
    """Red error notification."""
    ui.notify(message, type="negative", position="top-right")


def notify_warning(message: str):
    """Amber warning notification."""
    ui.notify(message, type="warning", position="top-right")


def notify_info(message: str):
    """Blue info notification."""
    ui.notify(message, type="info", position="top-right")
