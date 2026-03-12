"""ModelRenderersMixin — nested model and plugin-aware renderers for PydanticForm.

Extracted from ``pydantic_form.py`` to separate the complex rendering
logic (plugin dropdowns with sub-forms, recursive nested models,
optional model toggles) from the core form engine and scalar renderers.

All methods access ``self._prefix``, ``self._config``,
``self._field_bindings``, ``self._plugin_sub_forms``, and
``self._model_cls`` through MRO from the composing ``PydanticForm`` class.
"""

from __future__ import annotations

import logging
from typing import Any

from nicegui import ui
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ModelRenderersMixin:
    """Mixin providing nested-model and plugin-aware renderers for PydanticForm."""

    def _render_protocol_select(self, name, field_info, default):
        """Render a dropdown of available protocol names from the registry."""
        from panther.webapp.components.forms.pydantic_form import FieldBinding

        label = name.replace("_", " ").title()
        from panther.webapp.components.forms.plugin_forms import get_protocol_choices

        options = get_protocol_choices()
        val = default if default in options else (options[0] if options else "")
        with ui.row().classes(f"w-full items-center {self._prefix}-field"):
            sel = ui.select(options, value=val, label=label).classes(
                f"flex-grow {self._prefix}-field-enum"
            )
            if field_info.description:
                sel.tooltip(field_info.description)
        self._field_bindings[name] = FieldBinding(
            getter=lambda s=sel: s.value,
            setter=lambda v, s=sel: setattr(s, "value", v),
            field_type="scalar",
        )

    def _render_implementation_select(self, name, field_info, default):
        """Render a dropdown of available implementation names from the registry."""
        from panther.webapp.components.forms.pydantic_form import FieldBinding

        label = name.replace("_", " ").title()
        from panther.webapp.components.forms.plugin_forms import (
            get_implementation_choices,
        )

        options = get_implementation_choices()
        val = default if default in options else (options[0] if options else "")
        with ui.row().classes(f"w-full items-center {self._prefix}-field"):
            sel = ui.select(options, value=val, label=label).classes(
                f"flex-grow {self._prefix}-field-enum"
            )
            if field_info.description:
                sel.tooltip(field_info.description)
        self._field_bindings[name] = FieldBinding(
            getter=lambda s=sel: s.value,
            setter=lambda v, s=sel: setattr(s, "value", v),
            field_type="scalar",
        )

    def _render_plugin_select(self, name, field_info, default, extra):
        """Render a dropdown populated from the plugin registry.

        When the user selects a plugin, a sub-form is rendered below the
        dropdown showing the plugin-specific config fields (excluding
        fields already present on the parent model).
        """
        from panther.webapp.components.forms.pydantic_form import (
            FieldBinding,
            FormConfig,
            PydanticForm,
        )

        label = name.replace("_", " ").title()
        plugin_type = extra.get("plugin_type", "")

        from panther.webapp.components.forms.plugin_forms import (
            get_plugin_form_info,
            list_available_plugins,
        )

        plugins = list_available_plugins(plugin_type=plugin_type)
        options = [p["name"] for p in plugins]
        val = default if default in options else (options[0] if options else "")

        # Track the plugin sub-form
        sub_form_ref: dict[str, PydanticForm | None] = {"form": None}
        parent_fields = set(self._model_cls.model_fields.keys())

        def _load_plugin_form(plugin_name):
            sub_container.clear()
            sub_form_ref["form"] = None
            if not plugin_name:
                return
            info = get_plugin_form_info(plugin_name)
            if info is None or info.config_model is None:
                return
            sub_config = FormConfig(
                exclude_fields=frozenset(parent_fields),
                css_prefix=self._prefix,
            )
            with sub_container:
                sub_form_ref["form"] = PydanticForm(
                    info.config_model, config=sub_config
                )

        with ui.column().classes(f"w-full {self._prefix}-field"):
            with ui.row().classes("w-full items-center"):
                sel = ui.select(
                    options,
                    value=val,
                    label=label,
                    on_change=lambda e: _load_plugin_form(e.value),
                ).classes(f"flex-grow {self._prefix}-field-enum")
                if field_info.description:
                    sel.tooltip(field_info.description)
            sub_container = ui.column().classes("w-full q-pl-md")

        if val:
            _load_plugin_form(val)

        def _type_setter(v):
            sel.value = v
            _load_plugin_form(v)

        self._field_bindings[name] = FieldBinding(
            getter=lambda s=sel: s.value,
            setter=_type_setter,
            field_type="scalar",
        )
        self._plugin_sub_forms[name] = sub_form_ref

    # ── Nested model renderers ───────────────────────────────────────

    def _render_nested_model(self, name, model_cls, field_info, default):
        """Render a required nested BaseModel as a recursive sub-form."""
        from panther.webapp.components.forms.pydantic_form import (
            FieldBinding,
            PydanticForm,
        )

        label = name.replace("_", " ").title()
        initial = (
            default
            if isinstance(default, dict)
            else (default.model_dump() if isinstance(default, BaseModel) else None)
        )
        style = self._config.section_style

        if style == "card":
            with ui.card().classes(f"w-full q-pa-sm {self._prefix}-section"):
                ui.label(label).classes("text-subtitle2")
                sub = PydanticForm(model_cls, instance=initial, config=self._config)
        elif style == "flat":
            with ui.column().classes(f"w-full q-pl-md {self._prefix}-section"):
                ui.label(label).classes("text-subtitle2 text-grey-8")
                ui.separator().classes("q-my-xs")
                sub = PydanticForm(model_cls, instance=initial, config=self._config)
        else:  # expansion (default)
            with ui.expansion(label, icon="settings").classes(
                f"w-full {self._prefix}-section"
            ):
                sub = PydanticForm(model_cls, instance=initial, config=self._config)

        self._field_bindings[name] = FieldBinding(
            getter=lambda s=sub: s.get_value(),
            setter=lambda v, s=sub: s.set_value(v) if isinstance(v, dict) else None,
            field_type="nested",
            sub_form=sub,
        )

    def _render_optional_model(self, name, model_cls, field_info, default):
        """Render an Optional[BaseModel] field with an enable/disable toggle."""
        from panther.webapp.components.forms.pydantic_form import (
            FieldBinding,
            PydanticForm,
        )

        label = name.replace("_", " ").title()
        has_value = default is not None
        initial = (
            default
            if isinstance(default, dict)
            else (default.model_dump() if isinstance(default, BaseModel) else None)
        )

        sub_form_ref: dict[str, PydanticForm | None] = {"form": None}
        _pending_value: list[dict] = []

        with ui.column().classes(f"w-full {self._prefix}-section"):
            # Toggle FIRST — correct DOM order (above sub-container)
            toggle = ui.switch(
                f"Enable {label}",
                value=has_value,
            ).classes(f"{self._prefix}-field-bool")

            # Sub-container AFTER toggle
            sub_container = ui.column().classes("w-full")

            def _create_sub_form():
                """Create sub-form, clearing any previous one."""
                for child in list(sub_container):
                    child.delete()
                sub_container.clear()
                sub_form_ref["form"] = None
                sub_container.set_visibility(True)
                with sub_container:
                    sub_form_ref["form"] = PydanticForm(
                        model_cls, instance=initial, config=self._config
                    )
                # Apply any pending value stored by _setter
                if _pending_value:
                    sub_form_ref["form"].set_value(_pending_value.pop())

            def _destroy_sub_form():
                """Remove sub-form and hide container."""
                for child in list(sub_container):
                    child.delete()
                sub_container.clear()
                sub_form_ref["form"] = None
                sub_container.set_visibility(False)

            def _on_toggle(e):
                if e.value:
                    _create_sub_form()
                else:
                    _destroy_sub_form()

            # Initial state — go through the same path that the toggle uses
            if has_value:
                _create_sub_form()
            else:
                sub_container.set_visibility(False)

            # Register toggle handler AFTER initial rendering to avoid double-fire
            toggle.on_value_change(_on_toggle)

        def _getter():
            f = sub_form_ref["form"]
            return f.get_value() if f is not None else None

        def _setter(v):
            if v is not None and isinstance(v, dict):
                _pending_value.clear()
                _pending_value.append(v)
                toggle.value = True
                # If toggle callback fired synchronously, _pending_value was
                # consumed by _create_sub_form. If form already existed and
                # callback didn't fire, apply directly.
                f = sub_form_ref["form"]
                if f is not None and _pending_value:
                    f.set_value(_pending_value.pop())
            else:
                _pending_value.clear()
                toggle.value = False

        self._field_bindings[name] = FieldBinding(
            getter=_getter,
            setter=_setter,
            field_type="nested",
            sub_form=None,  # managed via ref
        )
