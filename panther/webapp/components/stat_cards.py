"""Dashboard stat card components."""

from typing import Optional

from nicegui import ui


def stat_card(
    title: str,
    value: str,
    icon: str = "info",
    color: str = "primary",
    subtitle: Optional[str] = None,
):
    """Render a stat card for the dashboard.

    Args:
        title: Card title.
        value: Main displayed value.
        icon: Material icon name.
        color: Quasar color name.
        subtitle: Optional subtitle text.
    """
    with ui.card().classes("q-pa-md"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.icon(icon, size="md").classes(f"text-{color}")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("text-caption text-grey-7")
                ui.label(value).classes("text-h5 font-bold")
                if subtitle:
                    ui.label(subtitle).classes("text-caption text-grey-6")
