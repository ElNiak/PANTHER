"""FormModels — type introspection utilities for Pydantic config models.

Provides field classification helpers used by ``PydanticForm`` and the
Dict/List widget layer (``dict_list_widgets``) within the PANTHER
(Protocol ANalysis and Testing Harness for Extensible Research) web
dashboard to detect complex field types that need special rendering.

The core workflow is:

1. ``classify_complex_field(annotation)`` inspects a type annotation and
   returns a category string (``"dict_str"``, ``"dict_model"``,
   ``"list_model"``) or ``None`` for types that ``PydanticForm`` handles
   inline.
2. ``get_complex_fields(model_cls)`` iterates all model fields, calls
   ``classify_complex_field`` on each, and returns a dict mapping field
   names to ``ComplexFieldInfo`` tuples.
3. ``PydanticForm._render()`` uses that dict to decide whether to
   delegate a field to ``create_widget_for_field()`` (complex) or render
   it directly (scalar / nested model / enum / literal).

Additional helpers:

* ``_extract_inner_type(annotation)`` — pulls the value type from
  ``Dict[K, V]`` or the element type from ``List[E]``.
* ``extract_section_data(config_dict, section_path)`` — navigates a
  nested dict/list by dot-separated path (e.g. ``"tests.0.services"``).
"""

from __future__ import annotations

import logging
from typing import Any, Literal, NamedTuple, Union, get_args, get_origin

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ComplexFieldInfo(NamedTuple):
    """Metadata for a Pydantic field that needs a custom widget.

    Produced by ``get_complex_fields()`` and consumed by
    ``create_widget_for_field()`` to instantiate the correct editor.

    Attributes:
        category: Widget category — one of ``"dict_str"``,
            ``"dict_model"``, or ``"list_model"``.
        annotation: The raw Python type annotation from the Pydantic
            field (e.g. ``Dict[str, ServiceConfig]``).
        value_type: The extracted inner type — the dict value type or
            list element type (e.g. ``ServiceConfig``, ``str``).
        description: Human-readable description from
            ``Field(description=...)``.
        json_schema_extra: Pass-through of ``Field(json_schema_extra=...)``
            metadata (e.g. ``{"key_generator": "service_name"}``).
    """

    category: Literal["dict_str", "dict_model", "list_model"]
    annotation: Any  # raw type annotation
    value_type: type  # inner type (str, ServiceConfig, etc.)
    description: str  # from Pydantic Field
    json_schema_extra: dict | None = None  # pass-through from Pydantic Field


# ── UI metadata for GlobalConfig sections ────────────────────────────

GLOBAL_SECTION_META: dict[str, tuple[str, str]] = {
    "logging": ("description", "Global log level and format settings."),
    "paths": ("folder", "Output, log, and plugin directory paths."),
    "docker": ("dns", "Build flags, Buildx, and user mapping configuration."),
    "progress": ("hourglass_top", "Progress bar and spinner display options."),
    "fast_fail": ("flash_on", "Stop execution early on critical failures."),
    "metrics": ("monitor_heart", "System metrics collection and export."),
    "observers": ("visibility", "Observer pipeline configurations."),
}


# ── Public API ───────────────────────────────────────────────────────


def classify_complex_field(annotation) -> str | None:
    """Classify a type annotation into a custom-widget category.

    Recursively unwraps ``Optional[T]`` before inspecting the core type.

    Args:
        annotation: A Python type annotation (e.g. ``Dict[str, str]``,
            ``Optional[List[ServiceConfig]]``).

    Returns:
        ``"dict_str"`` for ``Dict[str, str]`` / ``Dict[str, Any]``,
        ``"dict_model"`` for ``Dict[str, BaseModel]``,
        ``"list_model"`` for ``List[BaseModel]``,
        ``None`` for types handled inline by ``PydanticForm``.
    """
    origin = get_origin(annotation)

    # Unwrap Optional[T]
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return classify_complex_field(args[0])
        return None

    if origin is dict:
        args = get_args(annotation)
        if len(args) == 2:
            value_type = args[1]
            if isinstance(value_type, type) and issubclass(value_type, BaseModel):
                return "dict_model"
        return "dict_str"

    if origin is list:
        args = get_args(annotation)
        if args:
            elem = args[0]
            if isinstance(elem, type) and issubclass(elem, BaseModel):
                return "list_model"
        return None

    return None


def get_complex_fields(model_cls: type[BaseModel]) -> dict[str, ComplexFieldInfo]:
    """Return fields that need custom widgets.

    Iterates all fields of *model_cls*, classifies each annotation, and
    returns a mapping of field names to ``ComplexFieldInfo`` for every
    ``Dict`` or ``List[BaseModel]`` field.

    Args:
        model_cls: A Pydantic ``BaseModel`` subclass to inspect.

    Returns:
        A dict mapping field names to ``ComplexFieldInfo`` tuples.
        Fields with ``None`` classification are excluded.
    """
    result: dict[str, ComplexFieldInfo] = {}
    for name, field_info in model_cls.model_fields.items():
        category = classify_complex_field(field_info.annotation)
        if category is None:
            continue
        value_type = _extract_inner_type(field_info.annotation)
        extra = (
            field_info.json_schema_extra
            if isinstance(field_info.json_schema_extra, dict)
            else None
        )
        result[name] = ComplexFieldInfo(
            category=category,
            annotation=field_info.annotation,
            value_type=value_type,
            description=field_info.description or "",
            json_schema_extra=extra,
        )
    return result


def _extract_inner_type(annotation) -> type:
    """Extract the value/element type from a Dict or List annotation."""
    origin = get_origin(annotation)

    # Unwrap Optional
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return _extract_inner_type(args[0])

    if origin is dict:
        args = get_args(annotation)
        if len(args) == 2:
            return args[1]
        return str

    if origin is list:
        args = get_args(annotation)
        if args:
            return args[0]
        return str

    return str


def extract_section_data(config_dict: dict, section_path: str) -> Any | None:
    """Extract a nested section from a config dict using dot notation.

    Navigates dicts by key and lists by integer index.  For example,
    ``"tests.0.services"`` resolves to ``cfg["tests"][0]["services"]``.

    Args:
        config_dict: The root configuration dictionary.
        section_path: Dot-separated path to the desired section
            (e.g. ``"tests.0.network_environment"``).

    Returns:
        The value at the specified path, or ``None`` if any segment
        along the path does not exist.
    """
    current: Any = config_dict
    for part in section_path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current
