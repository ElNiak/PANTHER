"""Dashboard page — home page with summary stats."""

import logging
from pathlib import Path

from nicegui import app, ui

from panther.webapp.components.stat_cards import stat_card
from panther.webapp.services.plugin_service import PluginService
from panther.webapp.services.results_service import ResultsService

logger = logging.getLogger(__name__)


def content():
    """Render the dashboard page content."""
    output_dir = app.storage.general.get("output_dir", "outputs")

    plugin_svc = PluginService()
    results_svc = ResultsService(output_dir)

    plugin_count = len(plugin_svc.list_plugins())
    experiment_count = results_svc.count_experiments()
    config_path = app.storage.general.get("config_path")

    ui.label("Overview").classes("text-h5 q-mb-md")

    with ui.row().classes("gap-4 q-mb-lg"):
        stat_card("Plugins", str(plugin_count), icon="extension", color="primary")
        stat_card(
            "Past Experiments",
            str(experiment_count),
            icon="history",
            color="secondary",
        )
        stat_card(
            "Loaded Config",
            Path(config_path).name if config_path else "None",
            icon="description",
            color="accent",
        )

    ui.separator()

    ui.label("Quick Actions").classes("text-h6 q-mt-md q-mb-sm")
    with ui.row().classes("gap-3"):
        ui.button("New Config", icon="add", on_click=lambda: ui.navigate.to("/config"))
        ui.button(
            "Browse Results", icon="folder", on_click=lambda: ui.navigate.to("/results")
        )
        ui.button(
            "View Plugins",
            icon="extension",
            on_click=lambda: ui.navigate.to("/plugins"),
        )
