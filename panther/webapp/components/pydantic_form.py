"""Recursive Pydantic-to-NiceGUI form component.

Renders any ``BaseModel`` as editable NiceGUI widgets.  Designed to be
**embeddable**: it renders into whatever NiceGUI container is currently
active (expansion panel, sidebar, dialog card, etc.).

Three-layer architecture:

1. **PydanticForm** — type-dispatch logic (this file)
2. **FormConfig** — structural layout options (grouping, advanced toggle, section style)
3. **CSS classes** — every widget gets ``.{prefix}-*`` classes for visual theming
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Literal, Union, get_args, get_origin

from nicegui import ui
from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined

from panther.webapp.components.dict_list_widgets import create_widget_for_field
from panther.webapp.utils.form_models import (
    ComplexFieldInfo,
    _extract_inner_type,
    classify_complex_field,
    get_complex_fields,
)

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────────


@dataclass
class FormConfig:
    """Layout configuration for PydanticForm rendering.

    Change these values to adjust form structure without touching
    renderer code.  Visual styling is done via CSS classes.
    """

    show_advanced: bool = False
    """Show fields marked ``json_schema_extra["advanced"] = True``."""

    group_by_category: bool = True
    """Group fields by ``json_schema_extra["category"]``."""

    section_style: Literal["expansion", "card", "flat"] = "expansion"
    """How nested BaseModel sections render."""

    css_prefix: str = "pf"
    """CSS class prefix — all elements get ``{prefix}-*`` classes."""

    exclude_fields: frozenset[str] = frozenset()
    """Field names to skip when rendering (used for plugin sub-forms)."""


# ── Internal binding ─────────────────────────────────────────────────


@dataclass
class FieldBinding:
    """Stores getter/setter for a single form field."""

    getter: Callable[[], Any]
    setter: Callable[[Any], None]
    field_type: str  # "scalar" | "nested" | "complex"
    sub_form: PydanticForm | None = None
    widget: Any | None = None


# ── Main component ───────────────────────────────────────────────────


class PydanticForm:
    """Render a Pydantic BaseModel as NiceGUI form elements.

    Usage::

        with ui.card():
            form = PydanticForm(LoggingConfig)

        data = form.get_value()   # JSON-safe dict
        form.set_value(data)      # populate from dict
    """

    def __init__(  # noqa: D107
        self,
        model_cls: type[BaseModel],
        instance: BaseModel | dict | None = None,
        config: FormConfig | None = None,
    ) -> None:
        self._model_cls = model_cls
        self._config = config or FormConfig()
        self._field_bindings: dict[str, FieldBinding] = {}
        self._plugin_sub_forms: dict[str, dict[str, PydanticForm | None]] = {}
        self._prefix = self._config.css_prefix
        self.last_validation_error: ValidationError | None = None

        # Resolve initial data
        initial: dict[str, Any] = {}
        if isinstance(instance, BaseModel):
            initial = instance.model_dump()
        elif isinstance(instance, dict):
            initial = instance
        self._initial = initial

        # Render
        self._render()

    # ── Public API ───────────────────────────────────────────────────

    @property
    def model_cls(self) -> type[BaseModel]:
        """The Pydantic model class this form renders."""
        return self._model_cls

    def get_value(self) -> dict:
        """Collect current form values as a JSON-safe dict.

        Attempts to validate through the model class for clean
        serialisation.  Falls back to raw dict on validation failure.
        """
        raw: dict[str, Any] = {}
        for name, binding in self._field_bindings.items():
            if binding.field_type == "nested" and binding.sub_form is not None:
                raw[name] = binding.sub_form.get_value()
            elif binding.field_type == "complex" and binding.widget is not None:
                raw[name] = binding.widget.get_value()
            else:
                raw[name] = binding.getter()

        # Merge plugin sub-form values into raw dict
        for _field_name, ref in self._plugin_sub_forms.items():
            sub = ref.get("form")
            if sub is not None:
                raw.update(sub.get_value())

        try:
            validated = self._model_cls(**raw)
            self.last_validation_error = None
            return validated.model_dump(mode="json")
        except (ValidationError, ValueError) as exc:
            self.last_validation_error = (
                exc if isinstance(exc, ValidationError) else None
            )
            logger.warning(
                "Validation failed for %s, returning raw values: %s",
                self._model_cls.__name__,
                exc,
            )
            return raw

    def set_field_value(self, field_name: str, value: Any) -> None:
        """Set a single field's value by name."""
        binding = self._field_bindings.get(field_name)
        if binding:
            binding.setter(value)

    def set_value(self, data: dict) -> None:
        """Populate form widgets from a dict."""
        if not isinstance(data, dict):
            return
        for name, binding in self._field_bindings.items():
            if name not in data:
                continue
            value = data[name]
            if binding.field_type == "nested" and binding.sub_form is not None:
                if isinstance(value, dict):
                    binding.sub_form.set_value(value)
            elif binding.field_type == "complex" and binding.widget is not None:
                binding.widget.set_value(value)
            else:
                binding.setter(value)

        # Propagate to plugin sub-forms (they pick their own fields)
        for _field_name, ref in self._plugin_sub_forms.items():
            sub = ref.get("form")
            if sub is not None:
                sub.set_value(data)

    # ── Rendering ────────────────────────────────────────────────────

    def _render(self) -> None:
        """Render all fields into the currently active NiceGUI container."""
        model_fields = self._model_cls.model_fields
        complex_fields = get_complex_fields(self._model_cls)

        # Separate fields into categories
        categorised: dict[str, list[str]] = {}
        advanced_names: list[str] = []
        regular_names: list[str] = []

        for name, finfo in model_fields.items():
            if name in self._config.exclude_fields:
                continue
            extra = finfo.json_schema_extra or {}
            if (
                isinstance(extra, dict)
                and extra.get("advanced")
                and not self._config.show_advanced
            ):
                advanced_names.append(name)
                continue
            if (
                self._config.group_by_category
                and isinstance(extra, dict)
                and "category" in extra
            ):
                cat = extra["category"]
                categorised.setdefault(cat, []).append(name)
            else:
                regular_names.append(name)

        with ui.column().classes(f"w-full {self._prefix}-form"):
            # Render regular fields
            self._render_field_list(regular_names, model_fields, complex_fields)

            # Render categorised groups
            for cat, names in categorised.items():
                with ui.expansion(
                    cat.replace("_", " ").title(), icon="category"
                ).classes(f"w-full {self._prefix}-category-{cat}"):
                    self._render_field_list(names, model_fields, complex_fields)

            # Render advanced fields behind toggle
            if advanced_names:
                with ui.expansion("Advanced", icon="tune").classes(
                    f"w-full {self._prefix}-advanced"
                ):
                    self._render_field_list(
                        advanced_names, model_fields, complex_fields
                    )

    def _render_field_list(self, names, model_fields, complex_fields):
        """Render a list of field names."""
        for name in names:
            if name in complex_fields:
                info = complex_fields[name]
                initial_val = self._initial.get(name)
                widget = create_widget_for_field(name, info, initial_value=initial_val)
                self._field_bindings[name] = FieldBinding(
                    getter=widget.get_value,
                    setter=widget.set_value,
                    field_type="complex",
                    widget=widget,
                )
            else:
                finfo = model_fields[name]
                self._render_field(name, finfo)

    def _render_field(self, name: str, field_info) -> None:
        """Dispatch to the appropriate renderer based on type annotation."""
        annotation = field_info.annotation
        default = self._initial.get(name, field_info.default)
        if default is PydanticUndefined:
            default = None
        extra = field_info.json_schema_extra or {}

        # Specialized widget_type overrides (checked before type-based dispatch)
        if isinstance(extra, dict) and extra.get("widget_type") == "protocol_select":
            self._render_protocol_select(name, field_info, default)
            return

        if (
            isinstance(extra, dict)
            and extra.get("widget_type") == "implementation_select"
        ):
            self._render_implementation_select(name, field_info, default)
            return

        if isinstance(extra, dict) and extra.get("widget_type") == "plugin_select":
            self._render_plugin_select(name, field_info, default, extra)
            return

        if isinstance(extra, dict) and extra.get("widget_type") == "port":
            self._render_port(name, field_info, default, extra)
            return

        # Unwrap Optional[T]
        inner, is_optional = self._unwrap_optional(annotation)

        # Enum
        enum_cls = self._find_enum(inner)
        if enum_cls is not None:
            self._render_enum(name, enum_cls, field_info, default)
            return

        # Literal
        if get_origin(inner) is Literal:
            choices = list(get_args(inner))
            self._render_literal(name, choices, field_info, default)
            return

        # Nested BaseModel
        if isinstance(inner, type) and issubclass(inner, BaseModel):
            if is_optional:
                self._render_optional_model(name, inner, field_info, default)
            else:
                self._render_nested_model(name, inner, field_info, default)
            return

        # list[str] / list[int] / bare list
        if inner is list or get_origin(inner) is list:
            args = get_args(inner)
            elem = args[0] if args else str
            if not (isinstance(elem, type) and issubclass(elem, BaseModel)):
                self._render_list_scalar(name, field_info, default)
                return

        # Scalars
        if inner is bool or inner == bool:
            self._render_bool(name, field_info, default)
        elif inner is int or inner == int:
            self._render_number(name, field_info, default, step=1)
        elif inner is float or inner == float:
            self._render_number(name, field_info, default, step=0.1)
        else:
            self._render_str(name, field_info, default)

    # ── Scalar renderers ─────────────────────────────────────────────

    def _render_str(self, name, field_info, default):
        label = name.replace("_", " ").title()
        val = (
            default
            if isinstance(default, str)
            else (str(default) if default is not None else "")
        )
        with ui.row().classes(f"w-full items-center {self._prefix}-field"):
            inp = ui.input(label, value=val).classes(
                f"flex-grow {self._prefix}-field-str"
            )
            if field_info.description:
                inp.tooltip(field_info.description)
        self._field_bindings[name] = FieldBinding(
            getter=lambda i=inp: i.value,
            setter=lambda v, i=inp: setattr(i, "value", v if v is not None else ""),
            field_type="scalar",
        )

    def _render_number(self, name, field_info, default, step: int | float = 1):
        label = name.replace("_", " ").title()
        extra = field_info.json_schema_extra or {}
        metadata = field_info.metadata or []

        # Extract ge/le from Pydantic metadata
        kwargs: dict[str, Any] = {"step": step}
        min_val = None
        for m in metadata:
            if hasattr(m, "ge") and m.ge is not None:
                kwargs["min"] = m.ge
                min_val = m.ge
            if hasattr(m, "le") and m.le is not None:
                kwargs["max"] = m.le
            if hasattr(m, "gt") and m.gt is not None:
                kwargs["min"] = m.gt + step
                min_val = m.gt + step
            if hasattr(m, "lt") and m.lt is not None:
                kwargs["max"] = m.lt - step

        # Default: use provided default, else min constraint, else 0
        if isinstance(default, (int, float)):
            val = default
        elif min_val is not None:
            val = min_val
        else:
            val = 0

        with ui.row().classes(f"w-full items-center {self._prefix}-field"):
            inp = ui.number(label, value=val, **kwargs).classes(
                f"flex-grow {self._prefix}-field-number"
            )
            if isinstance(extra, dict) and "unit" in extra:
                ui.label(extra["unit"]).classes("text-caption text-grey-6")
            if field_info.description:
                inp.tooltip(field_info.description)

        self._field_bindings[name] = FieldBinding(
            getter=lambda i=inp: i.value,
            setter=lambda v, i=inp: setattr(i, "value", v if v is not None else 0),
            field_type="scalar",
        )

    def _render_bool(self, name, field_info, default):
        label = name.replace("_", " ").title()
        val = bool(default) if default is not None else False
        with ui.row().classes(f"w-full items-center {self._prefix}-field"):
            sw = ui.switch(label, value=val).classes(f"{self._prefix}-field-bool")
            if field_info.description:
                sw.tooltip(field_info.description)
        self._field_bindings[name] = FieldBinding(
            getter=lambda s=sw: s.value,
            setter=lambda v, s=sw: setattr(s, "value", bool(v)),
            field_type="scalar",
        )

    def _render_enum(self, name, enum_cls, field_info, default):
        label = name.replace("_", " ").title()
        options = [e.value for e in enum_cls]
        val = (
            default.value
            if isinstance(default, Enum)
            else (default if default in options else options[0])
        )
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

    def _render_literal(self, name, choices, field_info, default):
        label = name.replace("_", " ").title()
        val = default if default in choices else choices[0]
        with ui.row().classes(f"w-full items-center {self._prefix}-field"):
            sel = ui.select(choices, value=val, label=label).classes(
                f"flex-grow {self._prefix}-field-enum"
            )
            if field_info.description:
                sel.tooltip(field_info.description)
        self._field_bindings[name] = FieldBinding(
            getter=lambda s=sel: s.value,
            setter=lambda v, s=sel: setattr(s, "value", v),
            field_type="scalar",
        )

    def _render_list_scalar(self, name, field_info, default):
        label = name.replace("_", " ").title()
        items = default if isinstance(default, list) else []
        val = "\n".join(str(x) for x in items)
        with ui.column().classes(f"w-full {self._prefix}-field"):
            ui.label(label).classes(
                f"text-subtitle2 text-grey-8 {self._prefix}-field-label"
            )
            ta = (
                ui.textarea(value=val)
                .classes(f"w-full {self._prefix}-field-list")
                .props("rows=3")
            )
            if field_info.description:
                ta.tooltip(field_info.description)
        self._field_bindings[name] = FieldBinding(
            getter=lambda t=ta: [line for line in t.value.split("\n") if line.strip()],
            setter=lambda v, t=ta: setattr(
                t, "value", "\n".join(str(x) for x in v) if isinstance(v, list) else ""
            ),
            field_type="scalar",
        )

    def _render_port(self, name, field_info, default, extra):
        label = name.replace("_", " ").title()
        val = default if isinstance(default, int) else 0
        with ui.row().classes(f"w-full items-center {self._prefix}-field"):
            inp = ui.number(label, value=val, min=0, max=65535, step=1).classes(
                f"flex-grow {self._prefix}-field-number"
            )
            if field_info.description:
                inp.tooltip(field_info.description)
        self._field_bindings[name] = FieldBinding(
            getter=lambda i=inp: int(i.value) if i.value is not None else 0,
            setter=lambda v, i=inp: setattr(i, "value", v),
            field_type="scalar",
        )

    def _render_protocol_select(self, name, field_info, default):
        """Render a dropdown of available protocol names from the registry."""
        label = name.replace("_", " ").title()
        from panther.webapp.utils.plugin_forms import get_protocol_choices

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
        label = name.replace("_", " ").title()
        from panther.webapp.utils.plugin_forms import get_implementation_choices

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
        label = name.replace("_", " ").title()
        plugin_type = extra.get("plugin_type", "")

        from panther.webapp.utils.plugin_forms import (
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

            # Use on_value_change (post-creation)
            toggle.on_value_change(_on_toggle)

            # Initial state
            if has_value:
                with sub_container:
                    sub_form_ref["form"] = PydanticForm(
                        model_cls, instance=initial, config=self._config
                    )
            else:
                sub_container.set_visibility(False)

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

    # ── Type introspection helpers ───────────────────────────────────

    @staticmethod
    def _unwrap_optional(annotation) -> tuple[Any, bool]:
        """Unwrap ``Optional[T]`` → ``(T, True)``.  Non-optional → ``(annotation, False)``."""
        origin = get_origin(annotation)
        if origin is Union:
            args = get_args(annotation)
            non_none = [a for a in args if a is not type(None)]
            if len(non_none) == 1 and type(None) in args:
                return non_none[0], True
        return annotation, False

    @staticmethod
    def _find_enum(annotation) -> type[Enum] | None:
        """Return the Enum class if *annotation* is an Enum type, else None."""
        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return annotation
        return None
