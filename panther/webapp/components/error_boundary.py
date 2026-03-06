"""Error boundary context manager for UI rendering."""

import logging
import traceback
from contextlib import contextmanager

from nicegui import ui

logger = logging.getLogger(__name__)


@contextmanager
def error_boundary(title: str = "Rendering Error"):
    """Context manager that catches exceptions in UI rendering and shows an error card.

    Usage:
        with error_boundary("Config Panel"):
            # UI code that might fail
            config_form_panel(...)
    """
    try:
        yield
    except Exception as e:
        logger.error("UI rendering error in %s: %s", title, e, exc_info=True)
        with ui.card().classes("w-full bg-red-1 q-pa-md"):
            ui.label(f"{title}: Error").classes("text-subtitle2 text-red-9")
            ui.label(str(e)).classes("text-caption text-red-7")
            with ui.expansion("Traceback").classes("text-caption"):
                ui.code(traceback.format_exc()).classes("w-full")
