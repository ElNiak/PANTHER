"""NiceCRUD panel wrapper for PANTHER config models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from nicegui import ui
from niceguicrud import NiceCRUD, NiceCRUDConfig
from pydantic import BaseModel

from panther.webapp.components.dict_list_widgets import create_widget_for_field
from panther.webapp.components.singleton_crud import SingletonForm
from panther.webapp.utils.form_models import (
    build_form_model,
    get_complex_fields,
    pick_id_field,
)


@dataclass
class FormPanelResult:
    """Result from ``config_form_panel`` — holds NiceCRUD + custom widgets."""

    crud: Any  # NiceCRUD or SingletonForm
    widgets: dict[str, Any] = field(default_factory=dict)


def config_form_panel(
    model_cls: type[BaseModel],
    title: str,
    icon: str = "settings",
    description: str = "",
    pre_populate: bool = True,
    id_field: Optional[str] = None,
    singleton: bool = False,
) -> FormPanelResult:
    """Render a NiceCRUD instance + custom widgets inside a ui.expansion panel.

    Args:
        model_cls: Pydantic model class (will be auto-cleaned for NiceCRUD).
        title: Expansion panel title.
        icon: Material icon name.
        description: Help text shown above the form.
        pre_populate: Start with one default instance so users edit instead of adding.
        id_field: Primary key field for NiceCRUD (auto-detected if None).
        singleton: Use SingletonCRUD (no add/delete buttons) for single-instance configs.
    """
    FormModel = build_form_model(model_cls)
    resolved_id = id_field or pick_id_field(model_cls)

    widgets: dict[str, Any] = {}

    with ui.expansion(title, icon=icon).classes("w-full"):
        if description:
            ui.label(description).classes("text-caption text-grey-7 q-mb-sm")

        if singleton:
            # Inline form — no table, no search, no add/delete buttons
            instance = FormModel()
            crud = SingletonForm(
                FormModel,
                instance=instance,
                config=NiceCRUDConfig(id_field=resolved_id),
            )
        else:
            basemodels = [FormModel()] if pre_populate else []
            crud = NiceCRUD(
                FormModel,
                basemodels=basemodels,
                config=NiceCRUDConfig(id_field=resolved_id),
            )

        # Render custom widgets for Dict/List fields below the NiceCRUD form
        complex_fields = get_complex_fields(model_cls)
        if complex_fields:
            ui.separator().classes("q-my-sm")
            for field_name, info in complex_fields.items():
                widgets[field_name] = create_widget_for_field(field_name, info)

        # Field help — after widgets so we can include complex field descriptions
        _render_field_help(FormModel, complex_fields)

    return FormPanelResult(crud=crud, widgets=widgets)


def _render_field_help(form_model: type[BaseModel], complex_fields: dict | None = None):
    """Render collapsible field descriptions from Pydantic Field metadata."""
    descriptions = {}
    for name, field_info in form_model.model_fields.items():
        desc = field_info.description
        if desc:
            descriptions[name] = desc

    # Include complex field descriptions (rendered by widgets, not NiceCRUD)
    if complex_fields:
        for name, info in complex_fields.items():
            if info.description:
                descriptions[name] = f"{info.description} (custom widget)"

    if not descriptions:
        return

    with ui.expansion("Field descriptions", icon="help_outline").classes(
        "w-full text-caption"
    ):
        for field_name, desc in descriptions.items():
            with ui.row().classes("items-start gap-1 q-py-xs"):
                ui.label(field_name).classes("text-weight-medium text-grey-8")
                ui.label(f"— {desc}").classes("text-grey-6")
