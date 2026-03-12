"""PluginCard — compact metadata card for the plugins dashboard.

Renders a clickable NiceGUI card summarising a single PANTHER (Protocol
ANalysis and Testing Harness for Extensible Research) plugin.  Each card
shows the plugin name, a colour-coded status badge, a truncated
description, protocol chips, and capability badges.

The card is used by the plugins listing page; clicking it triggers a
callback that typically opens a ``plugin_detail_panel`` with exhaustive
information about the selected plugin.
"""

from typing import Callable

from nicegui import ui

PLUGIN_STATUS_COLORS: dict[str, str] = {
    "discovered": "blue-grey",
    "loaded": "blue",
    "initialized": "cyan",
    "active": "green",
    "failed": "red",
    "unloaded": "grey",
}


def plugin_card(plugin, on_click: Callable) -> ui.card:
    """Render a compact plugin card with key metadata.

    The card layout contains four rows:

    1. **Name + status badge** — colour-coded by lifecycle state
       (discovered, loaded, active, failed, etc.).
    2. **Description** — truncated to 80 characters to keep cards compact.
    3. **Protocol chips** — up to three ``ui.badge`` elements showing
       supported protocols, with a ``+N`` overflow badge.
    4. **Capability badges** — up to three capabilities, also with
       overflow.

    Args:
        plugin: A ``PluginMetadata`` instance (or compatible duck-typed
            object in tests) with at least ``name``, ``status``, and
            ``description`` attributes.
        on_click: Callback invoked with the ``plugin`` object when the
            card is clicked.  Typically opens a detail panel.

    Returns:
        The NiceGUI ``ui.card`` element for further layout composition.
    """
    status_val = (
        plugin.status.value if hasattr(plugin.status, "value") else plugin.status
    )
    status_color = PLUGIN_STATUS_COLORS.get(status_val.lower(), "grey")

    with (
        ui.card()
        .classes("w-full q-pa-sm cursor-pointer plugin-card")
        .on("click", lambda: on_click(plugin)) as card
    ):
        # Row 1: Name + status badge
        with ui.row().classes("items-center justify-between w-full"):
            ui.label(plugin.name).classes("text-subtitle1 font-bold")
            ui.badge(status_val.capitalize(), color=status_color)

        # Row 2: Truncated description
        desc = plugin.description or ""
        if len(desc) > 80:
            desc = desc[:80] + "..."
        if desc:
            ui.label(desc).classes("text-body2 text-grey-7")

        # Row 3: Protocol chips
        protocols = getattr(plugin, "supported_protocols", None) or []
        if protocols:
            with ui.row().classes("gap-1 q-mt-xs"):
                for proto in protocols[:3]:
                    ui.badge(proto, color="indigo").props("outline")
                if len(protocols) > 3:
                    ui.badge(f"+{len(protocols) - 3}", color="indigo").props("outline")

        # Row 4: Capability badges
        capabilities = getattr(plugin, "capabilities", None) or []
        if capabilities:
            with ui.row().classes("gap-1 q-mt-xs"):
                for cap in capabilities[:3]:
                    ui.badge(cap, color="blue-grey").props("outline")
                if len(capabilities) > 3:
                    ui.badge(f"+{len(capabilities) - 3}", color="blue-grey").props(
                        "outline"
                    )

    return card
