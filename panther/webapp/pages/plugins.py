"""Plugins page -- card-based browser for discovering and inspecting plugins.

Presents PANTHER (Protocol ANalyzer and THreat Evaluator for Research)
plugins in a filterable card grid.

This page presents every registered plugin as a card in a responsive
grid, with filtering by type and free-text search.  Clicking a card
opens a right-side drawer with detailed metadata.

**Plugin type tabs:**
    Tabs are generated dynamically from the ``_TYPE_TABS`` mapping.
    Only tabs that have at least one matching plugin are shown.
    Supported categories: IUT (Implementation Under Test), Tester,
    Network Environment, Execution Environment, and Protocol.

**Search:**
    A dense text input matches against the plugin name, description,
    supported protocols, and capabilities fields (case-insensitive
    substring match).

**Card grid:**
    Each plugin is rendered by the ``plugin_card`` component in a
    responsive column layout (``col-12 / col-sm-6 / col-md-4``).
    The grid is fully re-rendered on every filter change via
    ``_refresh_grid()``.

**Detail drawer:**
    A ``ui.right_drawer`` (420 px wide) hosts the
    ``render_plugin_detail`` component.  It receives the plugin
    object and an optional manifest dict from
    ``PluginService.get_plugin_manifest()``.

Data source:
    ``PluginService.list_plugins()`` returns a list of plugin metadata
    objects discovered by the plugin system's decorator-based
    registration mechanism.

NiceGUI patterns used:
    * ``ui.tabs`` / ``ui.tab`` for type filtering.
    * ``ui.right_drawer`` for the detail panel (slide-in from the
      right).
    * ``ui.row`` as a responsive card grid container.
    * Callback-driven grid refresh (``tabs.on_value_change``,
      ``search_input.on_value_change``).
"""

import logging

from nicegui import ui

from panther.webapp.components.display.plugin_card import plugin_card
from panther.webapp.components.display.plugin_detail_panel import render_plugin_detail
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
    """Render the plugins browser page content.

    Called by the NiceGUI router when the user navigates to ``/plugins``.
    The function:

    1. Fetches all registered plugins via ``PluginService.list_plugins()``.
    2. Creates a ``ui.right_drawer`` for the detail panel.
    3. Computes per-type counts and builds only the tabs that have
       plugins.
    4. Renders a search input alongside the tab bar.
    5. Calls ``_refresh_grid()`` to populate the initial card layout.
    6. Binds tab and search value-change events to ``_refresh_grid()``.
    """
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
        """Return True if the plugin matches the free-text search query."""
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
        """Return True if the plugin's type matches the active tab filter."""
        if tab_type_val is None:
            return True
        return plugin.type == tab_type_val or plugin.type.startswith(tab_type_val)

    def _on_card_click(plugin):
        """Open the right drawer with detailed metadata for the clicked plugin."""
        manifest = plugin_svc.get_plugin_manifest(plugin.name)
        render_plugin_detail(
            drawer_content,
            plugin,
            on_close=lambda: drawer.set_value(False),
            manifest=manifest,
        )
        drawer.set_value(True)

    def _refresh_grid():
        """Clear and re-render the card grid based on current tab and search filters."""
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
