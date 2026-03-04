"""Plugins page — browse discovered PANTHER plugins."""

import logging

from nicegui import ui

from panther.webapp.services.plugin_service import PluginService

logger = logging.getLogger(__name__)


def content():
    """Render the plugins browser page content."""
    plugin_svc = PluginService()

    ui.label("Registered Plugins").classes("text-h5 q-mb-md")

    plugins = plugin_svc.list_plugins()

    if not plugins:
        with ui.card().classes("w-full q-pa-lg text-center"):
            ui.icon("extension_off", size="xl").classes("text-grey-5")
            ui.label("No plugins discovered.").classes("text-body1 text-grey-7 q-mt-sm")
        return

    # Group by plugin type (PluginMetadata.type is a str)
    by_type: dict[str, list] = {}
    for p in plugins:
        by_type.setdefault(p.type, []).append(p)

    for plugin_type, items in sorted(by_type.items()):
        ui.label(plugin_type.replace("_", " ").title()).classes(
            "text-h6 q-mt-md q-mb-sm"
        )

        columns = [
            {"name": "name", "label": "Name", "field": "name", "sortable": True},
            {
                "name": "protocols",
                "label": "Protocols",
                "field": "protocols",
                "sortable": True,
            },
            {
                "name": "description",
                "label": "Description",
                "field": "description",
            },
        ]

        # Convert PluginMetadata to row dicts for ui.table
        rows = [
            {
                "name": p.name,
                "protocols": (
                    ", ".join(p.supported_protocols) if p.supported_protocols else ""
                ),
                "description": p.description,
            }
            for p in items
        ]

        ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")
