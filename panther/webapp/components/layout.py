"""Shared layout component for PANTHER web dashboard."""

from pathlib import Path

from nicegui import ui

# Resolve static directory relative to this file
STATIC_DIR = Path(__file__).parent.parent / "static"

NAV_ITEMS = [
    ("/", "Dashboard", "dashboard"),
    ("/config", "Config Builder", "settings"),
    ("/topology", "Topology Editor", "hub"),
    ("/experiments", "Experiments", "science"),
    ("/results", "Results", "assessment"),
    ("/plugins", "Plugins", "extension"),
]


def create_layout(page_title: str = "PANTHER"):
    """Create the shared page layout with header and sidebar navigation.

    Args:
        page_title: Title shown in the header.
    """
    ui.colors(primary="#1a237e", secondary="#283593", accent="#536dfe")

    with ui.header().classes("items-center justify-between bg-primary"):
        with ui.row().classes("items-center gap-4"):
            ui.icon("security", size="sm").classes("text-white")
            ui.label("PANTHER").classes("text-h6 text-white font-bold no-margin")
            ui.label(f"/ {page_title}").classes("text-subtitle1 text-white")

        with ui.row().classes("items-center gap-2"):
            ui.label("Protocol Testing Dashboard").classes("text-caption text-white")

    with ui.left_drawer(value=True).classes("bg-grey-2"):
        ui.label("Navigation").classes("text-subtitle2 q-mb-sm")
        for path, label, icon in NAV_ITEMS:
            with ui.link(target=path).classes("no-underline"):
                with ui.row().classes(
                    "items-center gap-2 q-pa-sm rounded "
                    "cursor-pointer hover:bg-grey-3 full-width"
                ):
                    ui.icon(icon, size="xs")
                    ui.label(label).classes("text-body2")

        ui.separator().classes("q-my-md")
        ui.label("PANTHER v1.2.1").classes("text-caption text-grey-7")

    with ui.footer().classes("bg-grey-1 text-grey-7 text-caption"):
        ui.label(
            "PANTHER - Protocol Analysis and Testing Harness " "for Extensible Research"
        )
