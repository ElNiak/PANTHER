"""StatCards — summary statistic card components for the dashboard.

Provides the ``stat_card()`` function that renders a compact information
card displaying a single key metric on the PANTHER (Protocol ANalysis and
Testing Harness for Extensible Research) web dashboard.  Each card
contains a Material icon, a title, a large value, and an optional
subtitle — arranged in a horizontal row layout suitable for a responsive
grid of KPI indicators.
"""

from typing import Optional

from nicegui import ui


def stat_card(
    title: str,
    value: str,
    icon: str = "info",
    color: str = "primary",
    subtitle: Optional[str] = None,
):
    """Render a single summary statistic card for the dashboard.

    The card is structured as a horizontal row containing a coloured
    Material icon and a vertical stack of title, large value, and an
    optional subtitle.  Multiple ``stat_card`` calls are typically
    placed inside a responsive ``ui.row`` or CSS grid.

    Args:
        title: Short label describing the metric (e.g. ``"Plugins"``).
        value: The main displayed value (e.g. ``"12"`` or ``"3 / 5"``).
        icon: Material icon name shown to the left of the text.
        color: Quasar colour name applied to the icon
            (e.g. ``"primary"``, ``"green"``, ``"red"``).
        subtitle: Optional secondary text shown below the value in a
            smaller, greyed font.
    """
    with ui.card().classes("q-pa-md"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.icon(icon, size="md").classes(f"text-{color}")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-caption text-grey-7")
                ui.label(value).classes("text-h5 font-bold")
                if subtitle:
                    ui.label(subtitle).classes("text-caption text-grey-6")
