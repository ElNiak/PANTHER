"""Plugin card component for the plugins dashboard."""

from typing import Callable

from nicegui import ui

_PLUGIN_STATUS_COLORS = {
    "discovered": "blue-grey",
    "loaded": "blue",
    "initialized": "cyan",
    "active": "green",
    "failed": "red",
    "unloaded": "grey",
}


def plugin_card(plugin, on_click: Callable) -> ui.card:
    """Render a compact plugin card with key metadata.

    Args:
        plugin: PluginMetadata (or FakePluginMetadata in tests).
        on_click: Callback invoked when the card is clicked.
    """
    status_val = (
        plugin.status.value if hasattr(plugin.status, "value") else plugin.status
    )
    status_color = _PLUGIN_STATUS_COLORS.get(status_val.lower(), "grey")

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
