"""DictListWidgets — custom NiceGUI widgets for Dict and List[BaseModel] fields.

Provides three widget classes for complex Pydantic field types that cannot
be rendered as simple scalar inputs by ``PydanticForm``.  These widgets
are used throughout the PANTHER (Protocol ANalysis and Testing Harness for
Extensible Research) config builder to edit structured configuration data:

* ``KeyValueEditor`` — edits ``Dict[str, str]`` / ``Dict[str, Any]`` fields
  as a dynamic list of key-value input rows.
* ``KeyedModelEditor`` — edits ``Dict[str, BaseModel]`` fields as a table
  of named entries with add/edit/delete dialogs.
* ``ModelListEditor`` — edits ``List[BaseModel]`` fields as an indexed list
  with add/edit/delete dialogs.

All three widgets expose a common interface:

- ``.get_value()`` — returns current data for YAML serialization.
- ``.set_value(data)`` — loads data (e.g. from parsed YAML or form sync).

The module also contains ``create_widget_for_field()``, the factory
function that ``PydanticForm`` calls to instantiate the correct widget
based on the ``ComplexFieldInfo.category`` classification.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from nicegui import ui
from pydantic import BaseModel

from panther.webapp.components.forms.form_models import ComplexFieldInfo

logger = logging.getLogger(__name__)


class KeyValueEditor:
    """Editor for ``Dict[str, str]`` and ``Dict[str, Any]`` fields.

    Renders as a list of key-value input rows with add/delete controls.
    """

    def __init__(  # noqa: D107
        self, field_name: str, description: str = "", initial: dict | None = None
    ):
        self.field_name = field_name
        self._rows: list[dict[str, str]] = []
        if initial:
            self._rows = [{"key": k, "value": str(v)} for k, v in initial.items()]

        with ui.column().classes("w-full"):
            ui.label(field_name.replace("_", " ").title()).classes(
                "text-subtitle2 text-grey-8"
            )
            if description:
                ui.label(description).classes("text-caption text-grey-6 q-mb-xs")
            self._container = ui.column().classes("w-full gap-1")
            ui.button("Add row", icon="add", on_click=self._add_row).props(
                "flat dense size=sm"
            )
        self._refresh()

    def _refresh(self):
        self._container.clear()
        with self._container:
            for idx, row in enumerate(self._rows):
                with ui.row().classes("w-full items-center gap-1"):
                    ui.input(
                        "Key",
                        value=row["key"],
                        on_change=lambda e, i=idx: self._update_key(i, e.value),
                    ).classes("w-1/3")
                    ui.input(
                        "Value",
                        value=row["value"],
                        on_change=lambda e, i=idx: self._update_value(i, e.value),
                    ).classes("w-1/2")
                    ui.button(
                        icon="close",
                        on_click=lambda _, i=idx: self._remove_row(i),
                    ).props("flat dense round size=sm color=negative")

    def _update_key(self, idx: int, value: str):
        if idx < len(self._rows):
            self._rows[idx]["key"] = value or ""

    def _update_value(self, idx: int, value: str):
        if idx < len(self._rows):
            self._rows[idx]["value"] = value or ""

    def _add_row(self):
        self._rows.append({"key": "", "value": ""})
        self._refresh()

    def _remove_row(self, idx: int):
        if idx < len(self._rows):
            self._rows.pop(idx)
            self._refresh()

    def get_value(self) -> dict[str, str]:
        """Return current data as a dict (skips empty keys, warns on duplicates)."""
        seen: dict[str, str] = {}
        for r in self._rows:
            if r["key"]:
                if r["key"] in seen:
                    logger.warning(
                        "Duplicate key '%s' in %s — last value wins",
                        r["key"],
                        self.field_name,
                    )
                seen[r["key"]] = r["value"]
        return seen

    def set_value(self, data: dict):
        """Load data from a dict."""
        self._rows = [{"key": k, "value": str(v)} for k, v in data.items()]
        self._refresh()


class KeyedModelEditor:
    """Editor for ``Dict[str, BaseModel]`` fields.

    Renders as a table of entries with key, summary, and edit/delete controls.
    An "Add entry" button opens a dialog for the key + model fields.
    """

    def __init__(  # noqa: D107
        self,
        field_name: str,
        value_type: type[BaseModel],
        description: str = "",
        initial: dict | None = None,
        key_generator: Callable[[dict], str] | None = None,
        dialog_factory: Callable | None = None,
        edit_dialog_factory: Callable | None = None,
    ):
        self.field_name = field_name
        self.value_type = value_type
        self._key_generator = key_generator
        self._dialog_factory = dialog_factory
        self._edit_dialog_factory = edit_dialog_factory
        self._entries: dict[str, BaseModel] = {}
        if initial:
            for k, v in initial.items():
                if isinstance(v, dict):
                    try:
                        self._entries[k] = self.value_type(**v)
                    except Exception:
                        logger.warning(
                            "Failed to parse %s entry %s",
                            field_name,
                            k,
                            exc_info=True,
                        )
                elif isinstance(v, BaseModel):
                    self._entries[k] = v

        with ui.column().classes("w-full"):
            ui.label(field_name.replace("_", " ").title()).classes(
                "text-subtitle2 text-grey-8"
            )
            if description:
                ui.label(description).classes("text-caption text-grey-6 q-mb-xs")
            self._container = ui.column().classes("w-full gap-1")
            ui.button("Add entry", icon="add", on_click=self._open_add_dialog).props(
                "flat dense size=sm"
            )
        self._refresh()

    def _refresh(self):
        self._container.clear()
        with self._container:
            if not self._entries:
                ui.label("No entries").classes("text-caption text-grey-5 q-py-xs")
                return
            for key in list(self._entries.keys()):
                model = self._entries[key]
                summary = self._summarize(model)
                with ui.row().classes("w-full items-center gap-2 q-py-xs"):
                    ui.label(key).classes("text-weight-medium").style(
                        "min-width: 100px"
                    )
                    ui.label(summary).classes("text-caption text-grey-6 flex-grow")
                    ui.button(
                        icon="edit",
                        on_click=lambda _, k=key: self._open_edit_dialog(k),
                    ).props("flat dense round size=sm")
                    ui.button(
                        icon="close",
                        on_click=lambda _, k=key: self._remove_entry(k),
                    ).props("flat dense round size=sm color=negative")

    def _summarize(self, model: BaseModel) -> str:
        """Generate a short summary of model fields."""
        data = model.model_dump()
        parts = []
        for k, v in list(data.items())[:3]:
            if v is not None and v != "" and v != [] and v != {}:
                parts.append(f"{k}={v}")
        return ", ".join(parts) if parts else "(empty)"

    def _open_add_dialog(self):
        if self._dialog_factory:
            self._dialog_factory(
                value_type=self.value_type,
                entries=self._entries,
                key_generator=self._key_generator,
                on_add=self._refresh,
            )
            return

        from panther.webapp.components.forms.pydantic_form import PydanticForm

        with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
            ui.label("Add entry").classes("text-h6")
            if self._key_generator is None:
                key_input = ui.input("Key").classes("w-full")
            else:
                key_input = None
                ui.label("Key auto-generated from implementation + role").classes(
                    "text-caption text-grey-6"
                )
            form = PydanticForm(self.value_type)

            def _save():
                data = form.get_value()
                if self._key_generator:
                    key = self._key_generator(data)
                else:
                    key = key_input.value
                if not key:
                    ui.notify("Key is required", type="warning")
                    return
                if key in self._entries:
                    ui.notify(f"Key '{key}' already exists", type="warning")
                    return
                try:
                    self._entries[key] = self.value_type(**data)
                except Exception:
                    logger.warning("Failed to create entry", exc_info=True)
                    ui.notify("Failed to create entry", type="negative")
                    return
                dialog.close()
                self._refresh()

            with ui.row().classes("justify-end w-full q-mt-sm"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Add", on_click=_save).props("color=primary")
        dialog.open()

    def _open_edit_dialog(self, key: str):
        if self._edit_dialog_factory:
            self._edit_dialog_factory(
                value_type=self.value_type,
                entries=self._entries,
                key_generator=self._key_generator,
                on_save=self._refresh,
                edit_key=key,
            )
            return

        from panther.webapp.components.forms.pydantic_form import PydanticForm

        model = self._entries.get(key)
        if model is None:
            return
        with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
            ui.label(f"Edit: {key}").classes("text-h6")
            form = PydanticForm(self.value_type, instance=model)

            def _save():
                try:
                    data = form.get_value()
                    self._entries[key] = self.value_type(**data)
                except Exception:
                    logger.warning("Failed to update entry %s", key, exc_info=True)
                    ui.notify(f"Failed to update entry '{key}'", type="negative")
                    return
                dialog.close()
                self._refresh()

            with ui.row().classes("justify-end w-full q-mt-sm"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Save", on_click=_save).props("color=primary")
        dialog.open()

    def _remove_entry(self, key: str):
        self._entries.pop(key, None)
        self._refresh()

    def get_value(self) -> dict[str, dict]:
        """Return current data as {key: model_dump()}."""
        return {k: v.model_dump(mode="json") for k, v in self._entries.items()}

    def set_value(self, data: dict):
        """Load data from a dict of {key: dict_data}."""
        self._entries = {}
        for k, v in data.items():
            if isinstance(v, dict):
                try:
                    self._entries[k] = self.value_type(**v)
                except Exception:
                    logger.warning("Failed to parse entry %s", k, exc_info=True)
        self._refresh()


class ModelListEditor:
    """Editor for ``List[BaseModel]`` fields.

    Renders as summary rows with edit/delete buttons and an "Add" button.
    """

    def __init__(  # noqa: D107
        self,
        field_name: str,
        element_type: type[BaseModel],
        description: str = "",
        initial: list | None = None,
    ):
        self.field_name = field_name
        self.element_type = element_type
        self._entries: list[BaseModel] = []
        if initial:
            for item in initial:
                if isinstance(item, dict):
                    try:
                        self._entries.append(self.element_type(**item))
                    except Exception:
                        logger.warning(
                            "Failed to parse %s list item",
                            field_name,
                            exc_info=True,
                        )
                elif isinstance(item, BaseModel):
                    self._entries.append(item)

        with ui.column().classes("w-full"):
            ui.label(field_name.replace("_", " ").title()).classes(
                "text-subtitle2 text-grey-8"
            )
            if description:
                ui.label(description).classes("text-caption text-grey-6 q-mb-xs")
            self._container = ui.column().classes("w-full gap-1")
            ui.button("Add", icon="add", on_click=self._open_add_dialog).props(
                "flat dense size=sm"
            )
        self._refresh()

    def _refresh(self):
        self._container.clear()
        with self._container:
            if not self._entries:
                ui.label("No entries").classes("text-caption text-grey-5 q-py-xs")
                return
            for idx, item in enumerate(self._entries):
                summary = self._summarize(item)
                with ui.row().classes("w-full items-center gap-2 q-py-xs"):
                    ui.label(f"[{idx}]").classes("text-weight-medium").style(
                        "min-width: 40px"
                    )
                    ui.label(summary).classes("text-caption text-grey-6 flex-grow")
                    ui.button(
                        icon="edit",
                        on_click=lambda _, i=idx: self._open_edit_dialog(i),
                    ).props("flat dense round size=sm")
                    ui.button(
                        icon="close",
                        on_click=lambda _, i=idx: self._remove_entry(i),
                    ).props("flat dense round size=sm color=negative")

    def _summarize(self, model: BaseModel) -> str:
        data = model.model_dump()
        parts = []
        for k, v in list(data.items())[:3]:
            if v is not None and v != "" and v != [] and v != {}:
                parts.append(f"{k}={v}")
        return ", ".join(parts) if parts else "(empty)"

    def _open_add_dialog(self):
        from panther.webapp.components.forms.pydantic_form import PydanticForm

        with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
            ui.label("Add entry").classes("text-h6")
            form = PydanticForm(self.element_type)

            def _save():
                try:
                    data = form.get_value()
                    self._entries.append(self.element_type(**data))
                except Exception:
                    logger.warning("Failed to add list entry", exc_info=True)
                    ui.notify("Failed to add entry", type="negative")
                    return
                dialog.close()
                self._refresh()

            with ui.row().classes("justify-end w-full q-mt-sm"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Add", on_click=_save).props("color=primary")
        dialog.open()

    def _open_edit_dialog(self, idx: int):
        from panther.webapp.components.forms.pydantic_form import PydanticForm

        if idx >= len(self._entries):
            return
        item = self._entries[idx]
        with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
            ui.label(f"Edit [{idx}]").classes("text-h6")
            form = PydanticForm(self.element_type, instance=item)

            def _save():
                try:
                    data = form.get_value()
                    self._entries[idx] = self.element_type(**data)
                except Exception:
                    logger.warning("Failed to update list entry %d", idx, exc_info=True)
                    ui.notify("Failed to update entry", type="negative")
                    return
                dialog.close()
                self._refresh()

            with ui.row().classes("justify-end w-full q-mt-sm"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Save", on_click=_save).props("color=primary")
        dialog.open()

    def _remove_entry(self, idx: int):
        if idx < len(self._entries):
            self._entries.pop(idx)
            self._refresh()

    def get_value(self) -> list[dict]:
        """Return current data as a list of dicts."""
        return [item.model_dump(mode="json") for item in self._entries]

    def set_value(self, data: list):
        """Load data from a list of dicts."""
        self._entries = []
        for item in data:
            if isinstance(item, dict):
                try:
                    self._entries.append(self.element_type(**item))
                except Exception:
                    logger.warning(
                        "Failed to parse list item for %s",
                        self.field_name,
                        exc_info=True,
                    )
        self._refresh()


def _build_service_dialog(
    value_type: type[BaseModel],
    entries: dict,
    key_generator: Callable | None,
    on_add: Callable | None = None,
    on_save: Callable | None = None,
    edit_key: str | None = None,
) -> None:
    """Custom reactive dialog for adding or editing a service entry.

    Provides protocol-filtered implementation/version dropdowns and
    IUT/tester type selection instead of the generic PydanticForm.

    When *edit_key* is provided the dialog opens in edit mode: dropdowns
    are pre-populated from the existing entry and saving updates in-place.
    """
    from panther.webapp.components.forms.plugin_forms import (
        get_implementation_choices,
        get_protocol_choices,
        get_version_choices,
    )
    from panther.webapp.components.forms.pydantic_form import FormConfig, PydanticForm

    # Accept both on_add (add-mode) and on_save (edit-mode) callbacks
    _callback = on_save or on_add

    # ── Resolve initial values from existing entry ───────────────
    existing = entries.get(edit_key) if edit_key else None
    if existing:
        existing_data = existing.model_dump()
        init_proto = existing_data.get("protocol", {}).get("name")
        init_ver = existing_data.get("protocol", {}).get("version")
        init_type = existing_data.get("implementation", {}).get("type", "iut")
        init_role = existing_data.get("protocol", {}).get("role", "server")
        init_impl = existing_data.get("implementation", {}).get("name")
        init_target = existing_data.get("protocol", {}).get("target", "")
    else:
        init_proto = None
        init_ver = None
        init_type = "iut"
        init_role = "server"
        init_impl = None
        init_target = ""

    is_edit = edit_key is not None and existing is not None
    title = f"Edit Service: {edit_key}" if is_edit else "Add Service"

    with ui.dialog() as dialog, ui.card().classes("w-[700px]"):
        ui.label(title).classes("text-h6")

        # ── Key dropdowns ────────────────────────────────────────────
        with ui.row().classes("w-full gap-4"):
            proto_select = ui.select(
                get_protocol_choices(),
                value=init_proto,
                label="Protocol",
            ).classes("flex-grow")
            ver_select = ui.select([], label="Version").classes("flex-grow")

        with ui.row().classes("w-full gap-4"):
            type_select = ui.select(
                {"iut": "IUT", "testers": "Tester"},
                value=init_type,
                label="Service Type",
            ).classes("flex-grow")
            role_select = ui.select(
                {"server": "Server", "client": "Client", "peer": "Peer"},
                value=init_role,
                label="Role",
            ).classes("flex-grow")

        impl_select = ui.select([], label="Implementation").classes("w-full")

        # Build target choices from sibling services (excluding self in edit mode)
        _target_choices = [k for k in entries.keys() if k != edit_key]
        target_select = ui.select(
            _target_choices,
            value=init_target if init_target in entries else None,
            label="Target service (type a name or select existing)",
            with_input=True,
            new_value_mode="add-unique",
        ).classes("w-full")
        target_select.set_visibility(init_role == "client")
        if not _target_choices:
            target_hint = ui.label(
                "No other services yet — type a target name and add the server later."
            ).classes("text-caption text-orange-7")
            target_hint.set_visibility(init_role == "client")
        else:
            target_hint = None

        # ── Reactive handlers ────────────────────────────────────────
        def _update_versions():
            proto = proto_select.value
            choices = get_version_choices(proto) if proto else []
            ver_select.options = choices
            ver_select.update()

        def _update_implementations():
            choices = get_implementation_choices(
                protocol=proto_select.value or None,
                service_type=type_select.value or None,
            )
            impl_select.options = choices
            impl_select.update()

        def _on_protocol_change(_e):
            _update_versions()
            _update_implementations()

        def _on_type_change(_e):
            _update_implementations()

        def _on_role_change(e):
            is_client = e.value == "client"
            target_select.set_visibility(is_client)
            if target_hint is not None:
                target_hint.set_visibility(is_client)

        proto_select.on_value_change(_on_protocol_change)
        type_select.on_value_change(_on_type_change)
        role_select.on_value_change(_on_role_change)

        # Populate version/implementation options, then set initial values
        _update_versions()
        _update_implementations()
        if init_ver:
            ver_select.value = init_ver
        if init_impl:
            impl_select.value = init_impl

        # ── Remaining fields (timeout, network, etc.) ────────────────
        handled = frozenset({"implementation", "protocol"})
        remaining_config = FormConfig(
            exclude_fields=handled,
            show_advanced=False,
        )
        with ui.expansion("Additional Settings", icon="tune").classes("w-full"):
            remaining_form = PydanticForm(
                value_type,
                instance=existing if is_edit else None,
                config=remaining_config,
            )

        # ── Save ─────────────────────────────────────────────────────
        def _save():
            if not impl_select.value:
                ui.notify("Select an implementation", type="warning")
                return
            if not proto_select.value:
                ui.notify("Select a protocol", type="warning")
                return

            protocol_data: dict[str, Any] = {
                "name": proto_select.value,
                "role": role_select.value,
            }
            if ver_select.value:
                protocol_data["version"] = ver_select.value
            if role_select.value == "client" and target_select.value:
                protocol_data["target"] = target_select.value

            data: dict[str, Any] = {
                "implementation": {
                    "name": impl_select.value,
                    "type": type_select.value,
                },
                "protocol": protocol_data,
                **remaining_form.get_value(),
            }

            if is_edit:
                # Edit mode: update existing entry in-place
                try:
                    entries[edit_key] = value_type(**data)
                except Exception:
                    logger.warning("Failed to update service entry", exc_info=True)
                    ui.notify("Invalid configuration", type="negative")
                    return
            else:
                # Add mode: generate key & check uniqueness
                key = key_generator(data) if key_generator else impl_select.value
                if not key:
                    ui.notify("Key is required", type="warning")
                    return
                if key in entries:
                    ui.notify(f"Key '{key}' already exists", type="warning")
                    return
                try:
                    entries[key] = value_type(**data)
                except Exception:
                    logger.warning("Failed to create service entry", exc_info=True)
                    ui.notify("Invalid configuration", type="negative")
                    return

            dialog.close()
            if _callback:
                _callback()

        with ui.row().classes("justify-end w-full q-mt-sm"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Save" if is_edit else "Add",
                on_click=_save,
            ).props("color=primary")

    dialog.open()


def create_widget_for_field(
    field_name: str,
    info: ComplexFieldInfo,
    initial_value: Any = None,
) -> KeyValueEditor | KeyedModelEditor | ModelListEditor:
    """Factory: instantiate the appropriate widget for a complex field.

    Dispatches on ``info.category`` to create the right editor widget:
    ``"dict_str"`` -> ``KeyValueEditor``, ``"dict_model"`` ->
    ``KeyedModelEditor``, ``"list_model"`` -> ``ModelListEditor``.

    For ``dict_model`` fields whose ``json_schema_extra`` contains
    ``key_generator="service_name"``, the specialised
    ``_build_service_dialog`` is wired as the add/edit dialog factory
    to provide protocol-filtered dropdowns.

    Args:
        field_name: The Pydantic field name (used as widget label).
        info: Classification metadata from ``classify_complex_field()``.
        initial_value: Optional pre-existing data to populate the widget.

    Returns:
        A widget instance with ``.get_value()`` / ``.set_value()`` API.

    Raises:
        ValueError: If ``info.category`` is not recognised.
    """
    if info.category == "dict_str":
        return KeyValueEditor(
            field_name=field_name,
            description=info.description,
            initial=initial_value,
        )
    elif info.category == "dict_model":
        key_gen = None
        dialog_factory = None
        edit_dialog_factory = None
        extra = info.json_schema_extra or {}
        if extra.get("key_generator") == "service_name":
            key_gen = lambda data: (
                f"{data.get('implementation', {}).get('name', 'svc')}"
                f"_{data.get('protocol', {}).get('role', 'unknown')}"
            )
            dialog_factory = _build_service_dialog
            edit_dialog_factory = _build_service_dialog
        return KeyedModelEditor(
            field_name=field_name,
            value_type=info.value_type,
            description=info.description,
            initial=initial_value,
            key_generator=key_gen,
            dialog_factory=dialog_factory,
            edit_dialog_factory=edit_dialog_factory,
        )
    elif info.category == "list_model":
        return ModelListEditor(
            field_name=field_name,
            element_type=info.value_type,
            description=info.description,
            initial=initial_value,
        )
    else:
        raise ValueError(f"Unknown complex field category: {info.category}")
