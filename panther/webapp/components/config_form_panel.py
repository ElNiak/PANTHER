"""ConfigFormPanel — wraps PydanticForm inside a collapsible expansion panel.

Composes a ``PydanticForm`` (the recursive model renderer) with a NiceGUI
``ui.expansion`` panel to produce a self-contained, collapsible config
section for the PANTHER (Protocol ANalysis and Testing Harness for
Extensible Research) config builder page.  An optional description string
and auto-generated field-help block are placed above and below the form
respectively.

Usage::

    result = config_form_panel(LoggingConfig, title="Logging", icon="description")
    data = result.form.get_value()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from nicegui import ui
from pydantic import BaseModel

from panther.webapp.components.pydantic_form import FormConfig, PydanticForm


@dataclass
class FormPanelResult:
    """Return value from ``config_form_panel``.

    Attributes:
        form: The ``PydanticForm`` instance rendered inside the panel.
            Use ``form.get_value()`` / ``form.set_value()`` to read or
            populate the form.
        widgets: Reserved for future use; currently always empty.
    """

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
    """Render a PydanticForm inside a ``ui.expansion`` panel.

    Creates a collapsible panel containing:

    1. An optional description label (grey caption text).
    2. A ``PydanticForm`` that renders all model fields as widgets.
    3. A collapsible "Field descriptions" section extracted from Pydantic
       ``Field(description=...)`` metadata.

    Args:
        model_cls: Pydantic model class whose fields are rendered.
        title: Text shown on the expansion panel header.
        icon: Material icon name displayed next to the title.
        description: Help text rendered above the form as a grey caption.
        pre_populate: Legacy parameter, kept for backward compatibility.
        singleton: Legacy parameter, kept for backward compatibility.
        form_config: Optional ``FormConfig`` to customise layout options
            (advanced toggle, CSS prefix, excluded fields, etc.).

    Returns:
        A ``FormPanelResult`` containing the ``PydanticForm`` instance.
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
