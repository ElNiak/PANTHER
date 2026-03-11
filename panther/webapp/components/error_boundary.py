"""ErrorBoundary — exception-catching context manager for UI rendering.

Provides a ``with error_boundary(title):`` block that catches any exception
raised during NiceGUI widget construction and replaces the failing subtree
with a styled error card showing the exception message and a collapsible
traceback.  This prevents a single broken component from crashing an entire
PANTHER (Protocol ANalysis and Testing Harness for Extensible Research)
dashboard page.

Usage::

    from panther.webapp.components.error_boundary import error_boundary

    with error_boundary("Config Panel"):
        config_form_panel(...)   # if this raises, an error card is shown
"""

import logging
import traceback
from contextlib import contextmanager

from nicegui import ui

logger = logging.getLogger(__name__)


@contextmanager
def error_boundary(title: str = "Rendering Error"):
    """Context manager that catches exceptions during UI rendering.

    On success the ``yield`` completes normally and no extra UI is added.
    On failure the exception is logged, and a red error card is rendered
    in the current container with:

    * A bold title identifying the failing section.
    * The exception message.
    * A collapsible traceback for debugging.

    Args:
        title: Human-readable label for the UI section being protected.
            Displayed in the error card header on failure.

    Example::

        with error_boundary("Config Panel"):
            config_form_panel(...)  # if this raises, error card is shown
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
