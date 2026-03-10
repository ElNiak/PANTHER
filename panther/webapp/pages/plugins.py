"""Plugins page — card-based dashboard with filtering and detail panel."""

import logging

from nicegui import ui

from panther.webapp.components.plugin_card import plugin_card
from panther.webapp.components.plugin_detail_panel import render_plugin_detail
from panther.webapp.services.plugin_service import PluginService

logger = logging.getLogger(__name__)

# Tab label → plugin type value (None = show all)
_TYPE_TABS = {
    "All": None,
    "IUT": "iut",
    "Tester": "tester",
    "Network Env": "network_environment",
    "Exec Env": "execution_environment",
    "Protocol": "protocol",
}


def content():
    """Render the plugins browser page content."""
    plugin_svc = PluginService()
    plugins = plugin_svc.list_plugins()

    ui.label("Registered Plugins").classes("text-h5 q-mb-md")

    if not plugins:
        with ui.card().classes("w-full q-pa-lg text-center"):
            ui.icon("extension_off", size="xl").classes("text-grey-5")
            ui.label("No plugins discovered.").classes("text-body1 text-grey-7 q-mt-sm")
        return

    # --- Right drawer for plugin details ---
    drawer = ui.right_drawer(value=False).classes("q-pa-md").props("width=420")
    with drawer:
        drawer_content = ui.column().classes("w-full")

    # --- Filter bar ---
    # Determine which type tabs have plugins
    type_counts = {}
    for p in plugins:
        ptype = p.type
        type_counts[ptype] = type_counts.get(ptype, 0) + 1

    # Build tabs: only show tabs that have at least one plugin
    active_tabs = {"All": None}
    for label, type_val in _TYPE_TABS.items():
        if type_val is None:
            continue
        # Match plugins whose type equals or starts with the tab's type value
        count = sum(
            1 for p in plugins if p.type == type_val or p.type.startswith(type_val)
        )
        if count > 0:
            active_tabs[label] = type_val

    with ui.row().classes("items-center gap-4 w-full q-mb-md"):
        tabs = ui.tabs().classes("q-mr-auto")
        with tabs:
            for label in active_tabs:
                count = (
                    len(plugins)
                    if active_tabs[label] is None
                    else sum(
                        1
                        for p in plugins
                        if p.type == active_tabs[label]
                        or p.type.startswith(active_tabs[label])
                    )
                )
                ui.tab(label).props(f'label="{label} ({count})"')
        search_input = (
            ui.input(placeholder="Search plugins...")
            .props("dense outlined clearable")
            .classes("w-64")
        )

    # --- Card grid ---
    grid_container = ui.row().classes("w-full q-gutter-md")

    def _matches_search(plugin, query: str) -> bool:
        """Check if plugin matches the search query."""
        if not query:
            return True
        q = query.lower()
        searchable = " ".join(
            [
                plugin.name,
                plugin.description or "",
                " ".join(getattr(plugin, "supported_protocols", None) or []),
                " ".join(getattr(plugin, "capabilities", None) or []),
            ]
        ).lower()
        return q in searchable

    def _matches_tab(plugin, tab_type_val) -> bool:
        """Check if plugin matches the selected tab type."""
        if tab_type_val is None:
            return True
        return plugin.type == tab_type_val or plugin.type.startswith(tab_type_val)

    def _on_card_click(plugin):
        """Handle card click — show detail panel in right drawer."""
        manifest = plugin_svc.get_plugin_manifest(plugin.name)
        render_plugin_detail(
            drawer_content,
            plugin,
            on_close=lambda: drawer.set_value(False),
            manifest=manifest,
        )
        drawer.set_value(True)

    def _refresh_grid():
        """Re-render the card grid based on current filters."""
        grid_container.clear()
        selected_tab = tabs.value
        tab_type_val = active_tabs.get(selected_tab)
        query = search_input.value or ""

        filtered = [
            p
            for p in plugins
            if _matches_tab(p, tab_type_val) and _matches_search(p, query)
        ]

        with grid_container:
            if not filtered:
                with ui.column().classes("w-full items-center q-pa-lg"):
                    ui.icon("search_off", size="lg").classes("text-grey-5")
                    ui.label("No plugins match your filters.").classes(
                        "text-body1 text-grey-7"
                    )
            else:
                for p in filtered:
                    with ui.column().classes("col-12 col-sm-6 col-md-4"):
                        plugin_card(p, on_click=_on_card_click)

    tabs.on_value_change(lambda _: _refresh_grid())
    search_input.on_value_change(lambda _: _refresh_grid())

    # Initial render
    _refresh_grid()
