"""Config form panel — wraps PydanticForm inside a ui.expansion panel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from nicegui import ui
from pydantic import BaseModel

from panther.webapp.components.pydantic_form import FormConfig, PydanticForm


@dataclass
class FormPanelResult:
    """Result from ``config_form_panel``."""

    form: PydanticForm
    widgets: dict[str, Any] = field(default_factory=dict)


def config_form_panel(
    model_cls: type[BaseModel],
    title: str,
    icon: str = "settings",
    description: str = "",
    pre_populate: bool = True,
    singleton: bool = False,
    form_config: FormConfig | None = None,
) -> FormPanelResult:
    """Render a PydanticForm inside a ui.expansion panel.

    Args:
        model_cls: Pydantic model class.
        title: Expansion panel title.
        icon: Material icon name.
        description: Help text shown above the form.
        pre_populate: Kept for backward compat, ignored.
        singleton: Kept for backward compat, ignored.
        form_config: Layout configuration for the form.
    """
    with ui.expansion(title, icon=icon).classes("w-full"):
        if description:
            ui.label(description).classes("text-caption text-grey-7 q-mb-sm")
        form = PydanticForm(model_cls, config=form_config)
        _render_field_help(model_cls)
    return FormPanelResult(form=form, widgets={})


def _render_field_help(model_cls: type[BaseModel]):
    """Render collapsible field descriptions from Pydantic Field metadata."""
    descriptions = {}
    for name, field_info in model_cls.model_fields.items():
        desc = field_info.description
        if desc:
            descriptions[name] = desc

    if not descriptions:
        return

    with ui.expansion("Field descriptions", icon="help_outline").classes(
        "w-full text-caption"
    ):
        for field_name, desc in descriptions.items():
            with ui.row().classes("items-start gap-1 q-py-xs"):
                ui.label(field_name).classes("text-weight-medium text-grey-8")
                ui.label(f"— {desc}").classes("text-grey-6")
