"""Custom NiceGUI widgets for Dict and List[BaseModel] config fields.

NiceCRUD cannot render Dict[str, str], Dict[str, BaseModel], or
List[BaseModel] natively. These widgets are rendered alongside the
NiceCRUD form within the same expansion panel.

All widgets expose a common interface:
- ``.get_value()`` — returns current data for YAML serialization
- ``.set_value(data)`` — loads data (e.g. from parsed YAML)
"""

from __future__ import annotations

import logging
from typing import Any

from nicegui import ui
from niceguicrud import NiceCRUD, NiceCRUDConfig
from pydantic import BaseModel

from panther.webapp.utils.form_models import (
    ComplexFieldInfo,
    build_form_model,
    pick_id_field,
)

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
                    ui.input("Key", value=row["key"]).classes("w-1/3").on(
                        "update:model-value",
                        lambda e, i=idx: self._update_key(i, e.args),
                    )
                    ui.input("Value", value=row["value"]).classes("w-1/2").on(
                        "update:model-value",
                        lambda e, i=idx: self._update_value(i, e.args),
                    )
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
    ):
        self.field_name = field_name
        self.value_type = value_type
        self.FormModel = build_form_model(value_type)
        self._id_field = pick_id_field(value_type)
        self._entries: dict[str, BaseModel] = {}
        if initial:
            for k, v in initial.items():
                if isinstance(v, dict):
                    try:
                        self._entries[k] = self.FormModel(**v)
                    except Exception:
                        logger.warning(
                            "Failed to parse %s entry %s", field_name, k, exc_info=True
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
        with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
            ui.label("Add entry").classes("text-h6")
            key_input = ui.input("Key").classes("w-full")
            # NiceCRUD form for the model fields (same pattern as SingletonForm)
            add_crud = NiceCRUD(
                self.FormModel,
                basemodels=[self.FormModel()],
                config=NiceCRUDConfig(id_field=self._id_field),
            )
            add_crud.button_row.set_visibility(False)

            def _save():
                key = key_input.value
                if not key:
                    ui.notify("Key is required", type="warning")
                    return
                if key in self._entries:
                    ui.notify(f"Key '{key}' already exists", type="warning")
                    return
                items = add_crud.basemodels
                if items:
                    self._entries[key] = items[0]
                dialog.close()
                self._refresh()

            with ui.row().classes("justify-end w-full q-mt-sm"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Add", on_click=_save).props("color=primary")
        dialog.open()

    def _open_edit_dialog(self, key: str):
        model = self._entries.get(key)
        if model is None:
            return
        with ui.dialog() as dialog, ui.card().classes("w-[600px]"):
            ui.label(f"Edit: {key}").classes("text-h6")
            # Use NiceCRUD with hidden buttons (same pattern as SingletonForm)
            edit_crud = NiceCRUD(
                self.FormModel,
                basemodels=[model],
                config=NiceCRUDConfig(id_field=self._id_field),
            )
            edit_crud.button_row.set_visibility(False)

            def _save():
                items = edit_crud.basemodels
                if items:
                    self._entries[key] = items[0]
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
        return {k: v.model_dump() for k, v in self._entries.items()}

    def set_value(self, data: dict):
        """Load data from a dict of {key: dict_data}."""
        self._entries = {}
        for k, v in data.items():
            if isinstance(v, dict):
                try:
                    self._entries[k] = self.FormModel(**v)
                except Exception:
                    logger.warning("Failed to parse entry %s", k, exc_info=True)
        self._refresh()


class ModelListEditor:
    """Editor for ``List[BaseModel]`` fields.

    Wraps a standard NiceCRUD instance for the element type.
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
        self.FormModel = build_form_model(element_type)
        id_field = pick_id_field(element_type)

        basemodels = []
        if initial:
            for item in initial:
                if isinstance(item, dict):
                    try:
                        basemodels.append(self.FormModel(**item))
                    except Exception:
                        logger.warning(
                            "Failed to parse %s list item", field_name, exc_info=True
                        )
                elif isinstance(item, BaseModel):
                    basemodels.append(item)

        with ui.column().classes("w-full"):
            ui.label(field_name.replace("_", " ").title()).classes(
                "text-subtitle2 text-grey-8"
            )
            if description:
                ui.label(description).classes("text-caption text-grey-6 q-mb-xs")
            self.crud = NiceCRUD(
                self.FormModel,
                basemodels=basemodels,
                config=NiceCRUDConfig(id_field=id_field),
            )

    def get_value(self) -> list[dict]:
        """Return current data as a list of dicts."""
        return [item.model_dump() for item in self.crud.basemodels]

    def set_value(self, data: list):
        """Load data from a list of dicts."""
        models = []
        for item in data:
            if isinstance(item, dict):
                try:
                    models.append(self.FormModel(**item))
                except Exception:
                    logger.warning(
                        "Failed to parse list item for %s",
                        self.field_name,
                        exc_info=True,
                    )
        self.crud.basemodels = models


def create_widget_for_field(
    field_name: str,
    info: ComplexFieldInfo,
    initial_value: Any = None,
) -> KeyValueEditor | KeyedModelEditor | ModelListEditor:
    """Instantiate the appropriate widget based on field classification."""
    if info.category == "dict_str":
        return KeyValueEditor(
            field_name=field_name,
            description=info.description,
            initial=initial_value,
        )
    elif info.category == "dict_model":
        return KeyedModelEditor(
            field_name=field_name,
            value_type=info.value_type,
            description=info.description,
            initial=initial_value,
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
