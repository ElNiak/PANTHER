"""PluginDetailPanel — exhaustive plugin information panel.

Renders a full-page detail view for a single PANTHER (Protocol ANalysis
and Testing Harness for Extensible Research) plugin inside a provided
NiceGUI container (typically a right drawer or dialog).  The panel
displays:

* Header with plugin name and close button.
* Status, version, type, and runtime-mode badges.
* Description and author information.
* Manifest-only fields (license, homepage link, compatibility range).
* Supported protocols, capabilities, and tags as badge sections.
* Plugin and external dependencies.
* Collapsible technical details (entry point, file path, supported events).
* Collapsible configuration section showing Pydantic model fields as a
  table, raw JSON schema, or default config.
* Collapsible extra fields (raw JSON).
"""

from typing import Callable

from nicegui import ui

from panther.core.utils.format_utils import format_json

_PLUGIN_STATUS_COLORS = {
    "discovered": "blue-grey",
    "loaded": "blue",
    "initialized": "cyan",
    "active": "green",
    "failed": "red",
    "unloaded": "grey",
}


def render_plugin_detail(
    container: ui.element,
    plugin,
    on_close: Callable,
    manifest=None,
) -> None:
    """Render full plugin details into the given container.

    Clears the container and populates it with an exhaustive breakdown
    of the plugin's metadata, manifest data, and configuration schema.
    The layout is designed for a right-drawer or dialog panel and
    includes collapsible sections for technical details and config.

    Args:
        container: A NiceGUI element (e.g. ``ui.column`` inside a
            drawer) whose contents will be replaced.
        plugin: A ``PluginMetadata`` instance (or compatible duck-typed
            object in tests) providing ``name``, ``status``, ``version``,
            ``description``, and optional collection attributes
            (``supported_protocols``, ``capabilities``, ``tags``, etc.).
        on_close: Callback invoked when the close button is clicked.
        manifest: Optional ``PluginManifest`` providing extended fields
            such as ``license``, ``homepage``, ``entry_point``,
            ``config_model``, ``config_schema``, and ``default_config``.
    """
    container.clear()

    status_val = (
        plugin.status.value if hasattr(plugin.status, "value") else plugin.status
    )
    status_color = _PLUGIN_STATUS_COLORS.get(status_val.lower(), "grey")
    plugin_type = getattr(plugin, "type", "")

    with container:
        # ── Header ──
        with ui.row().classes("items-center justify-between w-full q-mb-sm"):
            ui.label(plugin.name).classes("text-h6")
            ui.button(icon="close", on_click=on_close).props("flat round dense")

        # ── Badge row ──
        with ui.row().classes("gap-2 q-mb-md"):
            ui.badge(status_val.capitalize(), color=status_color)
            if plugin.version:
                ui.badge(f"v{plugin.version}", color="primary").props("outline")
            if plugin_type:
                type_label = plugin_type.replace("_", " ").title()
                ui.badge(type_label, color="secondary").props("outline")
            runtime_mode = getattr(plugin, "runtime_mode", None)
            if runtime_mode:
                ui.badge(runtime_mode, color="deep-purple").props("outline")

        # ── Overview ──
        if plugin.description:
            ui.label(plugin.description).classes("text-body1 q-mb-sm")

        author = getattr(plugin, "author", "")
        if author:
            _info_row("person", f"Author: {author}")

        # Manifest-only fields
        if manifest:
            license_val = getattr(manifest, "license", "")
            if license_val:
                _info_row("gavel", f"License: {license_val}")
            homepage = getattr(manifest, "homepage", "")
            if homepage:
                with ui.row().classes("items-center gap-1 q-mb-xs"):
                    ui.icon("link", size="xs").classes("text-grey-7")
                    ui.link(homepage, homepage, new_tab=True).classes("text-body2")

        ui.separator().classes("q-my-sm")

        # ── Protocols ──
        _badge_section(
            "Protocols",
            getattr(plugin, "supported_protocols", None) or [],
            "indigo",
        )

        # ── Capabilities ──
        _badge_section(
            "Capabilities",
            getattr(plugin, "capabilities", None) or [],
            "blue-grey",
        )

        # ── Tags ──
        _badge_section(
            "Tags",
            getattr(plugin, "tags", None) or [],
            "teal",
        )

        # ── Dependencies ──
        plugin_deps = getattr(plugin, "dependencies", None) or []
        ext_deps = getattr(plugin, "external_dependencies", None) or []
        if plugin_deps or ext_deps:
            ui.label("Dependencies").classes("text-subtitle2 q-mb-xs")
            if plugin_deps:
                ui.label("Plugin").classes("text-caption text-grey-7")
                with ui.row().classes("gap-1 q-mb-xs"):
                    for dep in plugin_deps:
                        dep_str = dep if isinstance(dep, str) else str(dep)
                        ui.badge(dep_str, color="green").props("outline")
            if ext_deps:
                ui.label("External").classes("text-caption text-grey-7")
                with ui.row().classes("gap-1 q-mb-md"):
                    for dep in ext_deps:
                        ui.badge(dep, color="orange").props("outline")

        # ── Compatibility (from manifest) ──
        if manifest:
            min_v = getattr(manifest, "min_panther_version", "")
            max_v = getattr(manifest, "max_panther_version", None)
            if min_v or max_v:
                ui.label("Compatibility").classes("text-subtitle2 q-mb-xs")
                if min_v:
                    _info_row("arrow_upward", f"Min PANTHER: {min_v}")
                if max_v:
                    _info_row("arrow_downward", f"Max PANTHER: {max_v}")

        # ── Technical Details (collapsible) ──
        _render_technical_details(plugin, manifest)

        # ── Configuration (collapsible, from manifest) ──
        if manifest:
            _render_config_section(manifest)

        # ── Extra Fields (collapsible) ──
        extra = getattr(plugin, "extra_fields", None) or {}
        if extra:
            with ui.expansion("Extra Fields", icon="data_object").classes(
                "w-full q-mt-sm"
            ):
                ui.code(format_json(extra), language="json").classes("w-full").style(
                    "max-height: 300px; overflow: auto"
                )


def _info_row(icon: str, text: str):
    """Render an icon + text info line."""
    with ui.row().classes("items-center gap-1 q-mb-xs"):
        ui.icon(icon, size="xs").classes("text-grey-7")
        ui.label(text).classes("text-body2 text-grey-7")


def _badge_section(title: str, items: list, color: str):
    """Render a labeled section of outline badges, if items non-empty."""
    if not items:
        return
    ui.label(title).classes("text-subtitle2 q-mb-xs")
    with ui.row().classes("gap-1 q-mb-md"):
        for item in items:
            ui.badge(item, color=color).props("outline")


def _render_technical_details(plugin, manifest):
    """Render technical details in an expansion panel."""
    entry_point = getattr(manifest, "entry_point", None) if manifest else None
    file_path = getattr(manifest, "file_path", None) if manifest else None
    plugin_path = getattr(plugin, "path", None)
    supported_events = (
        (getattr(manifest, "supported_events", None) or []) if manifest else []
    )

    if not any([entry_point, file_path, plugin_path, supported_events]):
        return

    with ui.expansion("Technical Details", icon="code").classes("w-full q-mt-sm"):
        if entry_point:
            ui.label("Entry Point").classes("text-caption text-grey-7")
            ui.label(entry_point).classes("text-body2 font-mono q-mb-sm")
        path_val = file_path or (str(plugin_path) if plugin_path else None)
        if path_val:
            ui.label("File Path").classes("text-caption text-grey-7")
            ui.label(str(path_val)).classes("text-body2 font-mono q-mb-sm")
        if supported_events:
            ui.label("Supported Events").classes("text-caption text-grey-7")
            with ui.row().classes("gap-1 q-mb-sm"):
                for event in supported_events:
                    ui.badge(event, color="purple").props("outline")


def _render_config_section(manifest):
    """Render config model fields or raw schema in an expansion panel."""
    config_model = getattr(manifest, "config_model", None)
    config_schema = getattr(manifest, "config_schema", None) or {}
    default_config = getattr(manifest, "default_config", None) or {}

    if not config_model and not config_schema and not default_config:
        return

    with ui.expansion("Configuration", icon="settings").classes("w-full q-mt-sm"):
        # Prefer Pydantic model introspection (service plugins)
        if config_model and hasattr(config_model, "model_fields"):
            _render_model_fields_table(config_model)
        elif config_schema:
            # Fallback: raw dict schema (protocol plugins)
            ui.label("Config Schema").classes("text-caption text-grey-7")
            ui.code(format_json(config_schema), language="json").classes(
                "w-full"
            ).style("max-height: 300px; overflow: auto")

        if default_config:
            ui.label("Default Config").classes("text-caption text-grey-7 q-mt-sm")
            ui.code(format_json(default_config), language="json").classes(
                "w-full"
            ).style("max-height: 300px; overflow: auto")


def _format_type(annotation) -> str:
    """Convert a Python type annotation to a human-readable string."""
    if annotation is None:
        return "Any"
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", None)

    # typing.Optional[X] is Union[X, None]
    if origin is type(None):
        return "None"
    import typing

    if origin is typing.Union and args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and type(None) in args:
            return f"{_format_type(non_none[0])}?"
        return " | ".join(_format_type(a) for a in non_none)
    if origin is list or (hasattr(origin, "__name__") and origin.__name__ == "List"):
        inner = _format_type(args[0]) if args else "Any"
        return f"list[{inner}]"
    if origin is dict or (hasattr(origin, "__name__") and origin.__name__ == "Dict"):
        k = _format_type(args[0]) if args else "Any"
        v = _format_type(args[1]) if args and len(args) > 1 else "Any"
        return f"dict[{k}, {v}]"
    # Pydantic model or plain class
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation).replace("typing.", "")


def _render_model_fields_table(config_cls):
    """Render a sortable table of Pydantic model fields with type and default info."""
    try:
        from pydantic.fields import PydanticUndefined
    except ImportError:
        PydanticUndefined = object()

    rows = []
    for name, info in config_cls.model_fields.items():
        type_str = _format_type(info.annotation)
        default = info.default
        if default is PydanticUndefined:
            default_str = "(required)"
        elif default is None:
            default_str = "None"
        else:
            default_str = str(default)
            if len(default_str) > 40:
                default_str = default_str[:37] + "..."
        rows.append(
            {
                "name": name,
                "type": type_str,
                "default": default_str,
                "description": info.description or "",
            }
        )

    columns = [
        {
            "name": "name",
            "label": "Field",
            "field": "name",
            "sortable": True,
            "align": "left",
        },
        {"name": "type", "label": "Type", "field": "type", "align": "left"},
        {
            "name": "default",
            "label": "Default",
            "field": "default",
            "align": "left",
        },
        {
            "name": "description",
            "label": "Description",
            "field": "description",
            "align": "left",
        },
    ]
    ui.label(f"{config_cls.__name__} Fields").classes("text-caption text-grey-7")
    ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")
