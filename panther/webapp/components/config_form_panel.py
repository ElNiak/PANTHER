"""NiceCRUD panel wrapper for PANTHER config models."""

from typing import Callable, Optional

from nicegui import ui
from niceguicrud import NiceCRUD, NiceCRUDConfig
from pydantic import BaseModel

from panther.webapp.utils.form_models import strip_omega_config


def config_form_panel(
    model_cls: type[BaseModel],
    id_field: str,
    title: str,
    icon: str = "settings",
    description: str = "",
    on_change: Optional[Callable[[dict], None]] = None,
) -> NiceCRUD:
    """Render a NiceCRUD instance inside a ui.expansion panel.

    Args:
        model_cls: Pydantic model class (will be auto-stripped of omega_config).
        id_field: Primary key field for NiceCRUD.
        title: Expansion panel title.
        icon: Material icon name.
        description: Help text shown above the form.
        on_change: Optional callback when form data changes.
    """
    FormModel = strip_omega_config(model_cls)
    with ui.expansion(title, icon=icon).classes("w-full"):
        if description:
            ui.label(description).classes("text-caption text-grey-7 q-mb-sm")
        _render_field_help(model_cls)
        crud = NiceCRUD(FormModel, config=NiceCRUDConfig(id_field=id_field))
    return crud


def _render_field_help(model_cls: type[BaseModel]):
    """Render collapsible field descriptions from Pydantic Field metadata."""
    descriptions = {}
    for name, field_info in model_cls.model_fields.items():
        if name == "omega_config":
            continue
        desc = field_info.description
        if desc:
            descriptions[name] = desc
        # Also check nested models for flattened field descriptions
        annotation = field_info.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            for sub_name, sub_info in annotation.model_fields.items():
                if sub_name == "omega_config":
                    continue
                if sub_info.description:
                    descriptions[f"{name}.{sub_name}"] = sub_info.description

    if not descriptions:
        return

    with ui.expansion("Field descriptions", icon="help_outline").classes(
        "w-full text-caption"
    ):
        for field_name, desc in descriptions.items():
            with ui.row().classes("items-start gap-1 q-py-xs"):
                ui.label(field_name).classes("text-weight-medium text-grey-8")
                ui.label(f"— {desc}").classes("text-grey-6")
