"""Type introspection utilities for Pydantic config models.

Provides field classification helpers used by ``PydanticForm`` and the
Dict/List widget layer to detect complex field types that need special
rendering (Dict, List[BaseModel]).
"""

from __future__ import annotations

import logging
from typing import Any, NamedTuple, Union, get_args, get_origin

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ComplexFieldInfo(NamedTuple):
    """Metadata for a field that needs a custom widget."""

    category: str  # "dict_str" | "dict_model" | "list_model"
    annotation: Any  # raw type annotation
    value_type: type  # inner type (str, ServiceConfig, etc.)
    description: str  # from Pydantic Field


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

    Returns:
        ``"dict_str"`` for Dict[str, str] / Dict[str, Any],
        ``"dict_model"`` for Dict[str, BaseModel],
        ``"list_model"`` for List[BaseModel],
        ``None`` for types handled inline by PydanticForm.
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

    Maps field_name -> ComplexFieldInfo for each Dict or List[BaseModel] field.
    """
    result: dict[str, ComplexFieldInfo] = {}
    for name, field_info in model_cls.model_fields.items():
        category = classify_complex_field(field_info.annotation)
        if category is None:
            continue
        value_type = _extract_inner_type(field_info.annotation)
        result[name] = ComplexFieldInfo(
            category=category,
            annotation=field_info.annotation,
            value_type=value_type,
            description=field_info.description or "",
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
    """Extract nested section using dot notation.

    E.g. ``'tests.0.services'`` -> ``cfg['tests'][0]['services']``.
    Returns ``None`` if the path doesn't exist.
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
